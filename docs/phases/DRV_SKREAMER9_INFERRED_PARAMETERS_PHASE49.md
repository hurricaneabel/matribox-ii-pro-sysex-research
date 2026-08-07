# Fase 49 — DRIVE / Skreamer 9 inferido da família

O manual oficial informa que Skreamer e Skreamer 9 expõem os mesmos controles:
GAIN, TONE e VOLUME. A identidade estrutural já catalogada do Skreamer 9 é
`class_id 0x03`, `model_id 0x01` e seletor secundário `0x03`.

Como teste controlado, o mapa fisicamente validado do Skreamer foi aplicado:

| Seletor inferido | Parâmetro | Domínio inferido |
|---:|---|---:|
| 0 | GAIN | 0–100 |
| 1 | TONE | 0–100 |
| 2 | VOLUME | 0–100 |

Nenhum valor padrão foi inventado. A hidratação lê os valores realmente salvos
no dump e limita-se aos três seletores. A entrada identifica explicitamente
`drv.skreamer` como fonte da inferência.

O catálogo passa à versão 27, com 30 efeitos parametrizados, 119 parâmetros e
237 efeitos pendentes. O monitor confirmou hidratação, alterações ao vivo e
coexistência em uma cadeia cheia. O modelo foi promovido para
`physically_validated` sem PCAPNG próprio.
