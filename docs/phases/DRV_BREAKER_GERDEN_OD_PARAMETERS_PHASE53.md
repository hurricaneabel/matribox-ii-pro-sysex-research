# Fase 53 — DRIVE / Breaker OD e Gerden OD

## Breaker OD

No firmware e aplicativo atuais, Breaker OD apresenta GAIN, TONE e VOLUME,
apesar de o manual em inglês listar uma configuração diferente. A interface
real é a fonte prioritária nesta fase.

O efeito recebe como inferência controlada o layout consecutivo já validado na
família DRIVE:

| Seletor inferido | Parâmetro | Domínio | Padrão informado |
|---:|---|---:|---:|
| 0 | GAIN | 0–100 | 60 |
| 1 | TONE | 0–100 | 50 |
| 2 | VOLUME | 0–100 | 50 |

Breaker OD foi inicialmente preparado como `partially_cataloged`.

## Gerden OD

A captura combinada confirmou dump salvo, eventos ao vivo e limites:

| Seletor | Parâmetro | Dump salvo | Evento seguinte | Limites | Padrão informado |
|---:|---|---:|---:|---:|---:|
| 0 | GAIN | 21 | 22 | 0–100 | 40 |
| 1 | TONE | 43 | 44 | 0–100 | 30 |
| 2 | VOLUME | 65 | 66 | 0–100 | 50 |
| 3 | VOICE | 87 | 88 | 0–100 | 60 |

VOICE usa a mesma codificação numérica direta dos demais controles. Gerden OD
entra como `physically_validated` pelas capturas.

## Validação final no monitor

Breaker OD foi confirmado nas posições 4 (`17 / 15 / 26`) e 10
(`81 / 69 / 78`). Gerden OD foi confirmado nas posições 5
(`0 / 7 / 25 / 33`) e 11 (`83 / 82 / 100 / 87`). Antes disso, os dois também
foram testados isoladamente nas posições 1 e 2.

As múltiplas instâncias funcionaram numa cadeia cheia, com outros efeitos,
hidratação, alterações ao vivo e estado desligado corretos. Breaker OD passa a
`physically_validated`, e a integração visual de Gerden OD fica aprovada.

Identidades:

```text
Breaker OD: class_id 03 / model_id 0E / secondary_selector 03
Gerden OD:  class_id 03 / model_id 10 / secondary_selector 03
```

O catálogo passa à versão 34, com 37 efeitos parametrizados, 141 parâmetros e
230 efeitos pendentes.
