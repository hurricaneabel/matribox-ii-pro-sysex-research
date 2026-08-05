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

Até esta etapa foram catalogadas **16 classes** e **267 posições/modelos**.

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
| 11 | RVB | `0x0A` | 12 |
| 12 | CLONE | `0x0B` | 10 posições |
| 13 | FX LOOP | `0x0C` | 1 |
| 14 | FX SEND | `0x0D` | 1 (`SND`) |
| 15 | FX RETURN | `0x0E` | 1 (`RTN`) |
| 16 | VOL | `0x0F` | 1 |

As listas completas de modelos, IDs, seletores e checksums ficam em:

```text
tools/commands/effect_catalog.py
docs/protocol_findings.md
```

## Últimas classes concluídas: blocos especiais

Os quatro blocos finais exibidos pelo editor foram capturados por
Wireshark/USBPcap e validados fisicamente. Embora cada bloco tenha somente um
item, o protocolo os identifica como quatro classes independentes.

| Classe | ID | Item | Modelo | Flag | Seletor |
|---|---:|---|---:|---:|---:|
| FX LOOP | `0x0C` | FX LOOP | `0x00` | `0x00` | `0x06` |
| FX SEND | `0x0D` | SND | `0x01` | `0x00` | `0x06` |
| FX RETURN | `0x0E` | RTN | `0x02` | `0x00` | `0x06` |
| VOL | `0x0F` | VOL | `0x03` | `0x00` | `0x06` |

As capturas confirmaram que todos usam o comando estrutural `0x17`. Como cada
classe possui apenas um item, não existe uma sequência interna de modelos a
ser percorrida com `0x16`.

Validador conjunto:

```powershell
python -m tools.experiments.validate_special_blocks_slot_11
```

A opção `A` percorre:

```text
FX LOOP
SND
RTN
VOL
RTN
```

A classe CLONE continua com dez posições selecionáveis. A importação NAM e a
importação de IR permanecem investigações separadas da seleção estrutural da
cadeia.

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
- RVB usa `0x0C` nos 12 modelos;
- CLONE usa `0x0F` nas 10 posições;
- FX LOOP, FX SEND, FX RETURN e VOL usam `0x06`;
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

Estado após a integração dos blocos especiais:

```text
158 testes executados
158 testes aprovados
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
tools/experiments/validate_rvb_models_slot_11.py
tools/experiments/validate_clone_slots_slot_11.py
tools/experiments/validate_special_blocks_slot_11.py
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

Com as 16 classes exibidas pelo editor catalogadas estruturalmente, a próxima
fase será dividida em frentes independentes:

1. mapear parâmetros internos de efeitos fixos e reversíveis;
2. investigar leitura de nomes e metadados das posições CLONE;
3. analisar a importação NAM sem reenviar dados desconhecidos;
4. investigar a importação de IR em captura separada.

A seleção normal de CLONE e IR na cadeia já funciona, mas transferência de
arquivos, escrita persistente e gerenciamento de nomes não serão misturados
com os comandos estruturais confirmados.

## Documentação técnica completa

O histórico detalhado das descobertas, estruturas, exceções, pacotes e
checksums está em:

```text
docs/protocol_findings.md
```

Esse arquivo é a fonte técnica principal da pesquisa.
