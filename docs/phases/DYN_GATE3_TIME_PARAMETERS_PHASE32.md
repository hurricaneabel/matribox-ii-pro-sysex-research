# Fase 32 — DYN / GATE 3, float32 completo e tempos em ms/s

**Status:** implementação aprovada offline e fisicamente no monitor principal.

## 1. Objetivo

Integrar os cinco parâmetros observados do `DYN / GATE 3` sem criar lógica
específica do efeito no monitor e, ao mesmo tempo, corrigir a leitura do valor
`0x1C` para casos que usam os quatro bytes completos de um `float32`.

Parâmetros confirmados:

```text
THRESHOLD → seletor 0 → 0–100
RATIO     → seletor 1 → 0–100
ATTACK    → seletor 2 → 1–500 ms
RELEASE   → seletor 3 → 10–10000 ms
HOLD      → seletor 4 → 0–1000 ms
```

## 2. Evidência física

Foram analisadas as capturas individuais de THRESHOLD, RATIO, ATTACK, RELEASE
e HOLD, uma captura combinada no slot humano 1 e uma captura corrigida no slot
humano 2.

A captura curta originalmente incluída no ZIP tinha nome de slot 2, mas os
bytes de slot eram `00 00`, isto é, slot humano 1. Uma captura standalone
posterior confirmou o slot humano 2 pelos bytes `00 01`.

Foram preservadas 58 respostas SysEx físicas únicas em:

```text
tests/fixtures/gate3_parameters/
```

Distribuição:

```text
slot humano 1 → 48 fixtures
slot humano 2 → 10 fixtures
```

A captura combinada no slot 1 confirmou eventos independentes:

```text
THRESHOLD 50 → 51 → 50
RATIO     50 → 52 → 50
ATTACK    250 → 251 → 250 ms
RELEASE   5000 → 5001 → 5000 ms
HOLD      500 → 501 → 500 ms
```

A captura corrigida no slot 2 confirmou:

```text
THRESHOLD 51 → 50
RATIO     51 → 50
ATTACK    300 → 250 ms
RELEASE   6037 → 5037 ms
HOLD      600 → 500 ms
```

## 3. Descoberta do payload float32 completo

O perfil histórico lia apenas os índices `59–62`, equivalentes aos quatro
nibbles dos dois bytes superiores do `float32`. Isso era suficiente para muitos
inteiros anteriores porque os dois bytes inferiores eram `00 00`.

O GATE 3 transmite valores que exigem todos os oito nibbles nos índices
`55–62`. Exemplos:

```text
5001 ms → bytes little-endian 00 48 9C 45
5037 ms → bytes little-endian 00 68 9D 45
6037 ms → bytes little-endian 00 A8 BC 45
```

Descartar os quatro primeiros nibbles reduziria a precisão e produziria valores
incorretos. Por isso, o perfil `effect_parameter_response_1c_v1` passou a
expor o payload completo de oito nibbles.

## 4. Compatibilidade com os efeitos anteriores

Foi criado o codec genérico:

```text
float32_nibbles_v1
kind: float32_as_nibbles
encoded_length: 8
```

O codec anterior continua existindo:

```text
upper_float32_nibbles_v1
encoded_length: 4
input_slice: [4, 8]
```

Assim, o perfil fornece oito nibbles para todos os efeitos, mas cada codec
seleciona somente a parte que conhece. Isso mantém COMP1, COMP2, COMP3,
boosts, gates anteriores, AC WOODY e AC SIM com o comportamento já validado.

## 5. Apresentação dos tempos

A unidade lógica armazenada permanece em milissegundos. O catálogo declara uma
regra portátil de apresentação:

```json
{
  "kind": "duration_milliseconds",
  "seconds_threshold": 1000,
  "seconds_decimals": 1,
  "decimal_separator": ","
}
```

Resultado esperado no monitor:

```text
900  → 900 ms
999  → 999 ms
1000 → 1,0 s
5037 → 5,0 s
6037 → 6,0 s
10000 → 10,0 s
```

A conversão afeta apenas o texto exibido. O estado interno e os testes continuam
preservando o valor físico integral em milissegundos.

## 6. Arquivos principais alterados

