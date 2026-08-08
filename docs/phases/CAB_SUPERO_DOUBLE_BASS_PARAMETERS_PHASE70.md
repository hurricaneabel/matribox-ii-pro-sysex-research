# Fase 70 — CAB / SUPERO 1X6 + DOUBLE BASS

## Objetivo

Abrir a pesquisa da classe CAB com apenas dois modelos fisicamente capturados antes de replicar o schema para os demais modelos. O foco é validar hidratação pelo dump salvo `0x10`, eventos ao vivo `0x1C`, seletores e a necessidade do `float32` completo.

## Modelos físicos

- `CAB / SUPERO 1X6` — `model_id=0`, `secondary_selector=10`;
- `CAB / DOUBLE BASS` — `model_id=69`, `secondary_selector=10`.

Os dois foram testados no mesmo slot físico para manter o slot constante e variar apenas o modelo.

## Mapa confirmado

| Seletor | Parâmetro | Wire / UI | Default |
|---:|---|---|---|
| 1 | VOLUME | `0..100` direto | `50` |
| 5 | LOW CUT | `19=OFF`; `20..2000` = Hz | `OFF` (`19`) |
| 6 | HIGH CUT | `2000..20000` = Hz; `20001=OFF` | `OFF` (`20001`) |

Seletores persistidos `2`, `3` e `4` apresentaram resíduos de slot e não correspondem a controles visíveis da classe CAB; portanto não são catalogados.

## Evidência de hidratação

SUPERO 1X6 foi salvo/reaberto com `VOLUME=37`, `LOW CUT=630 Hz`, `HIGH CUT=15500 Hz`, recuperados do dump inicial sem alteração de knobs. DOUBLE BASS repetiu a prova com `28`, `956 Hz`, `13262 Hz`.

## Evidência ao vivo

As capturas de sweep do SUPERO 1X6 e a confirmação do DOUBLE BASS produziram respostas `0x1C` nos mesmos seletores `1/5/6`. As sentinelas `19` e `20001` também foram observadas fisicamente.

## Codec

CAB usa `float32_nibbles_v1` (oito nibbles). Não usar `upper_float32_nibbles_v1`: frequências como `15501`, `13262` e `20001` dependem dos bits inferiores do `float32`, repetindo a lição aprendida anteriormente com GATE 3.

## Validação final no monitor

O usuário validou os dois modelos simultaneamente no `matribox_monitor --live`. A hidratação inicial mostrou `SUPERO 1X6` com `VOLUME=50`, `LOW CUT=OFF`, `HIGH CUT=OFF` e `DOUBLE BASS` com valores salvos não padrão. Alterações posteriores de VOLUME, LOW CUT e HIGH CUT acompanharam exatamente os valores exibidos na pedaleira, inclusive `HIGH CUT=OFF`. Isso confirma que o caminho de hidratação `0x10` e os eventos ao vivo `0x1C` usam o `float32_nibbles_v1` completo e que as sentinelas são formatadas corretamente no monitor.

## Estado desta fase

`SUPERO 1X6` e `DOUBLE BASS` ficam `physically_validated`. Os outros 59 CABs permanecem `pending`; o schema compartilhado é uma hipótese fortemente suportada pelos dois extremos da lista, mas será aplicado aos demais apenas em uma etapa posterior de candidatos e validação em lote.
