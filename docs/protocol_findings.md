## Controle de efeitos pela posição na cadeia

Foi confirmado um comando SysEx capaz de ligar e desligar um efeito de acordo
com sua posição na cadeia.

O comando não depende do tipo de efeito carregado.

O mesmo pacote funcionou com diferentes categorias, incluindo:

- DYN;
- DRV;
- AMP;
- CAB.

Isso indica que o comando controla a posição do efeito, e não um modelo ou
categoria específica.

### Posição do efeito

A posição é armazenada nos índices 39 e 40 da mensagem completa, contando
o byte `F0` como índice zero.

O protocolo utiliza numeração começando em zero:

| Posição na interface | Valor interno | Bytes enviados |
|---:|---:|---:|
| 1 | 0 | `00 00` |
| 2 | 1 | `00 01` |
| 3 | 2 | `00 02` |

A conversão utilizada é:

```python
protocol_position = effect_position - 1

slot_high = (protocol_position >> 4) & 0x0F
slot_low = protocol_position & 0x0F
```

### Estado ligado ou desligado

O estado é armazenado nos índices 47 e 48.

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

### Checksum confirmado

O checksum permanece no índice 7.

Resultados confirmados:

| Posição | Estado | Checksum |
|---:|---|---:|
| 1 | desligado | `1B` |
| 1 | ligado | `1C` |
| 2 | desligado | `1C` |
| 2 | ligado | `1D` |
| 3 | desligado | `1D` |
| 3 | ligado | `1E` |

O checksum foi calculado usando o tamanho informado no índice 9:

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

### Testes realizados

O comando foi confirmado nas posições:

- efeito 1;
- efeito 2;
- efeito 3.

Também foi confirmado que ele funciona independentemente do tipo de efeito
presente na posição.

O arquivo utilizado para gerar os comandos é:

```text
set_effect_slot.py
```

Os testes automáticos estão em:

```text
tests/test_effect_slot_protocol.py
```

Até este momento, somente as posições 1, 2 e 3 foram liberadas no código,
pois são as posições confirmadas por testes reais.