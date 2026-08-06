# Descobertas confirmadas do protocolo SysEx

Este documento mantém o registro técnico acumulado da pesquisa. As seções
históricas são preservadas mesmo quando descobertas posteriores ampliam ou
corrigem interpretações anteriores.

## Resumo consolidado atual

Classes completamente catalogadas:

| Classe | ID | Modelos | Observações de seletor |
|---|---:|---:|---|
| DYN | `0x00` | 14 | `0x00` e `0x01` |
| FREQ | `0x01` | 8 | `0x01` |
| WAH | `0x02` | 6 | `0x05` e `0x01` |
| DRV | `0x03` | 24 | `0x03` |
| AMP | `0x04` | 63 | `0x07` e `0x08` |
| CAB | `0x05` | 61 | `0x0A` |
| IR | `0x06` | 20 | `0x0A` |
| EQ | `0x07` | 5 | `0x01` |
| MOD | `0x08` | 23 | `0x04`; duas exceções em `0x01` |
| DLY | `0x09` | 17 | `0x0B` |
| RVB | `0x0A` | 12 | `0x0C` |
| CLONE | `0x0B` | 10 posições | `0x0F` |
| FX LOOP | `0x0C` | 1 | `0x06` |
| FX SEND | `0x0D` | 1 | `0x06` |
| FX RETURN | `0x0E` | 1 | `0x06` |
| VOL | `0x0F` | 1 | `0x06` |

Total confirmado no catálogo:

```text
16 classes
267 posições/modelos
```

Comandos estruturais principais:

| Comando | Tamanho | Uso |
|---:|---:|---|
| `0x14` | 54 bytes | volume do preset |
| `0x16` | 58 bytes | troca de modelo na mesma classe |
| `0x17` | 60 bytes | adição, substituição e remoção |
| `0x18` | 62 bytes | estado ligado/desligado do slot |

Estado da suíte após a integração dos blocos especiais:

```text
158 testes automáticos
158 aprovados
```

A captura dos comandos enviados pelo editor oficial é realizada com
Wireshark/USBPcap. O logger MIDI em Python continua útil para mensagens
recebidas, mas não substitui a interceptação USB do tráfego de saída.

---

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
- RVB;
- CLONE.

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

Na etapa inicial desta investigação existiam:

```text
15 testes automáticos
```

A suíte foi ampliada à medida que novas classes e operações foram
confirmadas. Após a integração da classe DLY existem:

```text
128 testes automáticos
128 aprovados
```

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

## Adição e remoção de efeitos da cadeia visual

Foi confirmado que configurar o modelo de um slot não é suficiente para fazer um efeito ausente aparecer visualmente na cadeia.

A criação e a remoção visual utilizam um comando SysEx separado, identificado pelo tipo `0x17`.

Características confirmadas:

```text
tamanho total: 60 bytes
índice 7: checksum
índice 9: 0x17
índices 39–40: slot de origem
índices 41–42: slot de destino
índices 43–44: estado inicial
índices 45–46: identificador do modelo
```

O valor que representa uma posição vazia é:

```text
0F 0F = vazio
```

### Remoção de um efeito

Para remover um slot existente da cadeia:

```text
índices 39–40 = slot existente
índices 41–42 = 0F 0F
```

Exemplo confirmado para remover o slot interno 11:

```text
origem  = 00 0A
destino = 0F 0F
checksum = 0x4E
```

Exemplo confirmado para remover o slot interno 12:

```text
origem  = 00 0B
destino = 0F 0F
checksum = 0x4F
```

### Adição de um efeito

Para adicionar um efeito a um slot ausente:

```text
índices 39–40 = 0F 0F
índices 41–42 = slot que será criado
índices 43–44 = 00 01
índices 45–46 = modelo escolhido
```

O efeito criado pelo editor oficial nasce ligado.

Exemplo confirmado para adicionar Filter no slot interno 11:

```text
origem  = 0F 0F
destino = 00 0A
estado  = 00 01
modelo  = 01 09
checksum = 0x5A
```

Exemplo confirmado para adicionar Octaver no slot interno 11:

```text
origem  = 0F 0F
destino = 00 0A
estado  = 00 01
modelo  = 02 01
checksum = 0x53
```

Exemplo confirmado para adicionar Filter no slot interno 12:

