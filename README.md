# AI Tracker

Sobreposição pequena, translúcida e click-through para Windows 11 que mostra o **limite restante da assinatura** das suas IAs de código: Claude Code, Codex CLI e Antigravity.

Só precisa do Python 3.11+ que já vem instalado. Sem `pip install` e sem admin.

## Usar

```
pythonw tracker.pyw            # ou dois cliques no tracker.pyw
python autostart.py on         # abre junto com o Windows (off desliga, status consulta)
```

Rode pelo terminal ou com dois cliques, **não** pelo F5 do VS Code (isso prende o programa ao debugger).

## Atalhos

| Atalho | Ação |
|---|---|
| `Ctrl+Alt+A` | Mostrar / ocultar |
| `Ctrl+Alt+N` | Alternar a IA exibida (cada uma, depois todas) |
| `Ctrl+Alt+S` | Alternar o estilo (`card`, `compact`, `minimal`, `taskbar`) |
| `Ctrl+Alt+P` | Trocar de canto; ao fim dos 4 cantos passa ao próximo monitor. Desfaz o arraste |
| `Ctrl+Alt+O` | Alternar a opacidade (35% a 100%) |
| `Ctrl+Alt+Q` | Sair |
| segurar `Ctrl+Alt` + arrastar | Mover a janela (fica salva) |

Todos os atalhos e a tecla de arrastar (`drag_key`) são configuráveis no `config.json`. Se um atalho já estiver em uso por outro programa, o overlay avisa na própria janela.

## Estilos

- **card**: completo, com abas por IA, barras, marcador de ritmo e tempo até o reset.
- **compact**: uma linha por janela (`5h`, `7d`), sem texto de reset.
- **minimal**: só números, numa linha: `Claude 32% · 5%   Codex 12% · 47%`.
- **taskbar**: faixa que se encaixa dentro da barra de tarefas, ao lado da bandeja (ajuste com `taskbar_gap_right` / `taskbar_gap_left`).

O **marcador de ritmo** (traço branco na barra) mostra quanto da janela de tempo já passou. Se a barra passa do traço, você está gastando mais rápido do que o tempo.
Cores: verde até 60%, amarelo até 85%, vermelho acima.

## De onde vêm os dados

| IA | Fonte | Observações |
|---|---|---|
| **Claude Code** | Endpoint OAuth do `/usage` (`api.anthropic.com`), com o token local de `~/.claude/.credentials.json` | Não oficial, pode mudar. O token só é lido e enviado ao domínio da Anthropic. Se falhar, cai num **fallback estimado** pelos logs `~/.claude/projects` (linhas com `~` no rótulo), calibrado pela última leitura boa |
| **Codex CLI** | Logs locais `~/.codex/sessions/**/rollout-*.jsonl` (`rate_limits`) | Sem rede nem token. Aparece só se o Codex estiver instalado. Confirmado com o app real (plano free mostra uma janela de 30 dias) |
| **Antigravity** | `language_server.exe` local da IDE (`GetUserStatus` em `127.0.0.1`) | Só fala com a máquina local. Aparece só com a IDE aberta. API interna, pode mudar |

Cada fonte é independente: se uma quebrar, as outras continuam e a quebrada mostra um traço com o motivo.

## Arquivos

```
tracker.pyw              entrada
autostart.py             liga/desliga a inicialização com o Windows
config.json              configuração (criado na 1ª execução)
cache_claude.json        última leitura do Claude (para o fallback)
ai_tracker/ui.py         janela, estilos, hotkeys, arrastar
ai_tracker/collector.py  coleta em segundo plano
ai_tracker/providers/    claude.py, codex.py, antigravity.py
```

Para adicionar uma IA: crie `providers/<nome>.py` com `NAME`, `fetch()` (devolve linhas `(rótulo, % usado, reset_epoch, janela_em_s)`) e, opcionalmente, `available()`; depois inclua o nome em `providers` no `config.json`.

## Limitações conhecidas

- Os endpoints do Claude e do Antigravity não são oficiais e podem mudar sem aviso.
- Em monitores com DPI diferente do principal, o tamanho do overlay segue o monitor principal.
- O estilo `taskbar` só se encaixa com a barra de tarefas embaixo e visível; senão cai no canto.
- Grok não é suportado (não tem log local).
