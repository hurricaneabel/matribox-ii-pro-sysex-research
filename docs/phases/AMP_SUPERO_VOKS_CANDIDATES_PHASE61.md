# Fase 61 — AMP / Supero 2 OD, Voks 15TB e Voks 30N

## Objetivo

Preparar três novos modelos AMP a partir dos controles, faixas e defaults
observados na interface oficial, sem promover a hipótese de ordem visual para
validação física antes do teste no `matribox_monitor --live`.

## Interface oficial e mapa candidato

### Supero 2 OD — `04 / 28 / 07`

Interface informada:

- GAIN 1, 0–100, padrão 50
- TONE 1, 0–100, padrão 50
- GAIN 2, 0–100, padrão 50
- TONE 2, 0–100, padrão 50
- VOLUME, 0–100, padrão 50

Hipótese somente-leitura a validar:

- `0 = GAIN 1`
- `1 = TONE 1`
- `2 = GAIN 2`
- `3 = TONE 2`
- `4 = VOLUME`

### Voks 15TB — `04 / 10 / 07`

Interface informada:

- GAIN, 0–100, padrão 30
- TONE CUT, 0–100, padrão 60
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- TREBLE, 0–100, padrão 50

Hipótese somente-leitura a validar:

- `0 = GAIN`
- `1 = TONE CUT`
- `2 = VOLUME`
- `3 = BASS`
- `4 = TREBLE`

### Voks 30N — `04 / 11 / 07`

Interface informada:

- GAIN, 0–100, padrão 30
- TONE CUT, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BRIGHT, OFF/ON, padrão OFF

Hipótese somente-leitura a validar:

- `0 = GAIN`
- `1 = TONE CUT`
- `2 = VOLUME`
- `3 = BRIGHT`, candidato `0=OFF`, `1=ON`

## Validação física concluída

O usuário validou os três efeitos simultaneamente no preset 56B, acompanhando
tanto o painel `matribox_monitor --live` quanto o log. O teste distribuiu os
valores em faixas baixa, média e alta para reduzir ambiguidade entre modelos.

Valores observados no monitor:

```text
SUPERO 2 OD
GAIN 1: 21
TONE 1: 34
GAIN 2: 9
TONE 2: 8
VOLUME: 23

VOKS 15TB
GAIN: 48
TONE CUT: 58
VOLUME: 66
BASS: 69
TREBLE: 66

VOKS 30N
GAIN: 91
TONE CUT: 90
VOLUME: 97
BRIGHT: ON
```

Todos os controles responderam corretamente. O `BRIGHT` do Voks 30N também foi
confirmado em funcionamento. Os três efeitos passam para
`physically_validated`, com `physical: true`, `read_only: true` e
`monitor_integration_physical_validation: approved`, sem necessidade de PCAPNG
adicional.

O catálogo permanece na versão 42, com 61 efeitos parametrizados, 241
parâmetros e 206 efeitos ainda `pending`.

## Valores sugeridos para validação física

Usar os três amps juntos no preset de pesquisa, mantendo faixas distintas para
facilitar a identificação visual e no log:

```text
SUPERO 2 OD
GAIN 1: 11
TONE 1: 17
GAIN 2: 23
TONE 2: 29
VOLUME: 31

VOKS 15TB
GAIN: 44
TONE CUT: 52
VOLUME: 61
BASS: 68
TREBLE: 74

VOKS 30N
GAIN: 83
TONE CUT: 91
VOLUME: 97
BRIGHT: ON
```

Depois executar:

```powershell
python -m tools.commands.matribox_monitor --live
```

A validação só será aprovada se nomes, ordem e valores corresponderem ao
hardware/software oficial, incluindo `BRIGHT` em ON/OFF.

## Validação offline

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

## Próximo passo exato

1. manter os três efeitos como `physically_validated`;
2. seguir para `VOKS 30TB` (`04 / 27 / 07`), conforme `model_id` real do catálogo;
3. levantar também `JAZZ 120` (`04 / 14 / 07`) e `SUPERB CL` (`04 / 15 / 07`);
4. preparar os novos mapas somente-leitura antes da promoção física.
