from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.chess_replay import PgnParseError, parse_chess_com_pgn, render_chess_replay_html

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_PGN_PATH = PROJECT_ROOT / "data_test" / "Znyldo_vs_llucsb_2026.04.14.pgn"
SUPPORTED_TIME_CONTROL = "120+1"
PGN_TEXT_PLACEHOLDER = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2026.04.14"]
[Round "?"]
[White "Znyldo"]
[Black "llucsb"]
[Result "1-0"]
[TimeControl "120+1"]

1. e4 {[%clk 0:01:59.5][%timestamp 15]} 1... e5 {[%clk 0:02:00.2][%timestamp 8]}"""


def main() -> None:
    st.set_page_config(
        page_title="Replay de Xadrez em Tempo Real",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Replay de partidas Chess.com no tempo real")
    st.caption(
        "Envie um arquivo `.pgn` ou cole o texto bruto do Chess.com com "
        "`TimeControl \"120+1\"` para assistir aos lances no tempo real em que foram jogados."
    )

    pasted_pgn = st.text_area(
        "Cole o texto do PGN",
        height=260,
        placeholder=PGN_TEXT_PLACEHOLDER,
        help=(
            "Use esta opção no celular ou quando não conseguir baixar/enviar o arquivo. "
            "O app limpa caracteres invisíveis comuns do texto copiado."
        ),
    )

    uploaded_file = st.file_uploader(
        "Arquivo PGN",
        type=["pgn"],
        help="O PGN precisa incluir os comentários `[%clk]` e `[%timestamp]` exportados pelo Chess.com.",
    )
    st.caption("Se os dois campos forem usados, o texto colado terá prioridade sobre o arquivo.")

    try:
        pgn_text, source_label = _resolve_pgn_source(uploaded_file, pasted_pgn)
    except UnicodeDecodeError:
        st.error("Não consegui decodificar o arquivo enviado em UTF-8.")
        st.stop()

    if pgn_text is None:
        if SAMPLE_PGN_PATH.exists():
            pgn_text = SAMPLE_PGN_PATH.read_text(encoding="utf-8")
            source_label = f"exemplo local: `{SAMPLE_PGN_PATH.name}`"
            st.info(
                "Nenhum PGN foi enviado ou colado. O app está usando o exemplo disponível em `data_test/`."
            )
        else:
            st.info("Envie um arquivo `.pgn` ou cole o texto do PGN para iniciar o replay.")
            st.stop()

    if not pgn_text.strip():
        st.info("O texto do PGN está vazio. Cole o conteúdo completo da partida para continuar.")
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


def _resolve_pgn_source(uploaded_file, pasted_pgn: str) -> tuple[str | None, str]:
    pasted_pgn = pasted_pgn.strip()
    if pasted_pgn:
        return pasted_pgn, "texto colado"

    if uploaded_file is not None:
        return uploaded_file.getvalue().decode("utf-8"), f"arquivo enviado: `{uploaded_file.name}`"

    return None, ""


if __name__ == "__main__":
    main()
