# Fase 74 — consolidação física da família MOD RATE/SYNC

## Resultado

A primeira família MOD foi encerrada com **11/11 modelos fisicamente validados** e **38 parâmetros**. O estado final mantém `catalog_version = 55`, com **212 efeitos `physically_validated`**, **55 `pending`**, nenhum `partially_cataloged` e **865 parâmetros catalogados** no projeto.

Modelos concluídos: E-CHORUS, B-CHORUS, VIBRATO, CE-ROTO, SINE TREM, TRIANGULE TREM, BBD ROTO, BBD PHASER, VIBE, TREMOLO e PHASER.

## Âncora e schemas

E-CHORUS foi a âncora PCAPNG profunda. As capturas confirmaram `class_id = 8`, `model_id = 1`, `secondary_selector = 4` e `0=DEPTH`, `1=RATE`, `2=VOLUME`, `3=SYNC`. O selector 4 persistido como 50 não corresponde a controle visível e permanece fora do catálogo.

A família validada usa três layouts:

- `DEPTH / RATE / VOLUME / SYNC`: E-CHORUS, B-CHORUS, VIBRATO, CE-ROTO, SINE TREM e TRIANGULE TREM;
- `DEPTH / RATE / SYNC`: BBD ROTO, BBD PHASER, VIBE e TREMOLO;
- `RATE / SYNC`: PHASER.

## RATE condicionado por SYNC

Com SYNC OFF, RATE usa `float32_nibbles_v1` completo e faixa física `0.1..10.0 Hz`, passo 0.1, default `0.5 Hz`. Com SYNC ON, o mesmo selector passa ao domínio enum wire `0..10`: `1/1`, `1/2`, `1/2d`, `1/2t`, `1/4`, `1/4d`, `1/4t`, `1/8`, `1/8d`, `1/8t`, `1/16`, default wire `4 = 1/4`.

O usuário confirmou fisicamente que toda troca de SYNC reseta RATE ao default do novo domínio: ON → `1/4`; OFF → `0.5 Hz`. O catálogo preserva `reset_on_controller_change = true`.

## Validação ao vivo

Após a candidata, o usuário executou `matribox_monitor --live --log mod_phase74_family_validation.txt` e testou os 11 modelos individualmente no equipamento. Ele confirmou que os valores exibidos pelo script corresponderam integralmente à pedaleira. O log contém eventos para todos os modelos da família, incluindo RATE em Hz, SYNC, DEPTH/VOLUME onde existentes, extremos e valores intermediários.

A compactação do log registra os eventos RATE sincronizados pelo valor wire em algumas linhas; a confirmação física do usuário cobre a apresentação correta das divisões rítmicas no monitor ao vivo.

## Próximo passo

Os demais MODs continuam `pending` e exigem schemas/âncoras próprios, especialmente D-CHORUS, M-CHORUS, FLANGER/FLANGER N/BASS JET, TREM JET, PHASER ST, PAN PHASER, U-VIBE, BIAS TREM, DETUNE e LOFI BIT.
