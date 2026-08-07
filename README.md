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

O monitor consolidado principal é:

```powershell
python -m tools.commands.matribox_monitor
```

Ele acompanha o preset atual, nome, etiqueta, cadeia de efeitos, ordem visual,
estado ligado/desligado e valores de parâmetros já catalogados. A leitura da
cadeia é não destrutiva e possui reenvios automáticos para a primeira
comunicação após ligar a pedaleira.

Após a Fase 35, o mesmo comando ganhou dois modos de apresentação sem alterar
o protocolo MIDI. O modo tradicional permanece append-only e é o recomendado
para pesquisa e preservação de evidências:

```powershell
python -m tools.commands.matribox_monitor
```

Para uso cotidiano, `--live` abre um buffer alternativo do terminal e redesenha
o mesmo painel a cada atualização, sem acumular um novo bloco para cada evento:

```powershell
python -m tools.commands.matribox_monitor --live
```

O modo painel pode preservar simultaneamente um histórico compacto das mudanças:

```powershell
python -m tools.commands.matribox_monitor --live --log data/dumps/monitor_live.txt
```

O arquivo de log registra eventos como mudanças de parâmetro e bypass, enquanto
a tela permanece limpa. `data/dumps/` continua fora do Git.

A Fase 36 hidrata os valores iniciais dos parâmetros catalogados
diretamente do dump somente leitura `0x10`. São doze slots de 60 bytes, com
quinze posições float32 endereçadas pelo seletor do parâmetro. Eventos ao vivo
continuam prevalecendo. O monitor também solicita um novo dump somente leitura
após mudanças estruturais para hidratar efeitos adicionados. A validação offline
passou com 443 testes. Carga, adição, substituição, reordenação, mudança de
classe e parâmetros ao vivo foram aprovados fisicamente.

A Fase 37 cadastra o `FREQ / Pitch`: HI PITCH `0–12`, LOW PITCH
`-12–0` e WET/DRY/RANGE `0–100`. Quatro dumps físicos confirmaram seletores
0–4, defaults `12 / 0 / 50 / 50 / 50` e LOW PITCH negativo nativo. A suíte
offline passou com 445 testes. A validação física aprovou hidratação, adição de
efeitos, alterações em tempo real e duas instâncias independentes.

A Fase 38 adiciona `FREQ / Harmony D` com MIX, KEY, MODE,
INTERVAL 1, INTERVAL 2 e SMOOTH. Os três enums musicais são apresentados por
nome, e o catálogo preserva a lacuna física entre INTERVAL 2 (seletor 4) e
SMOOTH (seletor 6). A suíte offline passou com 447 testes. A validação física
aprovou duas instâncias, hidratação e alterações em tempo real.

O primeiro parâmetro interno concluído foi o `GAIN` do `DYN / M-BOOST`. Desde a
Fase 36, o monitor hidrata o valor salvo antes do primeiro evento ao vivo e
depois atualiza a instância correta. O validador histórico permanece:

```powershell
python -m tools.experiments.validate_mboost_gain_live
```

A validação física da Fase 22 aprovou múltiplas instâncias simultâneas e os
slots internos 2, 8, 10 e 12, incluindo valores de 0 a 100. A Fase 23B também
foi aprovada fisicamente no validador genérico e no monitor principal, com dois
M-BOOSTs simultâneos, valores independentes e preservação do slot interno após
mudança de posição visual.

Validador genérico para qualquer parâmetro presente no catálogo JSON:

```powershell
python -m tools.experiments.validate_effect_parameters_live
```

A Fase 24 acrescentou `SUSTAIN` e `VOLUME` do `DYN / COMP1` e foi aprovada
fisicamente com múltiplas instâncias, valores independentes e coexistência com
M-BOOST. A Fase 25 acrescentou o `DYN / E-BOOST`:

```text
GAIN    → inteiro 0–100
+3dB    → booleano desligado/ligado
BRIGHT  → booleano desligado/ligado
```

