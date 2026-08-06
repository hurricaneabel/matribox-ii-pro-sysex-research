# Estado estrutural da cadeia de efeitos

## Modelo confirmado

A Matribox mantém duas estruturas relacionadas:

1. slots internos, que preservam classe, modelo, parâmetros e bypass;
2. uma lista que define a ordem visual e de processamento.

Mover um efeito altera a lista de referências. O conteúdo do slot interno não
é copiado nem trocado.

## Resposta estrutural

A resposta recebida depois de uma alteração possui tamanho variável:

```text
comprimento total = 14 + (byte[9] × 2)
```

A variação não é causada por índices móveis. A mensagem contém um contêiner
LZO1X codificado em pares de nibbles:

```text
SysEx
  → pares de nibbles
  → contêiner 01 00 00 10
  → fluxo LZO1X
  → payload estrutural de 89 bytes
```

O contêiner codificado começa no índice absoluto 13 e termina antes do `F7`.
Após juntar os pares de nibbles, os quatro bytes seguintes à assinatura
informam o tamanho comprimido em `uint32 little-endian`.

## Layout descomprimido

O payload de 89 bytes foi validado em 34 capturas físicas das Fases 14 e 15:

```text
0–3     cabeçalho interno 00 00 04 01
4–15    ordem visual dos 12 slots
16–27   classe por slot interno
28–75   12 registros de quatro bytes
76–87   estado ligado/desligado por slot interno
88      marcador do slot associado à resposta
```

Cada registro de efeito contém:

```text
modelo | auxiliar 1 | auxiliar 2 | seletor secundário
```

Slots vazios usam `0xFF` na ordem e na tabela de classes. Os identificadores
internos começam em zero; a interface humana apresenta os slots de 1 a 12.

## API estável

`tools.commands.chain_order.parse_chain_order_response()` preserva a API de
ordem e bypass e acrescenta os registros estruturais:

```python
state.human_slots
state.visual_enabled_states
state.record_for_internal_slot(4)
state.record_at_visual_position(1)
state.class_ids_by_internal_slot
state.model_ids_by_internal_slot
state.secondary_selectors_by_internal_slot
```

O decodificador LZO1X está em:

```text
tools/commands/structural_effect_state.py
```

O caminho experimental da Fase 16 continua disponível como fachada de
compatibilidade:

```text
tools/analysis/structural_effect_state.py
```

## Evidência com cinco efeitos

Preset original:

```text
slot 1: DYN / GATE 3       → classe 00, modelo 21, seletor 00
slot 2: AMP / TWD DELUXE   → classe 04, modelo 01, seletor 07
slot 3: DRV / SKREAMER     → classe 03, modelo 00, seletor 03
slot 4: MOD / E-CHORUS     → classe 08, modelo 01, seletor 04
slot 5: DLY / WARM         → classe 09, modelo 01, seletor 0B
```

A Fase 15 também confirmou que `AMP / VOKS BASS` e `AMP / A BASSFT` usam o
mesmo modelo `0x75` e são diferenciados pelos seletores `0x07` e `0x08`.
