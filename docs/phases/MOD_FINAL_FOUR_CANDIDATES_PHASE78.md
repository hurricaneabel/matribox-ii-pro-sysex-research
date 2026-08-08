# Fase 78 — quatro MOD finais candidatos

A Fase 78 prepara os quatro modelos restantes da classe MOD por inferência controlada, reutilizando apenas codecs e domínios já validados fisicamente. Nenhum modelo é promovido antes do teste ao vivo.

## D-CHORUS

Controle único `MODE`, informado como valores 1, 2, 3 e 4, default 1. Hipótese: selector 0 = MODE e os valores wire são literalmente 1..4.

## M-CHORUS

Ordem informada: `MIX / RATE / FILTER / DEPTH L / DEPTH C / DEPTH R / SYNC`. Hipótese de selectors 0..6 na mesma ordem. MIX/FILTER/DEPTH L/C/R usam 0..100 default 50. RATE/SYNC reutiliza integralmente o domínio validado na Fase 74: 0.1..10.0 Hz com SYNC OFF, enum rítmico 0..10 com SYNC ON, defaults 0.5 Hz e 1/4 e reset na troca.

## DETUNE

Ordem informada: `DETUNE / WET / DRY`. Hipótese selectors 0/1/2. DETUNE usa inteiro assinado -50..50 cents, default -25, reaproveitando `float32_nibbles_v1` já comprovado para valores negativos. WET/DRY usam 0..100, default 50.

## LOFI BIT

Ordem informada: `MIX / KRUSH / BIT / HI CUT / LO CUT`, selectors 0..4. Todos são 0..100; defaults 50 / 20 / 20 / 50 / 50.

## Estado candidato

Os quatro efeitos ficam `partially_cataloged`, `physical=false` e somente-leitura até validação no `matribox_monitor --live --log`. Se um modelo divergir, apenas ele exige PCAPNG. Estado global: `catalog_version = 59`, 220 `physically_validated`, 4 `partially_cataloged`, 43 `pending` e 922 parâmetros catalogados.


> Nota posterior: o teste físico mostrou que D-CHORUS não usa wire 1..4. A correção está documentada em `MOD_FINAL_FOUR_D_CHORUS_CORRECTION_PHASE78.md`: wire 0..3 → UI MODE 1..4.
