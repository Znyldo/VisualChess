from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MoveRecord:
    ply_index: int
    move_number: int
    color: str
    san: str
    clock_seconds: float
    elapsed_seconds: float
    raw_comment: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GameMetadata:
    event: str
    site: str
    date: str
    white: str
    black: str
    result: str
    time_control: str
    termination: str
    end_time: str
    link: str
    eco: str
    white_elo: str
    black_elo: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedGame:
    metadata: GameMetadata
    moves: list[MoveRecord]
    initial_seconds: float
    increment_seconds: float
    raw_pgn: str

