# Continuidade do projeto Matribox II Pro SysEx Research

> Documento oficial de retomada entre conversas.
>
> **Última atualização:** 8 de agosto de 2026
> **Marco consolidado:** Fase 69 — classe AMP concluída, 63/63 modelos fisicamente validados
> **Trabalho atual:** consolidação final da branch `research/amp-parameters`
> **Próximo passo:** executar a suíte local, revisar o diff e consolidar a branch; depois iniciar a próxima classe de parâmetros
> **Branch estável:** `main`
> **Branch de pesquisa atual:** `research/amp-parameters`

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

- Manter a branch `main` somente com marcos estáveis e fisicamente aprovados.
- Usar uma branch de pesquisa por classe de efeitos, começando por
  `research/dyn-parameters`; não criar uma branch por efeito individual.
- O usuário extrai pacotes ZIP manualmente; não é necessário fornecer comandos
  de extração.
- Reservar o preset 56B para descoberta/captura e o 56C para validação física;
  o 56C pode manter doze efeitos para testar início, meio e fim da cadeia.
- A suíte oficial usa `unittest`, não `pytest`.
- Nunca executar `git add`, commit ou limpeza antes da aprovação dos testes
  físicos quando a mudança envolver comunicação MIDI.
- Preservar capturas e experimentos enquanto uma hipótese ainda estiver em
  validação.
- Após a confirmação física, atualizar este documento, revisar o escopo,
  executar a suíte completa e então consolidar o commit.
- Não enviar comandos desconhecidos ou potencialmente destrutivos à pedaleira.
- Reservar a raiz do repositório para arquivos essenciais: `README.md`,
  `requirements.txt`, arquivos do Git e diretórios principais.
- Guardar relatórios históricos de fases em `docs/phases/`.
- Manter `venv/`, caches e `data/dumps/` fora do Git; dumps brutos devem ser
  arquivados externamente ou preservados apenas como ZIP local.

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
- alterar modelo, bypass e volume usando comandos conhecidos;
- reconhecer e decodificar em tempo real o parâmetro `GAIN` de qualquer
  instância de `DYN / M-BOOST` por um motor genérico orientado pelo JSON;
- reconhecer `SUSTAIN` e `VOLUME` do `DYN / COMP1`, mantendo os dois valores
  independentes no mesmo slot;
- reconhecer `GAIN`, `+3dB` e `BRIGHT` do `DYN / E-BOOST`, incluindo
  conversão física `0/1` para booleanos e exibição `ligado/desligado`;
- reconhecer `SHAPE` do `DYN / AC WOODY` e `THRESHOLD` do `DYN / GATE 1`,
  ambos inteiros de 0 a 100;
- reconhecer `BODY`, `TOP`, `VOLUME` e o `MODE` enum nomeado do `DYN / AC SIM`,
  convertendo 0–3 para STANDARD/JUMBO/ENHANCED/PIEZO pelo catálogo;
- decodificar `THRESHOLD`, `RATIO`, `ATTACK`, `RELEASE` e `HOLD` do
  `DYN / GATE 3`, preservando o float32 completo e exibindo tempos em `ms` ou
  `s` conforme o catálogo;
- apresentar parâmetros catalogados no monitor principal e manter valores
  separados por slot interno, efeito e parâmetro;
- hidratar valores persistidos dos parâmetros catalogados ao carregar o preset
  e após adicionar, substituir ou reordenar efeitos;
- carregar as 16 classes e 267 efeitos a partir de um catálogo JSON versionado
  e independente de Python/Windows;
- hidratar e exibir 555 parâmetros catalogados em 115 efeitos fisicamente
  validados, cobrindo integralmente as classes DYN, FREQ, WAH, DRIVE e AMP;
- representar parâmetros com domínio condicionado, como RATE do FILTER, sem
  fabricar mensagens USB para defaults implícitos do dispositivo.

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

Quando um efeito possui parâmetros catalogados, o monitor acrescenta linhas
como:

```text
  2. DYN / M-BOOST — ligado
     GAIN: 50

  3. DYN / COMP1 — ligado
     SUSTAIN: 20
     VOLUME: 50

  4. DYN / E-BOOST — ligado
     GAIN: 40
     +3dB: desligado
     BRIGHT: ligado
```

Os valores são hidratados pelo dump inicial. Eventos `0x1C` posteriores
substituem imediatamente o valor salvo da instância correta.

### Comportamentos fisicamente confirmados

- A troca de preset atualiza endereço, nome, etiqueta e solicita a nova cadeia.
- A mudança da ordem dos efeitos redesenha a cadeia na ordem correta.
- Adicionar, substituir ou reordenar efeitos solicita um novo dump somente
  leitura e hidrata os parâmetros do estado estrutural atualizado.
- Ligar ou desligar um efeito atualiza imediatamente somente o estado daquele
  slot, sem solicitar um novo dump completo.
- A inicialização após ligar a pedaleira possui reenvios automáticos; não é mais
  necessário encerrar e executar o monitor uma segunda vez.
- O monitor é somente leitura durante a consulta da cadeia. Ele não move,
  substitui, liga/desliga nem salva efeitos.

### Modos de saída do monitor

O comportamento histórico continua sendo o padrão e permanece append-only:

```powershell
python -m tools.commands.matribox_monitor
```

Esse modo não apaga a saída anterior e continua recomendado para pesquisa,
validação física e evidências que precisam ser compartilhadas.

O modo painel, validado fisicamente após a Fase 35, usa o buffer alternativo do
terminal, oculta o cursor durante a execução e redesenha o quadro inteiro após
cada mudança:

```powershell
python -m tools.commands.matribox_monitor --live
```

A saída de progresso da inicialização e do dump é silenciada somente nesse modo
para impedir escrita concorrente sobre o painel. Ao encerrar com `Ctrl+C`, o
cursor e o buffer normal do terminal são restaurados.

Opcionalmente, um log compacto pode ser mantido enquanto o painel permanece
limpo:

```powershell
python -m tools.commands.matribox_monitor --live --log data/dumps/monitor_live.txt
```

O `--log` não altera a comunicação MIDI; apenas persiste eventos já observados
pelo monitor. O diretório `data/dumps/` permanece ignorado pelo Git.

### Validadores de parâmetro

O validador genérico da Fase 23B usa o mesmo motor do monitor:

```powershell
python -m tools.experiments.validate_effect_parameters_live
```

O validador histórico específico do primeiro parâmetro fisicamente catalogado,
o `GAIN` do `DYN / M-BOOST`, permanece disponível:

```powershell
python -m tools.experiments.validate_mboost_gain_live
```

Ambos reutilizam a inicialização e o dump não destrutivo do monitor. Eles
escutam respostas `0x1C`, cruzam o slot interno com a cadeia atual e não enviam
comandos de escrita de parâmetro.

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

### 6.4 Parâmetros internos e identidade pelo contexto da cadeia

A Fase 22 isolou o `DYN / M-BOOST / GAIN`. A Fase 24 acrescentou
`DYN / COMP1 / SUSTAIN` e `VOLUME` e revelou uma correção arquitetural
essencial. A Fase 25 acrescentou `DYN / E-BOOST / GAIN`, `+3dB` e
`BRIGHT`, validando o primeiro uso de `value_type: boolean`. A Fase 26
acrescentou `DYN / AC WOODY / SHAPE` e `DYN / GATE 1 / THRESHOLD`. A
Fase 27 acrescentou os quatro controles contínuos do `DYN / COMP2`. A
Fase 28 acrescentou os sete controles contínuos do `DYN / COMP3`.

Estrutura confirmada da resposta de 70 bytes:

```text
comando                  0x1C
slot interno             índices 39–40, zero-based
classe DYN observada     índices 41–42
seletor do parâmetro     índice 48
valor                    índices 59–62
marcador/tipo            índices 63–64 = 01 01
codec                     16 bits superiores de float32 little-endian em nibbles
```

Seletores catalogados:

```text
M-BOOST / GAIN      → 0
COMP1 / SUSTAIN     → 0
COMP1 / VOLUME      → 1
COMP2 / SUSTAIN     → 0
COMP2 / ATTACK      → 1
COMP2 / VOLUME      → 2
COMP2 / CLIPPING    → 3
COMP3 / THRESHOLD   → 0
COMP3 / RATIO       → 1
COMP3 / VOLUME      → 2
COMP3 / ATTACK      → 3
COMP3 / RELEASE     → 4
COMP3 / TONE        → 5
COMP3 / BLEND       → 6
E-BOOST / GAIN      → 0
E-BOOST / +3dB      → 1
E-BOOST / BRIGHT    → 2
AC WOODY / SHAPE    → 0
GATE 1 / THRESHOLD  → 0
```

Os índices `21–22` permanecem `01 04` no M-BOOST, COMP1, COMP2, COMP3,
E-BOOST, AC WOODY e GATE 1.
Portanto, eles não representam o `model_id` do efeito. A mensagem informa slot,
seletor e valor; a identidade do efeito deve ser obtida da cadeia estrutural
atual naquele slot.

O E-BOOST confirmou que o codec `upper_float32_nibbles_v1` também representa
booleanos numéricos:

```text
0 → 00 00 00 00 → desligado
1 → 08 00 03 0F → ligado
```

A conversão para `False/True` e a apresentação humana são determinadas pelo
`value_type: boolean` do parâmetro no catálogo.

Fluxo correto:

```text
EffectParameterSignal
  → slot interno
  → efeito real na cadeia
  → parâmetros daquele efeito no JSON
  → message_match
  → EffectParameterEvent
```

Fixtures:

```text
tests/fixtures/mboost_gain/
tests/fixtures/comp1_parameters/
tests/fixtures/comp2_parameters/
tests/fixtures/comp3_parameters/
tests/fixtures/ac_boost_parameters/
tests/fixtures/bb_boost_parameters/
tests/fixtures/ac_sim_parameters/
tests/fixtures/rc_boost_parameters/
tests/fixtures/fat_boost_parameters/
tests/fixtures/gate2_parameters/
tests/fixtures/gate3_parameters/
tests/fixtures/e_boost_parameters/
tests/fixtures/ac_woody_parameters/
tests/fixtures/gate1_parameters/
```

### 6.5 Catálogo JSON multiplataforma

A Fase 23A migrou todos os dados estáticos de `effect_catalog.py` para:

```text
catalog/catalog.json
catalog/effects/<classe>/index.json
catalog/effects/<classe>/<efeito>.json
catalog/protocol_profiles/
catalog/value_codecs/
catalog/schemas/
```

O carregador fica em `tools/catalog/` e valida versão, chaves, menus, IDs,
seletores, caminhos relativos, parâmetros, perfis e codecs. O arquivo
`tools/commands/effect_catalog.py` agora é uma fachada: continua exportando os
mesmos nomes usados pelo monitor e pelos comandos, mas deriva todos os dados do
JSON.

A equivalência foi comprovada contra um snapshot anterior à migração:

```text
tests/fixtures/effect_catalog/legacy_catalog_snapshot.json
```

M-BOOST, COMP1, COMP2, COMP3, E-BOOST, AC-BOOST, BB-BOOST, RC-BOOST,
FAT BOOST, AC WOODY, AC SIM, GATE 1, GATE 2 e GATE 3 são os quatorze efeitos
DYN preenchidos. FILTER, OCTAVER, DUAL MELODY, PITCH, HARMONY D, PITCH S e
RING MOD são os sete primeiros efeitos FREQ parametrizados. Os outros 246 efeitos permanecem explicitamente
`pending`, sem parâmetros presumidos.

