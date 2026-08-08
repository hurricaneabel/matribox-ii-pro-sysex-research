# Fase 78 — correção D-CHORUS e validação dos demais MOD finais

O teste físico da Fase 78 confirmou integralmente M-CHORUS, DETUNE e LOFI BIT. Os três passam a `physically_validated` sem alteração de schema.

O D-CHORUS revelou uma diferença entre valor wire e apresentação da interface. O selector 0 transmite enum zero-based, enquanto a pedaleira apresenta MODE one-based:

- wire 0 → MODE 1
- wire 1 → MODE 2
- wire 2 → MODE 3
- wire 3 → MODE 4

O default físico da interface continua MODE 1, correspondente ao wire 0. A hipótese anterior 1..4 no wire explicava o sintoma observado: MODE 1 aparecia como valor ainda não reconhecido e os demais ficavam uma posição atrás.

A correção mantém D-CHORUS como `partially_cataloged` até um reteste curto do MODE 1..4. M-CHORUS, DETUNE e LOFI BIT ficam fisicamente aprovados. Estado global intermediário: `catalog_version = 59`, 223 `physically_validated`, 1 `partially_cataloged`, 43 `pending` e 922 parâmetros catalogados.