As cinco capturas controladas confirmaram os seletores `0`, `1` e `2`, os
slots internos 1 e 2 e a codificação numérica `0/1` para os interruptores. A
validação física no monitor principal aprovou a atualização independente dos
três parâmetros, a apresentação `ligado/desligado`, duas instâncias de E-BOOST
com estados separados e a coexistência com COMP1 e outros efeitos da cadeia.

A Fase 26 acrescentou dois efeitos DYN de parâmetro único:

```text
AC WOODY → SHAPE 0–100
GATE 1   → THRESHOLD 0–100
```

As capturas controladas confirmaram o comando `0x1C`, seletor `0`, o codec
`upper_float32_nibbles_v1` e os slots internos 1 e 2 para ambos. A integração
preserva 11 respostas físicas únicas por efeito. A validação no monitor
principal aprovou atualização independente de SHAPE e THRESHOLD, múltiplas
instâncias de AC WOODY com estados separados, preservação dos valores após
mudança da ordem visual e coexistência com COMP1, GATE 1 e efeitos de outras
classes.

A Fase 27 acrescentou os quatro controles contínuos do `DYN / COMP2`:

```text
SUSTAIN   → inteiro 0–100, seletor 0
ATTACK    → inteiro 0–100, seletor 1
VOLUME    → inteiro 0–100, seletor 2
CLIPPING  → inteiro 0–100, seletor 3
```

As seis capturas controladas confirmaram os slots internos 1 e 2 e preservaram
49 respostas físicas únicas. A suíte offline passou com 370 testes. A validação
física no monitor principal aprovou a apresentação dos quatro controles, a
atualização independente, duas instâncias simultâneas com estados separados e
a coexistência com COMP1, COMP3, M-BOOST, E-BOOST, AC-BOOST e BB-BOOST.

A Fase 28 acrescenta os sete controles contínuos do `DYN / COMP3`:

```text
THRESHOLD → inteiro 0–100, seletor 0
RATIO     → inteiro 0–100, seletor 1
VOLUME    → inteiro 0–100, seletor 2
ATTACK    → inteiro 0–100, seletor 3
RELEASE   → inteiro 0–100, seletor 4
TONE      → inteiro 0–100, seletor 5
BLEND     → inteiro 0–100, seletor 6
```

Nove capturas controladas confirmaram os slots internos 1 e 2 e preservaram
84 respostas SysEx físicas únicas. O monitor genérico não recebeu código
específico para o efeito: a ordem, a resolução e os valores vêm do catálogo
JSON e do contexto da cadeia. A integração passou com 376 testes e foi
aprovada fisicamente no monitor principal com os sete controles independentes,
duas instâncias simultâneas com estados separados e coexistência com efeitos
DYN e de outras classes.

A Fase 29 acrescenta os quatro controles contínuos de `DYN / AC-BOOST` e
`DYN / BB-BOOST`:

```text
GAIN    → inteiro 0–100, seletor 0
VOLUME  → inteiro 0–100, seletor 1
BASS    → inteiro 0–100, seletor 2
TREBLE  → inteiro 0–100, seletor 3
```

Doze capturas controladas confirmaram a mesma estrutura nos slots internos
humanos 1 e 2. Foram preservadas 32 respostas SysEx únicas por efeito. O
monitor continua inteiramente orientado pelo catálogo, sem parser específico
para cada boost. A integração passou com 382 testes e foi aprovada fisicamente no monitor
principal. AC-BOOST e BB-BOOST atualizaram os quatro controles de forma
independente enquanto coexistiam na mesma cadeia. Os estados ligado/desligado
também foram acompanhados sem perda dos valores já observados.

A Fase 30 acrescenta `DYN / RC-BOOST`, `DYN / FAT BOOST` e
`DYN / GATE 2`:

```text
RC-BOOST
GAIN 0–100 | VOLUME 0–100 | BASS 0–100 | TREBLE 0–100

FAT BOOST
BASS 0–100 | TREBLE 0–100 | VOLUME 0–100 | LOW CUT desligado/ligado

GATE 2
THRESHOLD 0–100 | ATTACK 0–100 | RELEASE 0–100
```