### 6.6 Motor genérico de parâmetros — Fase 23B

Arquivos principais:

```text
tools/parameters/codecs.py
tools/parameters/decoder.py
tools/parameters/state.py
tools/experiments/validate_effect_parameters_live.py
tests/test_effect_parameters.py
```

O decoder consulta o perfil, o codec e o `message_match` declarados no
catálogo. Desde a correção da Fase 24, ele primeiro produz
`EffectParameterSignal`, sem presumir o efeito. O núcleo do monitor consulta a
cadeia estrutural e então resolve `EffectParameterEvent` contra o efeito real
do slot. `mboost_gain.py` permanece como fachada de compatibilidade.

O estado guarda o último valor por slot interno, efeito e parâmetro. Eventos
são rejeitados quando o seletor não pertence ao efeito atual. Valores são
descartados ao trocar preset ou substituir o efeito.

Desde a Fase 36, o valor inicial é extraído do dump `0x10`. Mudanças
estruturais disparam uma nova consulta somente leitura para hidratar efeitos
adicionados ou substituídos.

Relatório:

```text
docs/phases/EFFECT_PARAMETER_ENGINE_PHASE23B.md
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
| `0x1C` | 70 bytes | atualização de parâmetro; M-BOOST/GAIN validado |

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
catalog/catalog.json
catalog/effects/
catalog/protocol_profiles/
catalog/value_codecs/
```

Fachada compatível:

```text
tools/commands/effect_catalog.py
```

Alguns IDs de modelo se repetem dentro da mesma classe. O seletor secundário é
necessário para desambiguar casos como modelos AMP distintos com o mesmo ID.

O catálogo usa JSON Schema Draft 2020-12, caminhos relativos portáteis e
versões explícitas. Ele pode ser consumido pelo laboratório Python e, no
futuro, por Kotlin/Android e desktop. Nesta candidata há 61 parâmetros
fisicamente confirmados em quatorze efeitos DYN e três FREQ. O AC SIM usa
`value_type: enum`, o GATE 3 usa `float32_nibbles_v1` e apresentação de tempo,
e o FILTER introduz `value_domain` controlado por outro parâmetro. Os outros
250 efeitos permanecem sem dados inventados.

## 10. Histórico consolidado das Fases 14–24

### Fase 14 — classe e modelo por slot

Mapeou os campos estruturais dos slots 1–5 usando mudanças controladas de
classe e modelo. Confirmou respostas auxiliares de 128 bytes e tamanhos
estruturais variáveis.

Arquivos relacionados:

```text
docs/phases/STRUCTURAL_CLASS_MODEL_PHASE14.md
tools/experiments/map_structural_class_model_all_slots.py
```

### Fase 15 — modelo e seletor

Separou mudanças de modelo e seletor nos slots 4 e 5. Confirmou que offsets
brutos fixos não eram seguros e preservou 13 capturas aprovadas.

```text
docs/phases/STRUCTURAL_MODEL_SELECTOR_PHASE15.md
tools/experiments/map_structural_model_selector_slots4_5.py
```

### Fase 16 — descoberta do LZO1X

Identificou o contêiner comprimido e normalizou todas as 34 capturas das Fases
14 e 15 para o payload estrutural fixo de 89 bytes.

```text
docs/phases/STRUCTURAL_EFFECT_STATE_PHASE16.md
tools/analysis/structural_effect_state.py
tests/fixtures/structural_effect_state/
```

### Fase 17 — integração ao parser estável

Promoveu o decodificador para `tools/commands/` e adicionou classe, modelo,
seletor e registros de efeito sem quebrar a API anterior de ordem e bypass.

```text
docs/phases/STRUCTURAL_CHAIN_INTEGRATION_PHASE17.md
```

### Fase 18 — validação física estrutural

Moveu a posição visual 5 para 4 e restaurou 4 para 5. Ordem, classe, modelo,
seletor, bypass e payload foram aprovados nas duas capturas.

Também revelou que a primeira seleção após cold boot pode ser perdida.

```text
docs/phases/STRUCTURAL_CHAIN_LIVE_VALIDATION_PHASE18.md
tools/experiments/validate_structural_chain_live.py
```

### Fase 19 — monitor consolidado e cold boot

Uniu preset, nome, etiqueta e parser de cadeia em
`tools.commands.matribox_monitor`. Acrescentou reenvios automáticos para
consultas perdidas após ligar a pedaleira.

A primeira versão ainda aguardava passivamente uma resposta estrutural que a
pedaleira não enviava ao trocar de preset.

```text
docs/phases/MATRIBOX_MONITOR_PHASE19.md
```

### Fase 20 — dump não destrutivo

Passou a solicitar o dump do preset atual, reconstruir os fragmentos e extrair
a cadeia do payload de 1.211 bytes. Foi validado offline contra 100 dumps
físicos e fisicamente em vários presets.

```text
docs/phases/MATRIBOX_MONITOR_PHASE20.md
tools/commands/preset_dump_state.py
tests/fixtures/preset_dump_chain/
```

### Fase 21 — bypass em tempo real

Passou a interpretar as respostas de 62 bytes emitidas ao ligar/desligar um
efeito. Validou dez capturas físicas dos slots 1–5 e foi aprovado ao vivo.

```text
docs/phases/MATRIBOX_MONITOR_PHASE21.md
tools/commands/effect_slot_state.py
tests/fixtures/effect_slot_state/
```

### Fase 22 — M-BOOST / GAIN isolado

Isolou o comando `0x1C`, o slot interno e a codificação do GAIN usando quatro
capturas controladas. Preservou 27 respostas SysEx físicas mínimas e criou um
validador somente de leitura.

A validação ao vivo aprovou múltiplos M-BOOSTs simultâneos nos slots internos
2, 8, 10 e 12, incluindo valores até 100, sem confundir as instâncias.

```text
docs/phases/MBOOST_GAIN_VALIDATION_PHASE22.md
tools/commands/mboost_gain.py
tools/experiments/validate_mboost_gain_live.py
tests/test_mboost_gain.py
tests/fixtures/mboost_gain/
```

### Fase 23A — catálogo JSON multiplataforma

Exportou automaticamente as 16 classes e 267 efeitos do catálogo Python para
arquivos JSON individuais, criou schemas, carregador, perfil de protocolo e
codec de valor. `effect_catalog.py` passou a funcionar como fachada compatível.

A comparação contra o snapshot legado confirmou equivalência registro por
registro. O M-BOOST/GAIN foi registrado como primeiro parâmetro validado. As
fases posteriores ampliaram o catálogo sem alterar a equivalência estrutural
original.

```text
docs/phases/EFFECT_CATALOG_JSON_PHASE23A.md
catalog/
tools/catalog/
tools/migrations/export_effect_catalog_to_json.py
tests/test_effect_catalog_json.py
tests/fixtures/effect_catalog/legacy_catalog_snapshot.json
```

### Fase 23B — motor genérico de parâmetros

Criou codecs, decoder e estado genéricos orientados pelo catálogo JSON,
preservou a API específica da Fase 22 e integrou parâmetros ao monitor. As 27
fixtures físicas são decodificadas pelo novo motor.

A validação física aprovou o validador genérico e o monitor principal com dois
M-BOOSTs simultâneos nos slots internos 2 e 3, valores independentes e
preservação da identidade interna após mudança de posição visual.

```text
docs/phases/EFFECT_PARAMETER_ENGINE_PHASE23B.md
tools/parameters/
tools/experiments/validate_effect_parameters_live.py
tests/test_effect_parameters.py
```


### Fase 24 — DYN / COMP1 com dois parâmetros

Capturou `SUSTAIN` e `VOLUME` nos slots internos 1 e 2, ambos de 0 a 100,
preservando 22 respostas físicas. Confirmou o seletor no índice 48:

```text
SUSTAIN → 0
VOLUME  → 1
```

Também provou que os índices `21–22` não são o model_id, pois M-BOOST e COMP1
usam o mesmo endereço `01 04`. O motor foi corrigido para resolver o efeito
pela cadeia atual antes de interpretar o seletor.

```text
docs/phases/DYN_COMP1_PARAMETERS_PHASE24.md
catalog/effects/dyn/001_comp1.json
tests/fixtures/comp1_parameters/
```

A suíte offline passou com 349 testes. A validação física no preset `56B`
aprovou o monitor com múltiplos COMP1, SUSTAIN e VOLUME independentes,
coexistência com M-BOOST e substituição de efeito sem colisão do seletor `0`.

### Fase 25 — DYN / E-BOOST com inteiro e booleanos

Capturou `GAIN`, `+3dB` e `BRIGHT` nos slots internos 1 e 2. O GAIN usa
0–100, enquanto os dois interruptores usam `0/1` pelo mesmo codec de valor:

```text
GAIN    → seletor 0
+3dB    → seletor 1
BRIGHT  → seletor 2
```

A captura combinada confirmou mensagens independentes para os dois
interruptores. Foram preservadas 19 respostas físicas únicas.

```text
docs/phases/DYN_EBOOST_PARAMETERS_PHASE25.md
catalog/effects/dyn/005_e_boost.json
tests/fixtures/e_boost_parameters/
```

A suíte offline passou com 356 testes. A validação física no preset `56B`
aprovou a ordem dos três parâmetros, valores booleanos em português, atualização
independente, duas instâncias simultâneas com estados separados e coexistência
com COMP1 e outros efeitos da cadeia.

### Fase 26 — DYN / AC WOODY e GATE 1

As capturas controladas confirmaram dois efeitos de parâmetro único:

```text
AC WOODY / SHAPE       → seletor 0, inteiro 0–100
GATE 1 / THRESHOLD     → seletor 0, inteiro 0–100
```

Ambos reutilizam `effect_parameter_response_1c_v1` e
`upper_float32_nibbles_v1`. Os slots internos humanos 1 e 2 foram observados.
Foram preservadas 11 respostas físicas únicas para cada efeito:

```text
docs/phases/DYN_AC_WOODY_GATE1_PARAMETERS_PHASE26.md
catalog/effects/dyn/010_ac_woody.json
catalog/effects/dyn/012_gate_1.json
tests/fixtures/ac_woody_parameters/
tests/fixtures/gate1_parameters/
```

A integração não exigiu mudança no motor. A validação física no monitor
principal aprovou SHAPE e THRESHOLD independentes, duas instâncias de AC WOODY
com estados separados, coexistência com os demais efeitos catalogados e
preservação dos valores após mudança da ordem visual.

### Fase 27 — DYN / COMP2 com quatro parâmetros

As seis capturas controladas confirmaram quatro controles contínuos de 0 a 100:

```text
SUSTAIN   → seletor 0
ATTACK    → seletor 1
VOLUME    → seletor 2
CLIPPING  → seletor 3
```

Os slots internos humanos 1 e 2 foram observados e 49 respostas físicas únicas
foram preservadas. A captura combinada incluiu a sequência acidental
`CLIPPING 54 → 5 → 50`; o valor 5 foi corretamente decodificado e mantido como
evidência.

```text
docs/phases/DYN_COMP2_PARAMETERS_PHASE27.md
catalog/effects/dyn/002_comp2.json
tests/fixtures/comp2_parameters/
```