```text
origem  = 0F 0F
destino = 00 0B
estado  = 00 01
modelo  = 01 09
checksum = 0x5B
```

Os slots apresentados ao usuário usam a numeração de 1 até 12.

No protocolo, os mesmos slots usam valores de 0 até 11:

```text
slot 1  = 00 00
slot 2  = 00 01
slot 11 = 00 0A
slot 12 = 00 0B
```

Foram implementados os seguintes comandos:

```text
python -m tools.commands.add_effect
python -m tools.commands.remove_effect
```

O comando `add_effect` permite criar qualquer um dos oito modelos FREQ já mapeados em um slot ausente.

O comando `remove_effect` retira um slot existente da cadeia visual.

Os testes automatizados cobrem a codificação dos slots de 1 até 12. Os testes físicos confirmaram a criação e a remoção nos slots 11 e 12, além de testes adicionais realizados diretamente na pedaleira.

Esses comandos alteram a cadeia carregada, mas não executam automaticamente o salvamento permanente do preset.

## Classes de efeitos e substituição entre classes

Foi confirmado que classe e modelo são identificadores separados no protocolo.

Classes atualmente confirmadas:

```text
FREQ = 0x01
DRV  = 0x03
```

A ordem em que as classes foram pesquisadas não representa necessariamente a ordem visual apresentada pelo editor oficial.

A ordem de exibição será tratada separadamente no catálogo do aplicativo final.

## Troca de modelo dentro da mesma classe

A troca de modelo dentro de uma classe utiliza o comando SysEx `0x16`.

Estrutura confirmada:

```text
tamanho total: 58 bytes
índice 7: checksum
índice 9: 0x16
índices 39–40: slot interno
índices 41–42: identificador da classe
índices 43–44: identificador do modelo
índice 50: segundo campo dependente da classe
```

Exemplo da classe DRV:

```text
classe DRV = 00 03
índice 50  = 03
```

Todos os 24 modelos DRV foram testados fisicamente no slot interno 11.

## Substituição entre classes

A substituição completa de um efeito por outro de classe diferente utiliza o comando SysEx `0x17`.

Quando o efeito permanece no mesmo slot:

```text
slot de origem = slot de destino
```

Estrutura confirmada:

```text
tamanho total: 60 bytes
índice 7: checksum
índice 9: 0x17
índices 39–40: slot de origem
índices 41–42: slot de destino
índices 43–44: identificador da nova classe
índices 45–46: identificador do novo modelo
índice 52: segundo campo dependente da classe
```

Exemplo confirmado:

```text
slot interno 11
FREQ / Filter → DRV / Skreamer

origem  = 00 0A
destino = 00 0A
classe  = 00 03
modelo  = 00 00
índice 52 = 03
checksum = 0x40
```

Retorno confirmado:

```text
slot interno 11
DRV / Skreamer → FREQ / Filter

origem  = 00 0A
destino = 00 0A
classe  = 00 01
modelo  = 01 09
índice 52 = 01
checksum = 0x46
```

## Modelos confirmados da classe DRV

```text
Skreamer     = 0x00
Skreamer9    = 0x01
Butter OD    = 0x02
Warm OD      = 0x04
Super OD     = 0x06
Blues OD     = 0x09
Full OD      = 0x0A
Breaker OD   = 0x0E
Gerden OD    = 0x10
Timmy OD     = 0x1E
Master OD    = 0x0F
Solar Fuzz   = 0x26
Fuzz Cream   = 0x22
Red Fuzz     = 0x24
JP Dist      = 0x2A
Dark Mouse   = 0x2B
Plexi Dist   = 0x2D
Master Dist  = 0x2E
Dist Plus    = 0x29
Shark        = 0x30
Strive       = 0x32
Sardar Dist  = 0x52
Bass OD      = 0x3F
Bass Dist    = 0x40
```

Os IDs não seguem a ordem visual apresentada no menu do editor.

Foram confirmados fisicamente:

```text
troca individual dos 24 modelos DRV
sequência automática com os 24 modelos
criação de DRV / Skreamer em slot ausente
criação de DRV / Sardar Dist em slot ausente
substituição FREQ → DRV
substituição DRV → FREQ
```

Comandos implementados:

```text
python -m tools.commands.add_effect
python -m tools.commands.set_effect
python -m tools.commands.remove_effect
```

O comando `set_effect` seleciona automaticamente:

