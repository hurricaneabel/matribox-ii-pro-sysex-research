# Fase 64 — AMP / BOG SV e BOG XT Blue candidatos

## Objetivo

Preparar BOG SV CL, BOG SV OD e BOG XT BLUE como candidatos somente-leitura a
partir dos controles, faixas e defaults informados pela interface oficial. Os
seletores seguem a ordem visual como hipótese controlada e só podem ser
promovidos depois da validação física no `matribox_monitor --live`.

## BOG SV CL — `04 / 1A / 07`

Interface oficial informada:

- GAIN, 0–100, padrão 30
- PRESENCE, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- TREBLE, 0–100, padrão 50
- BRIGHT, OFF/ON, padrão OFF

Mapa candidato:

- `0 = GAIN`
- `1 = PRESENCE`
- `2 = VOLUME`
- `3 = BASS`
- `4 = TREBLE`
- `5 = BRIGHT`

BRIGHT usa provisoriamente `0=OFF` e `1=ON`, seguindo a codificação booleana já
validada em outros AMP. A codificação e o seletor permanecem candidatos até o
teste físico deste modelo.

## BOG SV OD — `04 / 3D / 07`

Interface oficial informada:

- GAIN, 0–100, padrão 30
- PRESENCE, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- MIDDLE, 0–100, padrão 50
- TREBLE, 0–100, padrão 50

Mapa candidato:

- `0 = GAIN`
- `1 = PRESENCE`
- `2 = VOLUME`
- `3 = BASS`
- `4 = MIDDLE`
- `5 = TREBLE`

## BOG XT BLUE — `04 / 43 / 07`

Interface oficial informada:

- GAIN, 0–100, padrão 30
- PRESENCE, 0–100, padrão 50
- VOLUME, 0–100, padrão 50
- BASS, 0–100, padrão 50
- MIDDLE, 0–100, padrão 50
- TREBLE, 0–100, padrão 50

Mapa candidato:

- `0 = GAIN`
- `1 = PRESENCE`
- `2 = VOLUME`
- `3 = BASS`
- `4 = MIDDLE`
- `5 = TREBLE`

## Estado da candidata

Os três efeitos ficam em `partially_cataloged`. Todos os parâmetros usam
`physical: false`, `read_only: true`, origem da ordem marcada como
`candidate_from_user_reported_official_ui_order` e integração física do monitor
como `pending`.

O catálogo passa à versão 45, com 70 efeitos parametrizados, 295 parâmetros
descritos e 197 efeitos ainda `pending`.

## Validação offline

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

## Teste físico sugerido

Usar três instâncias no preset 56B, mantendo a estratégia baixa/média/alta:

```text
BOG SV CL
GAIN: 11
PRESENCE: 17
VOLUME: 23
BASS: 29
TREBLE: 35
BRIGHT: ON

BOG SV OD
GAIN: 44
PRESENCE: 51
VOLUME: 58
BASS: 64
MIDDLE: 69
TREBLE: 74

BOG XT BLUE
GAIN: 82
PRESENCE: 87
VOLUME: 91
BASS: 94
MIDDLE: 97
TREBLE: 100
```

Além do painel, alternar BRIGHT em BOG SV CL entre OFF e ON para confirmar a
codificação booleana.

## Próximo passo exato

1. executar `python -m tools.commands.matribox_monitor --live`;
2. confirmar nomes, ordem e valores dos três modelos;
3. testar BRIGHT OFF/ON no BOG SV CL;
4. somente depois promover os três para `physically_validated`.