A integração reutiliza integralmente o perfil `0x1C`, o codec compartilhado e
o estado genérico por slot. O núcleo do decoder e do monitor não precisou ser
alterado. A suíte offline passou com 370 testes. A validação física aprovou a
apresentação e atualização independente dos quatro controles, duas instâncias
simultâneas com estados separados e coexistência com outros efeitos DYN.


### Fase 28 — DYN / COMP3 com sete parâmetros

As nove capturas controladas confirmaram sete controles contínuos de 0 a 100:

```text
THRESHOLD  → seletor 0
RATIO      → seletor 1
VOLUME     → seletor 2
ATTACK     → seletor 3
RELEASE    → seletor 4
TONE       → seletor 5
BLEND      → seletor 6
```

Os slots internos humanos 1 e 2 foram observados e 84 respostas físicas únicas
foram preservadas:

```text
docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md
catalog/effects/dyn/003_comp3.json
tests/fixtures/comp3_parameters/
```

A integração reutiliza integralmente o perfil `0x1C`, o codec compartilhado e
o estado genérico por slot. O núcleo do decoder e do monitor não precisou ser
alterado. A suíte offline passou com 376 testes.

A validação física aprovou os sete parâmetros na ordem do catálogo, atualização
independente, preservação dos valores durante mudanças estruturais e duas
instâncias simultâneas com estados separados. A primeira manteve
`20, 45, 66, 59, 59, 62, 59`; a segunda recebeu
`25, 8, 30, 26, 24, 30, 33`.


## 11. Estado de validação no trabalho atual

Marco estável da classe DYN:

```text
Ran 401 tests
OK
```

A Fase 33 candidata adiciona FILTER e elevou a suíte offline para:

```text
Ran 409 tests
OK
```

A candidata cobre 55 fixtures físicas do FILTER nos slots humanos 1 e 2, os
seis seletores, RATE numérico com SYNC desligado, as onze divisões com SYNC
ligado, defaults implícitos `10` e `1/4`, ausência de evento RATE automático na
transição de SYNC, e a descoberta de que os índices `41–42` do envelope 0x1C
não são o class_id estrutural.

O estado derivado não cria `EffectParameterEvent` sintético: snapshots marcam
`value_origin = derived_device_rule`, enquanto pacotes reais usam
`observed_usb`. Se RATE `0–10` chegar antes de SYNC, o monitor mostra
`aguardando SYNC` para não escolher um domínio por suposição.

Validação física da Fase 33: **aprovada** no monitor principal, incluindo RATE
condicionado por SYNC e coexistência com efeito DYN.

## 12. Limitações e cuidados conhecidos

- A primeira mensagem enviada imediatamente após ligar a pedaleira pode não
  gerar resposta. O monitor possui reenvios automáticos; não remover essa
  proteção.
- Respostas auxiliares de 54 e 128 bytes devem continuar sendo ignoradas pelos
  parsers estruturais.
- O byte de checksum observado em respostas imediatas de bypass não é estável
  entre capturas fisicamente equivalentes.
- Um slot interno não é a mesma coisa que sua posição visual.
- Dados ocultos em slots fora da ordem visual não devem ser mostrados como
  efeitos ativos da cadeia.
- Não assumir offsets no SysEx comprimido; trabalhar sobre o payload LZO1X
  descomprimido.
- A mensagem `0x1C` não identifica de forma confiável o modelo do efeito;
  resolver sempre pela cadeia atual no slot interno.
- Seletores se repetem entre efeitos diferentes e nunca devem ser interpretados
  sem o contexto do efeito real.
- Booleanos continuam restritos aos valores físicos `0/1`.
- O valor inicial do parâmetro não é lido do dump; aparece como `aguardando
  alteração` até o primeiro evento ao vivo.
- Tempos do GATE 3 são preservados internamente em milissegundos. A tela pode
  arredondar `5037 ms` para `5,0 s`; não substituir o valor lógico pelo texto
  arredondado.
- O perfil agora expõe oito nibbles. Codecs históricos dependem de
  `input_slice: [4, 8]`; não remover essa compatibilidade.
- Não criar parser Python por efeito. A expansão deve continuar orientada por
  catálogo, perfis, codecs e regras de apresentação genéricas.
- Não colocar caminhos absolutos, `pickle` ou estruturas exclusivas de Python
  no catálogo.
- A captura curta antiga chamada de slot 2 era fisicamente slot 1; usar a
  captura standalone corrigida como evidência do slot humano 2.

## 13. Próximos passos recomendados

1. aplicar a documentação final de aprovação física da Fase 32;
2. executar os 401 testes, `compileall` e `git diff --check`;
3. revisar o escopo preparado da Fase 32;
4. criar o commit final na `research/dyn-parameters`;
5. enviar a branch e promover por fast-forward à `main`;
6. manter a classe DYN encerrada e escolher a próxima classe;
7. criar uma nova branch de pesquisa específica para essa classe.

A futura interface deve consumir `EffectParameterEvent`, `display_text` e as
definições JSON sem conhecer offsets, nibbles ou detalhes MIDI.

## 14. Checklist obrigatório para o próximo commit

```text
[x] A funcionalidade foi validada offline.
[x] A integração da Fase 32 foi validada fisicamente no monitor.
[x] A suíte unittest completa passou: 401 testes.
[x] python -m compileall tools tests passou.
[x] Os JSONs e o exportador foram validados.
[x] git diff --check passou.
[x] docs/PROJECT_CONTINUITY.md foi atualizado.
[x] README.md foi atualizado.
[ ] O escopo do git add deve ser revisado pelo usuário.
[ ] O commit e a promoção à main devem ser executados pelo usuário.
```

## 15. Atualização atual — Fase 28 consolidada: DYN / COMP3

A Fase 28 foi aprovada offline e fisicamente na branch
`research/dyn-parameters`.

Parâmetros consolidados:

```text
THRESHOLD  → seletor 0, inteiro 0–100
RATIO      → seletor 1, inteiro 0–100
VOLUME     → seletor 2, inteiro 0–100
ATTACK     → seletor 3, inteiro 0–100
RELEASE    → seletor 4, inteiro 0–100
TONE       → seletor 5, inteiro 0–100
BLEND      → seletor 6, inteiro 0–100
```

Foram preservadas 84 fixtures físicas: 70 no slot humano 1 e 14 no slot humano
2. Todos os parâmetros reutilizam `effect_parameter_response_1c_v1`,
`upper_float32_nibbles_v1`, marcador/tipo `01 01` e endereço opaco `01 04`.
A identidade continua sendo resolvida pela cadeia atual do slot.

Estado arquitetural:

- nenhum parser, codec ou perfil específico para COMP3 foi criado;
- o monitor continua orientado pelo catálogo JSON;
- `EffectParameterState` mantém os sete valores por slot, efeito e parâmetro;
- `catalog_version` está em 6;
- sete efeitos DYN e 19 parâmetros estão catalogados;
- 260 efeitos permanecem pendentes.

Validação offline consolidada:

```text
Ran 376 tests
OK
```

Também passaram `python -m compileall tools tests`, validação dos 319 arquivos
JSON e `git diff --check`.

Validação física consolidada:

```text
COMP3 A
THRESHOLD 20 | RATIO 45 | VOLUME 66 | ATTACK 59
RELEASE 59   | TONE 62  | BLEND 59

COMP3 B
THRESHOLD 25 | RATIO 8  | VOLUME 30 | ATTACK 26
RELEASE 24   | TONE 30  | BLEND 33
```

O primeiro conjunto permaneceu estável enquanto a cadeia foi ampliada. A
segunda instância recebeu os próprios sete valores sem contaminar a primeira.
O log não contém uma troca explícita de posição entre as duas instâncias, mas
confirma isolamento por slot e preservação durante mudanças estruturais.

Limitações preservadas:

- valores iniciais ainda aparecem como `aguardando alteração`;
- seletores não identificam o efeito sem o contexto da cadeia;
- o monitor permanece somente leitura;
- respostas auxiliares não `0x1C` continuam ignoradas.

### Próximo passo exato

1. executar novamente os 376 testes, `compileall` e `git diff --check`;
2. adicionar somente os arquivos da Fase 28 e desta aprovação;
3. criar o commit `feat: add COMP3 parameters`;
4. enviar `research/dyn-parameters`;
5. promover por fast-forward à `main`;
6. iniciar a Fase 29 com AC-BOOST e BB-BOOST;
7. capturar o AC SIM com MODE separado e tratá-lo em fase posterior com suporte
   categórico genérico.

## 16. Atualização atual — Fase 29 candidata: AC-BOOST e BB-BOOST

A implementação candidata da Fase 29 foi preparada sobre a Fase 28
fisicamente aprovada.

Parâmetros adicionados aos dois efeitos:

```text
GAIN    → seletor 0, inteiro 0–100
VOLUME  → seletor 1, inteiro 0–100
BASS    → seletor 2, inteiro 0–100
TREBLE  → seletor 3, inteiro 0–100
```

Evidências físicas preservadas:

```text
AC-BOOST → 32 fixtures, slots humanos 1 e 2
BB-BOOST → 32 fixtures, slots humanos 1 e 2
```

Cada efeito possui seis capturas controladas: quatro individuais, uma
combinada com valores exclusivos e uma validação curta no slot 2. As respostas
auxiliares de 54 bytes continuam ignoradas. No BB-BOOST, o evento extra
`VOLUME = 50` foi documentado sem duplicar o mesmo estado físico.

Estado arquitetural:

- nenhum parser, codec ou perfil específico foi criado;
- ambos reutilizam `effect_parameter_response_1c_v1`;
- ambos reutilizam `upper_float32_nibbles_v1`;
- o efeito é resolvido pela cadeia atual do slot;
- o monitor lê ordem, nomes e faixas diretamente do JSON;
- `catalog_version` está em 7;
- nove efeitos DYN e 27 parâmetros estão catalogados;
- 258 efeitos permanecem pendentes.

Validação offline candidata:

```text
Ran 382 tests
OK
```

Também passaram `python -m compileall tools tests`, a validação dos arquivos
JSON e a reprodução dos parâmetros pelo exportador do catálogo.

Estado físico consolidado:

```text
AC-BOOST
GAIN 33 | VOLUME 54 | BASS 43 | TREBLE 58

BB-BOOST
GAIN 26 | VOLUME 43 | BASS 66 | TREBLE 30
```

O monitor apresentou os dois efeitos simultaneamente, atualizou os quatro
parâmetros de cada um sem colisão e preservou os valores do outro efeito. O
bypass independente de AC-BOOST e BB-BOOST também foi acompanhado sem perda do
estado dos parâmetros.

O log final não inclui duas instâncias do mesmo boost nem uma troca explícita
de posição visual. As capturas físicas nos slots humanos 1 e 2 e a coexistência
sem colisões sustentam a aprovação da fase, preservando essa observação como
limitação do teste final.

### Próximo passo exato

1. aplicar `matribox_phase29_physical_approval_docs.zip`;
2. executar novamente os 382 testes, `compileall` e `git diff --check`;
3. revisar o escopo do `git add` e manter capturas futuras fora do commit;
4. criar o commit `feat: add AC-BOOST and BB-BOOST parameters`;
5. enviar `research/dyn-parameters`;
6. promover por fast-forward à `main`;
7. iniciar fase própria para AC SIM, incluindo suporte genérico a valores
   categóricos nomeados no parâmetro `MODE`.


## 17. Atualização atual — Fase 30 aprovada: RC-BOOST, FAT BOOST e GATE 2

