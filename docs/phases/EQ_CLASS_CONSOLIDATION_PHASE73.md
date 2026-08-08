# Fase 73 — consolidação final da classe EQ

A pesquisa de parâmetros da classe `EQ` foi encerrada com **5/5 modelos fisicamente validados** e **29 parâmetros** catalogados.

## Resultado final

- `GUITAR EQ 1`: 5 bandas + VOLUME;
- `GUITAR EQ 2`: 5 bandas + VOLUME;
- `BASS EQ 1`: 5 bandas + VOLUME;
- `BASS EQ 2`: 5 bandas + VOLUME;
- `CALIF EQ`: 5 bandas, sem VOLUME visível;
- bandas: `-50..50`, default `0`;
- VOLUME: `0..100`, default `50`;
- codec: `float32_nibbles_v1`;
- `catalog_version = 54`;
- 201 efeitos fisicamente validados no projeto;
- 827 parâmetros catalogados;
- 66 efeitos ainda sem parâmetros em outras classes.

## Layouts

Nos quatro primeiros EQs, selectors 0..4 seguem a ordem visual das cinco bandas e selector 5 representa VOLUME. GUITAR EQ 1 foi a âncora PCAPNG desse layout.

`CALIF EQ` usa somente selectors 0..4 para 80 Hz, 240 Hz, 750 Hz, 2.2 kHz e 6.6 kHz. O dump pode conservar `selector 5 = 50`, mas esse campo não corresponde a um controle visível e permanece ignorado como resíduo de slot.

## Valores assinados

As bandas usam valores assinados nativos em float32. Não existe offset artificial: por exemplo `-50`, `-37`, `-1`, `0`, `1`, `37` e `50` são transmitidos como os próprios valores físicos. O sweep do GUITAR EQ 1 teve alguns eventos incidentais no selector 2 causados pela roda do mouse, sem alterar o mapeamento; as fixtures preservam apenas frames inequívocos.

## Validação física final

Depois da implementação candidata, o usuário executou `matribox_monitor --live --log eq_phase73_validation.txt` e percorreu os cinco EQs, alterando os controles e comparando cada valor exibido pelo script com a pedaleira. O usuário confirmou explicitamente que **todos os valores corresponderam 100%**.

O log registrou, entre outros:

- GUITAR EQ 1: `-47 / -42 / -50 / 50 / 28`, VOLUME `25`;
- GUITAR EQ 2: `-50 / 50 / -28 / 43 / -14`, VOLUME `44` e `16`;
- BASS EQ 1: `50 / -50 / 50 / -50 / 37`, VOLUME `9`;
- BASS EQ 2: `-50 / -50 / 50 / 50 / -21`, VOLUME `71`;
- CALIF EQ: `50 / 37 / -33 / -47 -> -50 / 32`, sem evento de VOLUME.

Isso confirma o layout, os ranges assinados, o VOLUME dos quatro primeiros modelos e a ausência de VOLUME no CALIF EQ.
