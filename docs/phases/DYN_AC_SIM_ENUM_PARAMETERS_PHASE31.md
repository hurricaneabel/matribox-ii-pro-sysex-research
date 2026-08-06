# Fase 31 — DYN / AC SIM e parâmetros enum nomeados

## Objetivo

Integrar `BODY`, `TOP`, `VOLUME` e `MODE` do `DYN / AC SIM`, acrescentando ao
motor genérico o primeiro parâmetro categórico nomeado sem criar tratamento
específico no monitor.

## Capturas controladas

Foram analisadas seis capturas fornecidas em `ac sim.zip`:

```text
acsim_body_capture.pcapng
acsim_top_capture.pcapng
acsim_volume_capture.pcapng
acsim_mode_capture_enhanced - standard - jumbo - enhanced - piezo - standard.pcapng
AC_SIM_ALL_PARAMETERS_SLOT1_UNIQUE_VALUES_AND_BACK.pcapng
AC_SIM_ALL_PARAMETERS_SLOT2_SHORT_VALIDATION_enhanced_standart_enhanced.pcapng
```

## Resultado físico

```text
BODY    → seletor 0, inteiro 0–100
TOP     → seletor 1, inteiro 0–100
VOLUME  → seletor 2, inteiro 0–100
MODE    → seletor 3, enum numérico 0–3
```

O efeito é identificado estruturalmente como:

```text
class_id: 0x00
model_id: 0x01
secondary_selector: 0x01
```

Todos os parâmetros usam o perfil `effect_parameter_response_1c_v1`, o codec
`upper_float32_nibbles_v1`, marcador/tipo `01 01` e o endereço opaco `01 04`.
A identidade do efeito continua vindo da cadeia atual do slot.

## MODE

A pedaleira inicia o AC SIM em `ENHANCED`. Como o estado inicial não transmite
um evento, a sequência física informada e executada foi:

```text
ENHANCED → STANDARD → JUMBO → ENHANCED → PIEZO → STANDARD
```

Os eventos recebidos foram `0, 1, 2, 3, 0`, confirmando:

```text
0 → STANDARD
1 → JUMBO
2 → ENHANCED
3 → PIEZO
```

O MODE não exige codec novo. Os valores físicos são inteiros no mesmo formato
dos demais controles; a apresentação humana vem de `choices` declaradas no
JSON do parâmetro.

## Fixtures preservadas

Foram preservadas 30 respostas SysEx físicas únicas em:

```text
tests/fixtures/ac_sim_parameters/
```

Distribuição:

```text
slot 1: 22 fixtures
slot 2:  8 fixtures
```

A captura combinada confirmou `BODY 51`, `TOP 52`, `VOLUME 53` e
`MODE ENHANCED`, seguidos do retorno para `50/50/50/STANDARD`. A captura curta
repetiu os quatro seletores no slot interno humano 2.

## Arquitetura genérica acrescentada

`ParameterDefinition` passou a carregar um mapeamento imutável de escolhas
numéricas para rótulos. O loader exige, para `value_type: enum`:

- lista `choices` não vazia;
- valores inteiros e únicos;
- rótulos não vazios e únicos;
- valores dentro do `range` e alinhados ao `step`.

O codec numérico arredonda e valida o valor físico, procura o rótulo no
catálogo e entrega ao restante do sistema uma string. Assim, o monitor apenas
exibe `MODE: ENHANCED`, sem conhecer AC SIM ou os nomes das opções. Valores
não catalogados são rejeitados.

## Catálogo

O catálogo foi incrementado para `catalog_version: 9`. Agora existem 13
efeitos DYN com parâmetros, 42 controles físicos catalogados e 254 efeitos
ainda pendentes.

## Validação offline

```text
Ran 394 tests
OK
```

A suíte confirma:

- decodificação das 30 fixtures físicas;
- mapeamento `0–3` para os quatro rótulos;
- rejeição de valor enum desconhecido;
- carregamento e validação das `choices`;
- apresentação `MODE: ENHANCED` no monitor;
- reprodução determinística pelo exportador JSON;
- preservação dos slots 1 e 2 e das seis fontes.

Comandos oficiais:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

## Validação física aprovada

O monitor principal reconheceu o AC SIM na mesma cadeia de RC-BOOST e FAT
BOOST e apresentou os quatro parâmetros na ordem do catálogo:

```text
BODY | TOP | VOLUME | MODE
```

As quatro escolhas categóricas foram decodificadas pelo mecanismo genérico:

```text
PIEZO → ENHANCED → JUMBO → STANDARD
```

Isso confirma fisicamente que os valores `3`, `2`, `1` e `0` são traduzidos
pelas `choices` do catálogo, sem tabela específica do AC SIM no monitor.

Os controles contínuos também foram acompanhados independentemente. O log
registrou alterações de VOLUME entre `50` e `51`, TOP entre `49` e `50` e BODY
entre `47`, `48`, `49` e `52`, mantendo o MODE em `STANDARD` e sem modificar os
dois efeitos anteriores da cadeia.

A fase está aprovada para commit. O log final não inclui uma segunda instância
do AC SIM, mudança de posição visual ou bypass explícito. As capturas físicas
nos slots humanos 1 e 2, os testes simulados e a validação ao vivo de todos os
rótulos sustentam a aprovação, mantendo essas ausências como limitações de
cobertura.

## Limitações preservadas

- o valor inicial continua como `aguardando alteração`; o dump estrutural não
  fornece os valores iniciais dos parâmetros;
- a integração permanece somente leitura;
- apenas valores enum explicitamente catalogados são aceitos;
- GATE 3 e seus parâmetros temporais permanecem fora desta fase;
- o log final não cobre duas instâncias do AC SIM, reordenação ou bypass
  explícito.

## Próximo passo exato

1. aplicar o pacote documental de aprovação física;
2. executar novamente os 394 testes, `compileall` e `git diff --check`;
3. adicionar somente os arquivos da Fase 31;
4. criar o commit `feat: add AC SIM enum parameters`;
5. enviar `research/dyn-parameters`;
6. promover o mesmo commit por fast-forward à `main`;
7. iniciar a pesquisa do GATE 3 e de seus parâmetros temporais.
