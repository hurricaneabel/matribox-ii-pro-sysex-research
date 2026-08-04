# Matribox II Pro SysEx Research

Projeto experimental para estudar, testar e documentar o protocolo SysEx da
Sonicake Matribox II Pro.

Este projeto está separado do controlador principal. Apenas comandos
confirmados em testes reais na pedaleira serão posteriormente integrados ao
projeto principal.

## Objetivo

Descobrir como o editor oficial da Matribox II Pro se comunica com a
pedaleira por SysEx.

Os principais objetivos são:

- capturar mensagens SysEx reais;
- identificar parâmetros e valores;
- entender o formato dos pacotes;
- descobrir o cálculo do checksum;
- reproduzir comandos usando Python;
- documentar cada descoberta confirmada;
- criar futuramente um controlador para computador e celular.

## Estado atual

O primeiro comando SysEx de escrita foi confirmado com sucesso:

- alteração do volume do preset;
- funcionamento em diferentes presets;
- funcionamento em diferentes bancos;
- valores gerados automaticamente;
- valor codificado em dois nibbles;
- checksum recalculado automaticamente;
- envio realizado com Mido e python-rtmidi.

O comando altera o volume do preset atualmente selecionado na Matribox II Pro.

## Ambiente utilizado

Sistema operacional:

```text
Windows
```

Linguagem:

```text
Python 3.12
```

Bibliotecas:

```text
mido==1.3.3
python-rtmidi==1.5.8
```

## Portas MIDI utilizadas

Entrada MIDI:

```text
Matribox II Pro Subdevice 0
```

Saída MIDI:

```text
Matribox II Pro Subdevice 1
```

A porta de entrada é usada para capturar mensagens enviadas pela pedaleira.

A porta de saída é usada para enviar comandos para a pedaleira.

## Assinatura SysEx observada

As mensagens estudadas começam com:

```text
F0 21 25 4D 50
```

E terminam com:

```text
F7
```

O significado completo desses bytes ainda não foi confirmado.

Os bytes:

```text
4D 50
```

correspondem às letras `MP` em ASCII, mas ainda não está confirmado se isso
significa Matribox Pro.

## Mensagens de notificação e escrita

Nas mensagens enviadas pela pedaleira para o computador, o índice 8 foi
observado como:

```text
00
```

Nas mensagens de escrita enviadas pelo editor oficial para a pedaleira, o
índice 8 foi observado como:

```text
12
```

Hipótese atual:

```text
00 = notificação enviada pela pedaleira
12 = comando de escrita enviado para a pedaleira
```

Essa interpretação ainda precisa ser validada com outros parâmetros.

## Codificação do volume

O volume do preset é convertido para hexadecimal e separado em dois
nibbles.

Exemplo:

```text
Volume 49 decimal = 0x31 hexadecimal
Transmitido como: 03 01
```

Na mensagem SysEx completa:

```text
Índice 39 = nibble alto
Índice 40 = nibble baixo
```

A fórmula utilizada pelo código é:

```python
high_nibble = (volume >> 4) & 0x0F
low_nibble = volume & 0x0F
```

Exemplos:

| Volume | Hexadecimal | Bytes enviados |
|---:|---:|---:|
| 1 | 01 | 00 01 |
| 35 | 23 | 02 03 |
| 49 | 31 | 03 01 |
| 59 | 3B | 03 0B |
| 75 | 4B | 04 0B |
| 100 | 64 | 06 04 |

Exemplo com volume 75:

```text
75 decimal = 0x4B hexadecimal

Nibble alto = 04
Nibble baixo = 0B
```

Os bytes inseridos na mensagem são:

```text
04 0B
```

## Identificador do parâmetro de volume

O trecho observado próximo ao valor do volume é:

```text
05 00 01
```

Esse trecho é considerado atualmente o identificador do parâmetro
Preset Volume.

A estrutura observada é:

```text
05 00 01 [nibble alto] [nibble baixo]
```

Exemplo para volume 49:

```text
05 00 01 03 01
```

Exemplo para volume 75:

```text
05 00 01 04 0B
```

## Checksum

O checksum fica no índice 7 da mensagem SysEx completa, contando o byte
`F0` como índice zero.

A fórmula confirmada para o comando de alteração do volume é:

```python
checksum = sum(message[14:49]) & 0x7F
```

O cálculo soma os bytes dos índices 14 até 48.

Em Python, o índice final de um recorte não é incluído. Por isso:

```python
message[14:49]
```

representa os índices:

```text
14 até 48
```

O operador:

```python
& 0x7F
```

mantém o resultado entre 0 e 127, que é a faixa permitida para os bytes
internos de uma mensagem SysEx MIDI.

