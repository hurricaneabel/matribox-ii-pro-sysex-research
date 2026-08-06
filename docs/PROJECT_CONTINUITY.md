# Continuidade do projeto Matribox II Pro SysEx Research

> Documento oficial de retomada entre conversas.
>
> **Última atualização:** 6 de agosto de 2026
> **Marco consolidado:** Fase 28 — DYN / COMP3 com sete parâmetros,
> aprovado offline e fisicamente com duas instâncias simultâneas e estados
> independentes
> **Trabalho candidato:** Fase 29 — AC-BOOST e BB-BOOST integrados e aprovados
> offline; validação no monitor principal ainda pendente
> **Próxima pesquisa:** AC SIM reservado para fase própria por possuir o
> parâmetro categórico MODE
> **Branch estável:** `main`
> **Branch de pesquisa atual:** `research/dyn-parameters`

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
- apresentar parâmetros catalogados no monitor principal e manter valores
  separados por slot interno, efeito e parâmetro;
- carregar as 16 classes, 267 efeitos e 12 parâmetros confirmados por
  capturas em seis efeitos DYN a partir de um catálogo JSON versionado e
  independente de Python/Windows.

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
     GAIN: aguardando alteração

  3. DYN / COMP1 — ligado
     SUSTAIN: aguardando alteração
     VOLUME: aguardando alteração

  4. DYN / E-BOOST — ligado
     GAIN: aguardando alteração
     +3dB: aguardando alteração
     BRIGHT: aguardando alteração