As 17 capturas controladas preservaram 83 respostas SysEx físicas únicas e
confirmaram os slots internos humanos 1 e 2. A integração passou com 386
testes e foi aprovada fisicamente no monitor principal com os três efeitos
simultâneos. Os onze parâmetros foram atualizados sem colisões, e o LOW CUT
foi apresentado corretamente como `desligado` e `ligado`. O log final não
inclui duas instâncias do mesmo modelo nem teste explícito de bypass; essa
limitação de cobertura física permanece documentada.

A Fase 31 acrescenta o `DYN / AC SIM` e o primeiro parâmetro categórico
nomeado do catálogo:

```text
BODY    → inteiro 0–100, seletor 0
TOP     → inteiro 0–100, seletor 1
VOLUME  → inteiro 0–100, seletor 2
MODE    → enum nomeado, seletor 3
          0 STANDARD | 1 JUMBO | 2 ENHANCED | 3 PIEZO
```

Seis capturas controladas confirmaram os slots internos humanos 1 e 2 e
preservaram 30 respostas SysEx físicas únicas. O codec físico continua sendo
`upper_float32_nibbles_v1`; a novidade é uma lista genérica de `choices` no
catálogo, convertida para texto pelo motor de parâmetros. A integração passou
com 394 testes offline e foi aprovada fisicamente no monitor principal. As
quatro opções do MODE foram traduzidas corretamente para `STANDARD`, `JUMBO`,
`ENHANCED` e `PIEZO`, enquanto `BODY`, `TOP` e `VOLUME` permaneceram
independentes. O AC SIM coexistiu com RC-BOOST e FAT BOOST sem colisões. O
log final não inclui duas instâncias simultâneas do AC SIM, reordenação ou
bypass explícito; essa limitação de cobertura permanece documentada.

A Fase 32 acrescenta o `DYN / GATE 3` e o primeiro codec que reconstrói o
`float32` completo transmitido pelo comando `0x1C`:

```text
THRESHOLD → inteiro 0–100, seletor 0
RATIO     → inteiro 0–100, seletor 1
ATTACK    → 1–500 ms, seletor 2
RELEASE   → 10–10000 ms, seletor 3
HOLD      → 0–1000 ms, seletor 4
```

O payload físico ocupa oito nibbles nos índices `55–62`. O novo codec
`float32_nibbles_v1` preserva valores como `5001`, `5037` e `6037`, que seriam
arredondados incorretamente pelo codec histórico de quatro nibbles. O monitor
continua genérico e apresenta tempos abaixo de `1000 ms` em milissegundos; a
partir desse limite, converte para segundos com uma casa decimal, como
`RELEASE: 5,0 s`. Foram preservadas 58 fixtures físicas dos slots humanos 1 e
2. A integração passou com 401 testes offline e foi aprovada fisicamente no
monitor principal. O log confirmou valores contínuos de THRESHOLD e RATIO,
ATTACK em milissegundos, RELEASE atravessando a apresentação entre `ms` e `s`,
HOLD chegando a `1,0 s`, coexistência com os demais modelos DYN e isolamento
entre duas instâncias de GATE 3.

Com essa aprovação, os **14 modelos da classe DYN** e seus **47 parâmetros**
estão catalogados e validados. DYN é a primeira classe de efeitos concluída
integralmente no projeto.

A Fase 33 inicia a classe `FREQ` com o `FREQ / Filter` e introduz o primeiro
parâmetro de domínio condicionado do projeto:

```text
STEP 1 → inteiro 0–100, seletor 0
STEP 2 → inteiro 0–100, seletor 1
STEP 3 → inteiro 0–100, seletor 2
STEP 4 → inteiro 0–100, seletor 3
RATE   → seletor 4, domínio dependente de SYNC
SYNC   → booleano, seletor 5
```

