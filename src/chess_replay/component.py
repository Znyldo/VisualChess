from __future__ import annotations

import base64
import json
from pathlib import Path

from .models import ParsedGame
from .replay_engine import build_board_snapshots
from .time_utils import format_clock, format_elapsed


def render_chess_replay_html(game: ParsedGame, project_root: Path) -> str:
    payload = _build_payload(game, project_root)
    payload_json = json.dumps(payload, ensure_ascii=False)
    board_markup = _build_board_markup()
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root {{
      --ink: #261d16;
      --muted: #6c5a49;
      --panel: rgba(251, 247, 240, 0.92);
      --accent: #8d5f3b;
      --accent-soft: #ead9c4;
      --light-square: #f4e7cf;
      --dark-square: #ac7a55;
      --glass-border: rgba(95, 72, 52, 0.14);
      --move-highlight: rgba(244, 193, 102, 0.52);
      --move-origin: rgba(141, 95, 59, 0.18);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.78), transparent 38%),
        linear-gradient(135deg, #f6f0e6 0%, #e8dccb 100%);
      color: var(--ink);
    }}

    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
      gap: 20px;
      min-height: 100vh;
      padding: 18px;
    }}

    .panel {{
      border: 1px solid rgba(110, 90, 70, 0.18);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: 0 22px 70px rgba(38, 29, 22, 0.12);
      backdrop-filter: blur(8px);
    }}

    .board-panel {{
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .player-strip {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}

    .player-card {{
      border-radius: 18px;
      padding: 14px 16px;
      display: grid;
      gap: 6px;
      border: 1px solid rgba(36, 29, 22, 0.14);
    }}

    .player-card.white {{
      background: linear-gradient(180deg, #fffdf8 0%, #f5ecdd 100%);
      color: #1d1713;
    }}

    .player-card.black {{
      background: linear-gradient(180deg, #3c322c 0%, #241d19 100%);
      color: #f7efe5;
    }}

    .player-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
    }}

    .player-name {{
      font-size: 1.1rem;
      font-weight: 700;
    }}

    .player-meta {{
      font-size: 0.82rem;
      opacity: 0.8;
    }}

    .clock {{
      font-size: 1.9rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.02em;
    }}

    .clock.running {{
      color: #c1782f;
    }}

    .board-shell {{
      position: relative;
      overflow: hidden;
      border-radius: 22px;
      padding: 16px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.55), transparent 40%),
        linear-gradient(160deg, #efe5d9 0%, #dfcebb 100%);
      border: 1px solid rgba(95, 72, 52, 0.15);
    }}

    .board-frame {{
      width: min(100%, 560px);
      aspect-ratio: 1 / 1;
      margin: 0 auto;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 18px 48px rgba(38, 29, 22, 0.18);
      border: 6px solid rgba(101, 70, 45, 0.58);
      background: #6d4b30;
    }}

    .board-grid {{
      display: grid;
      height: 100%;
      grid-template-columns: repeat(8, 1fr);
      grid-template-rows: repeat(8, 1fr);
      width: 100%;
    }}

    .square {{
      position: relative;
      display: flex;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}

    .square.light {{
      background: var(--light-square);
    }}

    .square.dark {{
      background: var(--dark-square);
    }}

    .square::after {{
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0;
      transition: opacity 140ms ease;
    }}

    .square.from::after {{
      opacity: 1;
      background: var(--move-origin);
    }}

    .square.to::after {{
      opacity: 1;
      background: var(--move-highlight);
      box-shadow: inset 0 0 0 3px rgba(118, 71, 29, 0.28);
    }}

    .piece-slot {{
      position: relative;
      z-index: 2;
      width: 92%;
      height: 92%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 160ms ease, opacity 160ms ease;
    }}

    .piece {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      user-select: none;
      -webkit-user-drag: none;
      filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.18));
    }}

    .coord {{
      position: absolute;
      z-index: 3;
      font-size: 0.72rem;
      font-weight: 700;
      opacity: 0.78;
      pointer-events: none;
    }}

    .coord.file {{
      right: 6px;
      bottom: 4px;
    }}

    .coord.rank {{
      left: 6px;
      top: 4px;
    }}

    .square.light .coord {{
      color: rgba(72, 50, 33, 0.72);
    }}

    .square.dark .coord {{
      color: rgba(255, 244, 231, 0.74);
    }}

    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}

    button, select {{
      appearance: none;
      border: 1px solid rgba(38, 29, 22, 0.14);
      border-radius: 999px;
      padding: 10px 16px;
      font: inherit;
      background: #fffaf4;
      color: var(--ink);
    }}

    button {{
      cursor: pointer;
      font-weight: 700;
      transition: transform 120ms ease, box-shadow 120ms ease;
    }}

    button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(38, 29, 22, 0.1);
    }}

    .primary {{
      background: linear-gradient(180deg, #9d6c43 0%, #815333 100%);
      color: #fffaf5;
      border-color: rgba(120, 74, 39, 0.4);
    }}

    .status-bar {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(255, 250, 244, 0.82);
      border: 1px solid rgba(95, 72, 52, 0.12);
      color: var(--muted);
    }}

    .status-strong {{
      color: var(--ink);
      font-weight: 700;
    }}

    .moves-panel {{
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}

    .summary-card {{
      padding: 16px;
      border-radius: 18px;
      background:
        linear-gradient(135deg, rgba(154, 109, 69, 0.12), transparent 52%),
        rgba(255, 251, 245, 0.92);
      border: 1px solid rgba(95, 72, 52, 0.12);
    }}

    .match-title {{
      margin: 0;
      font-size: 1.35rem;
    }}

    .meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}

    .pill {{
      border-radius: 999px;
      padding: 6px 10px;
      background: var(--accent-soft);
      color: #5c3d24;
      font-size: 0.88rem;
      font-weight: 700;
    }}

    .link-row {{
      margin-top: 12px;
      font-size: 0.92rem;
    }}

    .link-row a {{
      color: #7b4d2b;
      text-decoration: none;
    }}

    .move-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      overflow: auto;
      max-height: 620px;
      padding-right: 4px;
    }}

    .move-row {{
      display: grid;
      grid-template-columns: 48px 1fr 1fr;
      gap: 10px;
      align-items: stretch;
      border-radius: 16px;
      padding: 10px;
      background: rgba(255, 250, 244, 0.78);
      border: 1px solid rgba(95, 72, 52, 0.1);
      transition: border-color 140ms ease, transform 140ms ease, background 140ms ease;
    }}

    .move-row.active {{
      border-color: rgba(157, 108, 67, 0.55);
      background: rgba(232, 213, 191, 0.6);
      transform: translateX(-2px);
    }}

    .move-number {{
      font-weight: 700;
      color: var(--muted);
      padding-top: 8px;
      text-align: center;
    }}

    .move-cell {{
      border-radius: 12px;
      padding: 10px 12px;
      display: grid;
      gap: 6px;
      min-height: 64px;
      align-content: start;
    }}

    .move-cell.white {{
      background: rgba(255, 255, 255, 0.75);
    }}

    .move-cell.black {{
      background: rgba(52, 43, 38, 0.92);
      color: #f8efe5;
    }}

    .move-san {{
      font-weight: 700;
      font-size: 1rem;
    }}

    .move-time {{
      font-size: 0.84rem;
      opacity: 0.82;
    }}

    .empty {{
      opacity: 0.4;
    }}

    .footer-note {{
      font-size: 0.84rem;
      color: var(--muted);
      line-height: 1.45;
    }}

    @media (max-width: 980px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}

      .move-list {{
        max-height: none;
      }}

      .board-frame {{
        width: min(100%, 520px);
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <section class="panel board-panel">
      <div class="player-strip">
        <div class="player-card white">
          <div class="player-top">
            <div>
              <div class="player-name">{_escape_html(game.metadata.white)}</div>
              <div class="player-meta">Brancas · Elo {(_escape_html(game.metadata.white_elo) or "—")}</div>
            </div>
            <div class="pill">{_escape_html(game.metadata.result)}</div>
          </div>
          <div id="white-clock" class="clock">{format_clock(game.initial_seconds)}</div>
        </div>
        <div class="player-card black">
          <div class="player-top">
            <div>
              <div class="player-name">{_escape_html(game.metadata.black)}</div>
              <div class="player-meta">Pretas · Elo {(_escape_html(game.metadata.black_elo) or "—")}</div>
            </div>
            <div class="pill">{_escape_html(game.metadata.time_control)}</div>
          </div>
          <div id="black-clock" class="clock">{format_clock(game.initial_seconds)}</div>
        </div>
      </div>

      <div class="board-shell">
        <div class="board-frame">
          <div id="board" class="board-grid">
            {board_markup}
          </div>
        </div>
      </div>

      <div class="controls">
        <button id="play-btn" class="primary">Play</button>
        <button id="pause-btn">Pause</button>
        <button id="restart-btn">Reiniciar</button>
        <select id="speed-select" aria-label="Velocidade da reprodução">
          <option value="1">Tempo real</option>
          <option value="2">2x</option>
          <option value="4">4x</option>
          <option value="8">8x</option>
        </select>
      </div>

      <div class="status-bar">
        <div id="status-text" class="status-strong">Pronto para reproduzir.</div>
        <div id="countdown-text">Aguardando início.</div>
      </div>
    </section>

    <aside class="panel moves-panel">
      <div class="summary-card">
        <h3 class="match-title">{_escape_html(game.metadata.white)} vs {_escape_html(game.metadata.black)}</h3>
        <div class="meta-row">
          <span class="pill">{_escape_html(game.metadata.result)}</span>
          <span class="pill">{_escape_html(game.metadata.event or "Live Chess")}</span>
          <span class="pill">{_escape_html(game.metadata.date)}</span>
          <span class="pill">{len(game.moves)} lances</span>
        </div>
        <div class="link-row">
          {_build_link_html(game.metadata.link)}
        </div>
      </div>

      <div id="move-list" class="move-list"></div>
      <div class="footer-note">
        O relógio usa o `[%timestamp]` do PGN do Chess.com, em décimos de segundo, combinado com o `[%clk]` exportado após cada lance.
      </div>
    </aside>
  </div>

  <script>
    const payload = {payload_json};
    const moveListNode = document.getElementById("move-list");
    const whiteClockNode = document.getElementById("white-clock");
    const blackClockNode = document.getElementById("black-clock");
    const statusNode = document.getElementById("status-text");
    const countdownNode = document.getElementById("countdown-text");
    const playButton = document.getElementById("play-btn");
    const pauseButton = document.getElementById("pause-btn");
    const restartButton = document.getElementById("restart-btn");
    const speedSelect = document.getElementById("speed-select");
    const squareRefs = {{}};

    document.querySelectorAll(".square").forEach((squareNode) => {{
      squareRefs[squareNode.dataset.square] = {{
        root: squareNode,
        slot: squareNode.querySelector(".piece-slot")
      }};
    }});

    const state = {{
      nextMoveIndex: 0,
      isPlaying: false,
      waitingMove: null,
      rafId: null,
      speedMultiplier: 1,
      liveClocks: {{
        white: payload.initial_seconds,
        black: payload.initial_seconds
      }}
    }};

    function formatClock(seconds) {{
      const safe = Math.max(Number(seconds) || 0, 0);
      const minutes = Math.floor(safe / 60);
      const remainder = safe - (minutes * 60);
      return `${{String(minutes).padStart(2, "0")}}:${{remainder.toFixed(1).padStart(4, "0")}}`;
    }}

    function formatElapsed(seconds) {{
      return `${{Number(seconds).toFixed(1)}}s`;
    }}

    function renderBoard(stateIndex) {{
      const snapshot = payload.snapshots[stateIndex];
      const lastMove = snapshot.last_move;
      Object.entries(squareRefs).forEach(([square, ref]) => {{
        const pieceCode = snapshot.pieces[square];
        ref.root.classList.toggle("from", Boolean(lastMove && lastMove.from_square === square));
        ref.root.classList.toggle("to", Boolean(lastMove && lastMove.to_square === square));
        ref.slot.innerHTML = pieceCode
          ? `<img class="piece" src="${{payload.piece_assets[pieceCode]}}" alt="${{pieceCode}}" />`
          : "";
      }});
    }}

    function renderMoveList() {{
      const rows = [];
      for (let index = 0; index < payload.moves.length; index += 2) {{
        const whiteMove = payload.moves[index];
        const blackMove = payload.moves[index + 1] || null;
        const active = state.nextMoveIndex === index || state.nextMoveIndex === index + 1;
        const blackCellHtml = blackMove
          ? `<div class="move-san">${{blackMove.san}}</div><div class="move-time">Pretas · ${{formatElapsed(blackMove.elapsed_seconds)}} · relógio ${{blackMove.clock_label}}</div>`
          : `<div class="move-san">—</div><div class="move-time">Sem resposta</div>`;
        rows.push(`
          <div class="move-row ${{active ? "active" : ""}}" id="move-row-${{whiteMove.move_number}}">
            <div class="move-number">${{whiteMove.move_number}}.</div>
            <div class="move-cell white">
              <div class="move-san">${{whiteMove.san}}</div>
              <div class="move-time">Brancas · ${{formatElapsed(whiteMove.elapsed_seconds)}} · relógio ${{whiteMove.clock_label}}</div>
            </div>
            <div class="move-cell black ${{blackMove ? "" : "empty"}}">
              ${{blackCellHtml}}
            </div>
          </div>
        `);
      }}
      moveListNode.innerHTML = rows.join("");
      const activeRow = document.querySelector(".move-row.active");
      if (activeRow) {{
        activeRow.scrollIntoView({{ block: "nearest", behavior: "smooth" }});
      }}
    }}

    function syncClockUi() {{
      whiteClockNode.textContent = formatClock(state.liveClocks.white);
      blackClockNode.textContent = formatClock(state.liveClocks.black);
      whiteClockNode.classList.toggle("running", state.waitingMove && state.waitingMove.move.color === "white");
      blackClockNode.classList.toggle("running", state.waitingMove && state.waitingMove.move.color === "black");
    }}

    function updateStatus(text, countdown = "Aguardando início.") {{
      statusNode.textContent = text;
      countdownNode.textContent = countdown;
    }}

    function currentSpeed() {{
      return state.speedMultiplier;
    }}

    function resetGame(playImmediately = false) {{
      if (state.rafId) {{
        cancelAnimationFrame(state.rafId);
      }}
      state.nextMoveIndex = 0;
      state.isPlaying = playImmediately;
      state.waitingMove = null;
      state.liveClocks.white = payload.initial_seconds;
      state.liveClocks.black = payload.initial_seconds;
      renderBoard(0);
      syncClockUi();
      renderMoveList();
      updateStatus("Pronto para reproduzir.", "Aguardando início.");
      if (playImmediately) {{
        queueNextMove();
        tick();
      }}
    }}

    function queueNextMove() {{
      if (state.nextMoveIndex >= payload.moves.length) {{
        state.isPlaying = false;
        state.waitingMove = null;
        updateStatus("Partida concluída.", `Resultado final: ${{payload.metadata.result}}.`);
        syncClockUi();
        renderMoveList();
        return;
      }}

      const move = payload.moves[state.nextMoveIndex];
      const mover = move.color;
      const before = state.liveClocks[mover];
      const beforeIncrementClock = Math.max(move.clock_seconds - payload.increment_seconds, 0);
      const remainingRealMs = Math.max(move.elapsed_seconds * 1000, 0);
      const durationMs = Math.max(remainingRealMs / currentSpeed(), 0);

      state.waitingMove = {{
        move,
        mover,
        before,
        beforeIncrementClock,
        remainingRealMs,
        durationMs,
        startedAt: performance.now()
      }};
      updateStatus(
        `${{move.color === "white" ? payload.metadata.white : payload.metadata.black}} pensando em ${{move.san}}.`,
        `Próximo lance em ~${{formatElapsed(move.elapsed_seconds / currentSpeed())}}.`
      );
      syncClockUi();
      renderMoveList();
    }}

    function applyMove(move) {{
      renderBoard(state.nextMoveIndex + 1);
      state.liveClocks[move.color] = move.clock_seconds;
      state.nextMoveIndex += 1;
      state.waitingMove = null;
      syncClockUi();
      renderMoveList();

      if (state.nextMoveIndex >= payload.moves.length) {{
        state.isPlaying = false;
        updateStatus("Partida concluída.", `Resultado final: ${{payload.metadata.result}}.`);
        return;
      }}

      const justPlayedBy = move.color === "white" ? payload.metadata.white : payload.metadata.black;
      const nextMove = payload.moves[state.nextMoveIndex];
      updateStatus(
        `Lance executado: ${{move.move_number}}${{move.color === "white" ? "." : "..."}} ${{move.san}} por ${{justPlayedBy}}.`,
        `Próximo: ${{nextMove.san}} em ${{nextMove.elapsed_label}}.`
      );
    }}

    function tick() {{
      if (!state.isPlaying) {{
        return;
      }}

      if (!state.waitingMove) {{
        queueNextMove();
        if (!state.isPlaying) {{
          return;
        }}
      }}

      const waiting = state.waitingMove;
      const elapsed = performance.now() - waiting.startedAt;
      const progress = waiting.durationMs <= 0 ? 1 : Math.min(elapsed / waiting.durationMs, 1);
      const currentClock = waiting.before + ((waiting.beforeIncrementClock - waiting.before) * progress);
      state.liveClocks[waiting.mover] = currentClock;
      syncClockUi();
      countdownNode.textContent = progress >= 1
        ? "Aplicando lance..."
        : `Próximo lance em ${{formatElapsed((waiting.durationMs - elapsed) / 1000)}}.`;

      if (progress >= 1) {{
        applyMove(waiting.move);
      }}

      state.rafId = requestAnimationFrame(tick);
    }}

    playButton.addEventListener("click", () => {{
      if (state.isPlaying) {{
        return;
      }}
      state.isPlaying = true;
      if (state.waitingMove) {{
        state.waitingMove.startedAt = performance.now();
        state.waitingMove.durationMs = Math.max(
          state.waitingMove.remainingRealMs / currentSpeed(),
          0
        );
      }}
      if (!state.waitingMove && state.nextMoveIndex === 0) {{
        updateStatus("Reprodução iniciada.", "Primeiro lance carregando...");
      }}
      tick();
    }});

    pauseButton.addEventListener("click", () => {{
      if (state.waitingMove) {{
        const elapsedPlaybackMs = performance.now() - state.waitingMove.startedAt;
        const remainingPlaybackMs = Math.max(state.waitingMove.durationMs - elapsedPlaybackMs, 0);
        state.waitingMove.remainingRealMs = remainingPlaybackMs * currentSpeed();
        state.waitingMove.before = state.liveClocks[state.waitingMove.mover];
        state.waitingMove.startedAt = null;
      }}
      state.isPlaying = false;
      if (state.rafId) {{
        cancelAnimationFrame(state.rafId);
      }}
      updateStatus("Reprodução pausada.", "Retome quando quiser.");
      syncClockUi();
    }});

    restartButton.addEventListener("click", () => {{
      resetGame(false);
    }});

    speedSelect.addEventListener("change", () => {{
      const previousSpeed = state.speedMultiplier;
      state.speedMultiplier = Number(speedSelect.value || "1");
      if (state.waitingMove) {{
        let remainingRealMs = state.waitingMove.remainingRealMs;
        if (state.isPlaying && state.waitingMove.startedAt !== null) {{
          const now = performance.now();
          const elapsed = now - state.waitingMove.startedAt;
          const remainingPlaybackMs = Math.max(state.waitingMove.durationMs - elapsed, 0);
          remainingRealMs = remainingPlaybackMs * previousSpeed;
          state.waitingMove.startedAt = now;
        }} else {{
          state.waitingMove.startedAt = null;
        }}
        state.waitingMove.before = state.liveClocks[state.waitingMove.mover];
        state.waitingMove.remainingRealMs = remainingRealMs;
        state.waitingMove.durationMs = remainingRealMs / currentSpeed();
      }}
    }});

    renderBoard(0);
    renderMoveList();
    syncClockUi();
    updateStatus("Pronto para reproduzir.", "Clique em Play para assistir no tempo real.");
  </script>
</body>
</html>
"""


def _build_payload(game: ParsedGame, project_root: Path) -> dict[str, object]:
    piece_assets = _load_piece_assets(project_root)
    snapshots = build_board_snapshots(game.moves)
    moves = []
    for move in game.moves:
        moves.append(
            {
                **move.to_dict(),
                "clock_label": format_clock(move.clock_seconds),
                "elapsed_label": format_elapsed(move.elapsed_seconds),
            }
        )

    return {
        "metadata": game.metadata.to_dict(),
        "initial_seconds": game.initial_seconds,
        "increment_seconds": game.increment_seconds,
        "moves": moves,
        "snapshots": [snapshot.to_dict() for snapshot in snapshots],
        "piece_assets": piece_assets,
    }


def _build_board_markup() -> str:
    squares: list[str] = []
    for rank in range(8, 0, -1):
        for file_index, file_name in enumerate("abcdefgh"):
            is_light = (file_index + rank) % 2 == 0
            classes = "square light" if is_light else "square dark"
            labels: list[str] = ['<div class="piece-slot"></div>']
            if file_name == "a":
                labels.append(f'<span class="coord rank">{rank}</span>')
            if rank == 1:
                labels.append(f'<span class="coord file">{file_name}</span>')
            label_markup = "".join(labels)
            squares.append(
                f'<div class="{classes}" data-square="{file_name}{rank}">{label_markup}</div>'
            )
    return "".join(squares)


def _load_piece_assets(project_root: Path) -> dict[str, str]:
    mapping = {
        "wK": "chess-white-king.png",
        "wQ": "chess-white-queen.png",
        "wR": "chess-white-rook.png",
        "wB": "chess-white-bishop.png",
        "wN": "chess-white-knight.png",
        "wP": "chess-white-pawn.png",
        "bK": "chess-black-king.png",
        "bQ": "chess-black-queen.png",
        "bR": "chess-black-rook.png",
        "bB": "chess-black-bishop.png",
        "bN": "chess-black-knight.png",
        "bP": "chess-black-pawn.png",
    }
    assets_dir = project_root / "assets" / "images"
    encoded: dict[str, str] = {}

    for key, filename in mapping.items():
        path = assets_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Peça não encontrada: {path}")
        encoded[key] = _file_to_data_uri(path)
    return encoded


def _file_to_data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _escape_html(value: str) -> str:
    value = value or ""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_link_html(link: str) -> str:
    if not link:
        return "Link original não disponível no PGN."
    safe_link = _escape_html(link)
    return f'<a href="{safe_link}" target="_blank" rel="noreferrer">Abrir partida original no Chess.com</a>'