```

Depois do primeiro evento `0x1C`, o valor real substitui o texto de espera.

### Comportamentos fisicamente confirmados

- A troca de preset atualiza endereço, nome, etiqueta e solicita a nova cadeia.
- A mudança da ordem dos efeitos redesenha a cadeia na ordem correta.
- Ligar ou desligar um efeito atualiza imediatamente somente o estado daquele
  slot, sem solicitar um novo dump completo.
- A inicialização após ligar a pedaleira possui reenvios automáticos; não é mais
  necessário encerrar e executar o monitor uma segunda vez.
- O monitor é somente leitura durante a consulta da cadeia. Ele não move,
  substitui, liga/desliga nem salva efeitos.

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

M-BOOST, COMP1, COMP2, COMP3, AC-BOOST, BB-BOOST, E-BOOST, AC WOODY e
GATE 1 são os nove efeitos com parâmetros preenchidos no catálogo atual. Os
outros 258 efeitos permanecem explicitamente `pending`, sem parâmetros
presumidos.

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

O valor inicial ainda não é extraído do dump. Após carregar o preset, o monitor
mostra `aguardando alteração` até receber o primeiro evento ao vivo.

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
futuro, por Kotlin/Android e desktop. Neste marco há 12 parâmetros fisicamente
confirmados em seis efeitos DYN; os demais efeitos permanecem sem dados
inventados.

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

Suíte completa candidata da Fase 29:

```text
Ran 382 tests
OK
```

Validação offline aprovada:

- 27 fixtures físicas do M-BOOST;
- 22 fixtures físicas do COMP1;
- 49 fixtures físicas únicas do COMP2;
- 84 fixtures físicas únicas do COMP3;
- 32 fixtures físicas únicas do AC-BOOST;
- 32 fixtures físicas únicas do BB-BOOST;
- 19 fixtures físicas únicas do E-BOOST;
- 11 fixtures físicas únicas do AC WOODY;
- 11 fixtures físicas únicas do GATE 1;
- SHAPE e THRESHOLD resolvidos pelo efeito real da cadeia;
- SUSTAIN e VOLUME independentes no mesmo slot do COMP1;
- SUSTAIN, ATTACK, VOLUME e CLIPPING independentes no COMP2;
- sete parâmetros independentes no COMP3;
- GAIN, +3dB e BRIGHT independentes no mesmo slot;
- conversão booleana estrita `0/1 → False/True`;
- exibição humana `desligado/ligado`;
- resolução explícita pelo efeito real da cadeia;
- detecção de ambiguidade quando o contexto da cadeia não é fornecido;
- manutenção da compatibilidade com `mboost_gain.py`;
- múltiplas instâncias com valores independentes;
- descarte de estado antigo ao substituir efeito ou trocar preset;
- apresentação do COMP1 na ordem SUSTAIN, VOLUME;
- apresentação do COMP2 na ordem SUSTAIN, ATTACK, VOLUME, CLIPPING;
- apresentação do COMP3 na ordem THRESHOLD, RATIO, VOLUME, ATTACK, RELEASE,
  TONE, BLEND;
- apresentação de AC-BOOST e BB-BOOST na ordem GAIN, VOLUME, BASS, TREBLE;
- atualização simulada independente dos quatro parâmetros dos dois boosts.

Validação física aprovada:

- inicialização, preset, metadados e cadeia;
- mudança de ordem e bypass em tempo real;
- M-BOOST/GAIN no validador e monitor;
- capturas controladas do COMP1 nos slots internos 1 e 2;
- seletores `0` para SUSTAIN e `1` para VOLUME;
- faixa controlada 0–100;
- COMP1 exibido no monitor principal;
- SUSTAIN e VOLUME atualizados independentemente;
- múltiplas instâncias de COMP1 com estados separados;
- COMP1 e M-BOOST simultâneos sem colisão do seletor `0`;
- preservação do estado de um COMP1 enquanto outro slot foi substituído por
  COMP2, COMP3 e M-BOOST;
- novo M-BOOST no slot substituído atualizando GAIN de forma independente.

Validação física aprovada para a Fase 25:

- E-BOOST exibindo GAIN, +3dB e BRIGHT na ordem do catálogo;
- atualização independente dos três parâmetros;
- apresentação dos interruptores como `ligado/desligado`;
- bypass do efeito sem corromper o estado dos parâmetros;
- duas instâncias simultâneas mantendo estados separados;
- uma instância com GAIN 31 e outra com GAIN 21, sem contaminação cruzada;
- coexistência com COMP1 e efeitos de outras classes sem colisão de seletores;
- substituições estruturais em outro slot sem atribuição ao efeito incorreto.

Validação física aprovada para a Fase 26:

- AC WOODY exibindo e atualizando `SHAPE`;
- GATE 1 exibindo e atualizando `THRESHOLD`;
- atualização independente de SHAPE e THRESHOLD;
- duas instâncias simultâneas de AC WOODY com estados separados;
- preservação dos valores após mudança de posição visual;
- GATE 1 preservando THRESHOLD após mudança de ordem;
- coexistência com COMP1, M-BOOST, E-BOOST e efeitos de outras classes;
- ausência de colisão apesar da reutilização do seletor `0`.

Validação física aprovada para a Fase 27:

- COMP2 exibindo SUSTAIN, ATTACK, VOLUME e CLIPPING na ordem do catálogo;
- atualização independente dos quatro controles no monitor principal;
- primeira instância mantendo SUSTAIN 21, ATTACK 60, VOLUME 50 e CLIPPING 10;
- segunda instância mantendo SUSTAIN 21, ATTACK 61, VOLUME 51 e CLIPPING 11;
- ausência de contaminação entre duas instâncias simultâneas de COMP2;
- coexistência com COMP1, COMP3, M-BOOST, E-BOOST, AC-BOOST e BB-BOOST;
- ausência de colisão apesar da reutilização dos seletores `0`, `1`, `2` e `3`;
- preservação dos valores pelo slot interno correto durante mudanças estruturais.

Validação física aprovada para a Fase 28:

- COMP3 exibindo THRESHOLD, RATIO, VOLUME, ATTACK, RELEASE, TONE e BLEND na
  ordem do catálogo;
- atualização independente dos sete controles no monitor principal;
- primeira instância mantendo 20, 45, 66, 59, 59, 62 e 59;
- segunda instância mantendo 25, 8, 30, 26, 24, 30 e 33;
- ausência de contaminação entre duas instâncias simultâneas de COMP3;
- preservação dos sete valores enquanto a cadeia recebeu efeitos DRV, FREQ,
  EQ, MOD, DLY e RVB;
- coexistência com COMP1 e COMP2;
- ausência de colisão apesar da reutilização dos seletores `0` a `6`;
- a troca explícita de posição entre as duas instâncias não aparece no log
  fornecido, mas o isolamento por slot e a estabilidade estrutural foram
  confirmados.

Fixtures físicas de regressão:

```text
tests/fixtures/structural_effect_state/
tests/fixtures/preset_dump_chain/
tests/fixtures/effect_slot_state/
tests/fixtures/mboost_gain/
tests/fixtures/comp1_parameters/
tests/fixtures/comp2_parameters/
tests/fixtures/comp3_parameters/
tests/fixtures/ac_boost_parameters/
tests/fixtures/bb_boost_parameters/
tests/fixtures/e_boost_parameters/
tests/fixtures/ac_woody_parameters/
tests/fixtures/gate1_parameters/
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
- Parâmetros catalogados fazem parte do monitor estável desde a Fase 23B.
- A mensagem `0x1C` não identifica de forma confiável o modelo do efeito. Não
  voltar a usar os índices `21–22` como `model_id`; resolver sempre pela cadeia
  atual no slot interno.
