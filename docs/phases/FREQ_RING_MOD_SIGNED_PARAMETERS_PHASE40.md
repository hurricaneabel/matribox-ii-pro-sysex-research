# Fase 40 — FREQ / Ring Mod e FINE assinado

## Objetivo

Cadastrar MIX, FREQ., FINE e TONE do `FREQ / Ring Mod`, confirmando o intervalo
assinado de FINE, os defaults persistidos e a exclusão de um campo residual
fora dos parâmetros do efeito.

## Identidade e layout

As capturas confirmaram `class_id = 0x01`, `model_id = 0x2F` e
`secondary_selector = 0x01` no slot interno 0.

| Seletor | Parâmetro | Domínio | Default |
|---:|---|---:|---:|
| 0 | MIX | 0–100 | 50 |
| 1 | FREQ. | 0–100 | 50 |
| 2 | FINE | -50–50 | 0 |
| 3 | TONE | 0–100 | 50 |

FINE usa `float32` negativo nativo, sem offset ou enum intermediário.

## Evidência física

Três dumps de reabertura produziram payloads completos de 1.211 bytes:

```text
default:    50 / 50 /   0 / 50
conjunto A: 21 / 43 / -17 / 65
conjunto B: 22 / 44 / -16 / 66
```

A varredura ao vivo confirmou os quatro seletores. Em FREQ., o valor 9 foi
acionado acidentalmente entre 50 e 99; como a ordem foi informada, ele constitui
um ponto adicional válido e não cria ambiguidade. FINE confirmou `-49`, `-1`,
`0`, `1`, `49` e `50`; o limite `-50` estava configurado no início da sequência.

## Campo residual

Os dumps mantiveram `10.0` no seletor 4, mas não existe controle correspondente
nem resposta ao vivo nesse seletor. Assim como no Pitch S, trata-se de estado
residual do slot. O catálogo declara somente 0–3 e o hidratador ignora o campo.

## Implementação e segurança

O catálogo passa para a versão 17. Todos os valores usam o codec genérico já
existente. Não foi criado parser específico nem comando SysEx de escrita.

Validação offline:

```text
Ran 451 tests
OK
compileall: aprovado
git diff --check: aprovado
```

## Validação física final

A integração foi aprovada no monitor `--live` usando o preset 56C com os doze
slots ocupados. Duas instâncias de Ring Mod nas posições visuais 4 e 12
mantiveram MIX, FREQ., FINE e TONE independentes. Foram confirmados MIX 0,
FINE negativo (`-33`) e positivo (`20`), hidratação e alterações em tempo real,
sem colisão com múltiplas instâncias de COMP1.

A Fase 40 está fisicamente aprovada.
