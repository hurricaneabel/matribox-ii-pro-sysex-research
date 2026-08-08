# Fase 62 — AMP / Voks 30TB, Jazz 120 e Superb CL validados

## Objetivo

Catalogar e validar fisicamente os parâmetros de Voks 30TB, Jazz 120 e Superb
CL, mantendo o fluxo somente-leitura do projeto e sem promover hipóteses antes
do teste no hardware.

## Voks 30TB — `04 / 27 / 07`

Interface oficial:

- GAIN, 0–100, padrão 30
- TONE CUT, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- TREBLE, 0–100, padrão 50
- CHAR, COOL/HOT, padrão COOL

Mapa fisicamente validado:

- `0 = GAIN`
- `1 = TONE CUT`
- `2 = VOLUME`
- `3 = BASS`
- `4 = TREBLE`
- `5 = CHAR`, com `0=COOL` e `1=HOT`

No preset 56B, o monitor exibiu `2/4/3/4/4/HOT`. O usuário alternou CHAR entre
COOL e HOT e confirmou os dois estados.

## Jazz 120 — `04 / 14 / 07`

Interface oficial:

- GAIN, 0–100, padrão 50
- BASS, 0–100, padrão 50
- MIDDLE, 0–100, padrão 50
- TREBLE, 0–100, padrão 50
- BRIGHT, OFF/ON, padrão OFF

Mapa fisicamente validado:

- `0 = GAIN`
- `1 = BASS`
- `2 = MIDDLE`
- `3 = TREBLE`
- `4 = BRIGHT`, com `0=OFF` e `1=ON`

No preset 56B, o monitor exibiu `39/55/43/55/ON`. O usuário alternou BRIGHT
entre OFF e ON e confirmou os dois estados.

## Superb CL — `04 / 15 / 07`

Interface oficial:

- GAIN, 0–100, padrão 35
- PRESENCE, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- MIDDLE, 0–100, padrão 50
- TREBLE, 0–100, padrão 50

Mapa fisicamente validado:

- `0 = GAIN`
- `1 = PRESENCE`
- `2 = VOLUME`
- `3 = BASS`
- `4 = MIDDLE`
- `5 = TREBLE`

No preset 56B, o monitor exibiu `66/74/82/88/94/100`, confirmando a ordem e a
hidratação dos seis controles, inclusive o extremo 100.

## Resultado

Os três efeitos passam de `partially_cataloged` para `physically_validated`.
Todos os parâmetros ficam com `physical: true`, `read_only: true`,
`monitor_integration_physical_validation: approved` e
`physical_validation_without_pcapng: true`.

O catálogo permanece na versão 43, com 64 efeitos parametrizados, 258
parâmetros e 203 efeitos ainda `pending`.

## Validação offline

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

## Próximo passo exato

1. manter a branch `research/amp-parameters`;
2. levantar controles, faixas e defaults de `SUPERB OD`;
3. preparar o próximo candidato somente-leitura;
4. validar no `matribox_monitor --live` antes de promover.
