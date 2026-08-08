# Fase 75 — consolidação da família FLANGER MOD

A família `FLANGER`, `FLANGER N` e `BASS JET` foi implementada inicialmente por inferência do layout comum informado pelo usuário e do RATE/SYNC já validado na Fase 74.

## Schema confirmado

Os três modelos usam a mesma ordem de parâmetros:

1. `DEPTH` — selector 0, 0..100, default 50
2. `RATE` — selector 1, 0.1..10.0 Hz com SYNC OFF; enum rítmico com SYNC ON
3. `PRE DELAY` — selector 2, 0..100, default 50
4. `FEEDBACK` — selector 3, 0..100, default 50
5. `SYNC` — selector 4, OFF/ON, default OFF

RATE e SYNC usam `float32_nibbles_v1`. A troca de SYNC reutiliza o comportamento fisicamente confirmado na Fase 74: RATE volta para 0.5 Hz ao desligar e para 1/4 ao ligar.

## Validação física

O usuário validou os três modelos no `matribox_monitor --live --log` e confirmou que todos os valores apresentados pelo script corresponderam exatamente aos valores da pedaleira. O log mostrou DEPTH, RATE, PRE DELAY, FEEDBACK e SYNC nos três modelos, incluindo RATE em Hz e domínio sincronizado.

Resultado: **3/3 `physically_validated`**, 15 parâmetros.
