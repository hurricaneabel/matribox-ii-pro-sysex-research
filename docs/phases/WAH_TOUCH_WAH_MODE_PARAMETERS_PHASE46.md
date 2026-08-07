# Fase 46 — WAH / TOUCH WAH e MODE enum

Uma captura combinada confirmou o dump salvo e os eventos ao vivo. A identidade
é `class_id 0x02`, `model_id 0x0F` e seletor secundário `0x01`.

| Seletor | Parâmetro | Domínio | Padrão |
|---:|---|---|---:|
| 0 | SENSE | 0–100 | 50 |
| 1 | RANGE | 0–100 | 50 |
| 2 | Q | 0–100 | 50 |
| 3 | MIX | 0–100 | 50 |
| 4 | MODE | GUITAR/BASS | GUITAR |

O dump preservou `21 / 43 / 65 / 87 / BASS`. Ao vivo, os numéricos mudaram
para `22 / 44 / 66 / 88`, SENSE confirmou 0, 50 e 100 e MODE alternou entre
GUITAR (`0`) e BASS (`1`). Os seletores 5 e 6 contêm resíduos 100 e 1 e são
ignorados.

O seletor secundário `0x01`, diferente do `0x05` dos primeiros WAH, reforça que
a identidade deve vir da cadeia estrutural. O catálogo passa à versão 24, com
27 efeitos parametrizados, 106 parâmetros e 240 efeitos pendentes.

A validação física final confirmou alterações em tempo real e hidratação em uma
cadeia cheia. Uma instância no fim da cadeia preservou
`81 / 74 / 69 / 89 / BASS`; outra região confirmou RANGE 55, Q 42, MIX 15 e
MODE GUITAR. A Fase 46 está aprovada.
