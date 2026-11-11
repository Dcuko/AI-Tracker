import ctypes, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# instancia unica: uma segunda execucao sai em silencio (evita conflito de hotkeys)
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\AiTrackerOverlay")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    sys.exit(0)

from ai_tracker import config
from ai_tracker.collector import Collector
from ai_tracker.ui import Overlay

cfg = config.load()
col = Collector(cfg["providers"], cfg["interval"])
col.start()
Overlay(cfg, col).run()
