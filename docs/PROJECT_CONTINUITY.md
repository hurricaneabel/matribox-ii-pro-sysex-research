# Continuidade do projeto Matribox II Pro SysEx Research

> Documento oficial de retomada entre conversas.
>
> **Última atualização:** 6 de agosto de 2026  
> **Marco consolidado:** Fase 21 — monitor ao vivo com preset, metadados, cadeia,
> ordem e bypass em tempo real  
> **Branch de trabalho:** `main`

## 1. Como usar este documento

Ao iniciar um novo chat, peça primeiro para ler este arquivo e o `README.md`.
Eles devem ser tratados como a fonte de contexto do estado atual do projeto.
Depois disso, consulte os documentos de fase somente quando for necessário
reconstruir uma descoberta específica.

Este arquivo deve ser atualizado **antes de todo commit que consolide uma nova
funcionalidade aprovada**. A atualização deve registrar:

1. o que foi implementado;
2. como foi validado offline;
3. como foi validado fisicamente;
4. limitações ou riscos ainda conhecidos;
5. qual é o próximo passo recomendado;
6. o novo total da suíte de testes.

## 2. Preferências permanentes de trabalho

- Trabalhar na branch `main`, sem criar outra branch, salvo pedido explícito.
- O usuário extrai pacotes ZIP manualmente; não é necessário fornecer comandos
  de extração.
- A suíte oficial usa `unittest`, não `pytest`.
- Nunca executar `git add`, commit ou limpeza antes da aprovação dos testes
  físicos quando a mudança envolver comunicação MIDI.
- Preservar capturas e experimentos enquanto uma hipótese ainda estiver em
  validação.
- Após a confirmação física, atualizar este documento, revisar o escopo,
  executar a suíte completa e então consolidar o commit.
- Não enviar comandos desconhecidos ou potencialmente destrutivos à pedaleira.

Comando oficial da suíte:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Validações adicionais antes de um commit:

```powershell
python -m compileall tools tests
git diff --check
```

## 3. Objetivo do projeto

Pesquisar, documentar e implementar com segurança o protocolo SysEx da
**Sonicake Matribox II Pro**, usando somente comandos capturados, reproduzidos
e validados fisicamente.

O estado atual já permite:

- consultar o preset ativo;
- carregar nome e etiqueta dos 240 presets;
- ler a cadeia completa de um preset sem modificá-lo;
- identificar classe, modelo, seletor e estado de cada efeito;
- acompanhar mudanças de ordem visual em tempo real;
- acompanhar liga/desliga de efeitos em tempo real;
- adicionar, substituir, remover e mover efeitos com comandos já validados;
- alterar modelo, bypass e volume usando comandos conhecidos.

## 4. Programa principal atual

Com o ambiente virtual ativado e o editor oficial fechado:

```powershell
python -m tools.commands.matribox_monitor
```

O monitor mostra:

```text
Preset atual: 31B
Nome: Steve Vai v2
Etiqueta: Rock
Efeitos:
  1. DYN / GATE 3 — ligado
  2. DRV / Skreamer — ligado
  3. CLONE / CLONE 10 — ligado
  4. IR / IR 14 — ligado
  5. EQ / GUITAR EQ 2 — ligado
  6. RVB / SKY — ligado
  7. DLY / RACK — ligado
```

### Comportamentos fisicamente confirmados

- A troca de preset atualiza endereço, nome, etiqueta e solicita a nova cadeia.
- A mudança da ordem dos efeitos redesenha a cadeia na ordem correta.
- Ligar ou desligar um efeito atualiza imediatamente somente o estado daquele
  slot, sem solicitar um novo dump completo.
- A inicialização após ligar a pedaleira possui reenvios automáticos; não é mais
  necessário encerrar e executar o monitor uma segunda vez.
- O monitor é somente leitura durante a consulta da cadeia. Ele não move,
  substitui, liga/desliga nem salva efeitos.

## 5. Ambiente validado

```text
Sistema operacional: Windows
Python: 3.12
MIDI: mido + python-rtmidi
Entrada: Matribox II Pro Subdevice 0
Saída:   Matribox II Pro Subdevice 1
```

Preparação habitual:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 6. Arquitetura atual do monitor

### 6.1 Inicialização e metadados

1. Abre as portas MIDI.
2. Envia quatro mensagens de handshake.
3. Solicita o bloco global de metadados.
4. Solicita o preset atual.
5. Reconstrói os 18 fragmentos globais.
6. Carrega endereço, nome e etiqueta dos 240 presets.
7. Usa tentativas automáticas para tolerar a primeira mensagem perdida após
   cold boot.

Arquivos principais:

```text
tools/commands/preset_monitor_live.py
tools/commands/preset_monitor_core.py
tools/commands/global_metadata_collector.py
tools/commands/global_preset_metadata.py
tools/commands/preset_state.py
```

