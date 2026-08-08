# Fase 72 — consolidação final da classe IR

A pesquisa de parâmetros normais da classe `IR` foi encerrada com **20/20 modelos fisicamente validados**. Importação de WAV/IR de terceiros, nomes importados e protocolo de transferência de arquivos permanecem deliberadamente fora do escopo até o término da catalogação de parâmetros de todas as classes.

## Resultado final

- 20 / 20 IR parametrizados e `physically_validated`;
- 60 parâmetros IR catalogados;
- `catalog_version = 53`;
- 196 efeitos fisicamente validados no projeto;
- 798 parâmetros catalogados;
- 71 efeitos ainda sem parâmetros em outras classes.

## Schema compartilhado

| Controle | Selector | Codec | Faixa física | Default | Sentinela OFF |
| --- | ---: | --- | --- | --- | --- |
| VOLUME | 1 | `float32_nibbles_v1` | 0..100 | 50 | — |
| LOW CUT | 5 | `float32_nibbles_v1` | 20..2000 Hz | OFF | raw 19 |
| HIGH CUT | 6 | `float32_nibbles_v1` | 2000..20000 Hz | OFF | raw 20001 |

A hidratação de preset (`0x10`) e os eventos ao vivo (`0x1C`) usam os mesmos valores físicos. Os seletores persistidos 2/3/4 observados nas âncoras são resíduos de slot e não controles visíveis do IR.

## Evidência PCAPNG

`IR 1` (`model_id = 0`) foi capturado em default/reopen e sweeps separados. O reopen personalizado confirmou `VOLUME 37`, `LOW CUT 637 Hz` e `HIGH CUT 15371 Hz`. `IR 20` (`model_id = 19`) confirmou o mesmo layout no extremo oposto da lista, incluindo reopen `28 / 953 / 13267` e eventos ao vivo. Fixtures de regressão preservam frames físicos dos dois extremos, inclusive `19 = OFF` e `20001 = OFF`.

Os nomes locais contendo `CLONE` nos arquivos de captura foram ignorados: nesta fase o catálogo mantém os modelos genéricos `IR 1` ... `IR 20`, pois nomes de IR importado pertencem ao protocolo de arquivos que será estudado separadamente.

## Validação física dos 20 modelos

Depois da implementação candidata, o usuário executou o monitor com log habilitado e percorreu **IR 1 até IR 20**, alterando VOLUME, LOW CUT e HIGH CUT e comparando o valor exibido pelo script com o valor mostrado na pedaleira. O usuário confirmou explicitamente que todos os modelos corresponderam corretamente.

O log `ir_phase72_validation.txt` registrou eventos de parâmetros para 19 dos 20 modelos e confirmou valores float32 não redondos em toda a faixa, além de `HIGH CUT OFF` em IR 9. `IR 4` não gerou uma linha de parâmetro no TXT durante a passagem, mas foi testado e confirmado visualmente pelo usuário, portanto a validação física manual cobre os 20 modelos.

## Escopo futuro

A classe IR está encerrada para edição normal de parâmetros. Upload/importação de WAV, slots de arquivos, nomes, fragmentação de transferência, checksum e demais operações com IRs de terceiros não são inferidos aqui e permanecem para investigação futura, após a conclusão da catalogação de parâmetros até a classe VOL.
