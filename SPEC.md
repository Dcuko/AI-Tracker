# AI Tracker: Spec v1 (estado final)

Sobreposição pequena, de baixa opacidade e click-through, que mostra o **limite restante da assinatura** das IAs de código. Uso e atalhos estão no [README.md](README.md).

## 1. Escopo

**Dentro (v1, entregue):** Claude Code, Codex CLI e Antigravity; 4 estilos; multi-monitor; arrastar; autostart.
**Fora:** Grok (sem log local; exigiria extensão de navegador), contagem de tokens/custo, histórico em gráfico, macOS/Linux.

## 2. Decisões

| Tema | Decisão |
|---|---|
| Métrica | % usado e tempo até o reset por janela |
| Plataforma | Windows 11 |
| Stack | Python 3.11 só com biblioteca padrão (`tkinter`, `ctypes`, `urllib`); sem `pip` |
| Visual | Click-through, translúcido, cantos nativos do Win11 (DWM) |
| Isolamento | Cada IA é um *provider*; uma quebrar não afeta as outras |

## 3. Fontes de dados (validadas em 2026-11-10)

| Fonte | Método | Status |
|---|---|---|
| Claude | `GET api.anthropic.com/api/oauth/usage` (header `anthropic-beta: oauth-2025-04-20`) com o token local; retorna `five_hour` e `seven_day` (`utilization`, `resets_at`) | **Confirmado** |
| Claude (fallback) | Tokens dos JSONL em `~/.claude/projects` (ids deduplicados) ÷ teto calibrado na última leitura boa; linhas marcadas com `~` | **Confirmado** (consistente no ponto de calibração; a precisão longe dele não foi medida) |
| Codex | `rate_limits` (`primary`/`secondary`) nos eventos `token_count` de `~/.codex/sessions/**/rollout-*.jsonl`; ignora buckets de outros modelos | **Confirmado** com o app real (plano free: uma janela de 30 dias, `secondary` nulo). Janelas 5h/semana de planos pagos seguem o mesmo formato, mas não foram vistas |
| Antigravity | `POST /exa.language_server_pb.LanguageServerService/GetUserStatus` (Connect/JSON) no `language_server.exe` local, porta descoberta pelo processo, header `X-Codeium-Csrf-Token`; usa `quotaInfo` (`remainingFraction`, `resetTime`) por modelo, agrupado por reset | **Confirmado** (só com a IDE aberta) |

Falha de um provider: mostra "—" com o motivo; 429 gera espera de 5 min; dado antigo ganha o marcador "desatualizado".

## 4. Interface

- **Estilos:** `card`, `compact`, `minimal` (só números), `taskbar` (faixa na barra de tarefas).
- **Posição:** 4 cantos × N monitores, ou livre (segurar `Ctrl+Alt` e arrastar; ancorada no canto mais próximo do monitor).
- **Seleção de IA:** abas no `card`; `Ctrl+Alt+N` alterna cada IA e "Todas".
- **Controle com click-through:** hotkeys globais (`RegisterHotKey`) e modo arrastar por tecla segurada (sem roubar o foco).
- **Marcador de ritmo:** traço na barra com a fração da janela já decorrida.

## 5. Arquitetura

```
tracker.pyw → config.load → Collector(thread) → providers/{claude,codex,antigravity}.fetch()
                         ↘ Overlay(tkinter) lê collector.snapshot() a cada 1 s
```

Contrato do provider: `NAME`, `fetch() -> [(rótulo, pct, reset_epoch, janela_s|None)]`, `available()` opcional (provider oculto se falso).

## 6. Requisitos não funcionais (verificados)

- Instalação: copiar a pasta e rodar. Instância única (mutex).
- Privacidade: token do Claude só é enviado a `api.anthropic.com`; o do Antigravity só fala com `127.0.0.1`. Nenhum é logado nem gravado (o cache guarda só percentuais).
- Recursos: consulta a cada 60 s, redesenho a cada 1 s, thread de coleta separada.

## 7. Riscos

| Risco | Mitigação |
|---|---|
| Endpoints de Claude e Antigravity não são oficiais | Fallback por log no Claude; estado "—" claro no Antigravity |
| Uso do token OAuth do Claude fora do app (termos de uso) | Decisão do usuário; basta tirar o provider do `config.json` |
| Formato do log do Codex diferir do esperado | Parser tolerante; falha isolada |
| DPI diferente entre monitores | Limitação documentada |

## 8. Pendências / ideias

- Ver o Codex num plano pago (janelas 5h e semana).
- Medir a precisão do fallback do Claude ao longo de uma janela inteira.
- Ajustar escala por monitor (DPI).
- Grok via extensão de navegador (v2, se quiser).