```text
mesma classe     = comando 0x16
classe diferente = comando 0x17
```

## Modelos confirmados da classe EQ

A classe EQ foi confirmada com o identificador:

```text
EQ = 0x07
```

Os cinco modelos exibidos pelo editor oficial foram capturados e testados
fisicamente no slot interno 11:

```text
GUITAR EQ 1 = 0x35
GUITAR EQ 2 = 0x36
BASS EQ 1   = 0x39
BASS EQ 2   = 0x3A
CALIF EQ    = 0x3C
```

Todos usam:

```text
seletor secundário = 0x01
flag estrutural     = 0x00
```

Checksums confirmados para troca de modelo no slot interno 11:

```text
GUITAR EQ 1 = 0x3F
GUITAR EQ 2 = 0x40
BASS EQ 1   = 0x43
BASS EQ 2   = 0x44
CALIF EQ    = 0x46
```

A criação direta no slot interno 12 também foi validada:

```text
GUITAR EQ 1 = checksum 0x5F
CALIF EQ    = checksum 0x66
```

A substituição direta por `GUITAR EQ 1` no slot interno 11 utiliza checksum
`0x4A`. A remoção do slot 12 continua utilizando checksum `0x4F`.

Os validadores físicos estão em:

```text
tools/experiments/validate_eq_models_slot_11.py
tools/experiments/validate_add_eq_slot_12.py
```

O gerenciador flexível permite adicionar, substituir e excluir efeitos em
qualquer slot interno entre 1 e 12:

```text
python -m tools.experiments.manage_effect_chain
```

## Modelos confirmados da classe MOD

A classe MOD foi confirmada com o identificador:

```text
MOD = 0x08
```

Foram capturados pelo Wireshark e testados fisicamente no slot interno 11 os
23 modelos exibidos pelo editor oficial:

```text
E-CHORUS        = 0x01, seletor 0x04
D-CHORUS        = 0x02, seletor 0x04
B-CHORUS        = 0x08, seletor 0x04
M-CHORUS        = 0x0F, seletor 0x04
FLANGER         = 0x11, seletor 0x04
FLANGER N       = 0x13, seletor 0x04
TREM JET        = 0x14, seletor 0x04
BASS JET        = 0x12, seletor 0x04
VIBRATO         = 0x17, seletor 0x04
BBD ROTO        = 0x15, seletor 0x04
CE-ROTO         = 0x16, seletor 0x04
PHASER          = 0x19, seletor 0x04
BBD PHASER      = 0x1A, seletor 0x04
PHASER ST       = 0x1B, seletor 0x04
PAN PHASER      = 0x1E, seletor 0x04
VIBE            = 0x1F, seletor 0x04
U-VIBE          = 0x20, seletor 0x04
TREMOLO         = 0x21, seletor 0x04
SINE TREM       = 0x26, seletor 0x04
TRIANGULE TREM  = 0x27, seletor 0x04
BIAS TREM       = 0x28, seletor 0x04
DETUNE          = 0x29, seletor 0x01
LOFI BIT        = 0x2E, seletor 0x01
```

Todos usam flag estrutural `0x00`. Os primeiros 21 modelos usam seletor
secundário `0x04`; `DETUNE` e `LOFI BIT` são exceções e usam `0x01`.

Checksums confirmados para troca de modelo com comando `0x16` no slot interno
11, na ordem visual do editor:

```text
3C 3D 43 4A 3D 3F 40 3E 43 41 42 45
46 47 4A 4B 3D 3E 43 44 45 43 48
```

A substituição estrutural do slot interno 11 por `MOD / E-CHORUS`, usando o
comando `0x17`, foi capturada com checksum `0x47`.

O validador físico da classe está em:

```text
tools/experiments/validate_mod_models_slot_11.py
```

O catálogo e o gerenciador flexível reconhecem MOD como a nona classe.

A criação de `MOD / E-CHORUS` no slot interno 12 foi validada fisicamente com:

```text
classe   = 0x08
modelo   = 0x01
seletor  = 0x04
checksum = 0x5C
```

A classe MOD foi integrada à `main` no commit:

```text
2a4059f feat: add validated MOD effect support
```

## Classe DLY completamente catalogada

A classe de delays foi confirmada por captura USB/Wireshark e validação física.

