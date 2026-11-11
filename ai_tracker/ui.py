import ctypes, queue, threading, time, tkinter as tk
import tkinter.font as tkfont
from ctypes import wintypes

from . import config

# paleta
BG, BORDER = "#101216", "#262b33"
FG, DIM, FAINT, TRACK = "#eef0f3", "#8a93a1", "#5b6370", "#232831"
GREEN, YELLOW, RED = "#4ade80", "#fbbf24", "#f87171"
F_NAME = ("Segoe UI Semibold", 9)
F_LABEL = ("Segoe UI", 9)
F_PCT = ("Segoe UI Semibold", 15)
F_PCT_S = ("Segoe UI Semibold", 10)
F_SMALL = ("Segoe UI", 8)
F_TINY = ("Segoe UI Semibold", 7)

CORNERS = ["bottom-right", "bottom-left", "top-right", "top-left"]
SIDES = ["right", "left"]  # posicoes do estilo "taskbar"
STYLES = ["card", "compact", "minimal", "taskbar"]
OPACITIES = [0.35, 0.5, 0.65, 0.8, 1.0]

u32 = ctypes.windll.user32
u32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
u32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
u32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
u32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
u32.GetAncestor.restype = wintypes.HWND
u32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
u32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
u32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, wintypes.UINT]


def _hwnd(widget):
    return u32.GetAncestor(widget.winfo_id(), 2)  # GA_ROOT


def _click_through(hwnd):
    style = u32.GetWindowLongPtrW(hwnd, -20)  # GWL_EXSTYLE
    # LAYERED | TRANSPARENT | TOOLWINDOW | NOACTIVATE
    u32.SetWindowLongPtrW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)


def _round_corners(hwnd, small=False):
    """Cantos arredondados nativos do Windows 11 (sem serrilhado)."""
    try:
        dwm = ctypes.windll.dwmapi
        pref = ctypes.c_int(3 if small else 2)  # DWMWCP_ROUNDSMALL / DWMWCP_ROUND
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(pref), 4)
        color = ctypes.c_int(0x33 << 16 | 0x2b << 8 | 0x26)  # COLORREF 0x00BBGGRR de BORDER
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(color), 4)
    except Exception:
        pass


def _show(hwnd, visible):
    # SW_HIDE / SW_SHOWNOACTIVATE: nao rouba o foco
    u32.ShowWindow(hwnd, 4 if visible else 0)
    if visible:
        _raise(hwnd)


def _raise(hwnd):
    # HWND_TOPMOST, NOMOVE|NOSIZE|NOACTIVATE
    u32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x13)


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


_ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_void_p)
u32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]


def _monitors():
    """[(area_de_trabalho, monitor_inteiro)] com (l, t, r, b) cada.
    A area de trabalho exclui a barra de tarefas. O principal vem primeiro;
    os demais ordenados da esquerda para a direita."""
    found = []

    def cb(hmon, _hdc, _rc, _lp):
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        if u32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            w, m = mi.rcWork, mi.rcMonitor
            found.append((not (mi.dwFlags & 1), m.left,
                          ((w.left, w.top, w.right, w.bottom),
                           (m.left, m.top, m.right, m.bottom))))
        return 1

    u32.EnumDisplayMonitors(None, None, _ENUMPROC(cb), 0)
    found.sort(key=lambda m: (m[0], m[1]))
    if found:
        return [m[2] for m in found]
    r = wintypes.RECT()
    u32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    rect = (r.left, r.top, r.right, r.bottom)
    return [(rect, rect)]


_VK = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B}
u32.GetAsyncKeyState.argtypes = [ctypes.c_int]


def _parse_keys(combo):
    """'Ctrl+Alt' -> [0x11, 0x12]. Vazio ou invalido -> [] (arrastar desativado)."""
    try:
        return [_VK[p.strip().lower()] for p in combo.split("+") if p.strip()]
    except KeyError:
        return []


def _keys_down(vks):
    return bool(vks) and all(u32.GetAsyncKeyState(vk) & 0x8000 for vk in vks)


def _hotkeys(spec, q):
    """Thread com loop de mensagens. spec: {id: (nome, 'Ctrl+Alt+A')}.
    Poe na fila ('key', id) ao disparar e ('fail', nome) se o registro falhar."""
    mods = {"ctrl": 2, "alt": 1, "shift": 4, "win": 8}

    def run():
        for hid, (name, combo) in spec.items():
            try:
                parts = [p.strip().lower() for p in combo.split("+")]
                m = sum(mods[p] for p in parts[:-1]) | 0x4000  # NOREPEAT
                key = parts[-1].upper()
                vk = ord(key) if len(key) == 1 else int(key[1:]) + 0x6F  # F1..F12
                ok = u32.RegisterHotKey(None, hid, m, vk)
            except Exception:
                ok = False
            if not ok:
                q.put(("fail", "%s (%s)" % (name, combo)))
        msg = wintypes.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                q.put(("key", msg.wParam))

    threading.Thread(target=run, daemon=True).start()


def _fmt_reset(ts):
    if not ts:
        return ""
    s = int(ts - time.time())
    if s <= 0:
        return "reseta agora"
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    if d:
        return "reseta em %dd %dh" % (d, h)
    return "reseta em %dh %02dm" % (h, m) if h else "reseta em %dm" % m


def _color(p):
    return GREEN if p < 60 else YELLOW if p < 85 else RED


def _short(label, window):
    """Rotulo curto da janela: 5h, 7d..."""
    if window == 18000:
        return "5h"
    if window == 604800:
        return "7d"
    if window and window % 86400 == 0:
        return "%dd" % (window // 86400)
    if window and window % 3600 == 0:
        return "%dh" % (window // 3600)
    return label[:3]


class Overlay:
    def __init__(self, cfg, collector):
        self.cfg, self.col = cfg, collector
        self.root = tk.Tk()
        r = self.root
        self.k = r.winfo_fpixels("1i") / 96.0  # fator de DPI
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", float(cfg["opacity"]))
        r.configure(bg=BG)
        self.canvas = tk.Canvas(r, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._fonts = {}
        self.grab = False       # modo de arrastar ativo (tecla segurada)
        self.dragging = False   # botao do mouse pressionado durante o arraste
        self.drag_vks = _parse_keys(cfg.get("drag_key", ""))
        self._off = (0, 0)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.visible = True
        self.fails = []
        self.n = 0
        self.q = queue.Queue()
        _hotkeys({
            1: ("mostrar/ocultar", cfg["hotkey_toggle"]),
            2: ("sair", cfg["hotkey_quit"]),
            3: ("trocar canto/monitor", cfg["hotkey_corner"]),
            4: ("opacidade", cfg["hotkey_opacity"]),
            5: ("trocar IA", cfg["hotkey_provider"]),
            6: ("trocar estilo", cfg["hotkey_style"]),
        }, self.q)
        r.update_idletasks()
        self.hwnd = _hwnd(r)
        _click_through(self.hwnd)
        _round_corners(self.hwnd, self.style() != "card")
        self.tick()
        self.poll()

    # ---- utilidades ----
    def s(self, v):
        return int(round(v * self.k))

    def font(self, spec):
        if spec not in self._fonts:
            self._fonts[spec] = tkfont.Font(family=spec[0], size=spec[1])
        return self._fonts[spec]

    def tw(self, text, spec):
        return self.font(spec).measure(text)

    def style(self):
        st = self.cfg.get("style", "card")
        return st if st in STYLES else "card"

    def names(self):
        return [n for n, st in self.col.snapshot().items() if not st.get("hidden")]

    def view(self, names):
        v = self.cfg.get("view", "all")
        return v if v in names else "all"

    def is_stale(self, st):
        return bool(st["rows"]) and time.time() - st["ts"] > self.cfg["interval"] * 3

    def monitor(self):
        mons = _monitors()
        return mons[min(max(int(self.cfg["monitor"]), 0), len(mons) - 1)]

    def place(self, w, h):
        s = self.s
        if self.dragging:  # durante o arraste a posicao e do mouse
            self.canvas.config(width=w, height=h)
            return
        free = self.cfg.get("free")
        if free:
            # ancorada no canto mais proximo do monitor: se o conteudo crescer, cresce para dentro
            mons = _monitors()
            _w, (ml, mt, mr, mb) = mons[min(max(int(free.get("monitor", 0)), 0), len(mons) - 1)]
            a = free.get("anchor", "bottom-right")
            dx, dy = s(free.get("dx", 0)), s(free.get("dy", 0))
            x = ml + dx if "left" in a else mr - w - dx
            y = mt + dy if "top" in a else mb - h - dy
            x, y = min(max(x, ml), mr - w), min(max(y, mt), mb - h)
            self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
            self.canvas.config(width=w, height=h)
            return
        (wl, wt, wr, wb), (ml, mt, mr, mb) = self.monitor()
        if self.style() == "taskbar" and wb < mb:  # barra de tarefas embaixo e visivel
            tbh = mb - wb
            if self.cfg.get("taskbar_side", "right") == "left":
                x = ml + s(self.cfg["taskbar_gap_left"])
            else:
                x = mr - w - s(self.cfg["taskbar_gap_right"])
            y = wb + (tbh - h) // 2
        else:
            m = s(self.cfg["margin"])
            corner = self.cfg["corner"]
            x = wl + m if "left" in corner else wr - w - m
            y = wt + m if "top" in corner else wb - h - m
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.canvas.config(width=w, height=h)

    # ---- estilos ----
    def _bar(self, x, y, w, h, pct, color, marker=None):
        c = self.canvas

        def pill(x0, x1, fill):
            x1 = max(x1, x0 + h)
            c.create_oval(x0, y, x0 + h, y + h, fill=fill, outline="")
            c.create_oval(x1 - h, y, x1, y + h, fill=fill, outline="")
            c.create_rectangle(x0 + h / 2, y, x1 - h / 2, y + h, fill=fill, outline="")

        pill(x, x + w, TRACK)
        if pct > 0:
            pill(x, x + w * min(pct, 100) / 100, color)
        if marker is not None:  # quanto da janela de tempo ja passou
            mx = x + w * marker
            c.create_line(mx, y - 2, mx, y + h + 2, fill=FG, width=max(1, self.s(1)))

    def draw_card(self, snap, names, view, shown):
        c, s = self.canvas, self.s
        w = s(self.cfg["width"])
        pad = s(14)
        y = s(12)
        now = time.time()

        if len(names) > 1:  # abas: cada IA + "Todas"
            x = pad
            for label in names + ["Todas"]:
                active = label == (view if view != "all" else "Todas")
                tw = self.tw(label, F_NAME)
                c.create_text(x, y + s(8), text=label, anchor="w",
                              fill=FG if active else FAINT, font=F_NAME)
                if active:
                    c.create_line(x, y + s(20), x + tw, y + s(20), fill=GREEN, width=s(2))
                x += tw + s(16)
            if view != "all" and self.is_stale(snap[view]):
                c.create_text(w - pad, y + s(8), text="desatualizado", anchor="e",
                              fill=YELLOW, font=F_SMALL)
            y += s(32)

        for name in shown:
            st = snap[name]
            if len(names) == 1 or view == "all":
                stale = self.is_stale(st)
                dot = YELLOW if stale else (GREEN if st["rows"] else FAINT)
                c.create_oval(pad, y + s(4), pad + s(7), y + s(11), fill=dot, outline="")
                c.create_text(pad + s(14), y + s(8), text=name.upper(), anchor="w",
                              fill=DIM, font=F_NAME)
                if stale:
                    c.create_text(w - pad, y + s(8), text="desatualizado", anchor="e",
                                  fill=YELLOW, font=F_SMALL)
                y += s(24)
            if st["error"] and not st["rows"]:
                c.create_text(pad, y + s(6), text=st["error"], anchor="w",
                              fill=FAINT, font=F_LABEL)
                y += s(26)
                continue
            for label, pct, reset, window in st["rows"]:
                col = _color(pct)
                c.create_text(pad, y + s(10), text=label, anchor="w", fill=FG, font=F_LABEL)
                c.create_text(w - pad, y + s(10), text="%d%%" % round(pct), anchor="e",
                              fill=col, font=F_PCT)
                marker = None
                if reset and window:
                    marker = min(1.0, max(0.0, 1 - (reset - now) / window))
                self._bar(pad, y + s(24), w - 2 * pad, s(6), pct, col, marker)
                c.create_text(pad, y + s(40), text=_fmt_reset(reset), anchor="w",
                              fill=FAINT, font=F_SMALL)
                y += s(54)
            y += s(2)
        if self.fails:
            c.create_text(pad, y + s(2), text="atalho indisponivel: " + ", ".join(self.fails),
                          anchor="nw", fill=RED, font=F_SMALL, width=w - 2 * pad)
            y += s(28)
        return w, y + s(6)

    def draw_compact(self, snap, names, view, shown):
        c, s = self.canvas, self.s
        w, pad = s(210), s(12)
        y = s(10)
        for name in shown:
            st = snap[name]
            stale = self.is_stale(st)
            dot = YELLOW if stale else (GREEN if st["rows"] else FAINT)
            c.create_oval(pad, y + s(4), pad + s(6), y + s(10), fill=dot, outline="")
            c.create_text(pad + s(13), y + s(7), text=name.upper(), anchor="w",
                          fill=DIM, font=F_NAME)
            y += s(20)
            if st["error"] and not st["rows"]:
                c.create_text(pad, y + s(6), text=st["error"], anchor="w",
                              fill=FAINT, font=F_SMALL)
                y += s(20)
                continue
            for label, pct, _reset, window in st["rows"]:
                col = _color(pct)
                c.create_text(pad, y + s(8), text=_short(label, window), anchor="w",
                              fill=DIM, font=F_SMALL)
                self._bar(pad + s(26), y + s(5), w - 2 * pad - s(26) - s(40), s(6), pct, col)
                c.create_text(w - pad, y + s(8), text="%d%%" % round(pct), anchor="e",
                              fill=col, font=F_PCT_S)
                y += s(19)
            y += s(5)
        if self.fails:
            c.create_text(pad, y, text="atalho indisponivel: " + ", ".join(self.fails),
                          anchor="nw", fill=RED, font=F_SMALL, width=w - 2 * pad)
            y += s(26)
        return w, y + s(3)

    def draw_minimal(self, snap, names, view, shown):
        """Uma linha so, apenas numeros: Claude 30% · 5%   Codex 12% · 47%"""
        c, s = self.canvas, self.s
        pad, h = s(12), s(28)
        x, cy = pad, h // 2
        for i, name in enumerate(shown):
            st = snap[name]
            if i:
                x += s(14)
            c.create_text(x, cy, text=name, anchor="w",
                          fill=YELLOW if self.is_stale(st) else DIM, font=F_SMALL)
            x += self.tw(name, F_SMALL) + s(7)
            if st["error"] and not st["rows"]:
                c.create_text(x, cy, text="—", anchor="w", fill=FAINT, font=F_PCT_S)
                x += self.tw("—", F_PCT_S)
                continue
            for j, (_l, pct, _r, _w) in enumerate(st["rows"]):
                if j:
                    c.create_text(x + s(4), cy, text="·", anchor="w", fill=FAINT, font=F_PCT_S)
                    x += s(12)
                t = "%d%%" % round(pct)
                c.create_text(x, cy, text=t, anchor="w", fill=_color(pct), font=F_PCT_S)
                x += self.tw(t, F_PCT_S)
        if not shown:
            c.create_text(x, cy, text="—", anchor="w", fill=FAINT, font=F_PCT_S)
            x += self.tw("—", F_PCT_S)
        return x + pad, h

    def draw_taskbar(self, snap, names, view, shown):
        """Faixa baixa para ficar sobre a barra de tarefas: nome, numeros e mini barra."""
        c, s = self.canvas, self.s
        pad, h = s(12), s(40)
        x = pad
        for i, name in enumerate(shown):
            st = snap[name]
            if i:
                x += s(18)
            nums, widths = [], []
            if st["error"] and not st["rows"]:
                nums, widths = [("—", FAINT)], [self.tw("—", F_PCT_S)]
            else:
                for _l, pct, _r, _w in st["rows"]:
                    t = "%d%%" % round(pct)
                    nums.append((t, _color(pct)))
                    widths.append(self.tw(t, F_PCT_S))
            sep = s(12)
            numw = sum(widths) + sep * max(0, len(nums) - 1)
            nm = name.upper()
            bw = max(numw, self.tw(nm, F_TINY))
            c.create_text(x, s(9), text=nm, anchor="w",
                          fill=YELLOW if self.is_stale(st) else DIM, font=F_TINY)
            nx = x
            for j, (t, col) in enumerate(nums):
                if j:
                    c.create_text(nx + s(4), s(22), text="·", anchor="w",
                                  fill=FAINT, font=F_PCT_S)
                    nx += sep
                c.create_text(nx, s(22), text=t, anchor="w", fill=col, font=F_PCT_S)
                nx += widths[j]
            if st["rows"]:
                self._bar(x, s(32), bw, s(3), st["rows"][0][1], _color(st["rows"][0][1]))
            x += bw
        if not shown:
            c.create_text(x, s(20), text="—", anchor="w", fill=FAINT, font=F_PCT_S)
            x += self.tw("—", F_PCT_S)
        return x + pad, h

    def draw(self):
        self.canvas.delete("all")
        snap = {n: st for n, st in self.col.snapshot().items() if not st.get("hidden")}
        names = list(snap)
        view = self.view(names)
        shown = [n for n in names if view == "all" or n == view]
        fn = getattr(self, "draw_" + self.style())
        w, h = fn(snap, names, view, shown)
        if self.grab:  # borda de destaque no modo arrastar
            self.canvas.create_rectangle(1, 1, w - 2, h - 2, outline=GREEN, width=self.s(2))
        self.place(w, h)

    # ---- arrastar (segure drag_key) ----
    def poll(self):
        try:
            if self.visible:
                want = self.dragging or _keys_down(self.drag_vks)
                if want != self.grab:
                    self.set_grab(want)
        finally:
            self.root.after(40, self.poll)

    def set_grab(self, on):
        """Liga/desliga o click-through. Sem WS_EX_TRANSPARENT a janela recebe o mouse,
        mas continua sem ativar (nao rouba o foco do app em uso)."""
        self.grab = on
        st = u32.GetWindowLongPtrW(self.hwnd, -20)
        u32.SetWindowLongPtrW(self.hwnd, -20, (st & ~0x20) if on else (st | 0x20))
        op = float(self.cfg["opacity"])
        self.root.attributes("-alpha", max(op, 0.92) if on else op)
        self.canvas.config(cursor="fleur" if on else "")
        self.draw()

    def _press(self, e):
        if self.grab:
            self.dragging = True
            self._off = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _motion(self, e):
        if self.dragging:
            self.root.geometry("+%d+%d" % (e.x_root - self._off[0], e.y_root - self._off[1]))

    def _release(self, _e):
        if not self.dragging:
            return
        self.dragging = False
        r = self.root
        x, y, w, h = r.winfo_x(), r.winfo_y(), r.winfo_width(), r.winfo_height()
        cx, cy = x + w / 2, y + h / 2
        mons = _monitors()
        mi = next((i for i, (_w, m) in enumerate(mons)
                   if m[0] <= cx < m[2] and m[1] <= cy < m[3]), 0)
        ml, mt, mr, mb = mons[mi][1]
        right, bottom = cx > (ml + mr) / 2, cy > (mt + mb) / 2
        dx = (mr - (x + w)) if right else (x - ml)
        dy = (mb - (y + h)) if bottom else (y - mt)
        self.cfg["free"] = {"monitor": mi,
                            "anchor": ("bottom" if bottom else "top") + "-" + ("right" if right else "left"),
                            "dx": round(dx / self.k), "dy": round(dy / self.k)}
        self.cfg["monitor"] = mi
        self._save()
        self.draw()

    # ---- eventos ----
    def _save(self):
        try:
            config.save(self.cfg)
        except OSError:
            pass

    def _handle(self, hid):
        if hid == 1:
            self.visible = not self.visible
            _show(self.hwnd, self.visible)
        elif hid == 2:
            self.root.destroy()
            return True
        elif hid == 3:
            # percorre as posicoes de um monitor e depois passa para o proximo monitor
            taskbar = self.style() == "taskbar"
            slots, key = (SIDES, "taskbar_side") if taskbar else (CORNERS, "corner")
            n = len(_monitors())
            mi = min(max(int(self.cfg["monitor"]), 0), n - 1)
            si = slots.index(self.cfg.get(key)) if self.cfg.get(key) in slots else 0
            si += 1
            if si >= len(slots):
                si, mi = 0, (mi + 1) % n
            self.cfg[key], self.cfg["monitor"] = slots[si], mi
            self.cfg["free"] = None  # sai da posicao arrastada e volta aos cantos
            self._save()
        elif hid == 4:
            cur = float(self.cfg["opacity"])
            nxt = next((o for o in OPACITIES if o > cur + 0.01), OPACITIES[0])
            self.cfg["opacity"] = nxt
            self.root.attributes("-alpha", nxt)
            self._save()
        elif hid == 5:
            names = self.names()
            if len(names) > 1:
                order = names + ["all"]
                cur = self.view(names)
                self.cfg["view"] = order[(order.index(cur) + 1) % len(order)]
                self._save()
        elif hid == 6:
            nxt = STYLES[(STYLES.index(self.style()) + 1) % len(STYLES)]
            self.cfg["style"] = nxt
            _round_corners(self.hwnd, nxt != "card")
            self._save()
        return False

    def tick(self):
        while True:
            try:
                kind, val = self.q.get_nowait()
            except queue.Empty:
                break
            if kind == "fail":
                self.fails.append(val)
            elif self._handle(val):
                return
        self.n += 1
        if self.visible:
            self.draw()
            if self.n % 5 == 0:
                _raise(self.hwnd)  # volta ao topo se outra janela topmost cobrir
        self.root.after(1000, self.tick)

    def run(self):
        self.root.mainloop()
