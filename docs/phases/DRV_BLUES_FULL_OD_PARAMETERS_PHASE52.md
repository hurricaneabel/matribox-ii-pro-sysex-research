# Fase 52 — DRIVE / Blues OD e Full OD

Full OD foi analisado em duas capturas combinadas, com dump salvo e alterações
ao vivo. A assinatura confirmada é:

| Seletor | Parâmetro | Domínio | Valor salvo observado |
|---:|---|---|---:|
| 0 | GAIN | 0–100 | 21 |
| 1 | TONE | 0–100 | 43 |
| 2 | VOLUME | 0–100 | 65 |
| 3 | MODE | LP=0, HP=1 | HP |

Os eventos ao vivo confirmaram `22 / 44 / 66`, os extremos 0 e 100 e a
alternância LP/HP. Os padrões informados pela interface oficial são
`40 / 60 / 50 / HP`.

Blues OD declara os mesmos três controles numéricos, sem MODE. Ele reutiliza
como inferência controlada os seletores consecutivos 0–2 já validados na família
DRIVE. Seus padrões informados são `40 / 60 / 50`. Até o teste físico no monitor,
foi inicialmente preparado como `partially_cataloged`.

## Validação final no monitor

Blues OD foi confirmado nas posições 4 (`16 / 33 / 31`) e 10
(`83 / 88 / 80`). Full OD foi confirmado nas posições 5
(`21 / 25 / 25 / LP`) e 11 (`72 / 97 / 86 / HP`). As quatro instâncias
coexistiram numa cadeia cheia e desligada, com outros efeitos.

Blues OD e Full OD passam a `physically_validated`, com integração do monitor
aprovada.

Identidades:

```text
Blues OD: class_id 03 / model_id 09 / secondary_selector 03
Full OD:  class_id 03 / model_id 0A / secondary_selector 03
```

O catálogo passa à versão 32, com 35 efeitos parametrizados, 134 parâmetros e
232 efeitos pendentes.