```text
classe DLY = 0x09
flag estrutural = 0x00
seletor secundário = 0x0B
quantidade de modelos = 17
```

Modelos confirmados, na ordem visual do editor oficial:

| # | Modelo | ID | Seletor |
|---:|---|---:|---:|
| 1 | WARM | `0x01` | `0x0B` |
| 2 | PURE | `0x00` | `0x0B` |
| 3 | MAG | `0x02` | `0x0B` |
| 4 | TUBE | `0x0B` | `0x0B` |
| 5 | BBD | `0x1D` | `0x0B` |
| 6 | PING PONG | `0x04` | `0x0B` |
| 7 | SLAPBACK | `0x05` | `0x0B` |
| 8 | SWEEP | `0x06` | `0x0B` |
| 9 | RING | `0x09` | `0x0B` |
| 10 | MULTI TAPE | `0x0C` | `0x0B` |
| 11 | SWEET | `0x0D` | `0x0B` |
| 12 | 999 ECHO | `0x12` | `0x0B` |
| 13 | RACK | `0x14` | `0x0B` |
| 14 | LO-FI | `0x26` | `0x0B` |
| 15 | REVERSE | `0x28` | `0x0B` |
| 16 | EKO D | `0x03` | `0x0B` |
| 17 | ICE DELAY | `0x2C` | `0x0B` |

A captura completa percorreu todos os modelos e terminou retornando para WARM.
O modelo PURE apareceu como `0x00` no primeiro pacote da sequência e foi
posteriormente confirmado fisicamente pelo validador.

Validador físico:

```text
python -m tools.experiments.validate_dly_models_slot_11
```

A opção `A` percorre os 16 modelos seguintes e retorna ao WARM.

### Checksums e validações físicas da classe DLY

Checksums confirmados para comando `0x16` no slot interno 11, na ordem visual
do editor:

```text
WARM       = 0x44
PURE       = 0x43
MAG        = 0x45
TUBE       = 0x4E
BBD        = 0x51
PING PONG  = 0x47
SLAPBACK   = 0x48
SWEEP      = 0x49
RING       = 0x4C
MULTI TAPE = 0x4F
SWEET      = 0x50
999 ECHO   = 0x46
RACK       = 0x48
LO-FI      = 0x4B
REVERSE    = 0x4D
EKO D      = 0x46
ICE DELAY  = 0x51
```

A primeira troca entre classes, de `MOD / E-CHORUS` para `DLY / WARM`, foi
capturada com comando `0x17`:

```text
slot       = 00 0A
classe     = 00 09
modelo     = 00 01
flag       = 00
seletor    = 0B
checksum   = 0x4F
```

A criação direta de `DLY / WARM` no slot interno 12 foi testada pelo
gerenciador flexível:

```text
classe     = 0x09
modelo     = 0x01
seletor    = 0x0B
checksum   = 0x64
```

A sequência automática do validador percorreu fisicamente:

```text
PURE
MAG
TUBE
BBD
PING PONG
SLAPBACK
SWEEP
RING
MULTI TAPE
SWEET
999 ECHO
RACK
LO-FI
REVERSE
EKO D
ICE DELAY
WARM
```

O pacote `modelo 0x00` foi inicialmente tratado como uma possível ação anterior
à rodada. A revisão da ordem correta mostrou que ele correspondia ao `PURE`.
A identificação foi confirmada na pedaleira pelo teste automático.

O catálogo e o gerenciador reconhecem DLY como a décima classe do utilitário.
A integração acrescenta testes para:

- ID e posição da classe;
- quantidade e ordem dos 17 modelos;
- IDs dos modelos;
- seletor `0x0B`;
- checksums do comando `0x16`;
- substituição por `WARM` no slot 11;
- adição de `WARM` e `PURE` no slot 12;
- pesquisa por nome, número e ID.

## Classe RVB completamente catalogada

A classe de reverbs foi confirmada por captura USB/Wireshark e validação
física.

```text
classe RVB = 0x0A
flag estrutural = 0x00
seletor secundário = 0x0C
quantidade de modelos = 12
```

Modelos confirmados, na ordem visual do editor oficial:

