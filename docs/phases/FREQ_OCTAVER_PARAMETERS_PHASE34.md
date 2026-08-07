# Fase 34 — FREQ / OCTAVER

## Objetivo

Catalogar e integrar os três parâmetros físicos do `FREQ / Octaver` reutilizando
o motor genérico de parâmetros já consolidado, sem introduzir inferências sobre
valores iniciais ou comportamento não observado.

## Identidade estrutural

```text
classe: FREQ
class_id estrutural: 1
effect_key: freq.octaver
model_id: 33
secondary_selector: 1
```

A identidade do efeito vem da cadeia estrutural atual. O comando de parâmetro
`0x1C` não identifica sozinho a classe ou o modelo.

## Parâmetros confirmados

```text
selector 0 → LOW OCT  → 0–100, passo 1
selector 1 → HIGH OCT → 0–100, passo 1
selector 2 → DRY      → 0–100, passo 1
```

Todos usam:

```text
profile: effect_parameter_response_1c_v1
codec: upper_float32_nibbles_v1
marker/type: 01 01
modo: somente leitura
```

## Evidências físicas

Fontes válidas:

```text
octaver_lowoct_first_dump.pcapng
octaver_highoct_firstdump.pcapng
octaver_dry_first_comp.pcapng
octaver_combined_values_dump.pcapng
octaver_short_dump_corrigido.pcapng
```

A primeira `octaver_short_dump.pcapng` foi feita novamente no slot humano 1 e
foi explicitamente excluída como prova de segundo slot.

As capturas individuais registram 0, 1, 50, 99, 100 e retorno a 50 para cada
controle. A combinada registra:

```text
LOW OCT  51 → 50
HIGH OCT 52 → 50
DRY      53 → 50
```

A short corrigida usa o slot físico `00 01` (slot humano 2):

```text
LOW OCT  61 → 50
HIGH OCT 62 → 50
DRY      63 → 50
```

Foram preservadas 24 fixtures físicas únicas: 18 do slot humano 1 e 6 do slot
humano 2.

## Arquitetura

Nenhuma alteração foi necessária no decoder, codecs, estado ou monitor. A fase
adiciona somente dados de catálogo, fixtures, testes, documentação e seed do
exportador para que uma reexportação reproduza o efeito parametrizado.

## Validação física aprovada

A integração foi validada no monitor principal com `DYN / COMP1` antes do
OCTAVER. O efeito foi reconhecido no slot humano 2 e os três parâmetros
responderam independentemente. Uma primeira instância estabilizou em:

```text
LOW OCT  = 37
HIGH OCT = 74
DRY      = 30
```

O bypass foi alternado para desligado e ligado novamente sem perda desses
valores. Em seguida, FILTER foi adicionado à cadeia e respondeu sem alterar o
estado do OCTAVER.

Uma segunda instância de OCTAVER foi criada simultaneamente e estabilizou em:

```text
primeiro OCTAVER: LOW OCT 37 | HIGH OCT 74 | DRY 30
segundo OCTAVER:  LOW OCT 54 | HIGH OCT 37 | DRY 58
```

Os dois estados permaneceram independentes enquanto a cadeia crescia. Mais
adiante, uma terceira instância apareceu no slot humano 7 e recebeu LOW OCT 52,
DRY 42 e HIGH OCT 73 sem contaminar as duas instâncias anteriores. Isso reforça
a resolução por slot interno real, inclusive em posições mais distantes da
cadeia.

## Estado final da fase

`catalog_version` passa a 12. O catálogo contém 16 efeitos parametrizados, 56
parâmetros físicos catalogados e 251 efeitos ainda pendentes.

A suíte offline passou com `Ran 413 tests` / `OK` e `compileall` foi aprovado.
O primeiro `git diff --check` local apontou apenas uma linha em branco excedente
no fim de `docs/protocol_findings.md`; o pacote documental final remove essa
linha e deixa a verificação limpa.

A Fase 34 está **fisicamente aprovada** e pronta para commit em
`research/freq-parameters`, seguida de promoção por fast-forward à `main`.