Com `SYNC` desligado, `RATE` é numérico `0–100` e a pedaleira redefine
implicitamente o valor para `10` ao entrar nesse domínio. Com `SYNC` ligado,
`RATE` usa onze divisões rítmicas (`1/1` até `1/16`) nos valores físicos
`0–10` e a pedaleira redefine implicitamente para `1/4` (`wire 4`). Essas
redefinições não chegam como mensagens `RATE` separadas: o estado do monitor é
derivado de uma regra declarativa catalogada e marcado internamente como
`derived_device_rule`, sem fabricar evento USB. Foram preservadas 55 fixtures
físicas nos slots humanos 1 e 2. A Fase 33 também comprovou que os índices
`41–42` do envelope `0x1C` não são o `class_id` estrutural: FILTER/FREQ transmite
`00 00` embora a classe estrutural FREQ seja `1`; a identidade continua vindo
da cadeia atual.


A validação física da Fase 33 foi aprovada no monitor principal com o FILTER no
slot humano 2 ao lado de `DYN / COMP1`. STEP 1–4 e RATE numérico atualizaram de
forma independente. Ao receber somente `SYNC = ON`, o monitor derivou
corretamente `RATE: 1/4`; as mudanças seguintes exibiram as divisões rítmicas
observadas e, ao receber somente `SYNC = OFF`, o monitor derivou corretamente
`RATE: 10`. A coexistência DYN/FREQ permaneceu estável, confirmando também a
correção da interpretação dos índices `41–42` do envelope `0x1C`.

O gerenciador flexível de escrita continua disponível em:

```powershell
python -m tools.experiments.manage_effect_chain
```

Ele permite adicionar, substituir e excluir efeitos nos slots internos de
`1` a `12`.


A Fase 34 adiciona o `FREQ / Octaver` usando somente a infraestrutura genérica
já validada:

```text
LOW OCT  → inteiro 0–100, seletor 0
HIGH OCT → inteiro 0–100, seletor 1
DRY      → inteiro 0–100, seletor 2
```

As capturas individuais, combinada e short corrigida confirmam os três
seletores, o codec `upper_float32_nibbles_v1` e os slots humanos 1 e 2. Foram
preservadas 24 fixtures físicas. A primeira short havia sido feita novamente
no slot humano 1 e foi explicitamente excluída da evidência de segundo slot; a
captura corrigida com bytes de slot `00 01` é a fonte válida. Nenhuma alteração
do decoder, codec ou monitor foi necessária. A validação física foi aprovada no
monitor principal: o OCTAVER respondeu no slot humano 2 ao lado de DYN / COMP1,
manteve LOW OCT/HIGH OCT/DRY após bypass OFF/ON e coexistiu com FILTER. Duas
instâncias simultâneas mantiveram estados independentes e uma terceira instância
foi validada mais adiante na cadeia, sem contaminar as anteriores.


A Fase 35 adiciona o `FREQ / Dual Melody` e comprova pela primeira vez um
intervalo numérico negativo no protocolo de parâmetros:

```text
HIGH PITCH → inteiro 0–24, seletor 0
LOW PITCH  → inteiro -24–0, seletor 1
DRY        → inteiro 0–100, seletor 2
HI VOL     → inteiro 0–100, seletor 4
LOW VOL    → inteiro 0–100, seletor 5
```

`LOW PITCH` não usa índice deslocado: `-24`, `-12` e `-1` aparecem nas
respostas físicas como float32 negativos reais e são decodificados pelo mesmo
`upper_float32_nibbles_v1`. Foram preservadas 40 fixtures físicas nos slots
humanos 1 e 2. O seletor 3 não aparece nas respostas device->host e não é
preenchido artificialmente. As capturas também mostram assimetria direcional
nos seletores de HI VOL/LOW VOL em mensagens host->device; como esta fase é
somente leitura, escrita fica explicitamente fora do escopo até pesquisa
específica. A validação física no monitor foi aprovada, incluindo valores
negativos, controles independentes, bypass e múltiplas instâncias sem
contaminação de estado.



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

As definições portáteis ficam em `catalog/effects/`. A fachada histórica
`tools/commands/effect_catalog.py` carrega esses JSONs sem quebrar os comandos
antigos. Detalhes do protocolo continuam em `docs/protocol_findings.md`.

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
| `0x1C` | 70 bytes | atualização ao vivo de parâmetro catalogado |

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

