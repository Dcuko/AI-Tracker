"""Antigravity (Google): cota por modelo, via o language server local da propria IDE.

A IDE sobe language_server.exe em portas locais aleatorias, protegido por um
csrf_token passado na linha de comando. O endpoint GetUserStatus (Connect/JSON)
devolve, por modelo, quotaInfo {remainingFraction, resetTime}. Nao usa a internet
nem credenciais do Google: so fala com 127.0.0.1. So existe com a IDE aberta
(sem ela o provider fica oculto). API interna e nao documentada: pode mudar.
"""
import json, re, subprocess, time, urllib.error, urllib.request
from datetime import datetime

NAME = "Antigravity"
PATH = "/exa.language_server_pb.LanguageServerService/GetUserStatus"
_PS = (
    "$p=Get-CimInstance Win32_Process -Filter \"Name='language_server.exe'\" "
    "| ? { $_.CommandLine -match 'csrf_token' } | select -First 1;"
    "if($p){ $ports=@(Get-NetTCPConnection -State Listen -OwningProcess $p.ProcessId "
    "-ea 0 | % LocalPort); @{cmd=$p.CommandLine;ports=$ports} | ConvertTo-Json -Compress }"
)
_cache = {"ts": 0.0, "info": None}


class ProviderError(Exception):
    pass


def _find():
    """(token, [portas]) do language server em execucao, ou None. Cache de 30 s."""
    if time.time() - _cache["ts"] < 30:
        return _cache["info"]
    info = None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", _PS],
                           capture_output=True, text=True, timeout=20,
                           creationflags=0x08000000)  # CREATE_NO_WINDOW
        if r.stdout.strip():
            d = json.loads(r.stdout)
            m = re.search(r"--csrf_token[= ]+(\S+)", d["cmd"])
            ports = d["ports"] if isinstance(d["ports"], list) else [d["ports"]]
            if m and ports:
                info = (m.group(1), [int(p) for p in ports])
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        info = None
    _cache.update(ts=time.time(), info=info)
    return info


def available():
    return _find() is not None


def _call(token, port):
    body = json.dumps({"metadata": {"ideName": "antigravity", "extensionName": "antigravity",
                                    "locale": "en"}}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, PATH), data=body,
        headers={"Content-Type": "application/json", "Connect-Protocol-Version": "1",
                 "X-Codeium-Csrf-Token": token})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.load(r)


def _epoch(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _family(label):
    return label.split()[0] if label else "?"


def fetch():
    """Retorna lista de linhas: (rotulo, pct usado 0-100, reset_epoch, janela_s ou None)."""
    info = _find()
    if not info:
        _cache["ts"] = 0
        raise ProviderError("abra o Antigravity")
    token, ports = info
    data = None
    for port in ports:  # uma das portas e HTTP, a outra HTTPS
        try:
            data = _call(token, port)
            break
        except (urllib.error.URLError, OSError, ValueError):
            continue
    if data is None:
        _cache["ts"] = 0  # a porta pode ter mudado: reprocura na proxima
        raise ProviderError("sem resposta")

    groups = {}  # (reset, fracao restante) -> familias de modelos
    for cfg in data.get("userStatus", {}).get("cascadeModelConfigData", {}) \
                   .get("clientModelConfigs", []):
        q = cfg.get("quotaInfo") or {}
        if "remainingFraction" not in q or not q.get("resetTime"):
            continue
        key = (q["resetTime"], round(float(q["remainingFraction"]), 4))
        fams = groups.setdefault(key, [])
        fam = _family(cfg.get("label", ""))
        if fam not in fams:
            fams.append(fam)
    if not groups:
        raise ProviderError("sem dados")

    rows = []
    for (reset, remaining), fams in groups.items():
        label = "Todos os modelos" if len(fams) >= 3 else "/".join(fams)
        if len(label) > 18:
            label = label[:17] + "…"
        rows.append((label, max(0.0, min(100.0, (1 - remaining) * 100)), _epoch(reset), None))
    rows.sort(key=lambda r: -r[1])  # o mais gasto primeiro
    return rows[:4]
