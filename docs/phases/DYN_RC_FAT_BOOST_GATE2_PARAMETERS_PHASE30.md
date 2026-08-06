# Fase 30 — DYN / RC-BOOST, FAT BOOST e GATE 2

## Objetivo

Integrar três efeitos DYN cujos parâmetros reutilizam integralmente o motor
genérico já validado, preservando as capturas físicas e sem adicionar parsers
específicos:

```text
RC-BOOST  → quatro controles contínuos
FAT BOOST → três controles contínuos e um booleano
GATE 2    → três controles contínuos
```

## Capturas controladas

Foram analisadas 17 capturas fornecidas em `dyn.rar`.

### RC-BOOST

```text
rscboost_gain_cap.pcapng
rcboost_volume_cap.pcapng
rcboost_bass_cap.pcapng
rcboost_treble_cap.pcapng
rcboost_short_cap.pcapng
rcboost_unique_values.pcapng
```

### FAT BOOST

```text
fatboost_bass_cap.pcapng
fatboost_treble_cap.pcapng
fatboost_volume_cap.pcapng
fatboost_low_cut_off-on, on-off, off - on, on-off.pcapng
fatboost_unique_value_off_on_off.pcapng
fatboost_short_cap_off_on_off.pcapng
```

### GATE 2

```text
gate2_threshold_cap.pcapng
gate2_attack_cap.pcapng
gate2_release_cap.pcapng
gate2_unique_value.pcapng
gate2_short_capture.pcapng
```

## Resultado físico

### RC-BOOST

```text
GAIN    → seletor 0, inteiro 0–100
VOLUME  → seletor 1, inteiro 0–100
BASS    → seletor 2, inteiro 0–100
TREBLE  → seletor 3, inteiro 0–100
```

A captura `rcboost_short_cap.pcapng` observou o slot humano 1, enquanto
`rcboost_unique_values.pcapng` observou o slot humano 2. Os nomes dos arquivos
não foram usados para inferir o slot; o valor veio dos bytes `message[39:41]`.
A captura individual de GAIN repetiu `100`, preservado uma única vez nas
fixtures.

### FAT BOOST

```text
BASS     → seletor 0, inteiro 0–100
TREBLE   → seletor 1, inteiro 0–100
VOLUME   → seletor 2, inteiro 0–100
LOW CUT  → seletor 3, booleano OFF/ON
```

O LOW CUT reutiliza o mesmo codec numérico:

```text
OFF → 0 → 00 00 00 00
ON  → 1 → 08 00 03 0F
```

A apresentação humana é determinada por `value_type: boolean`, resultando em
`desligado` e `ligado` no monitor.

### GATE 2

```text
THRESHOLD → seletor 0, inteiro 0–100
ATTACK    → seletor 1, inteiro 0–100
RELEASE   → seletor 2, inteiro 0–100
```

A captura individual de THRESHOLD não contém o retorno final para `50`, mas o
valor foi confirmado nas capturas combinada e de slot 2. A captura individual
de ATTACK não contém `99`; os pontos `0`, `1`, `50` e `100`, somados às demais
evidências e ao codec já consolidado, confirmam a faixa `0–100`.

## Protocolo compartilhado

Todos os onze parâmetros usam:

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

O endereço `01 04` continua não representando o `model_id`. A identidade do
efeito vem da cadeia estrutural atual do slot antes da resolução do seletor.

## Fixtures preservadas

```text
tests/fixtures/rc_boost_parameters/  → 32 respostas únicas
tests/fixtures/fat_boost_parameters/ → 28 respostas únicas
tests/fixtures/gate2_parameters/     → 23 respostas únicas
```

Total preservado: **83 respostas SysEx físicas únicas**.

As fixtures são deduplicadas por slot, parâmetro e valor, mas o manifesto
mantém todas as fontes controladas, sequências combinadas, validações do slot 2
e observações sobre eventos repetidos ou ausentes.

## Integração

Foram atualizados:

```text
catalog/effects/dyn/008_rc_boost.json
catalog/effects/dyn/009_fat_boost.json
catalog/effects/dyn/013_gate_2.json
```

O catálogo foi incrementado para `catalog_version: 8`. Agora há 12 efeitos DYN
com parâmetros, totalizando 38 controles físicos catalogados. Permanecem 255
efeitos com parâmetros pendentes.

Não houve alteração em:

```text
tools/parameters/decoder.py
tools/parameters/codecs.py
tools/parameters/state.py
tools/commands/preset_monitor_core.py
```

A migração reproduzível recebeu sementes para os três efeitos.

## Validação offline

```text
Ran 386 tests
OK
```

A cobertura nova verifica:

- as 83 fixtures físicas pelo contexto real do efeito;
- os seletores de RC-BOOST, FAT BOOST e GATE 2;
- o booleano LOW CUT com apresentação `ligado/desligado`;
- atualização simulada independente de todos os parâmetros;
- manifestos, fontes, slots e capturas combinadas;
- reprodução dos três efeitos pelo exportador JSON;
- redução dos efeitos pendentes de 258 para 255.

Também devem passar antes da validação física:

```powershell
python -m compileall tools tests
git diff --check
```

## Validação física aprovada

A integração foi validada no monitor principal com os três efeitos
simultaneamente na cadeia:

```text
RC-BOOST
GAIN 25 | VOLUME 56 | BASS 55 | TREBLE 63

FAT BOOST
BASS 60 | TREBLE 42 | VOLUME 28 | LOW CUT desligado

GATE 2
THRESHOLD 26 | ATTACK 34 | RELEASE 61
```

O RC-BOOST recebeu os quatro parâmetros enquanto FAT BOOST e GATE 2
permaneceram sem alterações. Em seguida, FAT BOOST recebeu BASS, TREBLE,
VOLUME e transições independentes de LOW CUT:

```text
desligado → ligado → desligado
```

Por fim, GATE 2 recebeu THRESHOLD, ATTACK e RELEASE sem modificar os estados
dos outros dois efeitos. Isso confirma a resolução de seletores iguais pelo
efeito real presente em cada slot e a coexistência sem colisões entre os três
modelos.

O log final não contém duas instâncias simultâneas do mesmo modelo, mudança de
posição visual ou teste explícito de bypass. As capturas controladas nos slots
humanos 1 e 2, a suíte simulada e a coexistência física dos três efeitos
sustentam a aprovação, mantendo essas ausências registradas como limitações da
cobertura final.

## Limitações preservadas

- o valor inicial continua como `aguardando alteração`;
- o `0x1C` isolado não identifica o modelo do efeito;
- seletores iguais continuam ambíguos sem o contexto da cadeia;
- o monitor permanece somente leitura;
- mensagens auxiliares não `0x1C` continuam ignoradas;
- o log final da fase não cobre duas instâncias do mesmo efeito, reordenação ou
  bypass explícito.

## Próximo passo exato

1. aplicar o pacote documental de aprovação física;
2. executar novamente os 386 testes, `compileall` e `git diff --check`;
3. adicionar somente os arquivos da Fase 30;
4. criar o commit `feat: add RC-BOOST FAT BOOST and GATE 2 parameters`;
5. enviar `research/dyn-parameters`;
6. promover o mesmo commit por fast-forward à `main`;
7. iniciar a Fase 31 com os parâmetros especiais do AC SIM e do GATE 3.