Estado após a preservação do M-BOOST/GAIN (Fase 22):

```text
316 testes executados
316 testes aprovados
```

Também é usado:

```powershell
python -m compileall tools tests
git diff --check
```

## Ferramentas principais

### Monitor ao vivo

```powershell
python -m tools.commands.matribox_monitor
```

Mostra preset, nome, etiqueta e efeitos; acompanha mudanças de ordem e
liga/desliga em tempo real.

### Validar parâmetros catalogados

```powershell
python -m tools.experiments.validate_effect_parameters_live
```

Usa o mesmo motor genérico do monitor, mostra efeito, parâmetro, valor, slot,
posição visual, perfil e codec. Não envia alterações.

O validador histórico específico do M-BOOST permanece disponível em:

```powershell
python -m tools.experiments.validate_mboost_gain_live
```

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

### Solicitar dump de preset

```powershell
python -m tools.commands.request_preset_dump
```

## Validadores físicos

Os validadores abaixo são evidências reproduzíveis das descobertas já
confirmadas na pedaleira. Eles não são executados pela suíte offline.

```text
tools/experiments/validate_live_preset_monitor.py
tools/experiments/validate_effect_parameters_live.py
tools/experiments/validate_mboost_gain_live.py
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
├── catalog/            # classes, efeitos, parâmetros, perfis e codecs JSON
├── data/
│   └── fixtures/       # amostras mínimas usadas pelos testes
├── docs/               # protocolo e continuidade
├── tests/              # regressão offline
└── tools/
    ├── catalog/        # carregamento e validação do JSON
    ├── parameters/     # decoder, codecs e estado genérico
    ├── commands/       # protocolo reutilizável e monitor
    └── experiments/    # validadores físicos preservados
```

## Dados gerados e histórico de pesquisa

Dumps, capturas, relatórios e análises produzidos durante novas investigações
são arquivos locais e ficam fora do Git por padrão. Os comandos podem recriar
`data/dumps/` quando necessário, mas essa pasta é ignorada pelo repositório.

Somente amostras pequenas e necessárias para testes de regressão entram em:

```text
data/fixtures/
```

As descobertas confirmadas permanecem consolidadas em
`docs/protocol_findings.md`. O material bruto anterior à limpeza foi preservado
no backup externo da Fase 1 e no histórico anterior à tag
`cleanup-phase1-a8092cd`.

## Segurança

Não são enviados comandos desconhecidos relacionados a:

- firmware;
- restauração de fábrica;
- apagamento em massa;
- escrita em memória desconhecida;
- configurações críticas não reversíveis.

Os testes usam presets dedicados e alterações reversíveis.

## Próxima investigação

A classe DYN permanece encerrada. As Fases 33 (`FREQ / Filter`), 34 (`FREQ /
Octaver`), 35 (`FREQ / Dual Melody`) e 36 (hidratação pelo dump) estão
fisicamente aprovadas. A Fase 37 adiciona `FREQ / Pitch` com HI PITCH, LOW
PITCH, WET, DRY e RANGE, incluindo hidratação dos defaults salvos e LOW PITCH
negativo. A integração física também foi aprovada. O `Harmony D` foi igualmente
aprovado com enums nomeados e múltiplas instâncias. O próximo efeito FREQ pode
ser `Pitch S` ou outro escolhido para a sequência da pesquisa.
Importação de IR e CLONE permanece um subsistema separado de arquivos externos.

## Continuidade entre chats

O ponto oficial de retomada do projeto, incluindo arquitetura, decisões,
histórico das fases, testes e próximos passos, está em:

```text
docs/PROJECT_CONTINUITY.md
```

Esse arquivo deve ser atualizado antes de todo commit que consolide uma nova
funcionalidade aprovada.

## Documentação técnica completa

O histórico detalhado das descobertas, estruturas, exceções, pacotes e
checksums está em:

```text
docs/protocol_findings.md
```

Esse arquivo é a fonte técnica principal da pesquisa.
