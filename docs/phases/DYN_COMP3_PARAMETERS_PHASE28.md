# Fase 28 — DYN / COMP3 com sete parâmetros

## Objetivo

Catalogar os sete controles contínuos do `DYN / COMP3` usando o motor genérico
de parâmetros já consolidado:

```text
THRESHOLD  0–100
RATIO      0–100
VOLUME     0–100
ATTACK     0–100
RELEASE    0–100
TONE       0–100
BLEND      0–100
```

Esta é a primeira integração com sete parâmetros independentes no mesmo efeito.
Ela testa a expansão do catálogo e do estado por slot sem criar parser, perfil,
codec ou lógica de monitor específicos para o COMP3.

## Capturas controladas

Preset de teste: `56B`.

Capturas individuais no slot interno humano 1:

```text
comp3_threshold_cap.pcapng
comp3_ratio_cap.pcapng
comp3_volume_cap.pcapng
comp3_attack_cap.pcapng
comp3_release_cap.pcapng
comp3_tone_cap.pcapng
comp3_blend_cap.pcapng
```

Cada captura individual percorreu os pontos físicos:

```text
0 → 1 → 2 → 10 → 25 → 50 → 75 → 99 → 100 → 50
```

Captura combinada no slot interno humano 1:

```text
COMP3_ALL_PARAMETERS_SLOT1_UNIQUE_VALUES_AND_BACK.pcapng
```

Sequência observada:

```text
THRESHOLD  50 → 51 → 50
RATIO      50 → 52 → 50
VOLUME     50 → 53 → 50
ATTACK     50 → 54 → 50
RELEASE    50 → 55 → 50
TONE       50 → 56 → 50
BLEND      50 → 57 → 50
```

Validação combinada no slot interno humano 2:

```text
COMP3_ALL_PARAMETERS_SLOT2_SHORT_VALIDATION.pcapng
```

A mesma identificação exclusiva foi repetida no segundo slot, com retorno a
50 após cada parâmetro.

## Estrutura confirmada

Os sete controles reutilizam o contrato estável:

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
THRESHOLD  → 0
RATIO      → 1
VOLUME     → 2
ATTACK     → 3
RELEASE    → 4
TONE       → 5
BLEND      → 6
```

O endereço `01 04` continua compartilhado por efeitos DYN diferentes. A
identidade do COMP3 é obtida da cadeia estrutural atual no slot e não desse
endereço.

## Observações das capturas

A captura individual de ATTACK repetiu `99 → 100` antes do retorno a 50. A
captura de TONE emitiu o valor 0 duas vezes. Essas repetições são eventos
válidos da pedaleira e não introduzem ambiguidade; apenas uma resposta física
de cada combinação slot/parâmetro/valor foi preservada como fixture.

## Fixtures físicas

Foram preservadas 84 respostas SysEx recebidas e únicas por combinação de
slot, parâmetro e valor:

```text
tests/fixtures/comp3_parameters/
```

Distribuição:

```text
slot interno humano 1  → 70 fixtures
slot interno humano 2  → 14 fixtures
```

No slot 1, cada parâmetro possui os nove pontos da captura individual e seu
valor exclusivo da captura combinada. No slot 2, cada parâmetro possui o valor
50 e seu valor exclusivo entre 51 e 57.

## Integração

O catálogo agora declara:

```text
DYN / COMP3
├── THRESHOLD  seletor 0
├── RATIO      seletor 1
├── VOLUME     seletor 2
├── ATTACK     seletor 3
├── RELEASE    seletor 4
├── TONE       seletor 5
└── BLEND      seletor 6
```

Todos são inteiros de 0 a 100, passo 1. O monitor principal e o estado por slot
já são orientados pelo catálogo; portanto, não houve alteração no núcleo do
decoder ou no monitor.

A migração reproduzível recebeu `COMP3_PARAMETER_SEEDS` e o catálogo foi
incrementado para `catalog_version: 6`.

## Validação offline

A suíte completa candidata passou:

```text
Ran 376 tests
OK
```

Cobertura acrescentada:

- leitura das 84 fixtures físicas pelo efeito real da cadeia;
- ordem dos seletores `0` a `6`;
- sete estados independentes no mesmo slot;
- apresentação dos sete controles na ordem da tela;
- atualização simulada dos sete parâmetros no slot interno humano 2;
- preservação das fontes e observações no manifesto de evidências;
- reprodução do COMP3 pelo exportador do catálogo;
- redução dos efeitos ainda pendentes de 261 para 260.

Também passaram `python -m compileall tools tests`, validação dos arquivos JSON
e verificação de whitespace do pacote candidato.

## Estado físico

A integração foi aprovada no monitor principal com a pedaleira real.

A primeira instância de COMP3 foi reconhecida com os sete controles na ordem
do catálogo e recebeu valores independentes durante a sessão:

```text
THRESHOLD  20
RATIO      45
VOLUME     66
ATTACK     59
RELEASE    59
TONE       62
BLEND      59
```

A cadeia foi ampliada progressivamente com efeitos DRV, FREQ, EQ, MOD, DLY e
RVB, e os sete valores da primeira instância permaneceram preservados.

Depois foi criada uma segunda instância simultânea de COMP3 em outro slot. O
monitor manteve estados separados:

```text
COMP3 A  THRESHOLD 20 | RATIO 45 | VOLUME 66 | ATTACK 59
         RELEASE 59   | TONE 62  | BLEND 59

COMP3 B  THRESHOLD 25 | RATIO 8  | VOLUME 30 | ATTACK 26
         RELEASE 24   | TONE 30  | BLEND 33
```

Isso aprova a resolução pelo efeito real e pelo slot interno mesmo quando duas
instâncias reutilizam os seletores `0` a `6`. O log fornecido não registra uma
troca explícita de posição entre as duas instâncias, mas confirma preservação
de estado durante mudanças estruturais e isolamento completo entre slots.

Estado da fase: `physically_validated`.

## Próximo passo exato

1. executar novamente os 376 testes, `compileall` e `git diff --check`;
2. revisar o escopo do `git add` para conter apenas a Fase 28 e sua aprovação;
3. criar o commit estável na branch `research/dyn-parameters`;
4. enviar a branch e promover o mesmo commit por fast-forward à `main`;
5. manter as capturas de AC-BOOST, BB-BOOST e AC SIM fora deste commit;
6. iniciar a Fase 29 com AC-BOOST e BB-BOOST juntos;
7. tratar o AC SIM em fase própria, pois o parâmetro MODE exige mapeamento
   categórico entre valores físicos e os rótulos STANDARD, JUMBO, ENHANCED e
   PIEZO.
