# Fase 29 — DYN / AC-BOOST e BB-BOOST

## Objetivo

Catalogar os quatro parâmetros contínuos de `DYN / AC-BOOST` e
`DYN / BB-BOOST` sem criar parsers específicos e preservando o fluxo genérico:

```text
cadeia estrutural atual
  → efeito real do slot
  → seletor do parâmetro
  → perfil 0x1C
  → codec numérico compartilhado
  → EffectParameterEvent
  → estado independente por slot
```

## Capturas controladas

Foram analisadas seis capturas por efeito.

### AC-BOOST

```text
acboost_gain_cap.pcapng
acboost_volume_cap.pcapng
acboost_bass_cap.pcapng
acboost_treble_cap.pcapng
acboost_unique_values_and_back.pcapng
acboost_short_validation.pcapng
```

### BB-BOOST

```text
bb-boost_gain_cap.pcapng
bb-boost_volume_cap.pcapng
bb-boost_bass_cap.pcapng
bb-boost_treble_cap.pcapng
bb-boost_unique_values.pcapng
bb-boost_slot2_short_validation.pcapng
```

As capturas individuais usaram a sequência reduzida
`0 → 1 → 50 → 99 → 100 → 50`. As capturas combinadas usaram valores exclusivos
`51`, `52`, `53` e `54`, seguidos do retorno para `50`. A validação curta
repetiu os mesmos quatro seletores no slot interno humano 2.

## Resultado físico do protocolo

Os dois efeitos compartilham a mesma organização:

```text
GAIN    → seletor 0
VOLUME  → seletor 1
BASS    → seletor 2
TREBLE  → seletor 3
```

Todos os parâmetros são inteiros de `0` a `100`, passo `1`.

Também foram confirmados:

```text
comando                    0x1C
tamanho                    70 bytes
slot interno               message[39:41]
seletor                    message[48]
valor                      message[59:63]
marcador/tipo              01 01
endereço opaco observado   01 04
perfil                     effect_parameter_response_1c_v1
codec                      upper_float32_nibbles_v1
slots humanos observados   1 e 2
```

O endereço `01 04` continua compartilhado por vários efeitos e não representa
o `model_id`. A identidade deve permanecer vinculada ao efeito real da cadeia
no slot recebido.

## Fixtures preservadas

Foram preservadas 32 respostas SysEx únicas por efeito:

```text
tests/fixtures/ac_boost_parameters/  → 32 fixtures
tests/fixtures/bb_boost_parameters/  → 32 fixtures
```

Por efeito:

```text
slot humano 1 → 24 fixtures
slot humano 2 →  8 fixtures
```

Cada parâmetro possui no slot 1 os pontos `0`, `1`, `50`, `99`, `100` e seu
valor exclusivo entre `51` e `54`. No slot 2, cada parâmetro possui `50` e seu
valor exclusivo.

As respostas auxiliares de 54 bytes observadas nas capturas de GAIN e de
validação curta foram documentadas e continuam ignoradas pelo parser de
parâmetros. No BB-BOOST, o evento adicional `VOLUME = 50` antes de `52 → 50`
foi registrado no manifesto, sem duplicar a fixture do mesmo estado.

## Integração

Os arquivos:

```text
catalog/effects/dyn/006_ac_boost.json
catalog/effects/dyn/007_bb_boost.json
```

agora declaram `capabilities: ["parameters"]` e
`parameter_catalog_status: "physically_validated"`.

A migração reproduzível recebeu sementes genéricas compartilhadas pelos dois
boosts. O catálogo foi incrementado para `catalog_version: 7`.

Não houve alteração no decoder, no codec, no perfil de protocolo, no estado ou
no monitor. A apresentação esperada é produzida diretamente pelo catálogo:

```text
DYN / AC-BOOST — ligado
   GAIN: aguardando alteração
   VOLUME: aguardando alteração
   BASS: aguardando alteração
   TREBLE: aguardando alteração

DYN / BB-BOOST — ligado
   GAIN: aguardando alteração
   VOLUME: aguardando alteração
   BASS: aguardando alteração
   TREBLE: aguardando alteração
```

## Validação offline

A suíte candidata passou:

```text
Ran 382 tests
OK
```

A cobertura acrescentada verifica:

- as 64 fixtures físicas pelo contexto do efeito;
- seletores `0`, `1`, `2` e `3` nos dois modelos;
- quatro estados independentes em cada efeito;
- apresentação no monitor na ordem da tela;
- atualização simulada no slot interno humano 2;
- manifestos, fontes, slots e capturas combinadas;
- reprodução dos dois efeitos pelo exportador JSON;
- redução dos efeitos pendentes de 260 para 258.

Também passaram:

```text
python -m compileall tools tests
validação de todos os arquivos JSON
git diff --check no pacote candidato
```

## Estado físico

A descoberta dos parâmetros e a equivalência do protocolo estão fisicamente
confirmadas pelas capturas nos slots humanos 1 e 2.

A integração também foi aprovada no monitor principal com os dois efeitos
simultâneos na cadeia.

Valores finais observados:

```text
AC-BOOST
GAIN 33 | VOLUME 54 | BASS 43 | TREBLE 58

BB-BOOST
GAIN 26 | VOLUME 43 | BASS 66 | TREBLE 30
```

Os quatro parâmetros de cada efeito foram atualizados separadamente. Enquanto
os controles do BB-BOOST eram alterados, os valores do AC-BOOST permaneceram
inalterados. O mesmo ocorreu no sentido inverso. O monitor também acompanhou o
bypass independente dos dois efeitos e preservou os valores já recebidos ao
desligar e religar cada bloco.

O log de aprovação não contém duas instâncias simultâneas do mesmo modelo nem
uma troca explícita de posição visual. As capturas nos slots humanos 1 e 2 e o
isolamento simultâneo entre AC-BOOST e BB-BOOST confirmam a resolução genérica
por slot. Essa ausência não bloqueia a consolidação da fase.

## Limitações preservadas

- o valor inicial continua aparecendo como `aguardando alteração`;
- a mensagem `0x1C` isolada não identifica AC-BOOST ou BB-BOOST;
- seletores iguais possuem significados diferentes em outros efeitos;
- o monitor permanece somente leitura;
- mensagens auxiliares não `0x1C` continuam ignoradas.

## Próximo passo exato

1. aplicar esta atualização documental sobre a implementação candidata;
2. executar novamente os 382 testes, `compileall` e `git diff --check`;
3. adicionar somente os arquivos da Fase 29;
4. criar o commit `feat: add AC-BOOST and BB-BOOST parameters`;
5. enviar `research/dyn-parameters`;
6. promover o mesmo commit por fast-forward à `main`;
7. iniciar uma fase própria para o AC SIM e seu parâmetro categórico `MODE`.
