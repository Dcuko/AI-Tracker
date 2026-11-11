"""Liga/desliga a inicializacao do AI Tracker com o Windows.

    python autostart.py on       cria o atalho na pasta Inicializar
    python autostart.py off      remove o atalho
    python autostart.py status   mostra se esta ligado

Usa so a biblioteca padrao (o atalho .lnk e criado via PowerShell/WScript.Shell).
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "tracker.pyw")
STARTUP = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
LINK = os.path.join(STARTUP, "AI Tracker.lnk")


def pythonw():
    exe = sys.executable
    cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return cand if os.path.isfile(cand) else exe


def on():
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.Arguments='\"%s\"';$s.WorkingDirectory='%s';"
        "$s.WindowStyle=7;$s.Description='AI Tracker overlay';$s.Save()"
    ) % (LINK, pythonw(), TARGET, HERE)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    if r.returncode or not os.path.isfile(LINK):
        sys.exit("falhou: " + (r.stderr.strip() or "atalho nao criado"))
    print("ligado:", LINK)


def off():
    if os.path.isfile(LINK):
        os.remove(LINK)
        print("desligado")
    else:
        print("ja estava desligado")


def status():
    print("ligado" if os.path.isfile(LINK) else "desligado")


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    {"on": on, "off": off, "status": status}.get(cmd, status)()
