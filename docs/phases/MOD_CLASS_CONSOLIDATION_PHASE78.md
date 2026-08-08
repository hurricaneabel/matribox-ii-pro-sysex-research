# Fase 78 — consolidação final da classe MOD

A classe MOD foi encerrada após pesquisa incremental por famílias, inferência controlada de schemas repetitivos e validação física no Matribox II Pro. Resultado final: **23/23 modelos `physically_validated`** e **95 parâmetros MOD**.

## Identidade estrutural

- classe: `MOD`
- `class_id = 0x08`
- 23 modelos
- `secondary_selector = 0x04` na maioria dos modelos; exceções estruturais já catalogadas permanecem preservadas.

## RATE / SYNC compartilhado

E-CHORUS foi a âncora física do domínio RATE/SYNC. RATE usa `float32_nibbles_v1` e o mesmo selector muda de domínio conforme SYNC:

- SYNC OFF: `0.1 .. 10.0 Hz`, default `0.5 Hz`;
- SYNC ON: wire `0..10` = `1/1, 1/2, 1/2d, 1/2t, 1/4, 1/4d, 1/4t, 1/8, 1/8d, 1/8t, 1/16`; default wire 4 = `1/4`;
- alternar SYNC reseta RATE para o default do novo domínio.

Esse schema foi reutilizado e confirmado fisicamente em E-CHORUS, B-CHORUS, VIBRATO, CE-ROTO, SINE TREM, TRIANGULE TREM, BBD ROTO, BBD PHASER, VIBE, TREMOLO, PHASER, FLANGER, FLANGER N, BASS JET, M-CHORUS, PHASER ST, U-VIBE e BIAS TREM.

## Dual RATE / dual SYNC

TREM JET e PAN PHASER usam dois pares RATE/SYNC independentes. Cada SYNC controla e reseta somente seu RATE associado. O comportamento foi validado ao vivo em ambos os modelos.

## Enums e valores especiais

- PHASER ST: `WARM=0`, `SHARP=1`;
- U-VIBE: `CHORUS=0`, `VIBRATO=1`;
- D-CHORUS: wire `0,1,2,3` corresponde à UI `MODE 1,2,3,4`; default wire 0 / UI 1;
- DETUNE: signed `-50 .. 50 cents`, default `-25`;
- parâmetros comuns DEPTH, MIX, VOLUME, FILTER, PRE DELAY, FEEDBACK, BIAS, WET, DRY, KRUSH, BIT, HI CUT e LO CUT usam os ranges/defaults catalogados, majoritariamente `0..100`.

## Quatro modelos finais

M-CHORUS, DETUNE e LOFI BIT foram confirmados integralmente na primeira validação da Fase 78. D-CHORUS revelou inicialmente um deslocamento constante porque a hipótese usava enum 1..4 no wire; o log mostrou wire 0..3. Após corrigir para `0→1, 1→2, 2→3, 3→4`, o usuário repetiu o teste e confirmou funcionamento correto.

## Validação física

A validação foi feita por famílias no `matribox_monitor --live --log`, sempre comparando os valores exibidos pelo script com os valores reais da pedaleira. O usuário confirmou correspondência integral em todos os 23 modelos. Capturas adicionais foram usadas apenas quando necessárias; schemas simples/repetitivos foram inferidos e depois comprovados diretamente no hardware.

## Estado final

- MOD: **23/23 `physically_validated`**
- parâmetros MOD: **95**
- MOD `partially_cataloged`: **0**
- MOD `pending`: **0**
- `catalog_version = 59`
- global `physically_validated = 224`
- global `partially_cataloged = 0`
- global `pending = 43`
- parâmetros globais catalogados = **922**

A próxima pesquisa pode começar na classe seguinte sem nenhuma pendência de parâmetros dentro de MOD.