### 6.2 Leitura não destrutiva da cadeia

Ao detectar um preset, o monitor envia o pedido de dump `0x10` para aquele
endereço. Os fragmentos são reconstruídos e o contêiner LZO1X é descomprimido
para um payload fixo de **1.211 bytes**.

Layout usado no dump descomprimido:

```text
185–260    estrutura, ordem, classes e registros de efeito
993–1004   bypass dos 12 slots internos
```

A partir desse bloco, o monitor reconstrói a cadeia visual e resolve os nomes
pelo catálogo confirmado.

Arquivos principais:

```text
tools/commands/preset_dump_state.py
tools/commands/chain_order.py
tools/commands/structural_effect_state.py
tools/commands/effect_catalog.py
```

### 6.3 Atualizações em tempo real

Há duas respostas importantes durante o monitoramento:

- resposta estrutural completa: atualiza ordem e registros da cadeia;
- resposta de bypass de 62 bytes: informa slot interno e estado `0/1`.

O parser de bypass atualiza de forma imutável:

- o registro do slot;
- o vetor de bypass;
- o payload estrutural associado;
- a visualização na ordem atual.

Se o bypass chegar enquanto o dump ainda está sendo montado, o evento mais
recente prevalece quando a cadeia é finalizada.

Arquivo principal:

```text
tools/commands/effect_slot_state.py
```

## 7. Estrutura estrutural confirmada

As respostas estruturais variáveis não usam offsets brutos variáveis para os
campos de efeito. Elas contêm um contêiner LZO1X codificado em nibbles.

Fluxo confirmado:

```text
SysEx
  -> pares de nibbles a partir do índice bruto 13
  -> contêiner 01 00 00 10
  -> tamanho comprimido uint32 little-endian
  -> LZO1X
  -> payload fixo de 89 bytes
```

Layout do payload de 89 bytes:

```text
0–3      cabeçalho interno
4–15     ordem visual dos 12 slots internos
16–27    classe por slot interno
28–75    12 registros de quatro bytes
76–87    bypass por slot interno
88       marcador do slot da resposta ou FF
```

Cada registro de efeito possui:

```text
modelo | auxiliar 1 | auxiliar 2 | seletor secundário
```

A API estável fica em `tools/commands/chain_order.py`. Exemplos:

```python
state.human_slots
state.visual_enabled_states
state.record_for_internal_slot(4)
state.record_at_visual_position(1)
state.visual_effect_records
state.response_slot_marker
```

## 8. Comandos SysEx principais confirmados

| Comando | Tamanho | Uso confirmado |
|---:|---:|---|
| `0x10` | variável | solicitar dump de preset |
| `0x14` | 54 bytes | alterar volume |
| `0x16` | 58 bytes | trocar modelo na mesma classe |
| `0x17` | 60 bytes | adicionar, substituir, remover ou mover efeito |
| `0x18` | 62 bytes | ligar/desligar slot; resposta usada pelo monitor |

O protocolo usa slots internos de `0` a `11`, enquanto a interface Python
apresenta slots de `1` a `12`:

```python
protocol_slot = displayed_slot - 1
```

## 9. Catálogo atual

O catálogo possui **16 classes** e **267 posições/modelos confirmados**:

```text
FREQ, DRV, DYN, WAH, AMP, CAB, IR, EQ,
MOD, DLY, RVB, CLONE, FX LOOP, FX SEND, FX RETURN, VOL
```

Fonte principal:

```text
tools/commands/effect_catalog.py
docs/protocol_findings.md
```

Alguns IDs de modelo se repetem dentro da mesma classe. O seletor secundário é
necessário para desambiguar casos como modelos AMP distintos com o mesmo ID.

## 10. Histórico consolidado das Fases 14–21

### Fase 14 — classe e modelo por slot

Mapeou os campos estruturais dos slots 1–5 usando mudanças controladas de
classe e modelo. Confirmou respostas auxiliares de 128 bytes e tamanhos
estruturais variáveis.

Arquivos relacionados:

```text
STRUCTURAL_CLASS_MODEL_PHASE14.md
tools/experiments/map_structural_class_model_all_slots.py
```

### Fase 15 — modelo e seletor

Separou mudanças de modelo e seletor nos slots 4 e 5. Confirmou que offsets
brutos fixos não eram seguros e preservou 13 capturas aprovadas.

```text
STRUCTURAL_MODEL_SELECTOR_PHASE15.md
tools/experiments/map_structural_model_selector_slots4_5.py
```

### Fase 16 — descoberta do LZO1X

Identificou o contêiner comprimido e normalizou todas as 34 capturas das Fases
14 e 15 para o payload estrutural fixo de 89 bytes.

```text
STRUCTURAL_EFFECT_STATE_PHASE16.md
tools/analysis/structural_effect_state.py
tests/fixtures/structural_effect_state/
```

### Fase 17 — integração ao parser estável

