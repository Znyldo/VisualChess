from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass

from .models import MoveRecord
from .pgn_parser import PgnParseError

FILES = "abcdefgh"
RANKS = "12345678"
STARTING_BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]
SAN_RE = re.compile(
    r"^(?P<piece>[KQRBN])?"
    r"(?P<disambiguation>[a-h1-8]{0,2})"
    r"(?P<capture>x)?"
    r"(?P<target>[a-h][1-8])"
    r"(?P<promotion>=?[QRBN])?"
    r"(?P<suffix>[+#])?$"
)


@dataclass(frozen=True)
class ResolvedMove:
    from_square: str
    to_square: str
    san: str
    color: str
    piece: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class BoardSnapshot:
    pieces: dict[str, str]
    last_move: ResolvedMove | None

    def to_dict(self) -> dict[str, object]:
        return {
            "pieces": dict(sorted(self.pieces.items())),
            "last_move": self.last_move.to_dict() if self.last_move else None,
        }


@dataclass
class Position:
    pieces: dict[str, str]
    turn: str
    castling_rights: dict[str, dict[str, bool]]
    en_passant_target: str | None


def build_board_snapshots(moves: list[MoveRecord]) -> list[BoardSnapshot]:
    state = _initial_position()
    snapshots = [BoardSnapshot(pieces=copy.deepcopy(state.pieces), last_move=None)]

    for move in moves:
        resolved_move, state = _apply_san_move(state, move)
        snapshots.append(
            BoardSnapshot(
                pieces=copy.deepcopy(state.pieces),
                last_move=resolved_move,
            )
        )

    return snapshots


def _initial_position() -> Position:
    pieces: dict[str, str] = {}

    for index, file_name in enumerate(FILES):
        pieces[f"{file_name}1"] = f"w{STARTING_BACK_RANK[index]}"
        pieces[f"{file_name}2"] = "wP"
        pieces[f"{file_name}7"] = "bP"
        pieces[f"{file_name}8"] = f"b{STARTING_BACK_RANK[index]}"

    return Position(
        pieces=pieces,
        turn="white",
        castling_rights={
            "white": {"king_side": True, "queen_side": True},
            "black": {"king_side": True, "queen_side": True},
        },
        en_passant_target=None,
    )


def _apply_san_move(state: Position, move: MoveRecord) -> tuple[ResolvedMove, Position]:
    if move.color != state.turn:
        raise PgnParseError(
            f"Ordem de turno inválida no lance `{move.san}`. Esperava `{state.turn}`."
        )

    san = move.san.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    if san in {"O-O", "O-O+", "O-O#"}:
        return _apply_castling(state, move, king_side=True)
    if san in {"O-O-O", "O-O-O+", "O-O-O#"}:
        return _apply_castling(state, move, king_side=False)

    parsed = _parse_san(san)
    candidates: list[str] = []
    moving_piece_code = f"{_color_prefix(state.turn)}{parsed['piece_type']}"

    for square, piece in state.pieces.items():
        if piece != moving_piece_code:
            continue
        if not _matches_disambiguation(square, parsed["source_file"], parsed["source_rank"]):
            continue
        if not _can_piece_reach(
            state,
            square,
            parsed["target"],
            state.turn,
            parsed["piece_type"],
            parsed["is_capture"],
        ):
            continue
        if _would_leave_king_in_check(
            state,
            from_square=square,
            to_square=parsed["target"],
            promotion=parsed["promotion"],
        ):
            continue
        candidates.append(square)

    if len(candidates) != 1:
        raise PgnParseError(
            f"Lance ambíguo ou inválido `{move.san}`. Candidatos encontrados: {candidates or 'nenhum'}."
        )

    from_square = candidates[0]
    new_state = _simulate_move(
        state,
        from_square=from_square,
        to_square=parsed["target"],
        promotion=parsed["promotion"],
    )
    resolved = ResolvedMove(
        from_square=from_square,
        to_square=parsed["target"],
        san=move.san,
        color=move.color,
        piece=parsed["piece_type"],
    )
    return resolved, new_state


