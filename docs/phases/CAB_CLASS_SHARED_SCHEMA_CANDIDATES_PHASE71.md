# Fase 71 — CAB / schema compartilhado para os 61 modelos

## Objetivo

Aplicar aos 59 CABs ainda pendentes o schema de parâmetros comprovado fisicamente na Fase 70 em dois modelos distantes da classe: `SUPERO 1X6` e `DOUBLE BASS`. Esta fase não promove os 59 candidatos para validação física; a promoção será feita somente após teste no hardware com `matribox_monitor --live`.

## Schema compartilhado candidato

Todos os 61 CABs expõem três controles visíveis com os mesmos defaults informados pela interface oficial:

- `VOLUME`: seletor persistido/resposta `1`, `float32_nibbles_v1`, faixa `0..100`, default `50`;
- `LOW CUT`: seletor `5`, `float32_nibbles_v1`, `19 = OFF`, `20..2000 Hz`, default `OFF`;
- `HIGH CUT`: seletor `6`, `float32_nibbles_v1`, `2000..20000 Hz`, `20001 = OFF`, default `OFF`.

Os seletores persistidos 2, 3 e 4 observados nas âncoras físicas não são expostos como parâmetros CAB; foram tratados como resíduos do slot.

## Evidência-base

A Fase 70 comprovou o mesmo layout em `SUPERO 1X6` e `DOUBLE BASS`, incluindo:

- hidratação pelo dump salvo `0x10`;
- eventos ao vivo `0x1C`;
- necessidade do `float32` completo;
- sentinelas `19` e `20001` formatadas como `OFF`;
- valores exibidos no monitor iguais aos valores da pedaleira.

## Estado da candidata

- CABs totais: 61;
- `physically_validated`: 2 (`SUPERO 1X6`, `DOUBLE BASS`);
- `partially_cataloged`: 59;
- `pending`: 0 dentro de CAB;
- parâmetros CAB catalogados: 183;
- `catalog_version`: 52.

A validação física dos 59 candidatos será feita pelo usuário modelo a modelo, podendo ser reportada em lotes. Até essa confirmação, cada um mantém `physical: false` e `monitor_integration_physical_validation: pending`.


## Validação física final

O usuário testou posteriormente todos os 59 candidatos, modelo por modelo, alterando VOLUME, LOW CUT e HIGH CUT e comparando em tempo real o `matribox_monitor --live` com a pedaleira. Todos os modelos acompanharam corretamente as alterações, inclusive frequências `float32` e as sentinelas OFF. Os 59 candidatos foram promovidos para `physically_validated`, encerrando CAB em 61/61. A consolidação final está em `CAB_CLASS_CONSOLIDATION_PHASE71.md`.