A Fase 30 foi integrada e aprovada sobre a Fase 29 fisicamente consolidada.

Parâmetros catalogados:

```text
RC-BOOST
GAIN 0 | VOLUME 1 | BASS 2 | TREBLE 3

FAT BOOST
BASS 0 | TREBLE 1 | VOLUME 2 | LOW CUT 3

GATE 2
THRESHOLD 0 | ATTACK 1 | RELEASE 2
```

Os números representam os seletores no índice `48`. Os dez controles
contínuos usam inteiro `0–100`; LOW CUT usa `value_type: boolean`, com
`OFF=0` e `ON=1`. Todos reutilizam `effect_parameter_response_1c_v1`,
`upper_float32_nibbles_v1`, marcador/tipo `01 01` e endereço opaco `01 04`.

Evidências preservadas:

```text
RC-BOOST  → 32 fixtures
FAT BOOST → 28 fixtures
GATE 2    → 23 fixtures
Total     → 83 fixtures
```

Estado arquitetural:

- nenhum parser, codec, estado ou monitor específico foi criado;
- a identidade do efeito continua vindo da cadeia atual do slot;
- os slots humanos 1 e 2 foram confirmados nas capturas;
- `catalog_version` está em 8;
- 12 efeitos DYN e 38 parâmetros estão catalogados;
- 255 efeitos permanecem pendentes.

Validação offline consolidada:

```text
Ran 386 tests
OK
```

Também passaram `python -m compileall tools tests`, validação dos arquivos JSON
e `git diff --check`.

Validação física consolidada:

```text
RC-BOOST
GAIN 25 | VOLUME 56 | BASS 55 | TREBLE 63

FAT BOOST
BASS 60 | TREBLE 42 | VOLUME 28 | LOW CUT desligado

GATE 2
THRESHOLD 26 | ATTACK 34 | RELEASE 61
```

Os três efeitos coexistiram na mesma cadeia. Cada grupo de parâmetros foi
atualizado sem alterar os valores dos outros efeitos. LOW CUT acompanhou
`desligado → ligado → desligado`, confirmando o suporte booleano genérico.

Limitações preservadas:

- valores iniciais ainda aparecem como `aguardando alteração`;
- mensagens `0x1C` isoladas não identificam o efeito;
- o monitor permanece somente leitura;
- eventos auxiliares não `0x1C` continuam ignorados;
- o log final não inclui duas instâncias do mesmo modelo, reordenação ou teste
  explícito de bypass.

### Consolidação

A Fase 30 foi aprovada fisicamente, documentada, consolidada e promovida à
`main`. O trabalho ativo passou para a Fase 31, exclusivamente AC SIM.

## 18. Atualização atual — Fase 31 aprovada: AC SIM e MODE enum

A Fase 31 acrescenta o primeiro parâmetro categórico nomeado do catálogo:

```text
BODY   → seletor 0, inteiro 0–100
TOP    → seletor 1, inteiro 0–100
VOLUME → seletor 2, inteiro 0–100
MODE   → seletor 3, enum numérico 0–3
```

Mapeamento confirmado:

```text
0 STANDARD | 1 JUMBO | 2 ENHANCED | 3 PIEZO
```

O MODE continua usando `upper_float32_nibbles_v1`. A tradução para texto é
orientada pelas `choices` do JSON e permanece genérica. Não existe tabela ou
condicional específica do AC SIM no monitor.

Evidências preservadas:

```text
30 fixtures físicas
slot humano 1 → 22
slot humano 2 → 8
```

A implementação acrescentou suporte genérico a enumerações em:

```text
catalog/schemas/effect.schema.json
tools/catalog/models.py
tools/catalog/loader.py
tools/parameters/codecs.py
```

Validação offline consolidada:

```text
Ran 394 tests
OK
```

Também passaram `python -m compileall tools tests`, validação dos 291 arquivos
JSON e `git diff --check`.

Validação física consolidada:

- o AC SIM foi reconhecido simultaneamente com RC-BOOST e FAT BOOST;
- o monitor apresentou `BODY`, `TOP`, `VOLUME` e `MODE` na ordem correta;
- MODE exibiu `PIEZO`, `ENHANCED`, `JUMBO` e `STANDARD` como rótulos;
- VOLUME alternou entre `50` e `51`;
- TOP alternou entre `49` e `50`;
- BODY apresentou `47`, `48`, `49` e `52`;
- os efeitos anteriores da cadeia permaneceram sem alteração.

O log final não inclui duas instâncias simultâneas do AC SIM, reordenação ou
bypass explícito. As capturas nos slots humanos 1 e 2 e a validação ao vivo de
todos os rótulos sustentam a aprovação, preservando essas ausências como
limitações de cobertura.

### Consolidação

A Fase 31 foi aprovada fisicamente, documentada e promovida à `main`. A Fase
32 foi iniciada separadamente na mesma branch de pesquisa, sem misturar os
PCAPNGs brutos ao repositório.

## 19. Atualização atual — Fase 32 aprovada: GATE 3 e tempos

A Fase 32 acrescenta o primeiro parâmetro temporal e o primeiro codec que
reconstrói os quatro bytes completos do valor `float32` transmitido em oito
nibbles.

```text
THRESHOLD → seletor 0, inteiro 0–100
RATIO     → seletor 1, inteiro 0–100
ATTACK    → seletor 2, 1–500 ms
RELEASE   → seletor 3, 10–10000 ms
HOLD      → seletor 4, 0–1000 ms
```

O perfil `effect_parameter_response_1c_v1` expõe os índices `55–62`. O codec
histórico `upper_float32_nibbles_v1` seleciona `[4, 8]`, enquanto o novo
`float32_nibbles_v1` usa o payload completo. Isso evita regressões e preserva
valores como `5001`, `5037` e `6037`.

A apresentação `duration_milliseconds` mantém o estado em milissegundos e
mostra valores a partir de 1000 em segundos com uma casa decimal.

Evidências preservadas:

```text
58 fixtures físicas
slot humano 1 → 48
slot humano 2 → 10
```

Validação offline consolidada:

```text
Ran 401 tests
OK
```

Também passaram `compileall`, leitura dos 327 arquivos JSON, reexportação do
catálogo e `git diff --check`.

Validação física consolidada:

- GATE 3 exibido na ordem THRESHOLD, RATIO, ATTACK, RELEASE e HOLD;
- THRESHOLD e RATIO preservados durante substituições do efeito no outro slot;
- ATTACK exibido de 249 até 243 ms;
- RELEASE exibido em segundos e milissegundos, incluindo 5,6 s, 2,0 s, 827 ms
  e 292 ms;
- HOLD exibido em milissegundos e em 1,0 s;
- coexistência confirmada com RC-BOOST, FAT BOOST, BB-BOOST, AC-BOOST,
  AC WOODY, AC SIM, GATE 1 e GATE 2;
- duas instâncias de GATE 3 apareceram simultaneamente sem contaminação de
  estado.

O log final não contém evento explícito de bypass. Valores iniciais continuam
aguardando o primeiro movimento, a exibição em segundos continua arredondada e
o monitor permanece somente leitura.

### Encerramento da classe DYN

Com a Fase 32, os 14 modelos DYN e seus 47 parâmetros estão catalogados,
documentados, cobertos por regressão e fisicamente aprovados. DYN é a primeira
classe encerrada integralmente no projeto.

### Próximo passo exato

1. revisar e preparar somente os arquivos da Fase 32;
2. criar o commit final em `research/dyn-parameters`;
3. enviar a branch ao remoto;
4. promover por fast-forward à `main`;
5. voltar à branch de pesquisa e confirmar a árvore limpa;
6. escolher a próxima classe e criar uma nova branch para ela.

## 20. Atualização atual — Fase 33 aprovada: FREQ / FILTER

A Fase 33 inicia a branch `research/freq-parameters` com o FILTER. Foram
confirmados STEP 1–4, RATE e SYNC nos seletores 0–5. RATE mantém o seletor 4,
mas muda de domínio conforme SYNC: numérico `0–100` quando desligado e onze
divisões rítmicas (`0–10`) quando ligado.

A pedaleira redefine RATE visualmente para `10` ao desligar SYNC e para `1/4`
ao ligar, sem transmitir um pacote RATE separado. A implementação representa
esses defaults como regra derivada declarativa, não como observação USB.

As capturas FREQ também provaram que os índices `41–42` do envelope 0x1C
continuam `00 00`, portanto não identificam a classe estrutural. A resolução
segue usando o efeito real presente no slot da cadeia.

Evidências preservadas:

```text
55 fixtures físicas
slot humano 1 → 41
slot humano 2 → 14
10 fontes de captura controladas
```

Validação offline:

```text
Ran 409 tests
OK
```

### Validação física consolidada

A validação no monitor principal foi aprovada com `DYN / COMP1` no slot humano
1 e `FREQ / Filter` no slot humano 2. STEP 1–4 responderam de forma independente
e RATE permaneceu numérico enquanto SYNC ainda estava desligado. Ao receber
`SYNC = ON`, sem evento RATE adicional, o monitor derivou imediatamente
`RATE: 1/4`; movimentos posteriores exibiram `1/4d` e retorno a `1/4`. Ao
receber `SYNC = OFF`, novamente sem evento RATE adicional, o monitor derivou
`RATE: 10`. A coexistência com a classe DYN permaneceu estável.

O log ao vivo não cobriu bypass nem reordenação visual durante esta sessão. A
resolução física dos slots humanos 1 e 2 permanece coberta pelas capturas
controladas preservadas na fase.

### Próximo passo exato

1. executar a suíte completa, `compileall` e `git diff --check`;
2. adicionar somente os arquivos da Fase 33 ao índice;
3. criar o commit da Fase 33 em `research/freq-parameters`;
4. enviar a branch ao remoto;
5. promover por fast-forward à `main`;
6. voltar para `research/freq-parameters` e confirmar a árvore limpa;
7. iniciar o próximo efeito da classe FREQ.

## 21. Atualização atual — Fase 34 aprovada: FREQ / OCTAVER

A Fase 34 adiciona o segundo efeito parametrizado da classe FREQ sem alterar o
motor principal. As capturas físicas confirmaram:

```text
LOW OCT  = seletor 0, inteiro 0–100
HIGH OCT = seletor 1, inteiro 0–100
DRY      = seletor 2, inteiro 0–100
```

Os três controles usam `effect_parameter_response_1c_v1` com
`upper_float32_nibbles_v1`. A identidade continua sendo resolvida pela cadeia
estrutural atual; o envelope 0x1C não identifica sozinho a classe ou o modelo.

Evidências preservadas:

```text
24 fixtures físicas
slot humano 1 → 18
slot humano 2 → 6
```

As três capturas individuais preservam 0, 1, 50, 99 e 100. A captura combinada
adiciona 51, 52 e 53 para LOW OCT, HIGH OCT e DRY. A primeira short foi feita
novamente no slot humano 1 e não conta como validação de segundo slot; a short
corrigida confirma `00 01` e os valores 61/62/63 com retorno a 50.

Não houve necessidade de alterar decoder, codec, estado de parâmetros ou
monitor. `catalog_version` passa a 12. O catálogo fica com 16 efeitos
parametrizados, 56 parâmetros catalogados e 251 efeitos pendentes.

Validação offline consolidada:

```text
Ran 413 tests
OK
compileall: aprovado
```

### Validação física consolidada