Essa fórmula foi confirmada para o pacote de alteração do Preset Volume.

Ainda não está confirmado se outros tipos de mensagens utilizam exatamente
a mesma faixa ou o mesmo cálculo.

## Estrutura provisória do pacote de volume

A mensagem completa possui 54 bytes, contando `F0` e `F7`.

Estrutura provisória:

| Índice | Conteúdo |
|---:|---|
| 0 | `F0`, início da mensagem SysEx |
| 1–4 | assinatura observada `21 25 4D 50` |
| 5–6 | valores fixos observados `00 00` |
| 7 | checksum |
| 8 | tipo de comando de escrita `12` |
| 9 | valor observado `14` |
| 10–38 | estrutura e identificação do parâmetro |
| 39 | nibble alto do volume |
| 40 | nibble baixo do volume |
| 41–48 | restante do conteúdo incluído no checksum |
| 49–52 | finalização fixa observada |
| 53 | `F7`, final da mensagem SysEx |

O significado completo dos campos fixos ainda não foi identificado.

## Testes confirmados

Foram confirmados os seguintes testes:

- captura de mensagens SysEx enviadas pela Matribox;
- captura de comandos enviados pelo editor oficial;
- reenvio de uma mensagem original capturada;
- alteração do volume usando uma mensagem capturada;
- geração automática de novos valores;
- separação correta do valor em dois nibbles;
- cálculo automático do checksum;
- alteração do volume em diferentes presets;
- alteração do volume em diferentes bancos;
- funcionamento sem depender do número do preset atual.

## Arquivos principais

### `logger.py`

Captura mensagens MIDI recebidas pela porta de entrada da Matribox.

As mensagens SysEx são exibidas em hexadecimal e registradas em arquivo.

### `checksum_test.py`

Testa diferentes fórmulas e faixas de checksum usando mensagens SysEx
capturadas.

### `set_volume.py`

Gera e envia um comando SysEx válido para alterar o volume do preset
atualmente selecionado.

O programa:

1. recebe um volume entre 0 e 100;
2. separa o valor em dois nibbles;
3. coloca os nibbles nos índices 39 e 40;
4. recalcula o checksum;
5. coloca o checksum no índice 7;
6. envia a mensagem pela porta MIDI de saída.

## Ativação do ambiente virtual

No PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Quando o ambiente estiver ativo, o terminal deve começar com:

```text
(venv)
```

## Instalação das dependências

Com o ambiente virtual ativo:

```powershell
python -m pip install -r requirements.txt
```

## Executar o controle de volume

Com a Matribox conectada e ligada:

```powershell
python set_volume.py
```

O programa solicitará:

```text
Digite o volume entre 0 e 100:
```

Digite um valor e pressione Enter.

Exemplo:

```text
75
```

O programa deverá mostrar informações semelhantes a:

```text
Checksum calculado: 32
Valor codificado: 04 0B
Comando enviado para volume 75.
```

## Executar o logger

Para capturar mensagens enviadas pela Matribox:

```powershell
python logger.py
```

Para parar a captura:

```text
Ctrl+C
```

## Segurança dos testes

Não serão enviados comandos desconhecidos relacionados a:

- atualização de firmware;
- restauração de fábrica;
- apagamento de presets;
- gravação em endereços de memória desconhecidos;
- importação de arquivos desconhecidos;
- alteração de configurações críticas.

Os primeiros testes serão realizados apenas com parâmetros reversíveis,
como:

- volume;
- valores de efeitos;
- ligar e desligar módulos;
- BPM;
- posição do Looper;
- parâmetros globais não destrutivos.

## Próximas investigações

Os próximos parâmetros a serem investigados são:

- ligar e desligar um módulo de efeito;
- identificar o número de cada módulo;
- alterar parâmetros de um efeito;
- descobrir comandos de leitura;
- interpretar respostas da pedaleira;
- identificar dumps completos de presets;
- confirmar o checksum em outros tipos de mensagem;
- entender a estrutura dos nomes de presets;
- documentar comandos globais.

## Pontos ainda desconhecidos

Ainda não foram confirmados:

- significado completo do cabeçalho;
- significado exato de `21 25 4D 50`;
- função de todos os campos fixos;
- estrutura genérica de qualquer parâmetro;
- formato de comandos de leitura;
- formato de dumps completos;
- mensagens de confirmação ou ACK;
- checksum utilizado em outros comandos;
- estrutura de módulos e algoritmos;
- formato de salvamento de presets.

## Projeto principal

Este repositório é utilizado apenas para pesquisa e testes SysEx.

Os comandos somente serão transferidos para o controlador principal depois
de:

1. serem capturados;
2. serem reproduzidos;
3. funcionarem em diferentes presets;
4. terem seus campos identificados;
5. possuírem testes;
6. estarem documentados.