def _apply_castling(
    state: Position,
    move: MoveRecord,
    *,
    king_side: bool,
) -> tuple[ResolvedMove, Position]:
    color = state.turn
    rank = "1" if color == "white" else "8"
    king_from = f"e{rank}"
    king_to = f"g{rank}" if king_side else f"c{rank}"
    rook_from = f"h{rank}" if king_side else f"a{rank}"
    rook_to = f"f{rank}" if king_side else f"d{rank}"
    side_key = "king_side" if king_side else "queen_side"

    if not state.castling_rights[color][side_key]:
        raise PgnParseError(f"Roque inválido `{move.san}`: direito de roque indisponível.")
    if state.pieces.get(king_from) != f"{_color_prefix(color)}K":
        raise PgnParseError(f"Roque inválido `{move.san}`: rei ausente em {king_from}.")
    if state.pieces.get(rook_from) != f"{_color_prefix(color)}R":
        raise PgnParseError(f"Roque inválido `{move.san}`: torre ausente em {rook_from}.")

    between = ["f", "g"] if king_side else ["b", "c", "d"]
    for file_name in between:
        if f"{file_name}{rank}" in state.pieces:
            raise PgnParseError(f"Roque inválido `{move.san}`: caminho bloqueado.")

    if _is_square_attacked(state, king_from, _opponent(color)):
        raise PgnParseError(f"Roque inválido `{move.san}`: rei está em xeque.")

    transit = [f"f{rank}", king_to] if king_side else [f"d{rank}", king_to]
    for square in transit:
        simulated = _simulate_move(state, from_square=king_from, to_square=square, promotion=None)
        if _is_square_attacked(simulated, square, _opponent(color)):
            raise PgnParseError(f"Roque inválido `{move.san}`: rei atravessa casa atacada.")

    new_state = copy.deepcopy(state)
    king_piece = new_state.pieces.pop(king_from)
    rook_piece = new_state.pieces.pop(rook_from)
    new_state.pieces[king_to] = king_piece
    new_state.pieces[rook_to] = rook_piece
    new_state.castling_rights[color]["king_side"] = False
    new_state.castling_rights[color]["queen_side"] = False
    new_state.en_passant_target = None
    new_state.turn = _opponent(color)

    return (
        ResolvedMove(
            from_square=king_from,
            to_square=king_to,
            san=move.san,
            color=color,
            piece="K",
        ),
        new_state,
    )


def _parse_san(san: str) -> dict[str, object]:
    match = SAN_RE.fullmatch(san)
    if not match:
        raise PgnParseError(f"Lance SAN não suportado: `{san}`.")

    disambiguation = match.group("disambiguation") or ""
    source_file = ""
    source_rank = ""

    if len(disambiguation) == 1:
        if disambiguation in FILES:
            source_file = disambiguation
        else:
            source_rank = disambiguation
    elif len(disambiguation) == 2:
        source_file = disambiguation[0]
        source_rank = disambiguation[1]

    promotion = match.group("promotion") or ""
    promotion = promotion.replace("=", "") or None

    return {
        "piece_type": match.group("piece") or "P",
        "source_file": source_file,
        "source_rank": source_rank,
        "is_capture": bool(match.group("capture")),
        "target": match.group("target"),
        "promotion": promotion,
    }


def _matches_disambiguation(square: str, source_file: str, source_rank: str) -> bool:
    if source_file and square[0] != source_file:
        return False
    if source_rank and square[1] != source_rank:
        return False
    return True


def _can_piece_reach(
    state: Position,
    from_square: str,
    to_square: str,
    color: str,
    piece_type: str,
    is_capture: bool,
) -> bool:
    if from_square == to_square:
        return False

    target_piece = state.pieces.get(to_square)
    if target_piece and _piece_color(target_piece) == color:
        return False
    if is_capture and not target_piece and not _is_en_passant_capture(
        state, from_square, to_square, piece_type, color
    ):
        return False
    if not is_capture and target_piece:
        return False

    from_x, from_y = _square_to_coords(from_square)
    to_x, to_y = _square_to_coords(to_square)
    dx = to_x - from_x
    dy = to_y - from_y

    if piece_type == "N":
        return (abs(dx), abs(dy)) in {(1, 2), (2, 1)}
    if piece_type == "K":
        return max(abs(dx), abs(dy)) == 1
    if piece_type == "B":
        return abs(dx) == abs(dy) and _path_is_clear(state.pieces, from_square, to_square)
    if piece_type == "R":
        return (dx == 0 or dy == 0) and _path_is_clear(state.pieces, from_square, to_square)
    if piece_type == "Q":
        straight = dx == 0 or dy == 0
        diagonal = abs(dx) == abs(dy)
        return (straight or diagonal) and _path_is_clear(state.pieces, from_square, to_square)
    if piece_type == "P":
        direction = 1 if color == "white" else -1
        start_rank = "2" if color == "white" else "7"
        if is_capture:
            return abs(dx) == 1 and dy == direction
        if dx != 0:
            return False
        if dy == direction:
            return to_square not in state.pieces
        if dy == 2 * direction and from_square[1] == start_rank:
            intermediate = _coords_to_square(from_x, from_y + direction)
            return intermediate not in state.pieces and to_square not in state.pieces
        return False
    return False


def _path_is_clear(pieces: dict[str, str], from_square: str, to_square: str) -> bool:
    from_x, from_y = _square_to_coords(from_square)
    to_x, to_y = _square_to_coords(to_square)
    step_x = 0 if to_x == from_x else (1 if to_x > from_x else -1)
    step_y = 0 if to_y == from_y else (1 if to_y > from_y else -1)
    current_x = from_x + step_x
    current_y = from_y + step_y

    while (current_x, current_y) != (to_x, to_y):
        if _coords_to_square(current_x, current_y) in pieces:
            return False
        current_x += step_x
        current_y += step_y
    return True


