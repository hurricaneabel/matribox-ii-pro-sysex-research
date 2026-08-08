# Fase 71 — consolidação final da classe CAB

## Resultado

A pesquisa de parâmetros da classe `CAB` foi encerrada com **61/61 modelos fisicamente validados**. Todos os modelos compartilham o mesmo schema de três controles, comprovado inicialmente por PCAPNG em dois extremos da lista (`SUPERO 1X6` e `DOUBLE BASS`) e depois confirmado pelo usuário, modelo por modelo, no `matribox_monitor --live`.

Estado final da classe:

```text
61 / 61 CAB parameterizados
61 / 61 parameter_catalog_status = physically_validated
0 partially_cataloged
0 pending
183 parâmetros CAB
```

## Schema compartilhado comprovado

| Controle | Seletor persistido / resposta | Codec | Faixa wire | Exibição | Default |
|---|---:|---|---|---|---|
| VOLUME | 1 | `float32_nibbles_v1` | 0..100 | 0..100 | 50 |
| LOW CUT | 5 | `float32_nibbles_v1` | 19..2000 | `19 = OFF`; 20..2000 Hz | OFF |
| HIGH CUT | 6 | `float32_nibbles_v1` | 2000..20001 | 2000..20000 Hz; `20001 = OFF` | OFF |

O uso de `float32_nibbles_v1` completo é obrigatório. A classe não usa o codec truncado de quatro nibbles; frequências como 15501, 13262 e a sentinela 20001 dependem do `float32` completo.

Os seletores persistidos 2, 3 e 4 observados nas capturas não correspondem a controles visíveis do CAB. Em `SUPERO 1X6` e `DOUBLE BASS` eles permaneceram como resíduos do slot e não foram catalogados.

## Método de descoberta e validação

A Fase 70 usou cinco capturas no `SUPERO 1X6`: boot/sincronização padrão, reabertura com valores personalizados salvos, sweep de LOW CUT, sweep de HIGH CUT e sweep de VOLUME. Isso comprovou simultaneamente hidratação pelo dump `0x10` e eventos ao vivo `0x1C`.

Valores salvos de referência do `SUPERO 1X6`:

```text
VOLUME = 37
LOW CUT = 630 Hz
HIGH CUT = 15500 Hz
```

O `DOUBLE BASS` foi usado como confirmação cruzada distante na lista, primeiro por reabertura com `28 / 956 / 13262` e depois por alterações ao vivo. Ele repetiu exatamente os seletores 1/5/6 e as sentinelas 19/20001.

Após essas duas âncoras físicas, a Fase 71 aplicou o schema aos 59 modelos restantes como `partially_cataloged`. O usuário então testou **cada modelo individualmente**, alterando VOLUME, LOW CUT e HIGH CUT e comparando os valores exibidos pelo script com a pedaleira. A confirmação final informou funcionamento 100% em todos os modelos, inclusive os valores `float32` e os estados OFF. Com isso, os 59 candidatos foram promovidos para `physically_validated`.

## Mapa dos 61 modelos

| # | Modelo | model_id | Seletores |
|---:|---|---:|---|
| 1 | SUPERO 1X6 | `00` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 2 | CHAP 1X8 | `01` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 3 | PRINCE 1X10 | `02` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 4 | TWD 2X10 | `14` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 5 | TWD LUX 1X12 | `0B` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 6 | DARK LUX 1X12 | `03` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 7 | TWIN VERB 2X12 | `12` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 8 | CUSTOM 2X12 | `1B` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 9 | B-MAN 2X10 | `16` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 10 | B-MAN 4X10 | `1E` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 11 | JAZZ 2X12 | `11` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 12 | BRIT 1X12 | `0E` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 13 | BRIT GN 2X12 | `13` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 14 | BRIT LD 4X12 | `1F` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 15 | BRIT TD 4X12 | `20` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 16 | BRIT MD 4X12 | `21` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 17 | BRIT GN 4X12 | `22` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 18 | BRIT 75 4X12 | `30` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 19 | BRIT BK 4X12 | `2B` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 20 | VOKS 1X12 | `08` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 21 | VOKS 2X12 | `0F` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 22 | BOG SV 1X12 | `06` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 23 | CHIEF 2X12 | `10` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 24 | CALIF DUAL 4X12 | `24` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 25 | CALIF STAR 1X12 | `09` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 26 | CALIF STAR 2X12 | `19` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 27 | CALIF 1X12 | `0C` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 28 | SUPERO 2X12 | `17` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 29 | SUPERB 2X12 | `18` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 30 | BLUE 2X12 | `1D` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 31 | HALEN 4X12 | `23` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 32 | BOG 4X12 | `25` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 33 | ENG 4X12 | `26` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 34 | BOG UB 4X12 | `27` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 35 | SOL 4X12 | `28` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 36 | TANGER 4X12 | `29` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 37 | WATT 4X12 | `2A` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 38 | WAM 4X12 | `2C` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 39 | HUMBLE 4X12 | `2D` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 40 | DIZZY 4X12 | `2E` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 41 | CALIF 4X12 | `31` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 42 | DV 1X15 | `32` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 43 | DV 4X10 | `37` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 44 | WORK 1X15 | `33` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 45 | WORK 4X10 | `39` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 46 | CALIF 2X10 | `35` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 47 | MAK 2X10 | `36` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 48 | A BASS 1X15 | `34` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 49 | A BASS 4X10 | `38` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 50 | A BASS 8X10 | `3B` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 51 | HART 4X12 | `3A` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 52 | D 1 | `3C` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 53 | D 2 | `3D` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 54 | OM | `3E` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 55 | JUMBO | `3F` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 56 | BIRD | `40` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 57 | GA | `41` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 58 | CLASSICAL AC | `42` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 59 | MANDOLIN | `43` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 60 | FRETLESS BASS | `44` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |
| 61 | DOUBLE BASS | `45` | 1:VOLUME, 5:LOW CUT, 6:HIGH CUT |

## Hidratação e monitor

A validação comprovou os dois caminhos usados pelo monitor:

```text
dump salvo 0x10 -> decode_saved_parameter_events -> float32 completo -> valor/Hz/OFF
evento ao vivo 0x1C -> parse_effect_parameter_response -> float32 completo -> valor/Hz/OFF
```

O comportamento esperado e aprovado é:

- LOW CUT wire `19` exibido como `OFF`, nunca `19 Hz`;
- HIGH CUT wire `20001` exibido como `OFF`, nunca `20001 Hz`;
- frequências intermediárias exibidas exatamente como informadas pela pedaleira;
- VOLUME exibido diretamente em 0..100;
- hidratação inicial e alterações ao vivo usando a mesma semântica de exibição.

## Estado global após CAB

```text
catalog_version: 52
267 efeitos estruturais
176 efeitos com parâmetros fisicamente validados
738 parâmetros catalogados
91 efeitos ainda sem parâmetros em outras classes
CAB: 61/61 physically_validated, 183 parâmetros
```

A classe CAB está encerrada sem modelos `pending` ou `partially_cataloged`.
