## Controle de efeitos pelos slots internos

Foi confirmado um comando SysEx capaz de ligar e desligar um efeito de acordo
com seu slot interno dentro do preset.

O comando não depende:

- do tipo de efeito carregado;
- da categoria do efeito;
- da posição visual atual na cadeia;
- do banco;
- do número do preset.

O mesmo comando funcionou com diferentes categorias, incluindo:

- DYN;
- DRV;
- WAH;
- AMP;
- CAB;
- MOD;
- FREQ;
- RVB.

## Diferença entre slot interno e posição visual

A Matribox mantém duas informações diferentes para cada efeito:

```text
Slot interno:
endereço persistente utilizado pelo protocolo SysEx

Posição visual:
local onde o efeito aparece atualmente na cadeia
```

Mover um efeito para outra posição da cadeia não altera seu slot interno.

Foi realizado o seguinte teste:

1. um WAH ocupava originalmente o slot interno 1;
2. o WAH foi movido para o final da cadeia;
3. o preset foi salvo;
4. outro banco e outro preset foram selecionados;
5. o preset original foi aberto novamente;
6. o comando do slot interno 1 continuou controlando o WAH;
7. o WAH foi apagado;
8. outro efeito foi adicionado;
9. o novo efeito reutilizou o slot interno 1.

Isso confirma que o slot interno funciona como um endereço persistente dentro
do preset.

## Numeração dos slots internos

Nosso programa apresenta os slots começando em 1.

O protocolo utiliza valores começando em zero:

| Slot apresentado | Valor interno | Bytes enviados |
|---:|---:|---:|
| 1 | 0 | `00 00` |
| 2 | 1 | `00 01` |
| 3 | 2 | `00 02` |
| 4 | 3 | `00 03` |
| 5 | 4 | `00 04` |
| 6 | 5 | `00 05` |
| 7 | 6 | `00 06` |
| 8 | 7 | `00 07` |
| 9 | 8 | `00 08` |
| 10 | 9 | `00 09` |
| 11 | 10 | `00 0A` |
| 12 | 11 | `00 0B` |

A conversão utilizada é:

```python
protocol_slot = effect_position - 1

slot_high = (protocol_slot >> 4) & 0x0F
slot_low = protocol_slot & 0x0F
```

Os bytes do slot interno são armazenados nos índices:

```text
39 = nibble alto
40 = nibble baixo
```

## Estado ligado ou desligado

O estado do efeito é armazenado nos índices 47 e 48.

Desligado:

```text
00 00
```

Ligado:

```text
00 01
```

A conversão utilizada é:

```python
state_value = 1 if enabled else 0

state_high = (state_value >> 4) & 0x0F
state_low = state_value & 0x0F
```

## Checksum

O checksum permanece no índice 7.

Resultados confirmados:

| Slot | Estado | Checksum |
|---:|---|---:|
| 1 | desligado | `1B` |
| 1 | ligado | `1C` |
| 2 | desligado | `1C` |
| 2 | ligado | `1D` |
| 3 | desligado | `1D` |
| 3 | ligado | `1E` |
| 4 | desligado | `1E` |
| 4 | ligado | `1F` |
| 12 | ligado | `27` |

O checksum é calculado utilizando o tamanho informado no índice 9:

```python
payload_start = 10
payload_end = payload_start + (message[9] * 2)

checksum = sum(message[payload_start:payload_end]) & 0x7F
```

Neste tipo de pacote:

```text
Índice 9 = 18 hexadecimal
```

`0x18` representa 24 bytes decodificados.

Como cada byte é transmitido em dois nibbles:

```text
24 × 2 = 48 bytes codificados
```

## Testes realizados

Foi criado um preset de teste com 12 efeitos adicionados em sequência.

O arquivo:

```text
set_effect_slot.py
```

foi testado nos 12 slots internos.

Todos os slots foram ligados e desligados corretamente:

```text
1 até 12
```

Também foi confirmado que o mesmo slot interno pode controlar diferentes
categorias de efeitos em diferentes presets.

Os testes automáticos estão em:

```text
tests/test_effect_slot_protocol.py
```

Atualmente existem:

```text
15 testes automáticos
```

Todos estão passando.

## Interpretação atual

Os índices 39 e 40 não identificam a posição visual do efeito.

Eles identificam o slot interno persistente utilizado pela estrutura do
preset.

A posição visual da cadeia deve estar armazenada em outro campo ou em outro
tipo de mensagem SysEx, ainda não identificado.