O monitor reconheceu `FREQ / Octaver` no slot humano 2 ao lado de `DYN / COMP1`.
LOW OCT, HIGH OCT e DRY responderam de forma independente; a primeira instância
foi estabilizada em 37/74/30. O bypass OFF/ON preservou os três valores.

FILTER foi adicionado à mesma cadeia sem alterar o estado do OCTAVER. Depois,
uma segunda instância de OCTAVER recebeu 54/37/58 enquanto a primeira manteve
37/74/30. A cadeia foi ampliada ainda mais e uma terceira instância no slot
humano 7 recebeu 52/73/42, novamente sem contaminar as anteriores. A integração
física está aprovada para múltiplas instâncias, coexistência entre classes e
slots distantes.

O primeiro `git diff --check` após a candidata apontou somente uma linha em
branco excedente no fim de `docs/protocol_findings.md`. O pacote documental de
aprovação remove essa linha antes do commit final.

### Próximo passo exato

1. extrair o pacote documental final da Fase 34 na raiz;
2. executar a suíte completa, `compileall` e `git diff --check`;
3. adicionar somente os arquivos da Fase 34 ao índice;
4. criar o commit da Fase 34 em `research/freq-parameters`;
5. enviar a branch ao remoto;
6. promover por fast-forward à `main`;
7. voltar para `research/freq-parameters` e confirmar `nothing to commit`;
8. iniciar o próximo efeito da classe FREQ.

## 22. Fase 35 consolidada — FREQ / DUAL MELODY

A Fase 34 foi fisicamente aprovada, commitada e promovida. A investigação FREQ
avançou para DUAL MELODY. Sete capturas físicas controladas confirmaram cinco
parâmetros recebidos no comando `0x1C`:

```text
HIGH PITCH = seletor 0, inteiro 0–24
LOW PITCH  = seletor 1, inteiro -24–0
DRY        = seletor 2, inteiro 0–100
HI VOL     = seletor 4, inteiro 0–100
LOW VOL    = seletor 5, inteiro 0–100
```

A principal descoberta é que LOW PITCH usa valores float32 negativos reais.
`-24`, `-23`, `-12`, `-1` e `0` foram observados diretamente no wire; não há
offset 0-based nem enum de apresentação. O codec `upper_float32_nibbles_v1` já
decodifica esses valores corretamente, então nenhum novo codec foi criado.

O seletor 3 não aparece nas respostas device->host. HI VOL e LOW VOL permanecem
respectivamente em 4 e 5. As mensagens host->device presentes nas capturas
mostram uma assimetria 3/4 para esses dois controles; por isso a Fase 35 é
estritamente de leitura e não autoriza escrita de DUAL MELODY.

Evidência preservada:

```text
40 fixtures físicas
slot humano 1 → 30
slot humano 2 → 10
```

`catalog_version` passa a 13. O catálogo fica com 17 efeitos parametrizados,
61 parâmetros catalogados e 250 efeitos pendentes. Não houve alteração em
decoder, codecs, estado ou monitor.

Validação offline final:

```text
Ran 418 tests
OK
compileall: aprovado
git diff --check: aprovado
```

### Validação física final

A Fase 35 foi aprovada no monitor principal. HIGH PITCH acompanhou valores
positivos; LOW PITCH acompanhou corretamente valores negativos reais, incluindo
pontos próximos aos extremos e o retorno a zero; DRY, HI VOL e LOW VOL
permaneceram independentes. O bypass foi validado sem perda dos últimos valores
e duas instâncias de DUAL MELODY em posições diferentes da cadeia mantiveram
estados independentes.

A validação ao vivo também confirmou que a resolução continua vinculada ao slot
interno real e ao modelo presente na cadeia. Nenhuma escrita de parâmetro foi
implementada; a assimetria host->device de HI VOL/LOW VOL permanece apenas como
evidência para uma pesquisa futura.

### Consolidação histórica

A Fase 35 e a melhoria 35A foram fisicamente aprovadas, promovidas à `main` e
serviram como base estável para a Fase 36. Os passos de branch e promoção desta
etapa já foram concluídos.

## 23. Melhoria pós-Fase 35 — painel `--live` e log compacto

Depois de consolidar a Fase 35, o monitor recebeu uma melhoria exclusivamente
de apresentação. Nenhum comando SysEx, parser estrutural, codec, catálogo ou
regra de resolução de parâmetros foi alterado.

O modo histórico continua sendo o padrão e imprime cada snapshot em sequência.
O novo `--live` utiliza buffer alternativo ANSI, restaura o terminal ao sair e
redesenha a tela inteira a cada atualização. A primeira candidata ainda deixava
quadros no histórico do terminal; a segunda passou a usar buffer alternativo;
a terceira, fisicamente aprovada, passou também a limpar cada quadro antes do
redesenho e a silenciar mensagens de progresso que poderiam escrever por cima
do painel.

O novo `--log ARQUIVO` preserva um histórico compacto independente da forma de
apresentação. Em combinação com `--live`, permite uso cotidiano com tela limpa
e evidência textual das alterações. Exemplos esperados:

```text
04:15:20 slot=9 Dual Melody LOW PITCH -12
04:15:21 slot=9 Dual Melody LOW PITCH -11
04:15:24 slot=9 Dual Melody LOW PITCH 0
```

A validação física confirmou que o painel final permanece em uma única tela e
atualiza valores sem resíduos de caracteres do quadro anterior. O modo normal
permanece disponível sem mudança de comportamento.

Validação offline da candidata aprovada:

```text
Ran 428 tests
OK
compileall: aprovado
git diff --check: aprovado
```

Arquivos funcionais da melhoria:

```text
tools/commands/matribox_monitor.py
tests/test_matribox_monitor_output.py
```

### Fase 36 consolidada

Os parâmetros catalogados são hidratados pelo bloco `273–992` do dump `0x10`.
Cada slot possui 60 bytes e quinze posições float32, endereçadas pelo
`parameter_selector`. Eventos `0x1C` continuam prevalecendo em tempo real.
A suíte offline possui 443 testes aprovados. Carga inicial, adição, substituição,
reordenação, mudança de classe e parâmetros em tempo real foram aprovados
fisicamente no painel `--live`.

### Próximo passo exato

1. revisar o pacote final da Fase 37;
2. executar commit e push em `research/freq-parameters` pelo usuário;
3. manter `main` como marco estável até a consolidação planejada da pesquisa;
4. seguir para `FREQ / Harmony D` ou outro efeito escolhido.

## 24. Atualização atual — candidata da Fase 37: FREQ / Pitch

Quatro capturas de reabertura do editor oficial confirmaram o Pitch no slot
interno 0 como `class_id = 0x01`, `model_id = 0x24`. O bloco salvo possui cinco
seletores consecutivos: HI PITCH 0, LOW PITCH 1, WET 2, DRY 3 e RANGE 4.

As faixas são `0–12`, `-12–0` e três vezes `0–100`. Os defaults implícitos são
`12 / 0 / 50 / 50 / 50`. LOW PITCH usa `float32` negativo nativo, confirmado
por `-12`, `-9` e `-8`. A candidata incrementa `catalog_version` para 14,
totaliza 18 efeitos parametrizados, 66 parâmetros catalogados e 249 efeitos
pendentes.

A hidratação não ganhou código específico: o leitor genérico da Fase 36 resolve
os valores pelo seletor cadastrado. A validação física foi aprovada com duas
instâncias de Pitch simultâneas, Filter e COMP1 na mesma cadeia. Os valores
iniciais foram hidratados corretamente; efeitos adicionados receberam seus
defaults; e os cinco controles acompanharam alterações em tempo real sem
colisão entre instâncias. Nenhuma escrita de parâmetro foi implementada.

## 25. Atualização atual — candidata da Fase 38: FREQ / Harmony D

Três dumps de reabertura e uma varredura ao vivo confirmaram MIX, KEY, MODE,
INTERVAL 1, INTERVAL 2 e SMOOTH. Os seletores são `0, 1, 2, 3, 4, 6`; o seletor
5 é uma lacuna física e não foi inventado. KEY, MODE e INTERVAL usam enums
nomeados; SMOOTH usa booleano. Defaults: `50 / C / MAJOR / +3RD / +5TH / OFF`.

O catálogo passa à versão 15, com 19 efeitos parametrizados, 72 parâmetros e
248 efeitos pendentes. A suíte offline possui 447 testes aprovados.

A validação física foi aprovada com duas instâncias simultâneas. Cada uma
preservou MIX, KEY, MODE, INTERVAL 1, INTERVAL 2 e SMOOTH independentes. Os
valores foram hidratados, acompanharam alterações em tempo real e coexistiram
com COMP1, WAH e DRV sem colisões.

### Próximo passo exato

1. aplicar o pacote final na branch `research/freq-parameters`;
2. revisar e executar commit e push pelo usuário;
3. manter `main` sem integração até encerrar a pesquisa FREQ;
4. iniciar `FREQ / Pitch S` ou outro efeito escolhido.

## 26. Atualização atual — candidata da Fase 39: FREQ / Pitch S

Três dumps completos e uma varredura ao vivo confirmaram RANGE 0, POSITION 1,
MIX 2 e LEVEL 3. RANGE é enum de seis rótulos de oitava; os demais parâmetros
usam 0–100. Defaults: `+1 OCT / 0 / 100 / 100`.

Um `10.0` residual apareceu no seletor 4 dos dumps, mas não existe controle ou
resposta ao vivo correspondente. O catálogo não declara esse seletor, e o teste
de hidratação confirma que ele é ignorado. O catálogo passa à versão 16, com 20
efeitos parametrizados, 76 parâmetros e 247 efeitos pendentes. A suíte offline
possui 449 testes aprovados.

A validação física foi aprovada no preset 56C com os doze slots ocupados. Duas
instâncias de Pitch S em regiões diferentes da cadeia mantiveram RANGE,
POSITION, MIX e LEVEL independentes, incluindo `-1 OCT` e `+/-2 OCT`. A
coexistência com múltiplos COMP1 não produziu colisões.

### Próximo passo exato

1. aplicar o pacote final na branch `research/freq-parameters`;
2. revisar e executar commit e push pelo usuário;
3. manter `main` sem integração até encerrar a pesquisa FREQ;
4. iniciar `FREQ / Ring Mod` usando 56B para descoberta e 56C para validação.

## 27. Atualização atual — candidata da Fase 40: FREQ / Ring Mod

Três dumps completos e uma varredura ao vivo confirmaram MIX 0, FREQ. 1,
FINE 2 e TONE 3. FINE usa -50–50 com negativos nativos; os demais controles
usam 0–100. Defaults: `50 / 50 / 0 / 50`.

O `10.0` residual no seletor 4 não corresponde a um controle e é ignorado pelo
catálogo. A candidata eleva `catalog_version` para 17, com 21 efeitos
parametrizados, 80 parâmetros e 246 efeitos pendentes. A suíte offline possui
451 testes aprovados.

A validação física foi aprovada no preset 56C com doze efeitos. Duas instâncias
de Ring Mod nas posições 4 e 12 mantiveram MIX, FREQ., FINE e TONE
independentes. MIX 0, FINE `-33` e FINE `20` foram exibidos corretamente e a
coexistência com múltiplos COMP1 não produziu colisões.

### Próximo passo exato

