import importlib, threading, time


class Collector(threading.Thread):
    """Consulta cada provider em segundo plano; a UI so le o ultimo estado."""

    def __init__(self, names, interval):
        super().__init__(daemon=True)
        self.mods = [importlib.import_module("ai_tracker.providers." + n) for n in names]
        self.interval = max(30, int(interval))
        self.state = {m.NAME: {"rows": [], "error": "carregando", "ts": 0} for m in self.mods}
        self.lock = threading.Lock()
        self._backoff = {}

    def snapshot(self):
        with self.lock:
            return {k: dict(v) for k, v in self.state.items()}

    def run(self):
        while True:
            now = time.time()
            for m in self.mods:
                check = getattr(m, "available", None)
                hidden = bool(check) and not check()  # ex.: Codex nao instalado
                with self.lock:
                    self.state[m.NAME]["hidden"] = hidden
                if hidden or self._backoff.get(m.NAME, 0) > now:
                    continue
                try:
                    rows = m.fetch()
                    upd = {"rows": rows, "error": None, "ts": time.time()}
                    self._backoff.pop(m.NAME, None)
                except Exception as e:  # um provider nunca derruba os outros
                    msg = str(e) or e.__class__.__name__
                    upd = {"error": msg}
                    if "429" in msg:
                        self._backoff[m.NAME] = now + 300
                with self.lock:
                    self.state[m.NAME].update(upd)
            time.sleep(self.interval)
