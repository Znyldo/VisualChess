from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.chess_replay import PgnParseError, parse_chess_com_pgn, render_chess_replay_html

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_PGN_PATH = PROJECT_ROOT / "data_test" / "Znyldo_vs_llucsb_2026.04.14.pgn"
SUPPORTED_TIME_CONTROL = "120+1"


def main() -> None:
    st.set_page_config(
        page_title="Replay Chess",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Replay de partidas Chess.com no tempo real")
    st.caption(
        "Carregue um `.pgn` do Chess.com com `TimeControl \"120+1\"` para assistir "
        "aos lances no tempo real em que foram jogados."
    )

    uploaded_file = st.file_uploader(
        "Arquivo PGN",
        type=["pgn"],
        help="O PGN precisa incluir os comentários `[%clk]` e `[%timestamp]` exportados pelo Chess.com.",
    )

    pgn_text: str | None = None
    source_label = "arquivo enviado"

    if uploaded_file is not None:
        pgn_text = uploaded_file.getvalue().decode("utf-8")
    elif SAMPLE_PGN_PATH.exists():
        pgn_text = SAMPLE_PGN_PATH.read_text(encoding="utf-8")
        source_label = f"exemplo local: `{SAMPLE_PGN_PATH.name}`"
        st.info(
            "Nenhum arquivo enviado ainda. O app está usando o PGN de exemplo disponível em `data_test/`."
        )

    if not pgn_text:
        st.stop()

    try:
        game = parse_chess_com_pgn(pgn_text)
    except (UnicodeDecodeError, PgnParseError) as exc:
        st.error(str(exc))
        st.stop()

    if game.metadata.time_control != SUPPORTED_TIME_CONTROL:
        st.error(
            f'Este app aceita apenas partidas com `TimeControl "{SUPPORTED_TIME_CONTROL}"`. '
            f'O arquivo carregado trouxe `{game.metadata.time_control}`.'
        )
        st.stop()

    html = render_chess_replay_html(game, PROJECT_ROOT)
    st.caption(f"Fonte atual: {source_label}")
    components.html(html, height=980, scrolling=False)


if __name__ == "__main__":
    main()
