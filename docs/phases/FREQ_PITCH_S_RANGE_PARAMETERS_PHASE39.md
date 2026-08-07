# Fase 39 — FREQ / Pitch S, RANGE enum e proteção contra campo residual

## Objetivo

Cadastrar RANGE, POSITION, MIX e LEVEL do `FREQ / Pitch S`, validando o enum
de oitavas, os defaults persistidos e a exclusão de um valor residual presente
fora dos seletores pertencentes ao efeito.

## Identidade e parâmetros

As capturas confirmaram `class_id = 0x01`, `model_id = 0x55` e
`secondary_selector = 0x01` no slot interno 0.

| Seletor | Parâmetro | Domínio | Default |
|---:|---|---|---|
| 0 | RANGE | enum 0–5 | +1 OCT |
| 1 | POSITION | 0–100 | 0 |
| 2 | MIX | 0–100 | 100 |
| 3 | LEVEL | 0–100 | 100 |

RANGE usa:

```text
0 -2 OCT | 1 -1 OCT | 2 +1 OCT | 3 +2 OCT | 4 +/-1 OCT | 5 +/-2 OCT
```

## Evidência física

Três capturas de reabertura produziram dumps completos de 1.211 bytes:

```text
default:   2 / 0  / 100 / 100
conjunto A: 1 / 21 / 43  / 65
conjunto B: 2 / 22 / 44  / 66
```

A varredura ao vivo confirmou os seletores 0–3 e os valores não zero dos
domínios. Os zeros já estavam ativos no início e, por isso, não geraram uma
nova resposta recebida; o dump default confirma POSITION 0 e o procedimento
controlado estabelece os pontos iniciais dos demais controles.

## Campo residual no seletor 4

Os três dumps preservaram `10.0` no seletor 4, embora o Pitch S apresente apenas
quatro parâmetros e nenhuma resposta ao vivo use esse seletor. O valor é estado
residual do slot reutilizado e não pertence ao efeito. O catálogo declara
somente 0–3; assim, o hidratador genérico ignora corretamente o campo residual.

## Implementação e segurança

O catálogo passa para a versão 16. RANGE usa o mecanismo genérico de enum e os
demais parâmetros usam inteiros já suportados. Não foi criado parser, codec ou
comando SysEx de escrita específico.

Validação offline:

```text
Ran 449 tests
OK
compileall: aprovado
git diff --check: aprovado
```

## Validação física final

A integração foi aprovada no monitor `--live` usando o preset 56C com os doze
slots ocupados. Duas instâncias de Pitch S em posições afastadas da cadeia
mantiveram RANGE, POSITION, MIX e LEVEL independentes. Foram confirmados
`-1 OCT` e `+/-2 OCT`, valores numéricos distintos, hidratação e alterações em
tempo real, sem colisão com múltiplas instâncias de COMP1.

A Fase 39 está fisicamente aprovada.
