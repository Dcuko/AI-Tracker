# AI Tracker

[Português](README.md) | **English**

A small, translucent, click-through overlay for Windows 11 that shows the **remaining subscription limit** of your coding AIs: Claude Code, Codex CLI and Antigravity.

It only needs the Python 3.11+ you already have. No `pip install`, no admin rights.

## Usage

```
pythonw tracker.pyw            # or double-click tracker.pyw
python autostart.py on         # start with Windows (off disables, status checks)
```

Run it from a terminal or by double-clicking, **not** with VS Code's F5 (that ties it to the debugger).

## Hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+Alt+A` | Show / hide |
| `Ctrl+Alt+N` | Switch the displayed AI (each one, then all) |
| `Ctrl+Alt+S` | Switch style (`card`, `compact`, `minimal`, `taskbar`) |
| `Ctrl+Alt+P` | Next corner; after the 4th corner, moves to the next monitor. Undoes a manual drag |
| `Ctrl+Alt+O` | Cycle opacity (35% to 100%) |
| `Ctrl+Alt+Q` | Quit |
| hold `Ctrl+Alt` + drag | Move the window (position is saved) |

All hotkeys and the drag key (`drag_key`) are configurable in `config.json`. If a hotkey is already taken by another program, the overlay says so in its own window.

## Styles

- **card**: full view, with a tab per AI, bars, a pace marker and time until reset.
- **compact**: one line per window (`5h`, `7d`), no reset text.
- **minimal**: numbers only, on one line: `Claude 32% · 5%   Codex 12% · 47%`.
- **taskbar**: a strip that fits inside the taskbar, next to the system tray (tune with `taskbar_gap_right` / `taskbar_gap_left`).

The **pace marker** (white tick on the bar) shows how much of the time window has already elapsed. If the bar is past the tick, you are spending faster than time passes.
Colors: green up to 60%, yellow up to 85%, red above.

## Where the data comes from

| AI | Source | Notes |
|---|---|---|
| **Claude Code** | The OAuth `/usage` endpoint (`api.anthropic.com`), using the local token in `~/.claude/.credentials.json` | Unofficial, may change. The token is only read and sent to Anthropic's domain. On failure it falls back to an **estimate** from the `~/.claude/projects` logs (rows labeled with `~`), calibrated by the last good reading |
| **Codex CLI** | Local logs `~/.codex/sessions/**/rollout-*.jsonl` (`rate_limits`) | No network or token. Shown only when Codex is installed. Confirmed with the real app (the free plan shows a single 30-day window) |
| **Antigravity** | The IDE's local `language_server.exe` (`GetUserStatus` on `127.0.0.1`) | Only talks to the local machine. Shown only while the IDE is open. Internal API, may change |

Each source is independent: if one breaks, the others keep working and the broken one shows a dash with the reason.

## Files

```
tracker.pyw              entry point
autostart.py             enables/disables start with Windows
config.json              settings (created on first run)
cache_claude.json        last Claude reading (used by the fallback)
ai_tracker/ui.py         window, styles, hotkeys, dragging
ai_tracker/collector.py  background polling
ai_tracker/providers/    claude.py, codex.py, antigravity.py
```

To add an AI: create `providers/<name>.py` with `NAME`, `fetch()` (returns rows `(label, % used, reset_epoch, window_seconds)`) and, optionally, `available()`; then add the name to `providers` in `config.json`.

## Known limitations

- The Claude and Antigravity endpoints are unofficial and may change without notice.
- On monitors with a different DPI than the primary one, the overlay size follows the primary monitor.
- The `taskbar` style only docks when the taskbar is at the bottom and visible; otherwise it falls back to a corner.
- Grok is not supported (no local log).