## Estrutura atual do projeto

O projeto foi organizado por finalidade para separar comandos, ferramentas de
captura, análise de dados e experimentos antigos.

```text
matribox-sysex/
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   └── dumps/
│       ├── preset_dump_received.txt
│       ├── preset_45B_original.bin
│       └── preset_45B_original.hex
│
├── docs/
│   └── protocol_findings.md
│
├── tests/
│   ├── test_effect_slot_protocol.py
│   └── test_volume_protocol.py
│
└── tools/
    ├── __init__.py
    │
    ├── analysis/
    │   ├── __init__.py
    │   ├── analisar.py
    │   ├── checksum_test.py
    │   └── decode_preset_dump.py
    │
    ├── capture/
    │   ├── __init__.py
    │   ├── logger.py
    │   └── teste_portas.py
    │
    ├── commands/
    │   ├── __init__.py
    │   ├── move_and_read_chain.py
    │   ├── move_effect_position.py
    │   ├── request_preset_dump.py
    │   ├── set_effect_slot.py
    │   └── set_volume.py
    │
    └── experiments/
        ├── __init__.py
        ├── enviar_teste.py
        └── teste_escrita.py
```

## Ferramentas de captura

### Verificar portas MIDI

```powershell
python tools\capture\teste_portas.py
```

### Capturar mensagens recebidas pela porta MIDI

```powershell
python tools\capture\logger.py
```

O logger observa mensagens entregues pela porta MIDI de entrada. Para
interceptar os comandos enviados pelo editor oficial à pedaleira, continua
sendo necessário utilizar o Wireshark com USBPcap.

## Ferramentas de análise

### Analisar mensagens

```powershell
python tools\analysis\analisar.py
```

### Testar hipóteses de checksum

```powershell
python tools\analysis\checksum_test.py
```

### Reconstruir o dump de preset

```powershell
python tools\analysis\decode_preset_dump.py
```

Esse script lê:

```text
data/dumps/preset_dump_received.txt
```

E gera:

```text
data/dumps/preset_45B_original.bin
data/dumps/preset_45B_original.hex
```

O primeiro dump reconstruído possui:

```text
289 bytes decodificados
```

Ele foi recebido em dois fragmentos:

```text
Fragmento 1:
185 bytes
offset 0

Fragmento 2:
104 bytes
offset 185
```

## Comandos SysEx confirmados

### Alterar o volume do preset

```powershell
python tools\commands\set_volume.py
```

### Ligar ou desligar um slot interno

```powershell
python tools\commands\set_effect_slot.py
```

Foram testados os 12 slots internos disponíveis no preset.

### Mover um efeito na cadeia visual

```powershell
python tools\commands\move_effect_position.py
```

Esse comando trabalha com posições visuais, não com os slots internos
persistentes.

### Mover e tentar ler a ordem devolvida

```powershell
python tools\commands\move_and_read_chain.py
```

A Matribox executa o movimento corretamente. Entretanto, a resposta da
pedaleira depende de uma sessão de comunicação previamente inicializada pelo
editor oficial.

### Solicitar o dump do preset 45B

```powershell
python tools\commands\request_preset_dump.py
```

O fluxo confirmado é:

```text
Python → Matribox:
seleciona o preset 45B

Matribox → Python:
confirma a seleção com uma mensagem SysEx de 54 bytes

Python → Matribox:
solicita a leitura do preset

Matribox → Python:
envia o dump em dois fragmentos
```

Atualmente, a pedaleira somente envia essas respostas depois que o editor
oficial foi aberto e realizou sua sincronização inicial.

Ainda é necessário descobrir e reproduzir a mensagem de inicialização dessa
sessão para que o programa Python funcione sem depender do editor oficial.

## Testes automáticos

Para executar todos os testes:

```powershell
python -m unittest discover -s tests -v
```

Estado atual:

```text
15 testes executados
15 testes aprovados
```

Os testes cobrem:

- codificação do volume em nibbles;
- checksum do volume;
- validação da faixa de volume;
- codificação dos slots internos;
- estado ligado e desligado;
- checksum dos slots;
- validação dos slots de 1 até 12.

## Observação sobre presets com 12 efeitos

O protocolo permite controlar os 12 slots internos.

Entretanto, durante os testes, um preset preenchido com 12 efeitos apresentou
instabilidade no editor oficial, incluindo travamentos e dificuldade para
reabrir o programa.

O preset de pesquisa `45B` foi reduzido para 11 efeitos para manter a
estabilidade durante a investigação.

Ainda não está confirmado se a quantidade de efeitos causou diretamente o
problema ou se o editor oficial estava em um estado de sessão instável.