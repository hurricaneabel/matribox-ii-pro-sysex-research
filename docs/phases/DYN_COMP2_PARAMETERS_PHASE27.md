# Fase 27 — DYN / COMP2 com quatro parâmetros

## Objetivo

Catalogar os quatro controles contínuos do `DYN / COMP2` sem criar parser,
perfil ou codec específico por efeito:

```text
SUSTAIN   0–100
ATTACK    0–100
VOLUME    0–100
CLIPPING  0–100
```

A fase amplia o teste do motor genérico: é o primeiro efeito catalogado com
quatro parâmetros contínuos independentes no mesmo slot.

## Capturas controladas

Preset de teste: `56B`.

Capturas individuais no slot interno humano 1:

```text
COMP2_SUSTAIN_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
COMP2_ATTACK_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
COMP2_VOLUME_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
COMP2_CLIPPING_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
```

Captura combinada no slot interno humano 1:

```text
COMP2_ALL_PARAMETERS_SLOT1_50_TO_51_52_53_54_AND_BACK.pcapng
```

Sequência física observada:

```text
SUSTAIN   50 → 51 → 50
ATTACK    50 → 52 → 50
VOLUME    50 → 53 → 50
CLIPPING  50 → 54 → 5 → 50
```

O valor intermediário `5` em CLIPPING foi um ajuste acidental durante a volta,
mas constitui evidência válida. Ele foi decodificado como inteiro 5, com valor
físico `0A 00 04 00`, e não introduziu ambiguidade na captura.

Validação combinada no slot interno humano 2:

```text
COMP2_ALL_PARAMETERS_SLOT2_SHORT_VALIDATION.pcapng
```

Sequência:

```text
SUSTAIN   50 → 51 → 50
ATTACK    50 → 52 → 50
VOLUME    50 → 53 → 50
CLIPPING  50 → 54 → 50
```

## Estrutura confirmada

Os quatro controles reutilizam o contrato já estável:

```text
comando                  0x1C
tamanho                  70 bytes
slot interno             índices 39–40, zero-based
seletor do parâmetro     índice 48
valor                    índices 59–62
marcador/tipo            índices 63–64 = 01 01
perfil                    effect_parameter_response_1c_v1
codec                     upper_float32_nibbles_v1
endereço opaco            índices 21–22 = 01 04
```

Seletores fisicamente observados:

```text
SUSTAIN   → 0
ATTACK    → 1
VOLUME    → 2
CLIPPING  → 3
```

O endereço `01 04` continua compartilhado por efeitos DYN com modelos
estruturais diferentes. A identidade do COMP2 vem obrigatoriamente da cadeia
atual do slot, não desse endereço.

## Fixtures físicas

Foram preservadas 49 respostas SysEx recebidas e únicas:

```text
tests/fixtures/comp2_parameters/
```

Distribuição:

```text
slot interno humano 1  → 41 fixtures
slot interno humano 2  → 8 fixtures
```

No slot 1, cada parâmetro possui os pontos `0, 1, 2, 10, 25, 50, 75, 99 e
100`. A captura combinada acrescenta `51`, `52`, `53`, `54` e o valor
intermediário `CLIPPING = 5`. No slot 2, cada parâmetro possui o valor 50 e seu
valor de identificação exclusivo.

A captura individual de VOLUME também continha um evento de preparação de
`ATTACK = 50`. Ele foi registrado durante a análise, mas não duplicado como
fixture do VOLUME porque já existe evidência controlada própria para ATTACK.
Respostas auxiliares não `0x1C` continuam fora do conjunto de parâmetros.

## Integração

O catálogo agora declara:

```text
DYN / COMP2
├── SUSTAIN   seletor 0
├── ATTACK    seletor 1
├── VOLUME    seletor 2
└── CLIPPING  seletor 3
```

Todos são inteiros de 0 a 100, passo 1. O monitor principal e o estado por slot
já eram orientados pelo catálogo, portanto não foi necessária alteração no
núcleo do decoder ou no monitor.

A migração reproduzível recebeu `COMP2_PARAMETER_SEEDS` e o catálogo foi
incrementado para `catalog_version: 5`.

## Validação offline

A suíte completa consolidada passou:

```text
Ran 370 tests
OK
```

Cobertura nova:

- leitura das 49 fixtures físicas pelo efeito real da cadeia;
- ordem dos seletores `0, 1, 2, 3`;
- quatro estados independentes no mesmo slot;
- apresentação dos quatro controles na ordem do catálogo;
- atualização simulada no slot interno humano 2;
- preservação documental do valor acidental `CLIPPING = 5`;
- reprodução do COMP2 pelo exportador do catálogo;
- redução dos efeitos ainda pendentes de 262 para 261.

Também passaram `python -m compileall tools tests`, validação dos JSONs e
verificação de whitespace do pacote candidato.

## Estado físico

A integração foi aprovada no monitor principal com a pedaleira real.

A primeira instância de COMP2 foi reconhecida com os quatro controles na ordem
do catálogo e recebeu valores independentes durante a sessão:

```text
SUSTAIN   21
ATTACK    61 → 60
VOLUME    51 → 50
CLIPPING  11 → 10
```

As mudanças de um controle não alteraram os demais. O efeito coexistiu sem
colisão com COMP1 e com substituições estruturais por BB-BOOST, AC-BOOST,
E-BOOST, M-BOOST e COMP3 em outro slot.

Depois foi criada uma segunda instância simultânea de COMP2. O monitor manteve
os estados separados:

```text
COMP2 A  SUSTAIN 21 | ATTACK 61 | VOLUME 51 | CLIPPING 11
COMP2 B  SUSTAIN 21 | ATTACK 60 | VOLUME 50 | CLIPPING 10
```

Isso aprova a resolução pelo efeito real e pelo slot interno, inclusive quando
as duas instâncias reutilizam os mesmos seletores `0`, `1`, `2` e `3`.

Estado da fase: `physically_validated`.

## Próximo passo exato

1. executar novamente os 370 testes, `compileall` e `git diff --check`;
2. revisar o escopo do `git add` para conter apenas a Fase 27 e sua aprovação;
3. criar o commit estável na branch `research/dyn-parameters`;
4. enviar a branch e promover o mesmo commit por fast-forward à `main`;
5. manter o ZIP de capturas do COMP3, AC-BOOST e BB-BOOST fora deste commit;
6. iniciar a próxima fase pela análise do COMP3, deixando os dois boosts para
   uma integração posterior caso compartilhem o mesmo contrato.
