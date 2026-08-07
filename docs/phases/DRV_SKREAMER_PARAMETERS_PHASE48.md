# Fase 48 — DRIVE / Skreamer

Quatro capturas controladas inauguraram a pesquisa da classe DRIVE. A identidade
estrutural confirmada é `class_id 0x03`, `model_id 0x00` e seletor secundário
`0x03`.

| Seletor | Parâmetro | Domínio | Padrão salvo |
|---:|---|---|---:|
| 0 | GAIN | 0–100 | 40 |
| 1 | TONE | 0–100 | 70 |
| 2 | VOLUME | 0–100 | 50 |

Os três dumps completos, descomprimidos para 1.211 bytes, preservaram exatamente:

```text
padrão: 40 / 70 / 50
salvo A: 21 / 43 / 65
salvo B: 22 / 44 / 66
```

A varredura ao vivo confirmou os seletores 0–2 e valores próximos aos limites.
O valor adicional VOLUME 2 não altera o mapa. Eventos de zero não foram emitidos
quando o controle já se encontrava em zero. Os seletores salvos 3–14 permanecem
zerados, sem resíduos a catalogar.

Todos os parâmetros reutilizam o perfil `effect_parameter_response_1c_v1` e o
codec `upper_float32_nibbles_v1`. A hidratação genérica limita a leitura aos
três seletores catalogados.

O catálogo passa à versão 26, com 29 efeitos parametrizados, 116 parâmetros e
238 efeitos pendentes. A análise física das capturas está concluída; a
integração final no monitor foi aprovada com GAIN 60, TONE 55 e VOLUME 78. A
Fase 48 está consolidada.
