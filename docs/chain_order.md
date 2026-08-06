# Ordem visual da cadeia de efeitos

## Modelo confirmado

A Matribox mantém duas estruturas distintas:

1. slots internos, que preservam a identidade do efeito e seus parâmetros;
2. uma lista separada que define a ordem visual e de processamento.

Mover um efeito altera a lista de referências. O conteúdo dos slots internos
não é copiado nem trocado.

## Resposta estrutural

A resposta recebida depois de uma movimentação possui tamanho variável.

```text
comprimento total = 14 + (byte[9] × 2)
```

Capturas físicas confirmadas:

```text
2 efeitos: byte[9] = 0x3B, total = 132 bytes
5 efeitos: byte[9] = 0x4F, total = 172 bytes
5 efeitos: byte[9] = 0x4D, total = 168 bytes
```

O tamanho pode variar mesmo quando a quantidade de efeitos é a mesma. Portanto,
o parser não deve depender de um tamanho fixo.

## Lista da ordem

A lista começa no índice absoluto 39. Cada entrada ocupa dois nibbles:

```text
00 00 = slot interno 1
00 01 = slot interno 2
...
00 0B = slot interno 12
0F 0F = fim da lista ou posição vazia
```

Os identificadores do protocolo começam em zero. A interface humana apresenta
os slots começando em um.

Exemplo:

```text
00 01 00 00 0F 0F
```

significa:

```text
posição visual 1 → slot interno 2
posição visual 2 → slot interno 1
fim
```

## Evidência com cinco efeitos

Ordem inicial:

```text
1. GATE 3
2. TWD DELUXE
3. SKREAMER
4. E-CHORUS
5. WARM
```

Os movimentos físicos produziram:

```text
1 → 5: (2, 3, 4, 5, 1)
3 → 1: (4, 2, 3, 5, 1)
5 → 2: (4, 1, 2, 3, 5)
2 → 1: (1, 4, 2, 3, 5)
2 → 4: (1, 2, 3, 4, 5)
```

A última resposta restaurou exatamente a ordem inicial.

## Módulos

```text
tools/commands/chain_order.py
tools/commands/move_and_read_chain.py
tools/experiments/validate_chain_order_five_effects.py
tests/test_chain_order.py
```
