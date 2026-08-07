# Fase 43 — WAH / CRY WAH

## Resultado

O `CRY WAH` foi identificado como `class_id 0x02`, `model_id 0x08` e
`secondary_selector 0x05`. O mapa confirmado é:

| Seletor | Parâmetro | Faixa | Padrão salvo |
|---:|---|---:|---:|
| 0 | RANGE | 0–100 | 50 |
| 1 | Q | 0–100 | 50 |
| 2 | VOLUME | 0–100 | 50 |
| 3 | POSITION | 0–100 | 50 |

Três dumps completos após reabrir o editor confirmaram os conjuntos
`50 / 50 / 50 / 50`, `21 / 43 / 65 / 87` e `22 / 44 / 66 / 88`. A varredura
ao vivo confirmou 0, 1, 50, 99 e 100 em todos os parâmetros.

Os seletores 4–6 contêm `100.0 / 100.0 / 1.0`, sem controles ou respostas ao
vivo correspondentes. O catálogo limitado a 0–3 impede a hidratação desses
resíduos.

## Implementação

- `catalog_version` 20;
- 24 efeitos parametrizados;
- 92 parâmetros catalogados;
- 243 efeitos pendentes;
- integração somente leitura;
- validação física final aprovada no monitor.

## Validação física final

O preset 56C foi validado com os doze slots ocupados. Um VOKS WAH na posição
visual 4 preservou `27 / 12 / 34 / 6`, enquanto o CRY WAH na posição 12 foi
hidratado como:

```text
RANGE 72, Q 81, VOLUME 85, POSITION 89
```

Os dois modelos WAH coexistiram com múltiplos COMP1 sem colisão. Isso confirma
que efeitos com o mesmo formato de parâmetros continuam resolvidos pela
identidade estrutural da instância. A Fase 43 está fisicamente aprovada.
