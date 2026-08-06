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

Três efeitos DYN possuem parâmetros internos catalogados:

```text
M-BOOST | GAIN                     | inteiro 0–100 | seletor 0
COMP1   | SUSTAIN, VOLUME          | inteiro 0–100 | seletores 0 e 1
E-BOOST | GAIN, +3dB, BRIGHT       | inteiro + booleanos | seletores 0, 1 e 2
```

No E-BOOST, `+3dB` e `BRIGHT` usam o mesmo codec numérico dos controles
contínuos, com `0 = desligado` e `1 = ligado`. O `value_type: boolean` do JSON
determina a apresentação humana sem criar um codec específico para botões.

O comando `0x1C` não identifica sozinho o modelo do efeito. O slot recebido é
cruzado com a cadeia estrutural atual; somente então o seletor é interpretado
dentro do efeito correto.

Os outros 264 efeitos permanecem com:

```json
"parameter_catalog_status": "pending",
"parameters": []
```

Nenhum dado de parâmetro é presumido antes de captura e validação física.
