# Continuidade do projeto Matribox II Pro SysEx Research

> Documento oficial de retomada entre conversas.
>
> **Última atualização:** 6 de agosto de 2026
> **Marco consolidado:** Fase 23A — catálogo de efeitos e parâmetros migrado
> para JSON multiplataforma, mantendo compatibilidade com o núcleo Python
> **Candidato em validação física:** Fase 23B — motor genérico de parâmetros
> integrado ao monitor principal
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
- alterar modelo, bypass e volume usando comandos conhecidos;
- reconhecer e decodificar em tempo real o parâmetro `GAIN` de qualquer
  instância de `DYN / M-BOOST` por um motor genérico orientado pelo JSON;
- apresentar parâmetros catalogados no monitor principal e manter valores
  separados por slot interno e instância;
- carregar as 16 classes, 267 efeitos e o primeiro parâmetro validado a partir
  de um catálogo JSON versionado e independente de Python/Windows.

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

### 6.4 Primeiro parâmetro interno isolado

A Fase 22 acrescentou um parser puro e um validador ao vivo para o
`DYN / M-BOOST / GAIN`:

```text
tools/commands/mboost_gain.py
tools/experiments/validate_mboost_gain_live.py
tests/test_mboost_gain.py
tests/fixtures/mboost_gain/
```

Estrutura confirmada da resposta de 70 bytes:

```text
comando                  0x1C
slot interno             índices 39–40, zero-based
classe DYN               índices 41–42
modelo M-BOOST 0x14      índices 21–22
GAIN                     índices 59–62
codec                     16 bits superiores de float32 little-endian em nibbles
faixa                     0–100
```

A validação ao vivo aprovou múltiplas instâncias simultâneas e observou os
slots internos 2, 8, 10 e 12. Os endereços esperados de 1 a 12 são aceitos
pelo parser, enquanto a posição visual continua sendo resolvida pela cadeia.

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

O M-BOOST é o único efeito com parâmetro preenchido neste marco. Os outros 266
efeitos permanecem explicitamente `pending`, sem parâmetros presumidos.

### 6.6 Motor genérico de parâmetros — Fase 23B

Arquivos principais:

```text
tools/parameters/codecs.py
tools/parameters/decoder.py
tools/parameters/state.py
tools/experiments/validate_effect_parameters_live.py
tests/test_effect_parameters.py
```

O decoder consulta o perfil, o codec, o efeito e o `message_match` declarados
no catálogo. Ele produz `EffectParameterEvent` sem condicionais específicas
para M-BOOST. `mboost_gain.py` agora é apenas uma fachada de compatibilidade.

O estado guarda o último valor por slot interno, efeito e parâmetro. Eventos
são rejeitados quando a cadeia atual identifica outro efeito no slot. Valores
são descartados ao trocar preset ou substituir o efeito.

O valor inicial ainda não é extraído do dump. Após carregar o preset, o monitor
mostra `aguardando alteração` até receber o primeiro evento ao vivo.

Relatório:

```text
EFFECT_PARAMETER_ENGINE_PHASE23B.md
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
futuro, por Kotlin/Android e desktop. O único parâmetro interno concluído neste
marco é `DYN / M-BOOST / GAIN`; os demais permanecem sem dados inventados.

## 10. Histórico consolidado das Fases 14–23A

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

### Fase 22 — M-BOOST / GAIN isolado

Isolou o comando `0x1C`, o slot interno e a codificação do GAIN usando quatro
capturas controladas. Preservou 27 respostas SysEx físicas mínimas e criou um
validador somente de leitura.

A validação ao vivo aprovou múltiplos M-BOOSTs simultâneos nos slots internos
2, 8, 10 e 12, incluindo valores até 100, sem confundir as instâncias.

```text
MBOOST_GAIN_VALIDATION_PHASE22.md
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
registro. O M-BOOST/GAIN foi registrado como primeiro parâmetro validado; os
outros 266 efeitos permanecem `pending`.

```text
EFFECT_CATALOG_JSON_PHASE23A.md
catalog/
tools/catalog/
tools/migrations/export_effect_catalog_to_json.py
tests/test_effect_catalog_json.py
tests/fixtures/effect_catalog/legacy_catalog_snapshot.json
```

### Fase 23B — motor genérico de parâmetros (candidato)

Criou codecs, decoder e estado genéricos orientados pelo catálogo JSON,
preservou a API específica da Fase 22 e integrou parâmetros ao monitor. As 27
fixtures físicas são decodificadas pelo novo motor. A validação física da
integração ao monitor ainda é obrigatória antes do commit.

```text
EFFECT_PARAMETER_ENGINE_PHASE23B.md
tools/parameters/
tools/experiments/validate_effect_parameters_live.py
tests/test_effect_parameters.py
```

## 11. Estado de validação no marco atual

Suíte completa do candidato da Fase 23B:

```text
Ran 340 tests
OK
```

Validação offline aprovada:

- 27 fixtures físicas decodificadas pelo motor genérico;
- compatibilidade integral com `mboost_gain.py`;
- múltiplas instâncias com valores independentes;
- descarte de estado antigo ao substituir efeito ou trocar preset;
- rejeição de mensagens incompatíveis e valores fora da faixa;
- cruzamento de efeito e slot com a cadeia estrutural atual;
- apresentação de valor pendente e valor recebido no snapshot do monitor.

Validação física já aprovada em fases anteriores:

- inicialização e recuperação após cold boot;
- leitura de preset, nome, etiqueta e cadeia;
- mudança de ordem e bypass em tempo real;
- leitura isolada do M-BOOST/GAIN;
- múltiplas instâncias e slots 2, 8, 10 e 12.

Validação física ainda pendente para a Fase 23B:

- atualização do GAIN dentro do monitor principal;
- duas ou mais instâncias com valores independentes no monitor;
- preservação correta após movimento visual;
- limpeza do valor ao trocar preset.

Fixtures físicas de regressão ficam em:

```text
tests/fixtures/structural_effect_state/
tests/fixtures/preset_dump_chain/
tests/fixtures/effect_slot_state/
tests/fixtures/mboost_gain/
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
- Parâmetros catalogados fazem parte do monitor candidato da Fase 23B, mas a
  integração ainda precisa de aprovação física antes do commit.
- O valor inicial do parâmetro não é lido do dump; aparece como `aguardando
  alteração` até o primeiro evento ao vivo.
- Não criar um parser Python separado para cada parâmetro. A expansão deve usar
  o catálogo JSON, codecs e perfis de protocolo genéricos já criados.
- Não colocar caminhos absolutos, objetos `pickle` ou estruturas exclusivas de
  Python no catálogo. Os arquivos atuais já obedecem essa regra.
- Não executar novamente a exportação com dados incompletos sem revisar o diff,
  porque o catálogo passará a receber novos parâmetros manualmente validados.

## 13. Próximos passos recomendados

1. extrair o pacote da Fase 23B e executar a suíte completa;
2. executar `tools.commands.matribox_monitor`;
3. confirmar `GAIN: aguardando alteração` e a atualização ao vivo;
4. testar duas ou mais instâncias de M-BOOST;
5. mover uma instância e trocar de preset para validar retenção e limpeza;
6. após aprovação física, atualizar este documento com o resultado final e
   consolidar o commit;
7. iniciar o próximo efeito DYN adicionando somente dados ao catálogo e novos
   perfis/codecs quando as capturas exigirem;
8. depois de concluir DYN, iniciar FREQ;
9. manter importação IR/CLONE como subsistema separado.

A futura interface deve consumir `EffectParameterEvent` e as definições JSON,
sem conhecer offsets, nibbles ou detalhes MIDI.

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