- Seletores podem se repetir entre efeitos diferentes: seletor `0` significa
  GAIN no M-BOOST, SUSTAIN no COMP1, SUSTAIN no COMP2, THRESHOLD no COMP3,
  GAIN no E-BOOST, GAIN no AC-BOOST, GAIN no BB-BOOST, SHAPE no AC WOODY
  e THRESHOLD no GATE 1. Os seletores `1` a `6` também podem ter significados
  diferentes conforme o efeito.
- Booleanos do protocolo devem continuar restritos aos valores físicos `0/1`;
  não aceitar outros números como verdadeiros.
- O valor inicial do parâmetro não é lido do dump; aparece como `aguardando
  alteração` até o primeiro evento ao vivo.
- Não criar um parser Python separado para cada parâmetro. A expansão deve usar
  o catálogo JSON, codecs e perfis de protocolo genéricos já criados.
- Não colocar caminhos absolutos, objetos `pickle` ou estruturas exclusivas de
  Python no catálogo. Os arquivos atuais já obedecem essa regra.
- Não executar novamente a exportação com dados incompletos sem revisar o diff,
  porque o catálogo passará a receber novos parâmetros manualmente validados.

## 13. Próximos passos recomendados

1. permanecer em `research/dyn-parameters`;
2. aplicar o pacote candidato da Fase 29;
3. repetir os 382 testes, `compileall` e `git diff --check`;
4. validar AC-BOOST e BB-BOOST no monitor principal;
5. confirmar valores independentes, duas instâncias e mudança de posição;
6. atualizar a documentação com o log físico aprovado;
7. criar o commit estável da Fase 29 e promovê-lo por fast-forward à `main`;
8. manter as capturas do AC SIM fora desse commit;
9. reservar o AC SIM para fase própria, porque MODE exige suporte genérico a
   valores categóricos e rótulos portáteis no catálogo.

A futura interface deve consumir `EffectParameterEvent` e as definições JSON,
sem conhecer offsets, nibbles ou detalhes MIDI.

## 14. Checklist obrigatório para o próximo commit

```text
[x] A funcionalidade foi validada offline.
[x] A integração da Fase 29 foi validada fisicamente no monitor principal.
[x] A suíte unittest completa passou.
[x] python -m compileall tools tests passou.
[x] git diff --check passou.
[x] docs/PROJECT_CONTINUITY.md foi atualizado.
[x] README.md foi atualizado se o uso público mudou.
[ ] O escopo do git add ainda deve ser revisado; arquivos locais não relacionados devem ficar fora.
[ ] O commit será feito na branch de pesquisa correta e só depois promovido à main.
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
