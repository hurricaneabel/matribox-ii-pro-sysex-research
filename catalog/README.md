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

## Estado inicial da Fase 23A

Os 16 índices de classe e os 267 efeitos foram exportados do catálogo Python
histórico. Todos preservam menu, nome, ID de classe, ID de modelo e seletor
secundário.

Somente `DYN / M-BOOST` possui parâmetro interno catalogado nesta fase:

```text
GAIN | 0–100 | comando 0x1C | leitura física aprovada
```

Os outros efeitos permanecem com:

```json
"parameter_catalog_status": "pending",
"parameters": []
```

Nenhum dado de parâmetro é presumido antes de captura e validação física.
