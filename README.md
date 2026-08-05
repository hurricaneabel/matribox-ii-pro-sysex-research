# Matribox II Pro SysEx Research

Pesquisa experimental e documentada do protocolo SysEx da **Sonicake
Matribox II Pro**.

O objetivo é compreender a comunicação usada pelo editor oficial, reproduzir
somente comandos confirmados em testes reais e construir uma base segura para
um futuro controlador de computador e celular.

> Este repositório é de pesquisa. Nenhum comando é considerado suportado antes
> de ser capturado, reproduzido na pedaleira, testado automaticamente e
> documentado.

## Estado atual

A estrutura de efeitos da Matribox já pode ser controlada por Python para:

- adicionar um efeito em slot ausente;
- substituir um efeito existente;
- trocar modelos dentro da mesma classe;
- remover um efeito;
- ligar ou desligar um slot;
- alterar o volume do preset;
- movimentar efeitos na cadeia visual;
- solicitar e reconstruir dumps de preset em condições já estudadas.

O gerenciador flexível principal é:

```powershell
python -m tools.experiments.manage_effect_chain
```

Ele permite adicionar, substituir e excluir efeitos nos slots internos de
`1` a `12`.

## Catálogo confirmado

Até esta etapa foram catalogadas **10 classes** e **241 modelos**.

A ordem abaixo é a ordem atual do utilitário de terminal. Ela não deve ser
interpretada como a ordem oficial da interface da pedaleira.

| Menu | Classe | ID SysEx | Modelos |
|---:|---|---:|---:|
| 1 | FREQ | `0x01` | 8 |
| 2 | DRV | `0x03` | 24 |
| 3 | DYN | `0x00` | 14 |
| 4 | WAH | `0x02` | 6 |
| 5 | AMP | `0x04` | 63 |
| 6 | CAB | `0x05` | 61 |
| 7 | IR | `0x06` | 20 |
| 8 | EQ | `0x07` | 5 |
| 9 | MOD | `0x08` | 23 |
| 10 | DLY | `0x09` | 17 |

As listas completas de modelos, IDs, seletores e checksums ficam em:

```text
tools/commands/effect_catalog.py
docs/protocol_findings.md
```

## Última classe concluída: DLY

A subclasse DLY foi capturada pelo Wireshark/USBPcap e validada fisicamente.

```text
classe DLY          = 0x09
flag estrutural     = 0x00
seletor secundário  = 0x0B
quantidade          = 17 modelos
```

Modelos na ordem do editor:

```text
WARM
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
```

O modelo `PURE` utiliza ID `0x00`. Ele apareceu no primeiro pacote da captura
completa e foi confirmado novamente no teste físico.

Validador:

```powershell
python -m tools.experiments.validate_dly_models_slot_11
```

A opção `A` percorre os modelos e retorna ao `WARM`.

## Comandos SysEx confirmados

| Tipo | Tamanho total | Função principal |
|---:|---:|---|
| `0x14` | 54 bytes | alterar volume do preset |
| `0x16` | 58 bytes | trocar modelo dentro da mesma classe |
| `0x17` | 60 bytes | adicionar, substituir ou remover efeito |
| `0x18` | 62 bytes | ligar ou desligar slot interno |

O checksum fica no índice `7`.

Nos comandos estruturais e de modelo, os valores de classe e modelo são
transmitidos em dois nibbles.

## Slots internos

O programa apresenta os slots de `1` a `12`.

O protocolo usa valores de `0` a `11`:

```python
protocol_slot = slot_apresentado - 1
```

Exemplos:

```text
slot 1  -> 00 00
slot 11 -> 00 0A
slot 12 -> 00 0B
```

Um slot interno é um endereço persistente dentro do preset e não é a mesma
coisa que a posição visual atual do efeito na cadeia.

## Adição, substituição e remoção

O comando `0x17` usa:

```text
39–40 = slot de origem
41–42 = slot de destino
43–44 = classe
45–46 = modelo
49    = flag estrutural
52    = seletor secundário
```

O valor de slot vazio é:

```text
0F 0F
```

Regras confirmadas:

```text
adicionar:
origem vazia, destino real

substituir:
origem igual ao destino

remover:
origem real, destino vazio
```

## Troca dentro da mesma classe

O comando `0x16` usa:

```text
39–40 = slot
41–42 = classe
43–44 = modelo
47    = flag estrutural
50    = seletor secundário
```

O catálogo armazena o seletor por modelo porque algumas classes possuem
exceções. Exemplos:

