# Fase 35 — FREQ / DUAL MELODY: valores assinados

## Objetivo

Catalogar e integrar em modo somente leitura os cinco parâmetros físicos do
`FREQ / Dual Melody`, com foco especial em determinar se `LOW PITCH -24..0` é
um valor numérico negativo real no SysEx ou apenas uma apresentação da UI.

## Resultado das capturas

As sete capturas controladas confirmaram:

```text
HIGH PITCH → seletor 0 → 0..24
LOW PITCH  → seletor 1 → -24..0
DRY        → seletor 2 → 0..100
HI VOL     → seletor 4 → 0..100
LOW VOL    → seletor 5 → 0..100
```

Todos usam o perfil `effect_parameter_response_1c_v1`, marker/type `01 01` e o
codec já existente `upper_float32_nibbles_v1`. A identidade do efeito continua
vindo da cadeia estrutural atual.

## Descoberta principal: LOW PITCH é float32 assinado nativo

A hipótese de um índice interno 0-based foi descartada pelas respostas físicas.
Os valores negativos aparecem diretamente no float32:

```text
valor da pedaleira   nibbles 59–62   float32 reconstruído
-24                  0C 00 0C 01     -24.0
-23                  0B 08 0C 01     -23.0
-12                  04 00 0C 01     -12.0
 -1                  08 00 0B 0F      -1.0
  0                  00 00 00 00       0.0
```

Nenhum novo codec é necessário. O `value_type` permanece `integer`; o range
negativo no catálogo faz a validação genérica aceitar somente `-24..0`.

## Seletor 3

As respostas device->host observadas usam `0, 1, 2, 4, 5`. Não houve resposta
do seletor 3. A implementação preserva essa lacuna; HI VOL e LOW VOL não são
renumerados.

Há uma observação direcional adicional: nas mensagens host->device presentes
nas mesmas capturas, HI VOL e LOW VOL aparecem com seletores 3 e 4. Isso não
afeta o monitor, que usa as respostas recebidas 4 e 5. Também significa que
essa fase não deve ser usada como evidência suficiente para implementar escrita.

## Evidência física preservada

Foram geradas 40 fixtures de 70 bytes a partir das respostas device->host:

```text
slot humano 1: 30 fixtures
slot humano 2: 10 fixtures
total:         40 fixtures
```

As capturas individuais preservam extremos e pontos próximos aos limites. A
combinada confirma `13 / -13 / 51 / 52 / 53`, seguida do retorno aos valores de
referência. A short no slot humano 2 confirma `14 / -14 / 61 / 62 / 63` e os
retornos.

Fontes controladas:

```text
DualMelody_Hipitch_first_dump.pcapng
DualMelody_LowPitch_first_dump.pcapng
DualMelody_dry_first_dump.pcapng
DualMelody_HiVol_first_dump.pcapng
DualMelody_LowVol_first_dump.pcapng
DualMelody_UniqueValue_dump.pcapng
DualMelody_ShortValue_dump.pcapng
```

## Arquitetura

Não foi necessária alteração em decoder, codec, estado ou monitor. A Fase 35
expande apenas dados, evidências e testes sobre a arquitetura genérica existente.

Arquivos principais desta fase:

```text
catalog/effects/freq/003_dual_melody.json
tests/fixtures/dual_melody_parameters/
tests/test_effect_catalog_json.py
tests/test_effect_parameters.py
tools/migrations/export_effect_catalog_to_json.py
```

## Estado da validação

A Fase 35 está **fisicamente aprovada** no monitor principal. A suíte final
executou 418 testes sem regressões; `compileall` e `git diff --check` também
foram aprovados.

## Validação física no monitor

A validação confirmou:

1. HIGH PITCH acompanhando valores positivos em tempo real;
2. LOW PITCH preservando corretamente valores negativos reais e o retorno a zero;
3. DRY, HI VOL e LOW VOL atualizando de forma independente;
4. bypass OFF/ON sem perda dos últimos valores observados;
5. duas instâncias de DUAL MELODY em posições distintas mantendo estados
   independentes, sem contaminação entre slots.

Isso encerra a integração somente leitura de DUAL MELODY. Não implementar
escrita com base nesta fase; a assimetria direcional de HI VOL/LOW VOL exige
pesquisa própria antes de qualquer comando host->device.
