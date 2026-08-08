# Fase 74 — família MOD RATE/SYNC (candidata)

## Escopo

Esta fase abre somente os modelos MOD que são cópias ou subconjuntos diretos do schema observado fisicamente no **E-CHORUS**. Modelos com parâmetros adicionais (FLANGER, M-CHORUS, TREM JET, PAN PHASER, U-VIBE, BIAS TREM etc.) permanecem `pending` até uma âncora própria.

Modelos candidatos: E-CHORUS, B-CHORUS, VIBRATO, CE-ROTO, SINE TREM, TRIANGULE TREM, BBD ROTO, BBD PHASER, VIBE, TREMOLO e PHASER.

## Âncora E-CHORUS

Capturas fornecidas: `MOD01_E_CHORUS_01_DEFAULT_BOOT_SYNC.pcapng`, `MOD01_E_CHORUS_02_CUSTOM_SAVED_REOPEN.pcapng` e `MOD01_E_CHORUS_03_PARAMETER_SWEEP.pcapng`. Elas confirmam `class_id = 8`, `model_id = 1`, `secondary_selector = 4` e os seletores `0=DEPTH`, `1=RATE`, `2=VOLUME`, `3=SYNC`. O dump padrão é `50 / 0.5 Hz / 50 / OFF`; o custom salvo reabre como `37 / 3.7 Hz / 73 / OFF`. O selector 4 persiste como 50 sem controle exposto e não é catalogado.

## Domínio RATE/SYNC

Com SYNC OFF, RATE usa float32 completo e apresenta `0.1–10.0 Hz`, passo `0.1`, default `0.5 Hz`. Com SYNC ON, o mesmo selector RATE muda para enum: `1/1, 1/2, 1/2d, 1/2t, 1/4, 1/4d, 1/4t, 1/8, 1/8d, 1/8t, 1/16`, wire `0..10`, default wire `4 = 1/4`.

O usuário confirmou fisicamente que alternar SYNC **sempre reseta RATE ao default do domínio**: OFF → `0.5 Hz`; ON → `1/4`. O catálogo usa `reset_on_controller_change = true`.

## Schemas candidatos

- `DEPTH / RATE / VOLUME / SYNC`: E-CHORUS, B-CHORUS, VIBRATO, CE-ROTO, SINE TREM, TRIANGULE TREM.
- `DEPTH / RATE / SYNC`: BBD ROTO, BBD PHASER, VIBE, TREMOLO.
- `RATE / SYNC`: PHASER.

Todos os 11 modelos ficam `partially_cataloged`. Somente E-CHORUS possui âncora PCAP nesta fase; os irmãos exigem validação no `matribox_monitor --live` antes de promoção para `physically_validated`.

## Contagens candidatas

A família adiciona 38 parâmetros (`6×4 + 4×3 + 1×2`). O catálogo passa à versão 55, mantendo 201 efeitos `physically_validated`, abrindo 11 `partially_cataloged`, reduzindo `pending` para 55 e elevando o total de parâmetros catalogados para 865.
