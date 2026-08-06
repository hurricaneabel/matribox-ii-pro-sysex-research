# Fase 23A — Catálogo JSON multiplataforma

## Objetivo

Migrar os dados estáticos de classes e efeitos que estavam codificados em
`tools/commands/effect_catalog.py` para um formato JSON versionado, legível por
Python, Kotlin/Android, desktop e ferramentas futuras, sem alterar o protocolo
MIDI nem quebrar a API histórica do projeto.

## Resultado

A migração preservou exatamente:

```text
16 classes
267 efeitos/posições
menu de cada classe e efeito
nome exibido
class_id
model_id
secondary_selector
```

Cada efeito possui agora um arquivo próprio em:

```text
catalog/effects/<classe>/
```

Cada classe possui um `index.json` que define sua identidade e a ordem dos
arquivos de efeito. O manifesto geral fica em `catalog/catalog.json`.

## Primeiro parâmetro no catálogo

`DYN / M-BOOST / GAIN` foi registrado como o primeiro parâmetro fisicamente
validado:

```text
faixa: 0–100
perfil: effect_parameter_response_1c_v1
codec: upper_float32_nibbles_v1
fixtures físicas: 27
slots observados ao vivo: 2, 8, 10 e 12
múltiplas instâncias: aprovado
reordenação visual: independente
```

Os outros 266 efeitos permanecem explicitamente sem parâmetros presumidos:

```json
"parameter_catalog_status": "pending",
"parameters": []
```

## Arquitetura criada

```text
catalog/
├── catalog.json
├── README.md
├── schemas/
│   ├── catalog.schema.json
│   ├── class-index.schema.json
│   ├── effect.schema.json
│   ├── protocol-profile.schema.json
│   └── value-codec.schema.json
├── effects/
│   └── <16 classes>/<267 efeitos>.json
├── protocol_profiles/
│   └── effect_parameter_response_1c_v1.json
└── value_codecs/
    └── upper_float32_nibbles_v1.json

tools/catalog/
├── models.py
├── loader.py
└── errors.py
```

O catálogo separa três responsabilidades:

```text
efeito/parâmetro   significado humano e identidade
perfil             localização dos campos na mensagem SysEx
codec              conversão entre valor humano e bytes
```

## Compatibilidade preservada

`tools/commands/effect_catalog.py` tornou-se uma fachada. Os imports antigos
continuam disponíveis:

```python
EFFECT_CLASSES
DYN_MODELS
AMP_CLASS_ID
EffectClass
EffectModel
find_effect_class
find_effect_model
```

Internamente, todos esses valores agora são derivados dos JSONs. O monitor e os
comandos existentes não precisaram mudar de API.

## Migração reproduzível

A ferramenta abaixo exporta as classes carregadas para o mesmo formato:

```powershell
python -m tools.migrations.export_effect_catalog_to_json --output catalog --force
```

Ela substitui somente `catalog.json` e `catalog/effects/`. Schemas, perfis e
codecs são contratos versionados e são preservados.

O snapshot abaixo conserva o estado exato do catálogo Python anterior à
migração:

```text
tests/fixtures/effect_catalog/legacy_catalog_snapshot.json
```

Os testes comparam o catálogo JSON contra esse snapshot registro por registro.

## Compatibilidade entre plataformas

O catálogo não contém:

- caminhos absolutos do Windows;
- objetos `pickle`;
- classes Python serializadas;
- referências ao ambiente virtual;
- arquivos binários grandes.

Os caminhos internos usam `/`, são relativos e podem ser empacotados como
recursos em Android ou desktop.

## Validação offline

```text
Testes específicos da migração: 12
Suíte completa: 328
Resultado: OK
```

Também foram aprovados:

```powershell
python -m compileall tools tests
python -m json.tool catalog/catalog.json

git diff --check
```

Esta fase não envia mensagens MIDI e não exige nova validação física. O
comportamento físico do M-BOOST permanece coberto pela Fase 22.

## Próximo passo

A próxima etapa recomendada é a **Fase 23B — motor genérico de parâmetros**:

1. criar um evento genérico de parâmetro;
2. implementar o codec `upper_float32_nibbles_v1` como componente reutilizável;
3. interpretar o perfil `effect_parameter_response_1c_v1` sem lógica exclusiva
   do M-BOOST;
4. manter `mboost_gain.py` como compatibilidade até a equivalência ser provada;
5. validar o motor genérico contra as 27 fixtures da Fase 22;
6. somente depois integrar parâmetros ao monitor principal.