1. aplicar o pacote final na branch `research/freq-parameters`;
2. revisar e executar commit e push pelo usuário;
3. manter `main` sem integração até encerrar a pesquisa FREQ;
4. iniciar `FREQ / Tape Mod` usando 56B para descoberta e 56C para validação.

## 28. Atualização atual — Fase 41 consolidada: FREQ / Tape Mod

As capturas ao vivo confirmaram SATURATION 0, MIX 1, VOLUME 2 e HIGH CUT 3,
todos em 0–100. Cada parâmetro percorreu 0, 1, 50, 99 e 100. Um conjunto
combinado `61 / 62 / 63 / 64` e uma validação no segundo slot confirmaram que o
envelope continua vinculado ao slot interno.

Três dumps completos após reabrir o aplicativo confirmaram `50 / 50 / 50 / 50`,
`21 / 43 / 65 / 87` e `22 / 44 / 66 / 88`. O `10.0` residual no seletor 4
não corresponde a um controle e é ignorado. A fase eleva
`catalog_version` para 18, com 22 efeitos parametrizados, 84 parâmetros e 245
efeitos pendentes.

O Tape Mod encerra o catálogo de parâmetros conhecido da classe FREQ. A
integração continua somente leitura e reutiliza integralmente a hidratação
genérica da Fase 36.

A validação física final usou o preset 56C com os doze slots ocupados. Duas
instâncias nas posições visuais 4 e 12 preservaram respectivamente
`30 / 31 / 21 / 30` e `81 / 80 / 70 / 71`. Múltiplos COMP1 coexistiram sem
colisão. A Fase 41 e a pesquisa de parâmetros FREQ estão aprovadas.

### Próximo passo exato

1. aplicar o pacote final na branch `research/freq-parameters`;
2. revisar, executar commit e publicar essa branch pelo usuário;
3. integrar `research/freq-parameters` na `main` com merge explícito;
4. publicar a `main` e confirmar que ambas apontam para o histórico esperado.

## 29. Atualização atual — Fase 42 consolidada: WAH / VOKS WAH

Três dumps de reabertura confirmaram RANGE 0, Q 1, VOLUME 2 e POSITION 3,
todos em 0–100 e com default 50. Os conjuntos persistidos foram
`50 / 50 / 50 / 50`, `21 / 43 / 65 / 87` e `22 / 44 / 66 / 88`. A identidade
estrutural é `class_id 0x02`, `model_id 0x01`, seletor secundário `0x05`.

A varredura ao vivo confirmou 0, 1, 50, 99 e 100 em cada controle. Os campos
4–6 do dump contêm `100 / 100 / 1`, sem controles ou respostas ao vivo
correspondentes, e por isso são ignorados. A fase eleva
`catalog_version` para 19, com 23 efeitos parametrizados, 88 parâmetros e 244
efeitos pendentes.

A validação física final usou uma cadeia com doze efeitos. Duas instâncias nas
posições 4 e 12 preservaram respectivamente `83 / 67 / 63 / 100` e
`2 / 24 / 11 / 3`, coexistindo com múltiplos COMP1 sem colisões.

### Próximo passo exato

1. aplicar o pacote final na branch `research/wah-parameters`;
2. revisar e publicar a Fase 42 pelo usuário quando desejado;
3. manter a `main` como marco estável durante a pesquisa WAH;
4. iniciar `WAH / Cry Wah` com o protocolo enxuto de descoberta.

## 30. Atualização atual — Fase 43 consolidada: WAH / CRY WAH

CRY WAH usa `class_id 0x02`, `model_id 0x08` e seletor secundário `0x05`.
RANGE, Q, VOLUME e POSITION ocupam os seletores 0–3, usam 0–100 e default 50.
Os dumps confirmaram `50 / 50 / 50 / 50`, `21 / 43 / 65 / 87` e
`22 / 44 / 66 / 88`; a varredura ao vivo cobriu 0, 1, 50, 99 e 100.

Os resíduos `100 / 100 / 1` nos seletores 4–6 são ignorados. A candidata eleva
o catálogo à versão 20, com 24 efeitos parametrizados, 92 parâmetros e 243
efeitos pendentes.

A validação física final usou uma cadeia com doze efeitos. VOKS WAH na posição
4 preservou `27 / 12 / 34 / 6`; CRY WAH na posição 12 preservou
`72 / 81 / 85 / 89`. Os dois modelos e múltiplos COMP1 coexistiram sem
colisões, confirmando resolução por identidade estrutural.

### Próximo passo exato

1. aplicar o pacote final na branch `research/wah-parameters`;
2. revisar e publicar a Fase 43 pelo usuário quando desejado;
3. manter a `main` estável durante a pesquisa WAH;
4. iniciar `WAH / Rack Wah` com o protocolo enxuto.

## 31. Atualização atual — Fase 44 consolidada: WAH / RACK WAH

Uma captura combinada confirmou `class_id 0x02`, `model_id 0x0A` e seletor
secundário `0x05`. RANGE, Q, VOLUME e POSITION usam 0–3; EQ usa o seletor 4 e
booleanos 0/1. O dump preservou `21 / 43 / 65 / 87 / OFF`; os eventos ao vivo
confirmaram `22 / 44 / 66 / 88` e `ON → OFF → ON`.

Os seletores 5 e 6 contêm resíduos 100 e 1 e são ignorados. O catálogo passa à
versão 21, com 25 efeitos parametrizados, 97 parâmetros e 242 pendentes.

A validação física final usou uma cadeia com doze efeitos. RACK WAH na posição
12 preservou `66 / 39 / 34 / 66 / OFF`, coexistindo com múltiplos COMP1. O EQ
foi apresentado corretamente como desligado.

### Próximo passo exato

1. aplicar o pacote final em `research/wah-parameters`;
2. revisar e publicar a Fase 44 pelo usuário quando desejado;
3. manter a `main` estável durante a pesquisa WAH;
4. iniciar `WAH / Bass Wah` com o protocolo enxuto.

## 32. Atualização atual — Fase 45 consolidada: WAH / BASS WAH

BASS WAH foi implementado sem nova captura, com base na repetição física do
mapa RANGE 0, Q 1, VOLUME 2 e POSITION 3 em VOKS, CRY e RACK WAH. A identidade
estrutural já conhecida é `class_id 0x02`, `model_id 0x07` e seletor secundário
`0x05`.

O efeito foi inicialmente testado como `partially_cataloged`. A validação física
com duas instâncias confirmou o mapa sem PCAPNG: posição 4 com
`23 / 28 / 0 / 23` e posição 12 com `84 / 88 / 84 / 81`. O efeito passa a
`physically_validated`; o catálogo passa à versão 23, com 26 efeitos
parametrizados, 101 parâmetros e 241 pendentes.

### Próximo passo exato

1. aplicar o pacote final em `research/wah-parameters`;
2. revisar e publicar a Fase 45 pelo usuário quando desejado;
3. manter a `main` estável durante a pesquisa WAH;
4. iniciar `WAH / Touch Wah`.

## 33. Atualização atual — Fase 46 consolidada: WAH / TOUCH WAH

TOUCH WAH usa `class_id 0x02`, `model_id 0x0F` e seletor secundário `0x01`.
SENSE, RANGE, Q e MIX ocupam 0–3. MODE ocupa 4, com GUITAR 0 e BASS 1. O dump
preservou `21 / 43 / 65 / 87 / BASS`; eventos ao vivo confirmaram
`22 / 44 / 66 / 88`, limites de SENSE e alternância do MODE.

Os seletores 5–6 contêm resíduos `100 / 1`. O catálogo passa à versão 24, com
27 efeitos parametrizados, 106 parâmetros e 240 pendentes.

A validação no monitor confirmou hidratação e alterações em tempo real, MODE
GUITAR/BASS e funcionamento em regiões distintas de uma cadeia cheia.

### Próximo passo exato

1. manter a Fase 46 em `research/wah-parameters`;
2. implementar e validar o último efeito WAH;
3. consolidar a documentação completa da classe;
4. integrar na `main` somente após aprovação do usuário.

## 34. Atualização atual — Fase 47 consolidada: WAH / AUTO WAH

AUTO WAH usa `class_id 0x02`, `model_id 0x15` e seletor secundário `0x01`.
DEPTH, RATE, VOLUME, LOW, Q, HIGH e SYNC ocupam os seletores 0–6. Os três dumps
reabertos confirmaram o padrão e os conjuntos controlados com SYNC desligado e
ligado.

RATE usa `float32_nibbles_v1`: com SYNC OFF, aceita 0,1–10,0 Hz em passos de
0,1; com SYNC ON, os valores 0–10 representam de 1/1 até 1/16. O dump preservou
3,7 Hz sem perda e 1/8D como wire value 8. O mecanismo condicionado já usado
por FREQ / Filter foi reutilizado, incluindo hidratação do controlador antes do
dependente e invalidação do RATE quando SYNC muda.

O catálogo passa à versão 25, com 28 efeitos parametrizados, 113 parâmetros e
239 pendentes. A suíte offline cobre catálogo, codec completo, hidratação dos
dois domínios e apresentação com unidade Hz.

O primeiro teste físico encontrou descartes esporádicos em RATE decimal por
tolerância excessivamente rígida ao passo 0,1. A correção normaliza o ruído de
float32 para o décimo mais próximo. Todos os valores de 0,1 a 10,0 estão
cobertos por regressão, enquanto 4,25 permanece inválido.

A validação física final confirmou os dois domínios, alterações em tempo real e
uma instância no fim da cadeia com `58 / 8,7 Hz / 100 / 54 / 70 / 60 / OFF`.
A classe WAH está encerrada.

### Próximo passo exato

1. aplicar o pacote final em `research/wah-parameters`;
2. executar a suíte offline completa;
3. criar os commits e publicar a branch pelo usuário;
4. integrar `research/wah-parameters` na `main` com merge explícito e publicar.

## 35. Atualização atual — Fase 48 consolidada: DRIVE / SKREAMER

Após a conclusão da classe WAH, a pesquisa segue em `research/drv-parameters`.
O primeiro efeito DRIVE usa a identidade estrutural `03 / 00 / 03`. GAIN, TONE
e VOLUME ocupam os seletores 0–2, usam inteiros 0–100 e possuem padrões salvos
40, 70 e 50.

Três dumps reabertos confirmaram `40 / 70 / 50`, `21 / 43 / 65` e
`22 / 44 / 66`. A varredura ao vivo confirmou os três seletores e valores
próximos aos limites. Os campos 3–14 estão zerados e não são hidratados.

O catálogo passa à versão 26, com 29 efeitos parametrizados, 116 parâmetros e
238 pendentes. A suíte cobre catálogo, exportação reproduzível e hidratação
somente dos três controles conhecidos.

A validação final no monitor confirmou GAIN 60, TONE 55 e VOLUME 78, além das
alterações ao vivo. O Skreamer está aprovado.

### Próximo passo exato

1. manter a Fase 48 em `research/drv-parameters`;
2. testar a repetição da assinatura GAIN/TONE/VOLUME no Skreamer 9;
3. promover a inferência se o monitor aprovar;
4. prosseguir pelos modelos DRIVE com captura proporcional ao risco.

## 36. Atualização atual — Fase 49 consolidada: DRIVE / SKREAMER 9

Skreamer 9 usa a identidade `03 / 01 / 03` e, segundo o manual, possui os mesmos
três controles do Skreamer. A candidata infere GAIN 0, TONE 1 e VOLUME 2, todos
em 0–100. Nenhum default foi declarado sem evidência.

