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

## Inicialização independente da sessão

A Matribox aceita comandos de escrita imediatamente, mas o envio de respostas
SysEx precisa ser habilitado por uma sequência de inicialização.

Mensagem observada no início da comunicação do editor oficial:

```text
F0 21 25 7E 47 50 2D 32 11 12 00 00 00 F7

## Controle de estado de efeitos

O comando de estado ligado/desligado utiliza uma mensagem SysEx de 62 bytes.

Campos confirmados:

```text
índice 7: checksum
índice 9: 0x18
índices 39–40: slot interno, começando em zero
índices 47–48: estado
```

Codificação do estado:

```text
00 00 = desligado
00 01 = ligado
```

Exemplo para o slot interno 1:

```text
slot 1 = 00 00
```

A Matribox responde ao comando com uma mensagem de 62 bytes contendo os mesmos campos de slot e estado.

Os slots internos de 1 até 12 já foram confirmados para o comando de estado.

## Troca de modelo de efeito

A troca de modelo utiliza uma mensagem SysEx de 58 bytes.

Campos confirmados:

```text
índice 7: checksum
índice 9: 0x16
índices 39–40: slot interno
índices 43–44: identificador do modelo em dois nibbles
```

O checksum é recalculado depois de alterar o slot ou o modelo.

Nesta etapa, a troca de modelo foi validada diretamente no slot interno 1.

## Modelos confirmados da classe FREQ

Os seguintes modelos foram identificados por captura USB e posteriormente testados diretamente pelo programa Python:

```text
Filter       = 0x19
Octaver      = 0x21
Dual Melody  = 0x23
Pitch        = 0x24
Harmony D    = 0x4E
Pitch S      = 0x55
Ring Mod     = 0x2F
Tape Mod     = 0x33
```

Codificação em nibbles:

```text
Filter       = 01 09
Octaver      = 02 01
Dual Melody  = 02 03
Pitch        = 02 04
Harmony D    = 04 0E
Pitch S      = 05 05
Ring Mod     = 02 0F
Tape Mod     = 03 03
```

Os oito modelos foram trocados com sucesso pelo comando:

```text
python -m tools.commands.set_effect_model
```

A classe FREQ está completamente mapeada em relação aos modelos exibidos pelo editor oficial.

Ainda não está confirmado qual campo identifica a classe do efeito.

Também ainda não foi validado se o mesmo modelo de pacote pode trocar modelos em todos os slots internos.