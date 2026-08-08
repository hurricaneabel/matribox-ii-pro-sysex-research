# Fase 75 — candidatos da família MOD FLANGER

## Escopo

A Fase 75 prepara **FLANGER, FLANGER N e BASS JET** como candidatos somente-leitura para validação ao vivo. Os três efeitos foram descritos pela interface com o mesmo layout e defaults:

1. `DEPTH` — 0..100, default 50;
2. `RATE` — 0.1..10.0 Hz com SYNC OFF, default 0.5 Hz;
3. `PRE DELAY` — 0..100, default 50;
4. `FEEDBACK` — 0..100, default 50;
5. `SYNC` — OFF/ON, default OFF.

O RATE/SYNC reutiliza o domínio já ancorado e fisicamente validado na Fase 74. Com SYNC ON, RATE usa o enum wire `0..10` para `1/1`, `1/2`, `1/2d`, `1/2t`, `1/4`, `1/4d`, `1/4t`, `1/8`, `1/8d`, `1/8t`, `1/16`, com default wire `4 = 1/4`. A troca de SYNC reseta RATE para o default do novo domínio.

## Hipótese candidata de seletores

Como a ordem de UI reportada é idêntica nos três modelos, a candidata usa a ordem natural:

- selector 0 = DEPTH;
- selector 1 = RATE;
- selector 2 = PRE DELAY;
- selector 3 = FEEDBACK;
- selector 4 = SYNC.

Todos os valores usam `float32_nibbles_v1`, consistente com a família RATE/SYNC já validada. Não há PCAPNG específico desta família nesta fase; qualquer divergência observada no hardware deve ser investigada somente no modelo problemático.

## Estado candidato

Os três modelos ficam `partially_cataloged`, com `physical = false` e `monitor_integration_physical_validation = pending` até o teste no `matribox_monitor --live --log`.

O catálogo passa a `catalog_version = 56` com:

- 212 efeitos `physically_validated`;
- 3 `partially_cataloged`;
- 52 `pending`;
- 880 parâmetros catalogados.

## Critério de promoção

Validar FLANGER, FLANGER N e BASS JET no equipamento, alterando DEPTH, RATE, PRE DELAY, FEEDBACK e SYNC e comparando o valor exibido pelo monitor com a pedaleira. Se os três corresponderem, promover a família inteira para `physically_validated`. Se um modelo divergir, preservar os demais e capturar PCAPNG apenas do modelo divergente.