A hidratação lê somente os valores reais do dump; a implementação não depende
de padrões inventados. O monitor confirmou o mapa, alterações ao vivo e uma
cadeia cheia. O modelo passa a `physically_validated` sem PCAPNG próprio.

### Próximo passo exato

1. manter a Fase 49 em `research/drv-parameters`;
2. usar captura curta nos layouts DRIVE ainda não comprovados;
3. validar o próximo efeito no monitor;
4. preservar a `main` estável até concluir a classe.

## 37. Atualização atual — Fase 50 consolidada: DRIVE / BUTTER OD

Butter OD usa a identidade `03 / 02 / 03`. Uma captura combinada confirmou GAIN
no seletor 0 e VOLUME no seletor 1, ambos 0–100. Os padrões informados são 40 e
70. Dois dumps idênticos preservaram `21 / 65 / 50`; o 50 do seletor 2 não tem
controle nem evento ao vivo e é ignorado.

A varredura confirmou 0, 1, 50, 99 e 100 nos dois controles. O catálogo passa à
versão 28, com 31 efeitos parametrizados, 121 parâmetros e 236 pendentes.

A validação final confirmou duas instâncias em cadeia cheia: posição 4 com
`0 / 48` e posição 12 com `82 / 81`. O Butter OD está aprovado.

### Próximo passo exato

1. manter a Fase 50 em `research/drv-parameters`;
2. testar inferências da família de três controles;
3. promover modelos aprovados sem captura quando seguro;
4. preservar captura curta para novos layouts.

## 38. Atualização consolidada — Fase 51: WARM OD e SUPER OD

Warm OD (`03 / 04 / 03`) e Super OD (`03 / 06 / 03`) declaram GAIN, TONE e
VOLUME no manual. A candidata reutiliza os seletores 0–2 já confirmados por
Skreamer e Skreamer 9. Os padrões informados são `40 / 50 / 50` e
`50 / 50 / 50`, respectivamente.

O teste físico confirmou os três seletores em duas instâncias simultâneas de
cada modelo, numa cadeia cheia: Warm OD nas posições 4 e 10; Super OD nas
posições 5 e 11. Hidratação, alterações em tempo real e estado desligado
funcionaram corretamente. Ambos estão `physically_validated`.

O catálogo passa à versão 30, com 33 efeitos parametrizados, 127 parâmetros e
234 pendentes.

### Próximo passo exato

1. aplicar o pacote de consolidação em `research/drv-parameters`;
2. executar a suíte offline;
3. seguir para o próximo efeito DRIVE;
4. investigar separadamente o retorno visual do aplicativo oficial ao slot 1
   quando um comando de alteração de efeito é enviado pelo script.

### Questão aberta: foco visual do aplicativo oficial

O comando externo modifica corretamente o slot solicitado, porém o aplicativo
oficial destaca novamente o slot 1. Tratar como problema de sincronização da UI,
não como falha da escrita, até uma captura comparativa localizar uma eventual
mensagem de seleção. Não modificar bytes desconhecidos do pacote estrutural.

## 39. Atualização consolidada — Fase 52: BLUES OD e FULL OD

Full OD (`03 / 0A / 03`) foi confirmado por duas capturas: GAIN/TONE/VOLUME nos
seletores 0–2 e MODE no seletor 3, com LP=0 e HP=1. O dump salvo confirmou
`21 / 43 / 65 / HP`; o monitor ainda precisa da aprovação visual final.

Blues OD (`03 / 09 / 03`) reutiliza como inferência os seletores 0–2 da família
de três controles, com padrões informados `40 / 60 / 50`. Ele permanece
foi confirmado fisicamente nas posições 4 e 10. Full OD foi confirmado nas
posições 5 e 11, incluindo LP/HP. Ambos funcionaram numa cadeia cheia e passam
a `physically_validated`.

O catálogo passa à versão 32: 35 efeitos parametrizados, 134 parâmetros e 232
pendentes.

### Próximo passo exato

1. aplicar o pacote consolidado na branch `research/drv-parameters`;
2. executar a suíte offline;
3. confirmar no aplicativo oficial os nomes reais dos controles de Breaker OD;
4. capturar Gerden OD com GAIN/TONE/VOLUME/VOICE;
5. continuar a classe DRIVE.

## 40. Atualização consolidada — Fase 53: BREAKER OD e GERDEN OD

Breaker OD (`03 / 0E / 03`) usa GAIN/TONE/VOLUME na interface do firmware,
apesar da divergência no manual. A candidata aplica seletores 0–2 e padrões
`60 / 50 / 50` e foi confirmado fisicamente nas posições 4 e 10.

Gerden OD (`03 / 10 / 03`) foi confirmado por captura com GAIN/TONE/VOLUME e
VOICE nos seletores 0–3. O dump salvo confirmou `21 / 43 / 65 / 87`, os eventos
ao vivo `22 / 44 / 66 / 88` e os limites 0–100. Ele entra como
`physically_validated`. A integração visual foi aprovada nas posições 5 e 11.

As quatro instâncias coexistiram numa cadeia cheia com outras classes; a
hidratação, as alterações ao vivo e o estado desligado funcionaram corretamente.

O catálogo passa à versão 34: 37 efeitos parametrizados, 141 parâmetros e 230
pendentes.

### Próximo passo exato

1. aplicar o pacote consolidado na branch `research/drv-parameters`;
2. executar a suíte offline;
3. criar os commits de implementação e documentação DRIVE;
4. publicar a branch de pesquisa;
5. seguir para o próximo efeito DRIVE.

## 41. Atualização consolidada — Fase 54

Timmy OD (`03 / 1E / 03`) possui GAIN/VOLUME/BASS/TREBLE em 0–3 e MODE em 4,
com I=0, II=1 e III=2. Master OD (`03 / 0F / 03`) possui cinco controles
numéricos consecutivos: GAIN/VOLUME/BASS/MIDDLE/TREBLE. Solar Fuzz
(`03 / 26 / 03`) usa somente FUZZ/VOLUME em 0–1; resíduos salvos em 2–4 são
explicitamente ignorados.

Os três layouts foram confirmados por capturas e aprovados no monitor juntos.
Timmy exibiu MODE I/III, Master os cinco controles e Solar somente FUZZ/VOLUME.
Todos estão `physically_validated` com integração aprovada.

### Próximo passo exato

## 42. Atualização consolidada — Fase 55

Fuzz Cream (`03 / 22 / 03`), Red Fuzz (`03 / 24 / 03`) e JP Dist
(`03 / 2A / 03`) reutilizam layouts já validados. Seus padrões informados são,
respectivamente, `40/50/50`, `50/50` e `50/50/50`.

Os três foram confirmados juntos com valores baixos, altos e limite 100. Todos
estão `physically_validated`, com integração aprovada.

### Próximo passo exato

## 43. Atualização consolidada — Fase 56

Dark Mouse (`03 / 2B / 03`) recebe GAIN/FILTER/VOLUME. Plexi Dist
(`03 / 2D / 03`) recebe GAIN/VOLUME/BASS/MIDDLE/TREBLE. Master Dist
(`03 / 2E / 03`) usa GAIN/VOLUME/BASS/CONTOUR/TREBLE. Todos reutilizam
seletores consecutivos já validados e padrões 50.

Os três foram confirmados juntos com valores baixos, altos e limite 100. FILTER,
MIDDLE e CONTOUR corresponderam à interface real. Todos estão
`physically_validated`, com integração aprovada.

### Próximo passo exato

## 44. Atualização consolidada — Fase 57

Dist Plus (`03 / 29 / 03`) reutiliza GAIN/VOLUME. Shark (`03 / 30 / 03`)
reutiliza GAIN/TONE/VOLUME. Strive (`03 / 32 / 03`) acrescenta MODE no seletor
3, inferido como I=0, II=1 e III=2. Todos têm padrões informados 50, com MODE I
no Strive.

Os três foram confirmados no monitor com valores baixos, altos e extremos.
Strive também confirmou MODE I/II/III. Todos estão `physically_validated`.

### Próximo passo exato

## 45. Atualização consolidada — Fase 58 e conclusão DRIVE

Sardar Dist (`03 / 52 / 03`) usa seis numéricos em 0–5. Bass OD
(`03 / 3F / 03`) usa GAIN/TONE/VOLUME/MODE/BLEND, com MODE inferido como
NORMAL=0, SCOOP=1 e EDGE=2. Bass Dist (`03 / 40 / 03`) usa
GAIN/BLEND/VOLUME/BASS/TREBLE. Todos os numéricos têm padrão 50.

Os três foram aprovados em duas instâncias simultâneas, com valores baixos,
altos, extremos 0/100 e MODE NORMAL/SCOOP/EDGE correto no Bass OD. Todos estão
`physically_validated`. O catálogo permanece na versão 39, com 52 efeitos
parametrizados, 199 parâmetros e 215 efeitos de outras classes ainda pendentes.

### Próximo passo exato

1. aplicar o pacote final na branch `research/drv-parameters`;
2. executar a suíte offline;
3. commitar implementação e documentação;
4. publicar a branch e integrá-la à `main`;
5. criar a branch de pesquisa da próxima classe.

## 46. Atualização atual — Fase 59 e início AMP

A classe DRIVE está integrada à `main` no merge `3abb40a`. A pesquisa atual
ocorre na branch `research/amp-parameters`.

TWD Deluxe (`04 / 01 / 07`) possui GAIN/TONE/VOLUME nos seletores 0–2 e ignora
resíduos salvos em 3–5. B-Man N (`04 / 03 / 07`) e B-Man Bri (`04 / 24 / 07`)
compartilham GAIN/PRESENCE/VOLUME/BASS/MIDDLE/TREBLE em 0–5. Todos foram
confirmados por PCAPNG, estão `physically_validated` e tiveram a integração
visual aprovada no monitor `--live`.

A validação final no preset 56B mostrou TWD Deluxe em `2/0/6`, B-Man N em
`33/88/100/78/84/90` e B-Man Bri em `78/100/90/100/90/100`. O TWD expôs
somente seus três controles válidos; os resíduos 3–5 permaneceram ocultos.

O catálogo permanece na versão 40: 55 efeitos parametrizados, 214 parâmetros e
212 efeitos pendentes.

### Próximo passo exato

1. manter a branch `research/amp-parameters`;
2. iniciar `DARK DOUBLE` (`04 / 04 / 07`) como próximo layout AMP pendente;
3. identificar os controles reais e seus seletores sem assumir equivalência só pelo nome/família;
4. capturar um conjunto diferencial curto e limites quando necessário;
5. integrar o mapa confirmado ao catálogo e validar no monitor `--live`.

## 47. Atualização consolidada — Fase 60: Dark/Supero

A interface oficial confirmou os controles e defaults de Dark Double
(`04 / 04 / 07`), Dark Deluxe (`04 / 05 / 07`) e Supero 2 CL
(`04 / 0F / 07`). A ordem visual foi inicialmente tratada como hipótese de
seletores consecutivos e testada somente em leitura.

A validação física no preset 56B confirmou integralmente os mapas: Dark Double
exibiu `19/20/19/17/9` com BRIGHT ligado; Dark Deluxe exibiu
`65/69/74/71`; Supero 2 CL exibiu `87/75/94`. O usuário também acompanhou as
alterações pelo log, usando faixas baixa, média e alta entre os três modelos,
com correspondência correta de todos os controles.

