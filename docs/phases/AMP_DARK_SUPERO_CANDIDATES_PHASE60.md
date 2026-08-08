# Fase 60 — AMP / Dark Double, Dark Deluxe e Supero 2 CL

## Objetivo

Validar fisicamente três modelos AMP a partir dos controles, faixas e defaults
observados na interface oficial, usando o `matribox_monitor --live` como leitura
somente-leitura.

## Interface oficial e mapa validado

### Dark Double — `04 / 04 / 07`

- `0 = GAIN`, 0–100, padrão 35
- `1 = VOLUME`, 0–100, padrão 50
- `2 = BASS`, 0–100, padrão 50
- `3 = MIDDLE`, 0–100, padrão 40
- `4 = TREBLE`, 0–100, padrão 60
- `5 = BRIGHT`, OFF/ON, padrão ON (`0=OFF`, `1=ON`)

### Dark Deluxe — `04 / 05 / 07`

- `0 = GAIN`, 0–100, padrão 30
- `1 = VOLUME`, 0–100, padrão 50
- `2 = BASS`, 0–100, padrão 50
- `3 = TREBLE`, 0–100, padrão 50

### Supero 2 CL — `04 / 0F / 07`

- `0 = GAIN`, 0–100, padrão 30
- `1 = TONE`, 0–100, padrão 50
- `2 = VOLUME`, 0–100, padrão 50

## Validação física

A candidata foi testada no preset 56B com os três amps simultaneamente. O
monitor apresentou:

```text
DARK DOUBLE
GAIN 19
VOLUME 20
BASS 19
MIDDLE 17
TREBLE 9
BRIGHT ligado

DARK DELUXE
GAIN 65
VOLUME 69
BASS 74
TREBLE 71

SUPERO 2 CL
GAIN 87
TONE 75
VOLUME 94
```

O teste físico também foi acompanhado pelo log, usando o primeiro amp com
valores baixos, o segundo com valores médios e o terceiro com valores altos.
Todos os controles corresponderam corretamente. A validação foi concluída sem
PCAPNG adicional, porque o mapa candidato foi confirmado diretamente no
hardware em modo somente-leitura.

Os três modelos passam para `physically_validated`; todos os parâmetros ficam
com `physical: true` e `monitor_integration_physical_validation: approved`.

## Validação offline

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

Resultado físico informado: **501 testes, OK**.

## Estado

O catálogo permanece na versão 41, com 58 efeitos parametrizados, 227
parâmetros e 209 efeitos ainda `pending`.

## Próximo passo exato

1. manter a branch `research/amp-parameters`;
2. levantar controles, faixas e defaults de `SUPERO 2 OD` (`04 / 28 / 07`);
3. em seguida levantar `VOKS 15TB` (`04 / 10 / 07`) e `VOKS 30N` (`04 / 11 / 07`);
4. preparar candidatos somente-leitura e validar no `matribox_monitor --live`;
5. não assumir equivalência de layout apenas pelo nome ou família.
