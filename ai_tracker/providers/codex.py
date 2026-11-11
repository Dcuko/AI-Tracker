"""Codex CLI: limite restante lido dos logs locais (~/.codex/sessions/**/rollout-*.jsonl).

Cada evento event_msg/token_count traz payload.rate_limits.{primary,secondary} com
used_percent, window_minutes e resets_at (epoch). Nao usa rede nem token.
"""
import json, os, time

NAME = "Codex"
HOME = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
SESSIONS = os.path.join(HOME, "sessions")
TAIL = 256 * 1024     # bytes lidos do fim de cada arquivo
MAX_FILES = 6         # quantos rollouts recentes tentar


class ProviderError(Exception):
    pass


def available():
    return os.path.isdir(SESSIONS)


def _recent_files():
    files = []
    for root, _dirs, names in os.walk(SESSIONS):
        for n in names:
            if n.startswith("rollout-") and n.endswith(".jsonl"):
                p = os.path.join(root, n)
                try:
                    files.append((os.path.getmtime(p), p))
                except OSError:
                    pass
    files.sort(reverse=True)
    return [p for _m, p in files[:MAX_FILES]]


def _tail_lines(path):
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - TAIL))
        data = f.read()
    lines = data.split(b"\n")
    return lines[1:] if size > TAIL else lines  # primeira linha pode estar cortada


def _latest_limits(path):
    """rate_limits do token_count mais recente do arquivo (ou None)."""
    for raw in reversed(_tail_lines(path)):
        if b"rate_limits" not in raw:
            continue
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        p = ev.get("payload") or {}
        rl = p.get("rate_limits")
        if p.get("type") == "token_count" and isinstance(rl, dict):
            lid = rl.get("limit_id")
            if lid in (None, "codex"):  # ignora buckets de outros modelos (ex.: Spark)
                return rl
    return None


def _label(window_min, fallback):
    if window_min == 300:
        return "Sessao 5h"
    if window_min == 10080:
        return "Semana"
    if window_min and window_min % 1440 == 0:
        return "%d dias" % (window_min // 1440)
    if window_min and window_min % 60 == 0:
        return "Janela %dh" % (window_min // 60)
    return fallback


def _row(w, fallback):
    if not isinstance(w, dict) or w.get("used_percent") is None:
        return None
    wm = w.get("window_minutes") or None
    reset = w.get("resets_at")
    if reset is None and w.get("resets_in_seconds") is not None:
        reset = time.time() + float(w["resets_in_seconds"])
    pct = float(w["used_percent"])
    if reset and reset < time.time():  # janela ja renovou: o valor do log esta velho
        pct, reset = 0.0, None
    return (_label(wm, fallback), pct, reset, wm * 60 if wm else None)


def fetch():
    """Retorna lista de linhas: (rotulo, pct 0-100, reset_epoch, duracao_da_janela_s)."""
    if not available():
        raise ProviderError("nao instalado")
    for path in _recent_files():
        try:
            rl = _latest_limits(path)
        except OSError:
            continue
        if rl:
            rows = [r for r in (_row(rl.get("primary"), "Principal"),
                                _row(rl.get("secondary"), "Secundario")) if r]
            if rows:
                rows.sort(key=lambda r: r[3] or 0)  # janela curta primeiro
                return rows
    raise ProviderError("sem dados (use o Codex uma vez)")
