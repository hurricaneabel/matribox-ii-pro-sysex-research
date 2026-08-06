# Fase 26 — DYN / AC WOODY e GATE 1

## Objetivo

Catalogar dois efeitos DYN de parâmetro único usando o motor genérico já
validado:

```text
AC WOODY → SHAPE: 0–100
GATE 1   → THRESHOLD: 0–100
```

A escolha conjunta reduz trabalho repetido sem misturar protocolos diferentes:
os dois efeitos apresentaram a mesma estrutura física e foram validados nos
slots internos humanos 1 e 2.

## Capturas controladas

Preset de teste: `56B`.

AC WOODY:

```text
AC_WOODY_SHAPE_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
ac_woody_slot2_short_capture.pcapng
```

GATE 1:

```text
GATE1_THRESHOLD_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
gate1_slot2_short_capture.pcapng
```

As respostas SysEx físicas únicas foram preservadas em:

```text
tests/fixtures/ac_woody_parameters/  → 11 mensagens
tests/fixtures/gate1_parameters/     → 11 mensagens
```

A captura completa do AC WOODY não registrou o retorno final de 100 para 50,
mas o valor 50 já havia sido observado no slot 1 e foi novamente confirmado no
slot 2. Isso não deixa lacuna na faixa ou no codec.

## Estrutura confirmada

Ambos reutilizam o perfil e o codec existentes:

```text
comando                  0x1C
tamanho                  70 bytes
slot interno             índices 39–40, zero-based
seletor do parâmetro     índice 48
valor                    índices 59–62
marcador/tipo            índices 63–64 = 01 01
perfil                    effect_parameter_response_1c_v1
codec                     upper_float32_nibbles_v1
```

Parâmetros:

```text
AC WOODY / SHAPE       → seletor 0, inteiro 0–100
GATE 1 / THRESHOLD     → seletor 0, inteiro 0–100
```

Valores-âncora confirmados:

```text
0   → 00 00 00 00
1   → 08 00 03 0F
2   → 00 00 04 00
10  → 02 00 04 01
25  → 0C 08 04 01
50  → 04 08 04 02
51  → 04 0C 04 02
75  → 09 06 04 02
99  → 0C 06 04 02
100 → 0C 08 04 02
```

Slots:

```text
slot humano 1 → 00 00
slot humano 2 → 00 01
```

O endereço opaco dos índices 21–22 permanece `01 04`. Como nas fases
anteriores, a identidade do efeito deve vir da cadeia estrutural atual e não
desse endereço.

## Implementação

Arquivos principais:

```text
catalog/effects/dyn/010_ac_woody.json
catalog/effects/dyn/012_gate_1.json
tests/fixtures/ac_woody_parameters/
tests/fixtures/gate1_parameters/
tests/test_effect_catalog_json.py
tests/test_effect_parameters.py
tools/migrations/export_effect_catalog_to_json.py
```

Não foi necessária alteração no decoder, codec, estado ou monitor. O motor da
Fase 24 já resolve corretamente:

```text
slot do evento
→ efeito real na cadeia
→ seletor dentro daquele efeito
→ parâmetro e valor
```

Isso é importante porque o seletor `0` agora possui vários significados em
efeitos diferentes, todos resolvidos pelo contexto da cadeia.

## Validação offline

A suíte completa passou:

```text
Ran 364 tests
OK
```

A regressão cobre:

- 11 fixtures físicas do AC WOODY;
- 11 fixtures físicas do GATE 1;
- faixa 0–100 e valor 51 no slot 2;
- resolução por contexto de efeito;
- apresentação de SHAPE e THRESHOLD no monitor;
- atualização ao vivo simulada no slot interno 2;
- exportação reproduzível do catálogo;
- preservação dos efeitos DYN já catalogados.

## Validação física da integração

Estado final:

```text
capturas controladas: aprovadas
slots 1 e 2: aprovados nas capturas
catálogo e fixtures: aprovados offline
monitor principal: aprovado fisicamente
```

O monitor principal reconheceu simultaneamente `GATE 1 / THRESHOLD` e
`AC WOODY / SHAPE`, mantendo os valores em `aguardando alteração` até o
primeiro evento ao vivo.

A validação física confirmou:

- `SHAPE` atualizando de forma contínua e independente enquanto `THRESHOLD`
  permanecia inalterado;
- `THRESHOLD` atualizando de forma contínua e independente enquanto `SHAPE`
  permanecia preservado;
- coexistência com COMP1, M-BOOST, E-BOOST e efeitos de outras classes;
- duas instâncias simultâneas de AC WOODY com estados distintos;
- preservação dos valores após substituições em outro slot;
- preservação da identidade interna após mudança da posição visual;
- GATE 1 mantendo `THRESHOLD` ao ser movido para outra posição visual.

Não foi observada colisão apesar de AC WOODY, GATE 1, M-BOOST, COMP1 e
E-BOOST reutilizarem o seletor `0` em efeitos diferentes. A resolução por
slot e efeito real da cadeia permaneceu correta.

## Estado

```text
descoberta física do protocolo: aprovada
integração offline: aprovada
monitor ao vivo: aprovado
Fase 26: fisicamente validada e pronta para consolidação
```