| # | Modelo | ID | Seletor | Checksum `0x16` no slot 11 |
|---:|---|---:|---:|---:|
| 1 | STUDIO | `0x0B` | `0x0C` | `0x50` |
| 2 | CLUB | `0x0C` | `0x0C` | `0x51` |
| 3 | ROOM | `0x00` | `0x0C` | `0x45` |
| 4 | HALL | `0x01` | `0x0C` | `0x46` |
| 5 | CHURCH | `0x02` | `0x0C` | `0x47` |
| 6 | PLATE | `0x03` | `0x0C` | `0x48` |
| 7 | SPRING | `0x04` | `0x0C` | `0x49` |
| 8 | SKY | `0x06` | `0x0C` | `0x4B` |
| 9 | SEA | `0x07` | `0x0C` | `0x4C` |
| 10 | MOD REVERB | `0x08` | `0x0C` | `0x4D` |
| 11 | SHIMMER | `0x09` | `0x0C` | `0x4E` |
| 12 | HAZE | `0x15` | `0x0C` | `0x4B` |

O último modelo foi confirmado com o nome `HAZE`.

### Captura entre classes

A troca de `DLY / WARM` para `RVB / STUDIO`, usando o comando `0x17`, foi
capturada com:

```text
slot de origem  = 00 0A
slot de destino = 00 0A
classe          = 00 0A
modelo          = 00 0B
flag            = 00
seletor         = 0C
checksum        = 0x5B
```

A volta para `DLY / WARM` confirmou novamente os campos já catalogados da
classe DLY.

### Validação física

O validador está em:

```text
tools/experiments/validate_rvb_models_slot_11.py
```

A sequência automática percorreu fisicamente:

```text
CLUB
ROOM
HALL
CHURCH
PLATE
SPRING
SKY
SEA
MOD REVERB
SHIMMER
HAZE
STUDIO
```

Todos os modelos funcionaram corretamente e o estado final retornou ao
`STUDIO`.

### Operações estruturais calculadas e cobertas por testes

```text
substituir slot 11 por STUDIO = checksum 0x5B
adicionar STUDIO no slot 12  = checksum 0x70
adicionar ROOM no slot 12    = checksum 0x65
adicionar HAZE no slot 12    = checksum 0x6B
```

O catálogo e o gerenciador flexível reconhecem RVB como a décima primeira
classe do utilitário. A integração acrescenta testes para:

- ID e posição da classe;
- quantidade e ordem dos 12 modelos;
- IDs dos modelos;
- seletor `0x0C`;
- checksums do comando `0x16`;
- substituição por `STUDIO` no slot 11;
- adição de `STUDIO`, `ROOM` e `HAZE` no slot 12;
- pesquisa por nome, número e ID.

Após esta integração, o catálogo possui 11 classes e 253 modelos, com 138
testes automáticos aprovados.

## Classe CLONE: seleção das dez posições catalogada

A seleção da classe CLONE foi confirmada por captura USB/Wireshark e validação
física. Esta seção documenta somente a presença do CLONE na cadeia e a troca
entre suas dez posições. A importação de arquivos NAM permanece fora desta
integração.

```text
classe CLONE = 0x0B
flag estrutural = 0x00
seletor secundário = 0x0F
quantidade de posições = 10
IDs = 0x00 até 0x09
```

Os nomes reais são definidos pelo conteúdo importado pelo usuário. Para manter
o catálogo estável antes de existir leitura de nomes e metadados, as posições
foram registradas provisoriamente como:

| # | Nome provisório | ID | Seletor | Checksum `0x16` no slot 11 |
|---:|---|---:|---:|---:|
| 1 | CLONE 1 | `0x00` | `0x0F` | `0x49` |
| 2 | CLONE 2 | `0x01` | `0x0F` | `0x4A` |
| 3 | CLONE 3 | `0x02` | `0x0F` | `0x4B` |
| 4 | CLONE 4 | `0x03` | `0x0F` | `0x4C` |
| 5 | CLONE 5 | `0x04` | `0x0F` | `0x4D` |
| 6 | CLONE 6 | `0x05` | `0x0F` | `0x4E` |
| 7 | CLONE 7 | `0x06` | `0x0F` | `0x4F` |
| 8 | CLONE 8 | `0x07` | `0x0F` | `0x50` |
| 9 | CLONE 9 | `0x08` | `0x0F` | `0x51` |
| 10 | CLONE 10 | `0x09` | `0x0F` | `0x52` |

### Captura entre classes

A troca de `RVB / STUDIO` para a primeira posição CLONE foi capturada com o
comando `0x17`:

