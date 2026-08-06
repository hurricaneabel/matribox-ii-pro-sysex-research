# Fase 24 — DYN / COMP1: SUSTAIN e VOLUME

## Objetivo

Catalogar os dois parâmetros do `DYN / COMP1` e validar o primeiro efeito com
mais de um parâmetro no motor genérico criado na Fase 23B.

Parâmetros informados e confirmados:

```text
SUSTAIN: 0–100
VOLUME:  0–100
```

## Capturas controladas

Preset de teste: `56B`.

Fontes Wireshark/USBPcap:

```text
COMP1_SUSTAIN_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
COMP1_VOLUME_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
COMP1_SLOT2_SUSTAIN_AND_VOLUME_50_51_50.pcapng
```

Foram preservadas 22 respostas SysEx físicas mínimas em:

```text
tests/fixtures/comp1_parameters/
```

## Estrutura confirmada

As respostas usam o mesmo perfil e codec já observados no M-BOOST:

```text
comando                  0x1C
tamanho                  70 bytes
slot interno             índices 39–40, zero-based
seletor do parâmetro     índice 48
valor                    índices 59–62
marcador                 índice 63 = 0x01
tipo                     índice 64 = 0x01
codec                     upper_float32_nibbles_v1
```

Seletores confirmados:

```text
SUSTAIN → 0x00
VOLUME  → 0x01
```

Faixa e valores controlados:

```text
0, 1, 2, 10, 25, 50, 75, 99 e 100
```

Os dois parâmetros foram confirmados nos slots internos humanos 1 e 2.

## Correção arquitetural importante

As capturas mostraram que os índices `21–22` permanecem `01 04` tanto no
M-BOOST quanto no COMP1. Portanto, esse campo **não é o model_id do efeito**.

Consequência:

```text
mensagem 0x1C
  → informa slot + seletor + valor
  → não identifica sozinha qual efeito ocupa o slot
```

A identidade correta deve ser resolvida pela cadeia estrutural atual:

```text
slot interno recebido
  → efeito real no slot da cadeia
  → parâmetros daquele efeito no catálogo JSON
  → seletor message_match
  → codec e valor
```

Isso evita a colisão real abaixo:

```text
seletor 0 no M-BOOST → GAIN
seletor 0 no COMP1   → SUSTAIN
```

## Implementação

O decoder passou a separar:

- `EffectParameterSignal`: envelope ainda sem identidade de efeito;
- `EffectParameterEvent`: resultado após cruzar o sinal com a cadeia.

Arquivos principais:

```text
tools/parameters/decoder.py
tools/commands/preset_monitor_core.py
catalog/protocol_profiles/effect_parameter_response_1c_v1.json
catalog/effects/dyn/001_comp1.json
catalog/effects/dyn/004_m_boost.json
```

O COMP1 foi cadastrado com:

```text
SUSTAIN → parameter_selector 0
VOLUME  → parameter_selector 1
```

O M-BOOST/GAIN também passou a declarar explicitamente
`parameter_selector = 0` e resolução por contexto da cadeia.

## Validação offline

```text
Ran 349 tests
OK
```

A regressão cobre:

- 22 fixtures físicas do COMP1;
- 27 fixtures físicas do M-BOOST;
- resolução ambígua sem contexto;
- resolução correta por efeito da cadeia;
- dois parâmetros independentes no mesmo slot;
- slots internos 1 e 2;
- manutenção da compatibilidade do validador histórico do M-BOOST;
- limpeza dos valores ao trocar preset.

## Validação física aprovada

A integração foi validada fisicamente em 6 de agosto de 2026 no preset `56B`,
usando o monitor principal:

```powershell
python -m tools.commands.matribox_monitor
```

O teste confirmou:

- exibição inicial de `M-BOOST / GAIN` e `COMP1 / SUSTAIN / VOLUME`;
- atualização independente de SUSTAIN e VOLUME;
- múltiplas instâncias de COMP1 mantendo estados separados;
- coexistência de M-BOOST e COMP1 sem colisão do seletor `0`;
- preservação do estado de uma instância de COMP1 enquanto outro slot foi
  substituído por COMP2, COMP3 e depois M-BOOST;
- atualização independente do novo `M-BOOST / GAIN` após a substituição;
- manutenção correta da identidade por slot interno e pelo efeito real da
  cadeia.

A limitação conhecida permanece: os valores iniciais aparecem como
`aguardando alteração` até o primeiro evento ao vivo de cada parâmetro.

## Estado

```text
capturas controladas: aprovadas
fixtures offline: aprovadas
motor corrigido: aprovado
monitor ao vivo: aprovado fisicamente
Fase 24: consolidável
```
