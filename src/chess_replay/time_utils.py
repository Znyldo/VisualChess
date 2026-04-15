from __future__ import annotations


def format_clock(seconds: float) -> str:
    safe_seconds = max(float(seconds), 0.0)
    minutes = int(safe_seconds // 60)
    remaining = safe_seconds - (minutes * 60)
    return f"{minutes:02d}:{remaining:04.1f}"


def format_elapsed(seconds: float) -> str:
    return f"{float(seconds):.1f}s"