```text
catalog/catalog.json
catalog/effects/dyn/014_gate_3.json
catalog/protocol_profiles/effect_parameter_response_1c_v1.json
catalog/schemas/effect.schema.json
catalog/value_codecs/float32_nibbles_v1.json
catalog/value_codecs/upper_float32_nibbles_v1.json

tools/catalog/loader.py
tools/catalog/models.py
tools/commands/preset_monitor_core.py
tools/parameters/__init__.py
tools/parameters/codecs.py
tools/parameters/decoder.py
tools/migrations/export_effect_catalog_to_json.py

tests/fixtures/gate3_parameters/
tests/test_effect_catalog_json.py
tests/test_effect_parameters.py
```

O catálogo passou para a versão 10, com 14 efeitos DYN parametrizados e 47
parâmetros fisicamente confirmados. Permanecem 253 efeitos sem parâmetros
presumidos.

## 7. Validação offline

A suíte completa passou:

```text
Ran 401 tests
OK
```

Também passaram:

```text
python -m compileall tools tests
validação e leitura de todos os JSONs
reexportação determinística do catálogo
verificação das 58 fixtures físicas
git diff --check
```

Os testes novos cobrem:

- os cinco seletores e suas faixas;
- todos os 58 binários físicos;
- reconstrução precisa de `5001`, `5037` e `6037`;
- compatibilidade do codec histórico por `input_slice`;
- apresentação adaptativa em `ms` e `s`;
- ordem do GATE 3 no monitor;
- independência entre slots humanos 1 e 2;
- rejeição de bytes fora do domínio de nibble.

## 8. Validação física aprovada

O monitor principal reconheceu o GATE 3 no segundo slot interno enquanto o
primeiro slot recebeu sucessivamente RC-BOOST, FAT BOOST, BB-BOOST, AC-BOOST,
AC WOODY, AC SIM, GATE 1 e GATE 2. Os estados já observados de THRESHOLD e
RATIO permaneceram associados ao GATE 3 durante todas essas mudanças
estruturais.

A ordem apresentada foi confirmada:

```text
THRESHOLD
RATIO
ATTACK
RELEASE
HOLD
```

O log físico registrou, entre outros valores:

```text
THRESHOLD: 37 → 36 → 35 → 94
RATIO: 61
ATTACK: 249 → 248 → 247 → 246 → 245 → 244 → 243 ms
RELEASE: 5,0 s → 5,6 s → 4,8 s → 3,9 s → 3,4 s → 2,0 s
RELEASE: 827 ms → 294 ms → 293 ms → 292 ms → 563 ms → 564 ms → 565 ms
HOLD: 526 ms → 558 ms → 892 ms → 894 ms → 895 ms → 1,0 s
```

Isso aprovou fisicamente a leitura dos oito nibbles, a preservação de valores
inteiros em milissegundos e a troca automática de apresentação entre `ms` e
`s`. O log também mostrou duas instâncias simultâneas de GATE 3: a primeira
permaneceu aguardando alterações e a segunda preservou THRESHOLD/RATIO, sem
contaminação de estado entre slots.

O bypass não aparece explicitamente no log enviado. O usuário confirmou que
os testes funcionaram sem problemas; a ausência do evento de bypass permanece
registrada apenas como limitação de cobertura do log, não como falha funcional.

## 9. Limitações preservadas

- Os valores iniciais ainda não são extraídos do dump; aparecem após o primeiro
  movimento físico.
- A interface da pedaleira arredonda tempos em segundos para uma casa decimal;
  o valor físico pode ser, por exemplo, `5037 ms` enquanto o monitor mostra
  `5,0 s`.
- A mensagem `0x1C` isolada continua sem identificar o modelo; a cadeia atual é
  obrigatória.
- O monitor permanece somente leitura.
- O log final não contém um evento explícito de bypass do GATE 3.

## 10. Encerramento da classe DYN

Com a aprovação da Fase 32, os 14 modelos da classe `DYN` estão parametrizados,
documentados, cobertos por fixtures físicas e validados no monitor principal.
A classe totaliza 47 parâmetros confirmados e passa a ser a primeira classe de
efeitos encerrada integralmente no projeto.

A branch `research/dyn-parameters` pode ser consolidada na `main`. A próxima
classe deverá iniciar em uma nova branch de pesquisa, sem reutilizar a branch
DYN como área de trabalho ativa.
