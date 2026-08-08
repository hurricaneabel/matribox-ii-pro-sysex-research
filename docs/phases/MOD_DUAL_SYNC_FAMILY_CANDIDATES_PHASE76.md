# Fase 76 — candidatos MOD com dois RATE/SYNC

Esta fase prepara `TREM JET` e `PAN PHASER` como candidatos por inferência controlada. Não há PCAPNG novo nesta etapa: a hipótese usa a ordem de parâmetros informada pelo usuário, tipos 0..100 já conhecidos e o protocolo RATE/SYNC fisicamente validado na Fase 74.

## TREM JET

Ordem candidata:

1. `FLG DEPTH` — selector 0, 0..100, default 50
2. `FLG RATE` — selector 1, controlado por `FLG SYNC`
3. `FEEDBACK` — selector 2, 0..100, default 50
4. `TRM DEPTH` — selector 3, 0..100, default 50
5. `TRM RATE` — selector 4, controlado por `TRM SYNC`
6. `FLG SYNC` — selector 5, default OFF
7. `TRM SYNC` — selector 6, default OFF

## PAN PHASER

Ordem candidata:

1. `PHS DEPTH` — selector 0, 0..100, default 50
2. `PHS RATE` — selector 1, controlado por `PHS SYNC`
3. `PAN DEPTH` — selector 2, 0..100, default 50
4. `PAN RATE` — selector 3, controlado por `PAN SYNC`
5. `PHS SYNC` — selector 4, default OFF
6. `PAN SYNC` — selector 5, default OFF

Cada RATE usa 0.1..10.0 Hz com seu SYNC desligado e o enum `1/1` até `1/16` com seu SYNC ligado. A infraestrutura de estado foi testada para garantir que cada SYNC invalida/reset somente seu RATE dependente.

Os dois modelos permanecem `partially_cataloged` até validação física no monitor. Se um selector divergir, somente o modelo divergente precisa de captura específica.