- MOD usa `0x04` na maioria dos modelos, mas `DETUNE` e `LOFI BIT` usam
  `0x01`;
- DLY usa `0x0B` nos 17 modelos;
- WAH, DYN e AMP também possuem grupos com seletores diferentes.

## Metodologia de captura

Os comandos enviados pelo editor oficial são interceptados com:

```text
Wireshark + USBPcap
```

O logger Python observa mensagens entregues pela porta MIDI de entrada, mas
não substitui a interceptação USB dos comandos do editor.

Procedimento usado para catalogar uma classe:

1. colocar um efeito conhecido em um slot de teste;
2. capturar a troca entre classes com comando `0x17`;
3. percorrer todos os modelos da nova classe;
4. extrair os pacotes `0x16`;
5. relacionar cada pacote com a ordem visual do editor;
6. recalcular os checksums;
7. criar um validador físico;
8. testar a sequência completa na pedaleira;
9. integrar ao catálogo;
10. executar toda a suíte antes do commit.

## Ambiente utilizado

```text
Sistema operacional: Windows
Python: 3.12
MIDI: mido + python-rtmidi
```

Portas usadas:

```text
Entrada: Matribox II Pro Subdevice 0
Saída:   Matribox II Pro Subdevice 1
```

## Preparação

Ativar o ambiente virtual:

```powershell
.\venv\Scripts\Activate.ps1
```

Instalar dependências:

```powershell
python -m pip install -r requirements.txt
```

## Testes

Executar toda a suíte:

```powershell
python -m unittest discover -s tests -v
```

Estado após a integração DLY:

```text
128 testes executados
128 testes aprovados
```

Também é usado:

```powershell
python -m compileall tools tests
git diff --check
```

## Ferramentas principais

### Gerenciar a cadeia

```powershell
python -m tools.experiments.manage_effect_chain
```

### Alterar o volume

```powershell
python -m tools.commands.set_volume
```

### Ligar ou desligar slot

```powershell
python -m tools.commands.set_effect_slot
```

### Adicionar efeito

```powershell
python -m tools.commands.add_effect
```

### Substituir ou trocar efeito

```powershell
python -m tools.commands.set_effect
```

### Remover efeito

```powershell
python -m tools.commands.remove_effect
```

### Verificar portas MIDI

```powershell
python -m tools.capture.teste_portas
```

### Logger MIDI

```powershell
python -m tools.capture.logger
```

### Solicitar dump de preset

```powershell
python -m tools.commands.request_preset_dump
```

## Validadores físicos

```text
tools/experiments/validate_eq_models_slot_11.py
tools/experiments/validate_add_eq_slot_12.py
tools/experiments/validate_mod_models_slot_11.py
tools/experiments/validate_dly_models_slot_11.py
tools/experiments/validate_unified_effect_chain_slot_12.py
tools/experiments/validate_unified_replacement_slot_11.py
```

## Estrutura do projeto

```text
matribox-sysex/
├── README.md
├── requirements.txt
├── data/
│   └── dumps/
├── docs/
│   └── protocol_findings.md
├── tests/
│   ├── test_effect_chain.py
│   ├── test_effect_model.py
│   ├── test_effect_slot_protocol.py
│   ├── test_volume_protocol.py
│   └── testes específicos por classe
└── tools/
    ├── analysis/
    ├── capture/
    ├── commands/
    └── experiments/
```

## Dumps de preset

O repositório contém capturas e reconstruções do preset de pesquisa `45B`.

A pesquisa já confirmou:

- dumps divididos em fragmentos;
- reconstrução de dados binários;
- comparação de dumps da mesma sessão;
- variação de volume no dump;
- comportamento de estado de slot;
- dependência de inicialização da sessão para certas respostas da pedaleira.

Os detalhes permanecem registrados em:

```text
data/dumps/
docs/protocol_findings.md
```

## Segurança

Não são enviados comandos desconhecidos relacionados a:

- firmware;
- restauração de fábrica;
- apagamento em massa;
- escrita em memória desconhecida;
- configurações críticas não reversíveis.

Os testes usam presets dedicados e alterações reversíveis.

## Próxima investigação

A próxima classe prevista é:

```text
RVB / Reverb
```

O ID, os modelos, seletores e flags somente serão registrados após captura e
validação física.

## Documentação técnica completa

O histórico detalhado das descobertas, estruturas, exceções, pacotes e
checksums está em:

```text
docs/protocol_findings.md
```

Esse arquivo é a fonte técnica principal da pesquisa.
