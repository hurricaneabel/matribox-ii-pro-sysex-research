# Fase 72 — IR: schema compartilhado de parâmetros

A classe IR foi aberta somente para catalogação dos parâmetros normais do efeito. Importação de WAV/IR de terceiros, nomes carregados e protocolo de transferência de arquivos ficam explicitamente fora do escopo até o término da catalogação de todas as classes de parâmetros.

## Âncoras físicas

Foram usados os extremos da lista estrutural:

- `IR 1` (`model_id = 0`): boot/default, reopen com valores salvos e sweeps separados de VOLUME, LOW CUT e HIGH CUT.
- `IR 20` (`model_id = 19`): reopen com valores salvos e confirmação ao vivo dos três parâmetros.

Os nomes `CLONE` usados nos nomes locais de alguns PCAPNGs não fazem parte do catálogo: nesta fase os modelos permanecem `IR 1` ... `IR 20`.

## Schema confirmado

| Controle | Selector | Codec | Faixa | Default | OFF |
| --- | ---: | --- | --- | ---: | ---: |
| VOLUME | 1 | `float32_nibbles_v1` | 0..100 | 50 | — |
| LOW CUT | 5 | `float32_nibbles_v1` | 20..2000 Hz | OFF | raw 19 |
| HIGH CUT | 6 | `float32_nibbles_v1` | 2000..20000 Hz | OFF | raw 20001 |

A hidratação pelo dump `0x10` e os eventos ao vivo `0x1C` usam os mesmos valores físicos. `IR 1` confirmou o reopen `37 / 637 / 15371`; `IR 20` confirmou `28 / 953 / 13267`. Os sweeps também confirmaram que as frequências são transmitidas diretamente como float32 completo, inclusive `19` e `20001` para as sentinelas OFF.

Assim como em CAB, os seletores persistidos 2/3/4 aparecem como resíduos de slot e não são controles visíveis do IR.

## Estado da candidata antes da validação final

O schema foi aplicado aos 20 modelos IR como somente-leitura para teste no monitor:

- 20/20 `partially_cataloged`;
- IR 1 e IR 20 possuem evidência física PCAPNG direta;
- IR 2..19 reutilizam o schema compartilhado como inferência controlada;
- 60 parâmetros IR catalogados;
- `catalog_version = 53`;
- 798 parâmetros catalogados no projeto;
- 71 efeitos permanecem sem parâmetros em outras classes.

A promoção para `physically_validated` fica condicionada ao teste dos 20 modelos no `matribox_monitor --live`, preferencialmente com log habilitado.


## Encerramento

A validação final dos 20 modelos está consolidada em `IR_CLASS_CONSOLIDATION_PHASE72.md`.
