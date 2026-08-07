# Fase 42 — WAH / VOKS WAH

## Objetivo

Iniciar a pesquisa da classe WAH cadastrando RANGE, Q, VOLUME e POSITION do
`VOKS WAH`, com hidratação pelo preset salvo e acompanhamento ao vivo.

## Identidade estrutural

```text
class_id           = 0x02
model_id           = 0x01
secondary_selector = 0x05
```

## Mapa confirmado

| Seletor | Parâmetro | Faixa | Padrão salvo |
|---:|---|---:|---:|
| 0 | RANGE | 0–100 | 50 |
| 1 | Q | 0–100 | 50 |
| 2 | VOLUME | 0–100 | 50 |
| 3 | POSITION | 0–100 | 50 |

Todos os controles usam inteiros codificados como `float32`. A varredura ao
vivo confirmou 0, 1, 50, 99 e 100 para cada seletor.

## Hidratação salva

Três capturas realizadas após salvar, encerrar e reabrir o editor oficial
produziram dumps completos de 1.211 bytes:

```text
50 / 50 / 50 / 50  padrão implícito
21 / 43 / 65 / 87  conjunto A
22 / 44 / 66 / 88  conjunto B
```

Os seletores 4, 5 e 6 contêm respectivamente `100.0`, `100.0` e `1.0`, mas o
efeito não possui controles correspondentes e não houve mensagens ao vivo para
eles. O catálogo declara somente 0–3, impedindo que resíduos do slot sejam
promovidos a parâmetros.

## Implementação

- `wah.voks_wah` passa a ter quatro parâmetros fisicamente validados;
- `catalog_version` passa a 19;
- o catálogo totaliza 23 efeitos parametrizados e 88 parâmetros;
- 244 efeitos continuam pendentes;
- o exportador reproduz o mesmo catálogo;
- nenhuma escrita SysEx foi adicionada.

## Validação física final

O preset 56C foi validado com os doze slots ocupados. Duas instâncias de VOKS
WAH nas posições visuais 4 e 12 foram hidratadas independentemente:

```text
posição 4:  RANGE 83, Q 67, VOLUME 63, POSITION 100
posição 12: RANGE 2,  Q 24, VOLUME 11, POSITION 3
```

As instâncias coexistiram com múltiplos COMP1 sem colisão. A Fase 42 está
fisicamente aprovada.
