# Fase 25 — DYN / E-BOOST: inteiro e booleanos

## Objetivo

Catalogar os três parâmetros do `DYN / E-BOOST` e validar o primeiro efeito que
combina um controle contínuo com dois interruptores booleanos no mesmo motor
genérico.

Parâmetros confirmados:

```text
GAIN:    0–100
+3dB:    desligado/ligado
BRIGHT:  desligado/ligado
```

## Capturas controladas

Preset de teste: `56B`.

Fontes Wireshark/USBPcap:

```text
EBOOST_GAIN_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
EBOOST_PLUS3DB_SLOT1_OFF_ON_OFF_ON_OFF.pcapng
EBOOST_BRIGHT_SLOT1_OFF_ON_OFF_ON_OFF.pcapng
EBOOST_SWITCHES_SLOT1_OFFOFF_ONOFF_ONON_OFFON_OFFOFF.pcapng
EBOOST_SLOT2_GAIN_AND_SWITCHES_VALIDATION.pcapng
```

Foram preservadas 19 respostas SysEx físicas únicas em:

```text
tests/fixtures/e_boost_parameters/
```

A captura combinada confirmou que `+3dB` e `BRIGHT` geram mensagens
independentes, sem compartilhamento de bits ou estado agregado.

## Estrutura confirmada

Os três parâmetros reutilizam o perfil existente:

```text
comando                  0x1C
tamanho                  70 bytes
slot interno             índices 39–40, zero-based
seletor do parâmetro     índice 48
valor                    índices 59–62
marcador/tipo            índices 63–64 = 01 01
perfil                    effect_parameter_response_1c_v1
codec                     upper_float32_nibbles_v1
```

Seletores:

```text
GAIN    → 0
+3dB    → 1
BRIGHT  → 2
```

O GAIN usa a faixa inteira 0–100 já conhecida. Os interruptores usam o mesmo
codec numérico:

```text
desligado / false / 0 → 00 00 00 00
ligado    / true  / 1 → 08 00 03 0F
```

Não foi necessário criar um codec exclusivo para botões. O catálogo declara
`value_type: boolean`, e a camada de apresentação converte `False/True` em
`desligado/ligado`.

Os slots internos humanos 1 e 2 foram confirmados.

## Implementação

Arquivos principais:

```text
catalog/effects/dyn/005_e_boost.json
tools/parameters/codecs.py
tools/parameters/decoder.py
tools/commands/preset_monitor_core.py
tests/fixtures/e_boost_parameters/
tests/test_effect_parameters.py
tests/test_effect_catalog_json.py
```

O codec numérico agora aceita três resultados conforme o `value_type`:

```text
integer  → inteiro validado pela faixa e passo
number   → número
boolean  → somente 0 ou 1, convertido para False ou True
```

O monitor e o validador exibem booleanos em português:

```text
+3dB: ligado
BRIGHT: desligado
```

A identidade do efeito continua vindo da cadeia estrutural atual. O endereço
opaco `01 04` também aparece no E-BOOST e não pode ser tratado como model_id.

## Validação offline

```text
Ran 356 tests
OK
```

A regressão cobre:

- 19 fixtures físicas únicas do E-BOOST;
- GAIN nos slots internos 1 e 2;
- seletores 1 e 2 para os interruptores;
- conversão física 0/1 para `False/True`;
- rejeição de valor booleano diferente de 0 ou 1;
- exibição `desligado/ligado`;
- independência de GAIN, +3dB e BRIGHT no mesmo slot;
- exportação reproduzível do catálogo JSON;
- manutenção dos 49 fixtures anteriores de M-BOOST e COMP1.

## Validação física da integração

A integração foi aprovada fisicamente no monitor principal com o preset `56B`.
O dump estrutural exibiu inicialmente:

```text
DYN / COMP1 — ligado
   SUSTAIN: aguardando alteração
   VOLUME: aguardando alteração
DYN / E-BOOST — ligado
   GAIN: aguardando alteração
   +3dB: aguardando alteração
   BRIGHT: aguardando alteração
```

O teste ao vivo confirmou:

- GAIN atualizado como inteiro em tempo real;
- +3dB apresentado como `ligado/desligado`;
- BRIGHT apresentado como `ligado/desligado`;
- atualização independente dos três parâmetros;
- bypass do E-BOOST sem corromper o estado de parâmetros;
- duas instâncias simultâneas de E-BOOST com valores separados;
- uma instância com `GAIN: 31`, `+3dB: desligado` e `BRIGHT: desligado`
  enquanto a outra manteve `GAIN: 21`, `+3dB: desligado` e
  `BRIGHT: desligado`;
- coexistência com COMP1 e efeitos de outras classes sem colisão de seletores;
- substituições estruturais em outro slot sem atribuir parâmetros ao efeito
  incorreto.

O monitor permaneceu somente leitura durante toda a validação.

## Estado

```text
capturas controladas: aprovadas
fixtures offline: aprovadas
catálogo e codec booleano: aprovados offline
monitor ao vivo: aprovado fisicamente
múltiplas instâncias: aprovadas fisicamente
Fase 25: pronta para consolidação
```