Assim, Dark Double fica com GAIN/VOLUME/BASS/MIDDLE/TREBLE/BRIGHT em 0–5,
Dark Deluxe com GAIN/VOLUME/BASS/TREBLE em 0–3 e Supero 2 CL com
GAIN/TONE/VOLUME em 0–2. Os três passam a `physically_validated`, com
integração do monitor `approved`, sem necessidade de PCAPNG adicional.

O catálogo permanece na versão 41: 58 efeitos parametrizados, 227 parâmetros e
209 efeitos `pending`. A suíte física/local informada encerrou com 501 testes
`OK`.

### Próximo passo exato

1. manter `research/amp-parameters`;
2. levantar controles, faixas e defaults de `SUPERO 2 OD` (`04 / 28 / 07`);
3. depois levantar `VOKS 15TB` (`04 / 10 / 07`) e `VOKS 30N` (`04 / 11 / 07`);
4. preparar candidatos somente-leitura e validar no monitor antes de promover;
5. não inferir layouts apenas por parentesco nominal.


## 48. Marco consolidado — Fase 61: Supero/Voks validados

Supero 2 OD (`04 / 28 / 07`) expõe GAIN 1/TONE 1/GAIN 2/TONE 2/VOLUME,
todos 0–100 e padrão 50. Voks 15TB (`04 / 10 / 07`) expõe
GAIN/TONE CUT/VOLUME/BASS/TREBLE, com defaults `30/60/50/50/50`. Voks 30N
(`04 / 11 / 07`) expõe GAIN/TONE CUT/VOLUME e BRIGHT, com defaults
`30/50/50/OFF`.

O usuário confirmou os três simultaneamente no preset 56B, acompanhando painel
e log. O monitor exibiu Supero 2 OD em `21/34/9/8/23`, Voks 15TB em
`48/58/66/69/66` e Voks 30N em `91/90/97/ON`. Todos os valores responderam
corretamente, incluindo BRIGHT. Os três passam a `physically_validated`, com
integração `approved`, sem PCAPNG adicional. O catálogo permanece na versão 42:
61 efeitos parametrizados, 241 parâmetros e 206 efeitos `pending`.

## 49. Marco consolidado — Fase 62: Voks/Jazz/Superb validados

A interface oficial informou Voks 30TB (`04 / 27 / 07`) com
GAIN/TONE CUT/VOLUME/BASS/TREBLE e CHAR COOL/HOT, defaults
`30/50/50/50/50/COOL`; Jazz 120 (`04 / 14 / 07`) com
GAIN/BASS/MIDDLE/TREBLE e BRIGHT OFF/ON, defaults `50/50/50/50/OFF`; e Superb
CL (`04 / 15 / 07`) com GAIN/PRESENCE/VOLUME/BASS/MIDDLE/TREBLE, defaults
`35/50/50/50/50/50`.

A validação física no preset 56B confirmou Voks 30TB em `2/4/3/4/4/HOT`, Jazz
120 em `39/55/43/55/ON` e Superb CL em `66/74/82/88/94/100`. O usuário também
alternou CHAR entre COOL/HOT e BRIGHT entre OFF/ON, confirmando as codificações
`0/1` e a ordem dos seletores. Os três passam a `physically_validated`, com
integração do monitor `approved`, sem PCAPNG adicional.

O catálogo permanece na versão 43: 64 efeitos parametrizados, 258 parâmetros e
203 efeitos `pending`.

### Próximo passo exato

1. manter `research/amp-parameters`;
2. levantar controles, faixas e defaults de `SUPERB OD`;
3. preparar candidato somente-leitura e validar no monitor antes de promover.

## 50. Marco consolidado — Fase 63: Superb/Calif validados

A interface oficial informou Superb OD (`04 / 48 / 07`) com
GAIN/PRESENCE/VOLUME/BASS/MIDDLE/TREBLE, todos 0–100 e padrão 50; Calif Star
CL (`04 / 19 / 07`) com o mesmo conjunto, mas GAIN padrão 40; e Calif Star OD
(`04 / 4A / 07`) com INPUT/GAIN/PRESENCE/VOLUME/BASS/MIDDLE/TREBLE, todos
0–100 e padrão 50.

A validação física no preset 56B confirmou Superb OD em `3/5/7/1/4/6`, Calif
Star CL em `33/41/54/62/45/62` e Calif Star OD em
`94/93/79/90/97/88/100`. A ordem dos seletores foi confirmada nos três modelos,
inclusive o sétimo seletor do Calif Star OD e o extremo `TREBLE = 100`. Os três
passam a `physically_validated`, com integração do monitor `approved`, sem
PCAPNG adicional.

O catálogo permanece na versão 44: 67 efeitos parametrizados, 277 parâmetros e
200 efeitos `pending`.

### Próximo passo exato

1. manter `research/amp-parameters`;
2. validar BOG SV CL, BOG SV OD e BOG XT BLUE no `matribox_monitor --live`;
3. alternar BRIGHT OFF/ON no BOG SV CL;
4. promover somente após confirmação física.

## 51. Fase 64 — BOG SV e BOG XT Blue candidatos

A interface oficial informa BOG SV CL (`04 / 1A / 07`) com
GAIN/PRESENCE/VOLUME/BASS/TREBLE (0–100, defaults `30/50/50/50/50`) e BRIGHT
OFF/ON, padrão OFF. BOG SV OD (`04 / 3D / 07`) e BOG XT BLUE
(`04 / 43 / 07`) expõem GAIN/PRESENCE/VOLUME/BASS/MIDDLE/TREBLE, todos 0–100,
com GAIN padrão 30 e os demais em 50.

A candidata usa a ordem da interface oficial como hipótese de seletores 0–5.
BOG SV CL coloca BRIGHT no seletor 5 com codificação candidata `0=OFF/1=ON`;
os outros dois usam seis parâmetros inteiros consecutivos. Os três permanecem
`partially_cataloged`, `physical: false` e somente-leitura até teste no hardware.

O catálogo passa à versão 45: 70 efeitos parametrizados, 295 parâmetros e 197
efeitos `pending`.

### Próximo passo exato

1. executar `python -m tools.commands.matribox_monitor --live`;
2. confirmar ordem, nomes e valores nos três BOG;
3. testar BRIGHT OFF/ON no BOG SV CL;
4. somente depois promover os três para `physically_validated`.

## 52. Marco consolidado — Fase 69: classe AMP concluída

A pesquisa de parâmetros AMP foi encerrada com **63/63 modelos** em
`physically_validated`. A classe contém **356 parâmetros** e não possui mais
modelos `pending` ou `partially_cataloged`.

As fases 65–69 foram executadas em lotes maiores para reduzir trabalho manual;
a documentação detalhada desses lotes foi consolidada em
`docs/phases/AMP_CLASS_CONSOLIDATION_PHASE69.md`.

A validação final incluiu os dez últimos modelos: DIZZY VH S, DIZZY VH+,
DIZZY VH+ S, A BASSVT, VOKS BASS, CALI BASS, A BASSFT, F-2BASS, AC PREAMP e
AC PREAMP 2. O painel ao vivo confirmou a ordem e os valores de todos os
controles, incluindo `MIDRANGE` do A BASSVT e `BRIGHT` do F-2BASS.

Uma exceção importante descoberta durante a Fase 68 foi preservada: no
`HALEN 51`, `PRESENCE` usa o seletor **6**; o seletor 5 é um campo
oculto/não catalogado.

Estado consolidado do catálogo:

```text
catalog_version: 50
267 efeitos estruturais
115 efeitos com parâmetros fisicamente validados
555 parâmetros catalogados
152 efeitos ainda sem parâmetros em outras classes
AMP: 63/63 physically_validated, 356 parâmetros
```

Estado da suíte de encerramento:

```text
520 testes executados
520 testes aprovados
```

### Próximo passo exato

1. aplicar o delta final da Fase 69 no ambiente Windows;
2. executar `python -m unittest discover -s tests -p "test_*.py"`;
3. executar `python -m compileall tools tests` e `git diff --check`;
4. revisar o diff consolidado da classe AMP;
5. somente depois consolidar/commitir `research/amp-parameters`;
6. iniciar a próxima classe de parâmetros ainda pendente, com CAB como próximo
   grupo natural na ordem do catálogo.

## 53. Fases 70–71 — classe CAB concluída

A pesquisa CAB começou com duas âncoras físicas. `SUPERO 1X6` foi capturado desde a abertura do aplicativo oficial, incluindo hidratação padrão e personalizada, sweeps separados de LOW CUT/HIGH CUT/VOLUME e eventos ao vivo. `DOUBLE BASS`, no extremo final da lista, confirmou o mesmo layout por dump salvo e alterações `0x1C`.

O schema físico comum é VOLUME no seletor 1 (0..100, default 50), LOW CUT no seletor 5 (`19 = OFF`, 20..2000 Hz) e HIGH CUT no seletor 6 (2000..20000 Hz, `20001 = OFF`), todos decodificados com `float32_nibbles_v1` completo. Os seletores persistidos 2, 3 e 4 observados nas âncoras são resíduos do slot e não controles CAB.

Na Fase 71 o schema foi aplicado aos 59 modelos restantes como candidatos. O usuário testou depois os 61 modelos individualmente no `matribox_monitor --live`, alterando os três parâmetros e comparando os valores com a pedaleira. Todos funcionaram corretamente, inclusive valores de frequência float32 e OFF. A classe termina com **61/61 `physically_validated`**, **183 parâmetros CAB**, nenhum `pending`/`partially_cataloged` em CAB, `catalog_version = 52`, **176 efeitos fisicamente validados**, **738 parâmetros catalogados** e **91 efeitos ainda sem parâmetros** em outras classes.

A consolidação completa está em `docs/phases/CAB_CLASS_CONSOLIDATION_PHASE71.md`.

## 54. Fase 72 — IR: schema compartilhado e conclusão física

IR 1 e IR 20 confirmaram por PCAPNG o mesmo layout de parâmetros usado por CAB: VOLUME no seletor 1, LOW CUT no 5 e HIGH CUT no 6, todos em `float32_nibbles_v1`. LOW CUT usa `19 = OFF` e 20..2000 Hz; HIGH CUT usa 2000..20000 Hz e `20001 = OFF`. Dumps salvos e eventos `0x1C` confirmaram os valores personalizados `37/637/15371` em IR 1 e `28/953/13267` em IR 20.

Os 20 modelos IR foram preparados inicialmente como `partially_cataloged`. O usuário então testou IR 1..20 individualmente com `matribox_monitor --live --log ir_phase72_validation.txt`, alterando os controles e comparando os valores exibidos com a pedaleira. Ele confirmou que todos os 20 modelos corresponderam exatamente ao equipamento. O log registrou mudanças ao vivo em 19 modelos; IR 4 não gerou linha de parâmetro no TXT, mas foi confirmado fisicamente pelo usuário durante a validação manual.

A classe termina com **20/20 `physically_validated`**, **60 parâmetros IR**, nenhum `pending`/`partially_cataloged` em IR, `catalog_version = 53`, **196 efeitos fisicamente validados**, **798 parâmetros catalogados** e **71 efeitos ainda sem parâmetros** em outras classes. A consolidação completa está em `docs/phases/IR_CLASS_CONSOLIDATION_PHASE72.md`.

Importação de WAV/IR de terceiros permanece fora do escopo até o fim da catalogação de parâmetros das demais classes.
