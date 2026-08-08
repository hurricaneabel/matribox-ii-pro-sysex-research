# Fase 73 — EQ: candidatos de parâmetros

A classe `EQ` foi aberta com cinco modelos estruturais. A pesquisa desta fase cobre somente leitura/hidratação dos parâmetros normais; nenhuma escrita SysEx nova é introduzida.

## Modelos e controles informados pela interface

Os quatro primeiros modelos compartilham cinco bandas com faixa `-50..50`, default `0`, mais VOLUME `0..100`, default `50`:

- `GUITAR EQ 1`: 125 Hz, 400 Hz, 800 Hz, 1.6 kHz, 4 kHz, VOLUME;
- `GUITAR EQ 2`: 100 Hz, 500 Hz, 1 kHz, 3 kHz, 6 kHz, VOLUME;
- `BASS EQ 1`: 33 Hz, 150 Hz, 600 Hz, 2 kHz, 8 kHz, VOLUME;
- `BASS EQ 2`: 50 Hz, 120 Hz, 400 Hz, 800 Hz, 4.5 kHz, VOLUME.

`CALIF EQ` possui somente cinco bandas `-50..50`, todas com default `0`: 80 Hz, 240 Hz, 750 Hz, 2.2 kHz e 6.6 kHz. Não existe VOLUME visível nesse modelo.

## Âncoras PCAPNG

`GUITAR EQ 1` (`model_id = 53`) foi capturado em boot/default, reopen com valores personalizados e sweep. O dump personalizado confirmou `-37 / -19 / 7 / 26 / 43 / 73`, e os eventos `0x1C` provaram:

| Selector | Controle | Faixa |
| ---: | --- | --- |
| 0 | 125 Hz | -50..50 |
| 1 | 400 Hz | -50..50 |
| 2 | 800 Hz | -50..50 |
| 3 | 1.6 kHz | -50..50 |
| 4 | 4 kHz | -50..50 |
| 5 | VOLUME | 0..100 |

Os valores assinados são enviados diretamente como `float32_nibbles_v1`; não há offset de 50. A captura do sweep contém alguns eventos incidentais no selector 2 causados por interação acidental com a roda do mouse, mas eles permanecem dentro da faixa e não alteram o mapeamento. As fixtures usam somente eventos inequívocos.

`CALIF EQ` (`model_id = 60`) confirmou selectors 0..4 para suas cinco bandas, também com `float32_nibbles_v1` e faixa `-50..50`. O dump pode conservar `selector 5 = 50`, mas a interface não expõe VOLUME e o sweep não produz controle correspondente; por isso esse valor é tratado como resíduo de slot e não é catalogado.

## Candidata inicial

O schema foi aplicado aos cinco EQs como somente-leitura:

- 5/5 `partially_cataloged` aguardando validação no monitor;
- 29 parâmetros EQ catalogados;
- `GUITAR EQ 1` e `CALIF EQ` possuem evidência PCAPNG direta;
- `GUITAR EQ 2`, `BASS EQ 1` e `BASS EQ 2` reutilizam o layout 0..5 como inferência controlada apoiada pela estrutura idêntica informada na interface;
- `catalog_version = 54`;
- 196 efeitos fisicamente validados no projeto;
- 827 parâmetros catalogados;
- 66 efeitos permanecem sem parâmetros em outras classes.

A promoção para `physically_validated` depende do teste dos cinco modelos no `matribox_monitor --live`, preferencialmente com `--log` habilitado.


## Promoção física

Após a candidata, os cinco modelos foram testados individualmente no hardware com `matribox_monitor --live --log eq_phase73_validation.txt`. O usuário confirmou correspondência exata entre pedaleira e script para todos os parâmetros. O fechamento e os contadores finais estão em `EQ_CLASS_CONSOLIDATION_PHASE73.md`.
