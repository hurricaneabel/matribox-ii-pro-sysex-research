# Fase 50 — DRIVE / Butter OD

Uma captura combinada confirmou identidade, dump salvo e eventos ao vivo. A
identidade estrutural é `class_id 0x03`, `model_id 0x02` e seletor secundário
`0x03`.

| Seletor | Parâmetro | Domínio | Padrão informado |
|---:|---|---|---:|
| 0 | GAIN | 0–100 | 40 |
| 1 | VOLUME | 0–100 | 70 |

A captura contém dois dumps completos idênticos. O slot preservou
`21 / 65 / 50 / 0...`: os dois primeiros valores correspondem aos controles;
o seletor 2 mantém 50 sem controle ou evento ao vivo e é rejeitado pelo catálogo.

A varredura confirmou 0, 1, 50, 99 e 100 independentemente nos seletores 0 e 1.
Ambos reutilizam o codec `upper_float32_nibbles_v1`. A hidratação genérica lê
somente GAIN e VOLUME.

O catálogo passa à versão 28, com 31 efeitos parametrizados, 121 parâmetros e
236 efeitos pendentes. A validação final confirmou duas instâncias numa cadeia
cheia: posição 4 com GAIN 0/VOLUME 48 e posição 12 com GAIN 82/VOLUME 81. A
Fase 50 está aprovada.