```text
slot de origem  = 00 0A
slot de destino = 00 0A
classe          = 00 0B
modelo          = 00 00
flag            = 00
seletor         = 0F
checksum        = 0x54
```

A volta para `RVB / STUDIO` confirmou novamente os campos da classe RVB. A
troca para CLONE apareceu repetidamente com a mesma estrutura.

### Troca entre as posições

A captura completa começou com a primeira posição já selecionada, percorreu:

```text
CLONE 2
CLONE 3
CLONE 4
CLONE 5
CLONE 6
CLONE 7
CLONE 8
CLONE 9
CLONE 10
CLONE 1
```

As trocas internas usam o comando `0x16`, com IDs sequenciais de `0x00` a
`0x09`, flag `0x00` e seletor `0x0F`. Toda a sequência foi testada fisicamente
e funcionou corretamente.

Validador físico:

```text
python -m tools.experiments.validate_clone_slots_slot_11
```

### Operações estruturais calculadas e cobertas por testes

```text
substituir slot 11 por CLONE 1 = checksum 0x54
adicionar CLONE 1 no slot 12  = checksum 0x69
adicionar CLONE 10 no slot 12 = checksum 0x72
```

O catálogo e o gerenciador flexível reconhecem CLONE como a décima segunda
classe do utilitário. A integração acrescenta testes para:

- ID e posição da classe;
- quantidade e ordem das dez posições;
- IDs sequenciais de `0x00` a `0x09`;
- seletor `0x0F`;
- checksums do comando `0x16`;
- substituição por `CLONE 1` no slot 11;
- adição de `CLONE 1` e `CLONE 10` no slot 12;
- pesquisa por nome, número e ID.

### Importação NAM ainda não investigada

As capturas de seleção não contêm o arquivo NAM, nome do usuário, metadados ou
transferência extensa. Isso confirma que selecionar uma posição CLONE e
importar conteúdo são operações separadas.

A futura investigação da importação deverá observar, sem reenviar dados antes
da análise:

- formato do conteúdo transmitido;
- nome e metadados da posição;
- índice de destino;
- tamanho total;
- possível divisão em blocos;
- checksums por bloco ou da transferência;
- comando de início e finalização;
- respostas e confirmações da pedaleira;
- comportamento de substituição e backup.

A importação de IR deve permanecer separada, pois pode utilizar outro formato
e outros comandos.

Após esta integração, o catálogo possui 12 classes e 263 posições/modelos,
com 148 testes automáticos aprovados.

## Classes especiais FX LOOP, FX SEND, FX RETURN e VOL

As quatro últimas categorias exibidas pelo editor possuem apenas um item cada,
mas as capturas confirmaram que são classes SysEx independentes. Todas foram
validadas fisicamente no slot interno 11.

| Menu | Classe | ID da classe | Item | ID do modelo | Seletor | Checksum `0x17` slot 11 |
|---:|---|---:|---|---:|---:|---:|
| 13 | FX LOOP | `0x0C` | FX LOOP | `0x00` | `0x06` | `0x4C` |
| 14 | FX SEND | `0x0D` | SND | `0x01` | `0x06` | `0x4E` |
| 15 | FX RETURN | `0x0E` | RTN | `0x02` | `0x06` | `0x50` |
| 16 | VOL | `0x0F` | VOL | `0x03` | `0x06` | `0x52` |

Todos usam flag estrutural `0x00`. A sequência observada é regular, mas os
valores foram registrados a partir das capturas, não inferidos:

```text
classe 0x0C -> modelo 0x00
classe 0x0D -> modelo 0x01
classe 0x0E -> modelo 0x02
classe 0x0F -> modelo 0x03
```

### Capturas entre classes

A troca de `CLONE 1` para `FX LOOP` confirmou:

```text
classe   = 0x0C
modelo   = 0x00
flag     = 0x00
seletor  = 0x06
checksum = 0x4C
```

A troca de `FX LOOP` para `SND` confirmou:

```text
classe   = 0x0D
modelo   = 0x01
flag     = 0x00
seletor  = 0x06
checksum = 0x4E
```

A troca de `SND` para `RTN` confirmou:

```text
classe   = 0x0E
modelo   = 0x02
flag     = 0x00
seletor  = 0x06
checksum = 0x50
```

