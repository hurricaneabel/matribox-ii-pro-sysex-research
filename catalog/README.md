# Catálogo JSON multiplataforma

Esta pasta contém os dados estáticos confirmados da Sonicake Matribox II Pro.
Ela foi criada para ser consumida pelo laboratório Python atual e, futuramente,
por aplicações Kotlin para Android e desktop.

## Separação de responsabilidades

- `catalog.json`: manifesto e versões do catálogo;
- `effects/<classe>/index.json`: identidade da classe e ordem dos efeitos;
- `effects/<classe>/*.json`: identidade estrutural e parâmetros de cada efeito;
- `protocol_profiles/`: localização dos campos em mensagens SysEx confirmadas;
- `value_codecs/`: descrição portátil da conversão valor/bytes;
- `schemas/`: contratos JSON Schema Draft 2020-12.

Os arquivos não contêm caminhos absolutos, objetos Python serializados ou
outros dados exclusivos do Windows.

## Estado atual do catálogo

Os 16 índices de classe e os 267 efeitos foram exportados do catálogo Python
histórico. Todos preservam menu, nome, ID de classe, ID de modelo e seletor
secundário.

Treze efeitos DYN possuem parâmetros internos catalogados, totalizando 42
controles físicos:

```text
M-BOOST | GAIN                              | inteiro 0–100 | seletor 0
COMP1   | SUSTAIN, VOLUME                   | inteiro 0–100 | seletores 0 e 1
COMP2   | SUSTAIN, ATTACK, VOLUME, CLIPPING | inteiro 0–100 | seletores 0–3
COMP3   | THRESHOLD, RATIO, VOLUME, ATTACK, RELEASE, TONE, BLEND | inteiro 0–100 | seletores 0–6
AC-BOOST| GAIN, VOLUME, BASS, TREBLE         | inteiro 0–100 | seletores 0–3
BB-BOOST| GAIN, VOLUME, BASS, TREBLE         | inteiro 0–100 | seletores 0–3
RC-BOOST| GAIN, VOLUME, BASS, TREBLE         | inteiro 0–100 | seletores 0–3
FAT BOOST| BASS, TREBLE, VOLUME, LOW CUT      | inteiros + booleano | seletores 0–3
E-BOOST | GAIN, +3dB, BRIGHT                | inteiro + booleanos | seletores 0–2
AC WOODY| SHAPE                             | inteiro 0–100 | seletor 0
GATE 1  | THRESHOLD                         | inteiro 0–100 | seletor 0
GATE 2  | THRESHOLD, ATTACK, RELEASE         | inteiro 0–100 | seletores 0–2
AC SIM  | BODY, TOP, VOLUME, MODE             | inteiros + enum nomeado | seletores 0–3
```

No AC SIM, `MODE` usa os mesmos valores numéricos do codec compartilhado,
mas o catálogo converte `0–3` para `STANDARD`, `JUMBO`, `ENHANCED` e `PIEZO`.
O monitor permanece genérico: nenhum rótulo foi codificado diretamente nele.

No E-BOOST, `+3dB` e `BRIGHT` usam o mesmo codec numérico dos controles
contínuos, com `0 = desligado` e `1 = ligado`. O `value_type: boolean` do JSON
determina a apresentação humana sem criar um codec específico para botões.

O comando `0x1C` não identifica sozinho o modelo do efeito. O slot recebido é
cruzado com a cadeia estrutural atual; somente então o seletor é interpretado
dentro do efeito correto.

Os outros 254 efeitos permanecem com:

```json
"parameter_catalog_status": "pending",
"parameters": []
```

Nenhum dado de parâmetro é presumido antes de captura e validação física.
