# Fase 63 — AMP / Superb OD e Calif Star validados

## Objetivo

Catalogar e validar fisicamente Superb OD, Calif Star CL e Calif Star OD,
preservando o fluxo somente-leitura e promovendo os seletores apenas depois da
confirmação no hardware e no `matribox_monitor --live`.

## Superb OD — `04 / 48 / 07`

Interface oficial:

- GAIN, 0–100, padrão 50
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

No preset 56B, o monitor exibiu `3/5/7/1/4/6`, confirmando ordem e hidratação
dos seis controles em valores baixos.

## Calif Star CL — `04 / 19 / 07`

Interface oficial:

- GAIN, 0–100, padrão 40
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

No preset 56B, o monitor exibiu `33/41/54/62/45/62`, confirmando os seis
seletores em faixa intermediária.

## Calif Star OD — `04 / 4A / 07`

Interface oficial:

- INPUT, 0–100, padrão 50
- GAIN, 0–100, padrão 50
- PRESENCE, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- MIDDLE, 0–100, padrão 50
- TREBLE, 0–100, padrão 50

Mapa fisicamente validado:

- `0 = INPUT`
- `1 = GAIN`
- `2 = PRESENCE`
- `3 = VOLUME`
- `4 = BASS`
- `5 = MIDDLE`
- `6 = TREBLE`

No preset 56B, o monitor exibiu `94/93/79/90/97/88/100`, confirmando os sete
seletores e o extremo superior `100`.

## Resultado

Os três efeitos passam de `partially_cataloged` para `physically_validated`.
Todos os parâmetros ficam com `physical: true`, `read_only: true`,
`monitor_integration_physical_validation: approved` e
`physical_validation_without_pcapng: true`.

O catálogo permanece na versão 44, com 67 efeitos parametrizados, 277
parâmetros descritos e 200 efeitos ainda `pending`.

## Validação offline

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

## Próximo passo exato

1. manter a branch `research/amp-parameters`;
2. levantar controles, faixas e defaults de `BOG SV CL`;
3. preparar o próximo candidato somente-leitura;
4. validar no `matribox_monitor --live` antes de promover.
