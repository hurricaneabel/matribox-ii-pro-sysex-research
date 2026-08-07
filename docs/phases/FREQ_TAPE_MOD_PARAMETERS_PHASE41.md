# Fase 41 — FREQ / Tape Mod

## Objetivo

Cadastrar SATURATION, MIX, VOLUME e HIGH CUT do último efeito da classe FREQ,
preservando a hidratação genérica pelo dump salvo e as atualizações ao vivo.

## Identidade estrutural

```text
class_id          = 0x01
model_id          = 0x33
secondary_selector = 0x01
```

## Mapa confirmado

| Seletor | Parâmetro | Faixa | Padrão salvo |
|---:|---|---:|---:|
| 0 | SATURATION | 0–100 | 50 |
| 1 | MIX | 0–100 | 50 |
| 2 | VOLUME | 0–100 | 50 |
| 3 | HIGH CUT | 0–100 | 50 |

Todos os controles usam inteiros codificados como `float32`. Capturas ao vivo
confirmaram 0, 1, 50, 99 e 100 para cada seletor, o conjunto combinado
`61 / 62 / 63 / 64` e repetição no segundo slot.

## Hidratação salva

Três capturas realizadas após salvar, encerrar e reabrir o editor oficial
produziram dumps completos de 1.211 bytes:

```text
50 / 50 / 50 / 50  padrão implícito
21 / 43 / 65 / 87  conjunto A
22 / 44 / 66 / 88  conjunto B
```

O seletor 4 contém `10.0` residual, sem controle correspondente e sem resposta
ao vivo. O catálogo declara somente 0–3, portanto a hidratação o ignora.

## Implementação

- `freq.tape_mod` passa a ter quatro parâmetros fisicamente validados;
- `catalog_version` passa a 18;
- o catálogo totaliza 22 efeitos parametrizados e 84 parâmetros;
- 245 efeitos continuam pendentes;
- o exportador reproduz o mesmo catálogo;
- nenhum comando de escrita SysEx foi adicionado.

## Validação física final

O preset 56C foi validado com os doze slots ocupados. Duas instâncias de Tape
Mod nas posições visuais 4 e 12 foram hidratadas independentemente:

```text
posição 4:  SATURATION 30, MIX 31, VOLUME 21, HIGH CUT 30
posição 12: SATURATION 81, MIX 80, VOLUME 70, HIGH CUT 71
```

As duas instâncias coexistiram com múltiplos COMP1 sem colisão. A Fase 41 está
fisicamente aprovada e encerra a pesquisa de parâmetros da classe FREQ.
