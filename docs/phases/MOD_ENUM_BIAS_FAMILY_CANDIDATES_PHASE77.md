# Fase 77 — MOD: PHASER ST, U-VIBE e BIAS TREM candidatos

A Fase 77 prepara três modelos MOD por inferência controlada, reutilizando somente mecanismos já fisicamente validados nas Fases 74–76. Nenhum dos três é promovido antes do teste no hardware.

## PHASER ST

Ordem informada pela interface: `COLOR / RATE / SYNC`.

Hipótese candidata:

- selector 0 = COLOR (`WARM=0`, `SHARP=1`), default WARM;
- selector 1 = RATE;
- selector 2 = SYNC.

RATE/SYNC reutiliza o domínio validado do E-CHORUS: 0.1–10.0 Hz com SYNC OFF, enum rítmico wire 0–10 com SYNC ON, defaults 0.5 Hz e 1/4 e reset na troca de SYNC.

## U-VIBE

Ordem informada pela interface: `DEPTH / RATE / VOLUME / MODE / SYNC`.

Hipótese candidata:

- selector 0 = DEPTH (0–100, default 50);
- selector 1 = RATE;
- selector 2 = VOLUME (0–100, default 50);
- selector 3 = MODE (`CHORUS=0`, `VIBRATO=1`), default CHORUS;
- selector 4 = SYNC.

## BIAS TREM

Ordem informada pela interface: `DEPTH / RATE / VOLUME / SYNC / BIAS`.

Hipótese candidata:

- selector 0 = DEPTH (0–100, default 50);
- selector 1 = RATE;
- selector 2 = VOLUME (0–100, default 50);
- selector 3 = SYNC;
- selector 4 = BIAS (0–100, default 50).

## Estado candidato

Os três modelos ficam `partially_cataloged`, `physical=false` e somente-leitura até validação no `matribox_monitor --live --log`. Se algum selector ou enum divergir, apenas o modelo divergente exige PCAPNG específico.

Estado global da candidata: `catalog_version = 58`, 217 efeitos `physically_validated`, 3 `partially_cataloged`, 47 `pending` e 906 parâmetros catalogados.