def _would_leave_king_in_check(
    state: Position,
    *,
    from_square: str,
    to_square: str,
    promotion: str | None,
) -> bool:
    simulated = _simulate_move(
        state,
        from_square=from_square,
        to_square=to_square,
        promotion=promotion,
    )
    king_square = _find_king_square(simulated.pieces, state.turn)
    return _is_square_attacked(simulated, king_square, _opponent(state.turn))


def _simulate_move(
    state: Position,
    *,
    from_square: str,
    to_square: str,
    promotion: str | None,
) -> Position:
    new_state = copy.deepcopy(state)
    piece = new_state.pieces.pop(from_square)
    color = _piece_color(piece)
    piece_type = piece[1]

    if _is_en_passant_capture(state, from_square, to_square, piece_type, color):
        capture_square = f"{to_square[0]}{from_square[1]}"
        new_state.pieces.pop(capture_square, None)

    new_state.pieces.pop(to_square, None)

    if promotion:
        new_state.pieces[to_square] = f"{_color_prefix(color)}{promotion}"
    else:
        new_state.pieces[to_square] = piece

    _update_castling_rights_after_move(new_state, piece, from_square, to_square)

    if piece_type == "P" and abs(_square_to_coords(from_square)[1] - _square_to_coords(to_square)[1]) == 2:
        middle_rank = (_square_to_coords(from_square)[1] + _square_to_coords(to_square)[1]) // 2
        new_state.en_passant_target = _coords_to_square(_square_to_coords(from_square)[0], middle_rank)
    else:
        new_state.en_passant_target = None

    new_state.turn = _opponent(color)
    return new_state


def _update_castling_rights_after_move(
    state: Position,
    piece: str,
    from_square: str,
    to_square: str,
) -> None:
    color = _piece_color(piece)
    piece_type = piece[1]

    if piece_type == "K":
        state.castling_rights[color]["king_side"] = False
        state.castling_rights[color]["queen_side"] = False

    if piece_type == "R":
        if from_square == "a1":
            state.castling_rights["white"]["queen_side"] = False
        elif from_square == "h1":
            state.castling_rights["white"]["king_side"] = False
        elif from_square == "a8":
            state.castling_rights["black"]["queen_side"] = False
        elif from_square == "h8":
            state.castling_rights["black"]["king_side"] = False

    if to_square == "a1":
        state.castling_rights["white"]["queen_side"] = False
    elif to_square == "h1":
        state.castling_rights["white"]["king_side"] = False
    elif to_square == "a8":
        state.castling_rights["black"]["queen_side"] = False
    elif to_square == "h8":
        state.castling_rights["black"]["king_side"] = False


def _find_king_square(pieces: dict[str, str], color: str) -> str:
    target = f"{_color_prefix(color)}K"
    for square, piece in pieces.items():
        if piece == target:
            return square
    raise PgnParseError(f"Rei `{color}` não encontrado no tabuleiro.")


def _is_square_attacked(state: Position, square: str, by_color: str) -> bool:
    for from_square, piece in state.pieces.items():
        if _piece_color(piece) != by_color:
            continue
        if _attacks_square(state, from_square, square, piece):
            return True
    return False


def _attacks_square(state: Position, from_square: str, target_square: str, piece: str) -> bool:
    piece_type = piece[1]
    color = _piece_color(piece)
    from_x, from_y = _square_to_coords(from_square)
    to_x, to_y = _square_to_coords(target_square)
    dx = to_x - from_x
    dy = to_y - from_y

    if piece_type == "P":
        direction = 1 if color == "white" else -1
        return abs(dx) == 1 and dy == direction
    if piece_type == "N":
        return (abs(dx), abs(dy)) in {(1, 2), (2, 1)}
    if piece_type == "K":
        return max(abs(dx), abs(dy)) == 1
    if piece_type == "B":
        return abs(dx) == abs(dy) and _path_is_clear(state.pieces, from_square, target_square)
    if piece_type == "R":
        return (dx == 0 or dy == 0) and _path_is_clear(state.pieces, from_square, target_square)
    if piece_type == "Q":
        straight = dx == 0 or dy == 0
        diagonal = abs(dx) == abs(dy)
        return (straight or diagonal) and _path_is_clear(state.pieces, from_square, target_square)
    return False


def _is_en_passant_capture(
    state: Position,
    from_square: str,
    to_square: str,
    piece_type: str,
    color: str,
) -> bool:
    if piece_type != "P":
        return False
    if state.en_passant_target != to_square:
        return False
    from_x, from_y = _square_to_coords(from_square)
    to_x, to_y = _square_to_coords(to_square)
    direction = 1 if color == "white" else -1
    return abs(to_x - from_x) == 1 and (to_y - from_y) == direction


def _piece_color(piece: str) -> str:
    return "white" if piece.startswith("w") else "black"


def _color_prefix(color: str) -> str:
    return "w" if color == "white" else "b"


def _opponent(color: str) -> str:
    return "black" if color == "white" else "white"


def _square_to_coords(square: str) -> tuple[int, int]:
    return FILES.index(square[0]), RANKS.index(square[1])


def _coords_to_square(file_index: int, rank_index: int) -> str:
    return f"{FILES[file_index]}{RANKS[rank_index]}"