Promoveu o decodificador para `tools/commands/` e adicionou classe, modelo,
seletor e registros de efeito sem quebrar a API anterior de ordem e bypass.

```text
STRUCTURAL_CHAIN_INTEGRATION_PHASE17.md
```

### Fase 18 — validação física estrutural

Moveu a posição visual 5 para 4 e restaurou 4 para 5. Ordem, classe, modelo,
seletor, bypass e payload foram aprovados nas duas capturas.

Também revelou que a primeira seleção após cold boot pode ser perdida.

```text
STRUCTURAL_CHAIN_LIVE_VALIDATION_PHASE18.md
tools/experiments/validate_structural_chain_live.py
```

### Fase 19 — monitor consolidado e cold boot

Uniu preset, nome, etiqueta e parser de cadeia em
`tools.commands.matribox_monitor`. Acrescentou reenvios automáticos para
consultas perdidas após ligar a pedaleira.

A primeira versão ainda aguardava passivamente uma resposta estrutural que a
pedaleira não enviava ao trocar de preset.

```text
MATRIBOX_MONITOR_PHASE19.md
```

### Fase 20 — dump não destrutivo

Passou a solicitar o dump do preset atual, reconstruir os fragmentos e extrair
a cadeia do payload de 1.211 bytes. Foi validado offline contra 100 dumps
físicos e fisicamente em vários presets.

```text
MATRIBOX_MONITOR_PHASE20.md
tools/commands/preset_dump_state.py
tests/fixtures/preset_dump_chain/
```

### Fase 21 — bypass em tempo real

Passou a interpretar as respostas de 62 bytes emitidas ao ligar/desligar um
efeito. Validou dez capturas físicas dos slots 1–5 e foi aprovado ao vivo.

```text
MATRIBOX_MONITOR_PHASE21.md
tools/commands/effect_slot_state.py
tests/fixtures/effect_slot_state/
```

## 11. Estado de validação no marco atual

Suíte completa após a Fase 21:

```text
Ran 306 tests
OK
```

Validação física aprovada pelo usuário:

- inicialização e recuperação após cold boot;
- leitura de preset, nome e etiqueta;
- leitura de cadeias vazias e cadeias com vários efeitos;
- identificação correta dos modelos exibidos;
- mudança da ordem visual em tempo real;
- liga/desliga em tempo real sem novo dump;
- preservação da ordem durante atualização de bypass.

Fixtures físicas de regressão ficam em:

```text
tests/fixtures/structural_effect_state/
tests/fixtures/preset_dump_chain/
tests/fixtures/effect_slot_state/
```

## 12. Limitações e cuidados conhecidos

- A primeira mensagem enviada imediatamente após ligar a pedaleira pode não
  gerar resposta. O monitor possui reenvios automáticos; não remover essa
  proteção.
- Respostas auxiliares de 54 e 128 bytes devem continuar sendo ignoradas pelos
  parsers estruturais.
- O byte de checksum observado em respostas imediatas de bypass não é estável
  entre capturas fisicamente equivalentes. O parser valida os demais campos
  fixos, slot e estado, mas não usa esse byte para rejeitar a resposta.
- Um slot interno não é a mesma coisa que sua posição visual.
- Dados ocultos em slots fora da ordem visual não devem ser mostrados como
  efeitos ativos da cadeia.
- Não assumir offsets no SysEx comprimido; sempre trabalhar sobre o payload
  LZO1X descomprimido.
- Mudanças em parâmetros internos de efeitos ainda não fazem parte do monitor.

## 13. Próximos passos recomendados

O núcleo de monitoramento está estável. As próximas frentes devem ser tratadas
separadamente e com novas capturas quando necessário:

1. verificar e, se necessário, integrar atualização ao vivo de troca de modelo
   ou classe sem depender de nova troca de preset;
2. mapear parâmetros internos dos efeitos e suas mensagens de atualização;
3. criar uma camada de apresentação mais amigável sobre o monitor estável
   (interface de terminal, desktop ou API), sem misturar UI com o protocolo;
4. investigar nomes e metadados de posições CLONE;
5. estudar importação NAM e IR sem reenviar comandos desconhecidos;
6. revisar e organizar scripts experimentais antigos somente depois de manter
   fixtures e evidências necessárias aos testes.

## 14. Checklist obrigatório para o próximo commit

```text
[ ] A funcionalidade foi validada offline.
[ ] A funcionalidade MIDI foi validada fisicamente, quando aplicável.
[ ] A suíte unittest completa passou.
[ ] python -m compileall tools tests passou.
[ ] git diff --check passou.
[ ] docs/PROJECT_CONTINUITY.md foi atualizado.
[ ] README.md foi atualizado se o uso público mudou.
[ ] O escopo do git add foi revisado; arquivos locais não relacionados ficaram fora.
[ ] O commit será feito na main, salvo pedido explícito em contrário.
```