A troca de `RTN` para `VOL` confirmou:

```text
classe   = 0x0F
modelo   = 0x03
flag     = 0x00
seletor  = 0x06
checksum = 0x52
```

As voltas às classes anteriores reproduziram os campos já conhecidos. As
sequências foram repetidas nas capturas e mantiveram os mesmos pacotes.

### Validação física conjunta

O validador está em:

```text
tools/experiments/validate_special_blocks_slot_11.py
```

A opção automática percorreu fisicamente:

```text
FX LOOP
SND
RTN
VOL
RTN
```

Todos os blocos foram selecionados corretamente. Como cada classe possui um
único item, a validação usa substituições estruturais `0x17`; não existe troca
interna entre modelos da mesma classe para esses quatro casos.

### Adição em slot vazio calculada e coberta por testes

```text
adicionar FX LOOP no slot 12 = checksum 0x61
adicionar SND no slot 12     = checksum 0x63
adicionar RTN no slot 12     = checksum 0x65
adicionar VOL no slot 12     = checksum 0x67
```

O gerenciador flexível reconhece automaticamente as quatro classes por ler o
catálogo central. A integração acrescenta testes para:

- IDs e posições de menu das classes;
- presença de um único item em cada classe;
- IDs de modelo `0x00`, `0x01`, `0x02` e `0x03`;
- seletor comum `0x06`;
- flag estrutural `0x00`;
- checksums capturados das substituições no slot 11;
- checksums calculados das adições no slot 12;
- pesquisa por classe, nome e número de menu;
- total consolidado do catálogo.

Após esta integração, o catálogo possui 16 classes e 267 posições/modelos,
com 158 testes automáticos aprovados.


## Parâmetros ao vivo — comando 0x1C

As capturas de `DYN / M-BOOST`, `DYN / COMP1`, `DYN / E-BOOST`,
`DYN / AC WOODY` e `DYN / GATE 1`
confirmaram respostas SysEx de 70 bytes para mudanças de parâmetros:

```text
39–40  slot interno zero-based
41–42  classe observada (DYN = 00 00 nas capturas atuais)
48     seletor do parâmetro
59–62  valor em quatro nibbles
63–64  marcador/tipo = 01 01
```

O valor usa o codec `upper_float32_nibbles_v1`: os dois bytes superiores de um
float32 little-endian são transmitidos como quatro nibbles. As faixas 0–100 de
M-BOOST/GAIN, COMP1/SUSTAIN/VOLUME, E-BOOST/GAIN, AC WOODY/SHAPE e
GATE 1/THRESHOLD usam esse mesmo codec.
O E-BOOST também confirmou que valores booleanos usam o mesmo formato:
`0 → 00 00 00 00` e `1 → 08 00 03 0F`. A conversão para
`desligado/ligado` é determinada pelo `value_type: boolean` do catálogo.

Seletores confirmados:

```text
M-BOOST / GAIN    = 0
COMP1 / SUSTAIN   = 0
COMP1 / VOLUME    = 1
E-BOOST / GAIN    = 0
E-BOOST / +3dB    = 1
E-BOOST / BRIGHT  = 2
AC WOODY / SHAPE  = 0
GATE 1 / THRESHOLD = 0
```

### Identidade do efeito não vem do suposto model_id

Os índices `21–22` permanecem `01 04` no M-BOOST, no COMP1, no E-BOOST,
no AC WOODY e no GATE 1,
apesar de seus `model_id` estruturais serem diferentes. Portanto, esse campo
não pode ser interpretado como model_id.

A resolução correta é contextual:

```text
slot recebido no 0x1C
  → registro estrutural atual daquele slot
  → efeito do catálogo JSON
  → seletor do parâmetro no índice 48
  → codec e valor
```

Sem a cadeia atual, uma mensagem com seletor `0` é ambígua: pode representar
GAIN no M-BOOST, SUSTAIN no COMP1, GAIN no E-BOOST, SHAPE no AC WOODY ou
THRESHOLD no GATE 1. O motor deve exigir o efeito real do slot antes de
produzir `EffectParameterEvent`.

Evidências mínimas:

```text
tests/fixtures/mboost_gain/
tests/fixtures/comp1_parameters/
tests/fixtures/e_boost_parameters/
tests/fixtures/ac_woody_parameters/
tests/fixtures/gate1_parameters/
```
