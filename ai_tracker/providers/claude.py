"""Claude Code: limite restante.

Fonte principal: endpoint OAuth usado pelo /usage (nao oficial), com o token local.
Fallback (token expirado, offline, erro HTTP, 429): estimativa a partir dos logs
~/.claude/projects/**/*.jsonl, calibrada pela ultima leitura boa:
    teto_de_tokens = tokens_na_janela / pct_real
Linhas estimadas ganham " ~" no rotulo.
"""
import glob, json, os, time, urllib.request, urllib.error
from datetime import datetime

CRED = os.path.expanduser("~/.claude/.credentials.json")
PROJECTS = os.path.expanduser("~/.claude/projects")
URL = "https://api.anthropic.com/api/oauth/usage"
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "cache_claude.json")
NAME = "Claude"
WIN5 = 5 * 3600
_cooldown_until = 0.0   # depois de um 429, nao insiste por 5 min
_last_calib = 0.0


class ProviderError(Exception):
    pass


def _token():
    try:
        with open(CRED, encoding="utf-8") as f:
            o = json.load(f)["claudeAiOauth"]
    except (OSError, KeyError, ValueError):
        raise ProviderError("sem login")
    exp = o.get("expiresAt")
    if exp and exp / 1000 < time.time():
        raise ProviderError("token expirado (abra o Claude Code)")
    return o["accessToken"]


def _iso(s):
    return datetime.fromisoformat(s).timestamp() if s else None


def _request():
    req = urllib.request.Request(URL, headers={
        "Authorization": "Bearer " + _token(),
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "ai-tracker/0.1",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise ProviderError("HTTP %d" % e.code)
    except (urllib.error.URLError, OSError, ValueError):
        raise ProviderError("offline")


# ---- tokens locais (para o fallback) ----
def _tokens_since(start):
    """Soma de tokens (entrada + saida + criacao de cache) desde `start` (epoch).
    As mensagens repetem o mesmo id em varias linhas: conta cada id uma vez."""
    seen, total = set(), 0
    for p in glob.glob(os.path.join(PROJECTS, "**", "*.jsonl"), recursive=True):
        try:
            if os.path.getmtime(p) < start:
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"usage"' not in line:
                        continue
                    try:
                        ev = json.loads(line)
                        msg = ev.get("message") or {}
                        u = msg.get("usage")
                        ts = ev.get("timestamp")
                        if not u or not ts or _iso(ts.replace("Z", "+00:00")) < start:
                            continue
                        mid = msg.get("id") or ev.get("uuid")
                        if mid in seen:
                            continue
                        seen.add(mid)
                        total += (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0) \
                            + (u.get("cache_creation_input_tokens") or 0)
                    except (ValueError, TypeError):
                        continue
        except OSError:
            continue
    return total


def _load():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(d):
    try:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except OSError:
        pass


def _calibrate(rows):
    """Guarda a ultima leitura boa e o teto de tokens da janela de 5h (a cada 5 min)."""
    global _last_calib
    cache = {"rows": rows, "ts": time.time()}
    old = _load()
    cache["cap"] = old.get("cap")
    sess = next((r for r in rows if r[3] == WIN5), None)
    if sess and sess[2] and sess[1] >= 3 and time.time() - _last_calib > 300:
        _last_calib = time.time()
        start = sess[2] - WIN5
        toks = _tokens_since(start)
        if toks > 0:
            cache["cap"] = toks / (sess[1] / 100.0)
    _save(cache)


def _fallback(reason):
    c = _load()
    if not c.get("rows"):
        raise ProviderError(reason)
    now, rows = time.time(), []
    for label, pct, reset, window in c["rows"]:
        if reset and reset < now:           # janela renovou desde a ultima leitura
            pct, reset = 0.0, None
        elif window == WIN5 and reset and c.get("cap"):
            toks = _tokens_since(reset - WIN5)
            pct = max(pct, min(100.0, toks / c["cap"] * 100))
        rows.append((label + " ~", pct, reset, window))
    return rows


def fetch():
    """Retorna lista de linhas: (rotulo, pct 0-100, reset_epoch, duracao_da_janela_s)."""
    global _cooldown_until
    if time.time() < _cooldown_until:
        return _fallback("limite de requisicoes")
    try:
        d = _request()
    except ProviderError as e:
        if "429" in str(e):
            _cooldown_until = time.time() + 300
        return _fallback(str(e))

    rows = []
    for key, label, window in (("five_hour", "Sessao 5h", WIN5),
                               ("seven_day", "Semana", 7 * 86400)):
        b = d.get(key)
        if b and b.get("utilization") is not None:
            rows.append((label, float(b["utilization"]), _iso(b.get("resets_at")), window))
    if not rows:
        return _fallback("sem dados")
    _calibrate(rows)
    return rows
