from __future__ import annotations

import re

from .models import GameMetadata, MoveRecord, ParsedGame

HEADER_RE = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
CLOCK_RE = re.compile(r"\[%clk\s+([0-9:.]+)\]")
TIMESTAMP_RE = re.compile(r"\[%timestamp\s+(\d+)\]")
RESULT_TOKENS = {"1-0", "0-1", "1/2-1/2", "*"}


class PgnParseError(ValueError):
    """Raised when a PGN cannot be parsed for real-time replay."""


def parse_chess_com_pgn(pgn_text: str) -> ParsedGame:
    headers, movetext = _split_headers_and_movetext(pgn_text)
    time_control = headers.get("TimeControl", "")
    initial_seconds, increment_seconds = _parse_time_control(time_control)
    mainline_text = _strip_variations(movetext)
    moves = _parse_moves(mainline_text)

    if not moves:
        raise PgnParseError("Nenhum lance principal foi encontrado no PGN.")

    metadata = GameMetadata(
        event=headers.get("Event", ""),
        site=headers.get("Site", ""),
        date=headers.get("Date", ""),
        white=headers.get("White", "Brancas"),
        black=headers.get("Black", "Pretas"),
        result=headers.get("Result", "*"),
        time_control=time_control,
        termination=headers.get("Termination", ""),
        end_time=headers.get("EndTime", ""),
        link=headers.get("Link", ""),
        eco=headers.get("ECO", ""),
        white_elo=headers.get("WhiteElo", ""),
        black_elo=headers.get("BlackElo", ""),
    )
    return ParsedGame(
        metadata=metadata,
        moves=moves,
        initial_seconds=initial_seconds,
        increment_seconds=increment_seconds,
        raw_pgn=pgn_text,
    )


def _split_headers_and_movetext(pgn_text: str) -> tuple[dict[str, str], str]:
    headers: dict[str, str] = {}
    movetext_lines: list[str] = []
    in_headers = True

    for line in pgn_text.splitlines():
        stripped = line.strip()
        if in_headers and stripped.startswith("["):
            match = HEADER_RE.match(stripped)
            if match:
                headers[match.group(1)] = match.group(2)
            continue
        if not stripped and in_headers:
            in_headers = False
            continue
        in_headers = False
        movetext_lines.append(line)

    movetext = "\n".join(movetext_lines).strip()
    if not headers:
        raise PgnParseError("Cabeçalhos do PGN não foram encontrados.")
    if not movetext:
        raise PgnParseError("Movetext do PGN está vazio.")
    return headers, movetext


def _parse_time_control(value: str) -> tuple[float, float]:
    match = re.fullmatch(r"(\d+)\+(\d+)", value.strip())
    if not match:
        raise PgnParseError(
            'O app aceita apenas PGNs com `TimeControl` no formato `"120+1"`.'
        )
    return float(match.group(1)), float(match.group(2))


def _strip_variations(text: str) -> str:
    result: list[str] = []
    depth = 0
    in_comment = False

    for char in text:
        if in_comment:
            if depth == 0:
                result.append(char)
            if char == "}":
                in_comment = False
            continue
        if char == "{":
            if depth == 0:
                result.append(char)
            in_comment = True
            continue
        if char == "(":
            depth += 1
            continue
        if char == ")" and depth > 0:
            depth -= 1
            continue
        if depth == 0:
            result.append(char)
    return "".join(result)


def _parse_moves(text: str) -> list[MoveRecord]:
    moves: list[MoveRecord] = []
    index = 0
    move_number = 1
    color = "white"

    while index < len(text):
        index = _skip_whitespace(text, index)
        if index >= len(text):
            break

        current_char = text[index]

        if current_char == "{":
            _, index = _consume_braced(text, index)
            continue

        if current_char == "$":
            index += 1
            while index < len(text) and text[index].isdigit():
                index += 1
            continue

        if current_char.isdigit():
            token, index = _consume_token(text, index)
            if token in RESULT_TOKENS:
                break
            if token.endswith("..."):
                move_number = int(token.split(".")[0])
                color = "black"
                continue
            if token.endswith("."):
                move_number = int(token.split(".")[0])
                color = "white"
                continue

        token, index = _consume_token(text, index)
        if not token or token == "...":
            continue
        if token in RESULT_TOKENS:
            break

        san = _normalize_san(token)
        index = _skip_whitespace(text, index)
        comment = ""
        if index < len(text) and text[index] == "{":
            comment, index = _consume_braced(text, index)

        clock_match = CLOCK_RE.search(comment)
        timestamp_match = TIMESTAMP_RE.search(comment)
        if not clock_match or not timestamp_match:
            raise PgnParseError(
                f"Não encontrei `[%clk]` e `[%timestamp]` no lance `{san}`."
            )

        moves.append(
            MoveRecord(
                ply_index=len(moves),
                move_number=move_number,
                color=color,
                san=san,
                clock_seconds=_parse_clock(clock_match.group(1)),
                elapsed_seconds=int(timestamp_match.group(1)) / 10.0,
                raw_comment=comment,
            )
        )

        if color == "white":
            color = "black"
        else:
            color = "white"
            move_number += 1

    return moves


def _skip_whitespace(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _consume_token(text: str, index: int) -> tuple[str, int]:
    start = index
    while index < len(text) and not text[index].isspace() and text[index] not in "{}":
        index += 1
    return text[start:index], index


def _consume_braced(text: str, index: int) -> tuple[str, int]:
    start = index
    depth = 0
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                index += 1
                break
        index += 1
    return text[start:index], index


def _normalize_san(token: str) -> str:
    token = token.strip()
    token = re.sub(r"[\!\?]+$", "", token)
    return token


def _parse_clock(value: str) -> float:
    parts = value.split(":")
    if len(parts) != 3:
        raise PgnParseError(f"Relógio inválido no comentário: `{value}`.")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds
