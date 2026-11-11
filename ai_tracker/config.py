import json, os

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(DIR, "config.json")
DEFAULTS = {
    "corner": "bottom-right",   # top-left | top-right | bottom-left | bottom-right
    "margin": 16,
    "opacity": 0.6,
    "interval": 60,             # segundos entre consultas
    "width": 250,
    "style": "card",            # card | compact | minimal | taskbar
    "taskbar_side": "right",    # lado da barra de tarefas no estilo taskbar
    "taskbar_gap_right": 290,   # px livres a direita (bandeja do sistema + relogio)
    "taskbar_gap_left": 170,    # px livres a esquerda (widgets)
    "drag_key": "Ctrl+Alt",     # segure para arrastar a janela com o mouse ("" desativa)
    "free": None,               # posicao livre salva ao arrastar (P volta aos cantos)
    "monitor": 0,               # indice do monitor (0 = principal)
    "view": "all",              # "all" ou o nome de uma IA (ex.: "Claude")
    "providers": ["claude", "codex", "antigravity"],
    "hotkey_toggle": "Ctrl+Alt+A",
    "hotkey_quit": "Ctrl+Alt+Q",
    "hotkey_corner": "Ctrl+Alt+P",    # troca canto e, ao fim dos 4, o monitor
    "hotkey_provider": "Ctrl+Alt+N",  # alterna a IA exibida (cada uma, depois todas)
    "hotkey_style": "Ctrl+Alt+S",     # alterna o estilo de exibicao
    "hotkey_opacity": "Ctrl+Alt+O",   # alterna a opacidade
}


def save(cfg):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except FileNotFoundError:
        try:
            with open(PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, indent=2)
        except OSError:
            pass
    except (OSError, ValueError):
        pass
    return cfg


