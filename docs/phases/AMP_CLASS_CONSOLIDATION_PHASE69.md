# Fase 69 — consolidação final da classe AMP

## Objetivo

Encerrar a pesquisa de parâmetros da classe `AMP` depois da validação física dos
63 modelos. As fases 59–64 possuem relatórios próprios; os lotes acelerados das
fases 65–69 foram documentados de forma consolidada aqui para evitar retrabalho
durante a coleta.

## Resultado final

A classe AMP está completamente catalogada e fisicamente validada:

```text
63 / 63 modelos AMP com parâmetros
63 / 63 parameter_catalog_status = physically_validated
356 parâmetros AMP descritos
0 modelos AMP partially_cataloged
0 modelos AMP pending
```

No projeto inteiro, o catálogo permanece na versão 50 e passa a ter:

```text
267 efeitos estruturais
115 efeitos com parâmetros fisicamente validados
555 parâmetros catalogados
152 efeitos ainda sem parâmetros (outras classes)
```

As classes de parâmetros concluídas são DYN, FREQ, WAH, DRIVE e AMP.

## Validação física final da Fase 69

Os dez modelos finais foram aprovados no `matribox_monitor --live` no preset 56B.
A leitura final observada foi:

```text
DIZZY VH S    0 / 100 / 23 / 77 / 40 / 65
DIZZY VH+     100 / 0 / 12 / 88 / 27 / 66
DIZZY VH+ S   74 / 34 / 100 / 0 / 37 / 57
A BASSVT      GAIN 11 / BASS 92 / MIDDLE 40 / MIDRANGE 1.6KHZ / TREBLE 99 / VOLUME 1
VOKS BASS     VOLUME 10 / BASS 93 / TREBLE 43
CALI BASS     GAIN 0 / VOLUME 100 / BASS 29 / MIDDLE 88 / TREBLE 64
A BASSFT      VOLUME 100 / BASS 38 / TREBLE 0
F-2BASS       VOLUME 13 / BRIGHT OFF / BASS 97 / MIDDLE 77 / TREBLE 30
AC PREAMP     VOLUME 0 / TONE 100 / BALANCE 15 / EQ FREQ 98 / EQ Q 38 / EQ GAIN 94
AC PREAMP 2   VOLUME 100 / TONE 78 / BALANCE 65 / EQ FREQ 0 / EQ Q 94 / EQ GAIN 29
```

O usuário confirmou que os controles acompanharam corretamente as mudanças em
tempo real. O `MIDRANGE` do A BASSVT e o `BRIGHT` do F-2BASS também foram
aprovados como controles categórico/booleano do modelo.

## Exceções e padrões importantes da classe AMP

- `TWD DELUXE`: somente seletores 0–2 são controles; campos persistidos 3–5 são
  resíduos e não devem aparecer no monitor.
- `DARK DOUBLE`, `VOKS 30N`, `JAZZ 120`, `BOG SV CL` e `F-2BASS` possuem
  controles booleanos `BRIGHT` em posições específicas.
- `VOKS 30TB` usa `CHAR` como enum `COOL/HOT`.
- `SUPERO 2 OD` possui dois pares GAIN/TONE antes do VOLUME.
- `BRIT 45JP` e `BRIT 50JP` usam `GAIN 2` no seletor 6.
- `HALEN 51` é uma exceção importante: `PRESENCE` está no seletor **6**; o
  seletor 5 é um campo oculto/não catalogado e não deve ser confundido com a
  ordem visual do editor.
- `A BASSVT` usa `MIDRANGE` no seletor 3 com cinco escolhas: `220HZ`, `450HZ`,
  `800HZ`, `1.6KHZ`, `3KHZ`; o padrão informado pela interface é `450HZ`
  (`wire value 1`).
- `AC PREAMP` e `AC PREAMP 2` usam a assinatura própria
  `VOLUME/TONE/BALANCE/EQ FREQ/EQ Q/EQ GAIN`.
- A maioria dos controles contínuos AMP usa intervalo 0–100 e o mesmo codec
  `upper_float32_nibbles_v1`, mas **a ordem visual não deve ser usada como regra
  universal**, como demonstrado pelo HALEN 51.

## Mapa completo dos 63 AMP

| # | Modelo | Identidade | Seletores catalogados |
|---:|---|---|---|
| 1 | TWD DELUXE | `04/01/07` | 0:GAIN, 1:TONE, 2:VOLUME |
| 2 | B-MAN N | `04/03/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 3 | B-MAN BRI | `04/24/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 4 | DARK DOUBLE | `04/04/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE, 5:BRIGHT |
| 5 | DARK DELUXE | `04/05/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:TREBLE |
| 6 | SUPERO 2 CL | `04/0F/07` | 0:GAIN, 1:TONE, 2:VOLUME |
| 7 | SUPERO 2 OD | `04/28/07` | 0:GAIN 1, 1:TONE 1, 2:GAIN 2, 3:TONE 2, 4:VOLUME |
| 8 | VOKS 15TB | `04/10/07` | 0:GAIN, 1:TONE CUT, 2:VOLUME, 3:BASS, 4:TREBLE |
| 9 | VOKS 30N | `04/11/07` | 0:GAIN, 1:TONE CUT, 2:VOLUME, 3:BRIGHT |
| 10 | VOKS 30TB | `04/27/07` | 0:GAIN, 1:TONE CUT, 2:VOLUME, 3:BASS, 4:TREBLE, 5:CHAR |
| 11 | JAZZ 120 | `04/14/07` | 0:GAIN, 1:BASS, 2:MIDDLE, 3:TREBLE, 4:BRIGHT |
| 12 | SUPERB CL | `04/15/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 13 | SUPERB OD | `04/48/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 14 | CALIF STAR CL | `04/19/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 15 | CALIF STAR OD | `04/4A/07` | 0:INPUT, 1:GAIN, 2:PRESENCE, 3:VOLUME, 4:BASS, 5:MIDDLE, 6:TREBLE |
| 16 | BOG SV CL | `04/1A/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:TREBLE, 5:BRIGHT |
| 17 | BOG SV OD | `04/3D/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 18 | BOG XT BLUE | `04/43/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 19 | BOG XT RED | `04/6E/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 20 | DOCTOR CL | `04/1B/07` | 0:GAIN, 1:TONE CUT, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 21 | DOCTOR OD | `04/49/07` | 0:GAIN, 1:TONE CUT, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 22 | DRAGON CL | `04/1F/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 23 | DRAGON CL B | `04/7B/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 24 | DRAGON OD | `04/7C/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 25 | SOL 100 CL | `04/23/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 26 | SOL 100 OD | `04/47/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 27 | SOL 100 LD | `04/59/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 28 | BRIT 45 | `04/2A/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 29 | BRIT 45+ | `04/2B/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 30 | BRIT 45JP | `04/2C/07` | 0:GAIN 1, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE, 6:GAIN 2 |
| 31 | BRIT 50 | `04/2D/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 32 | BRIT 50+ | `04/2E/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 33 | BRIT 50JP | `04/2F/07` | 0:GAIN 1, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE, 6:GAIN 2 |
| 34 | BRIT SLP | `04/30/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 35 | BRIT 800 | `04/35/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 36 | BRIT 900 | `04/4E/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 37 | FLYMAN 1 | `04/40/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 38 | FLYMAN 2 | `04/41/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 39 | FLYMAN+ 1 | `04/5D/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 40 | FLYMAN+ 2 | `04/5E/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 41 | CALIF IIC+ 1 | `04/39/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 42 | CALIF IIC+ 2 | `04/3A/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 43 | CALIF IIC+ 3 | `04/3B/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 44 | CALIF IV LD 1 | `04/55/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 45 | CALIF IV LD 2 | `04/56/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 46 | CALIF IV LD 3 | `04/57/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 47 | CALIF DUAL V | `04/68/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 48 | CALIF DUAL M | `04/69/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 49 | TANGER R100 | `04/53/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 50 | HALEN 51 | `04/5A/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE, 6:PRESENCE |
| 51 | ENG 120 | `04/5F/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 52 | ENG 120+ | `04/60/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 53 | DIZZY VH | `04/65/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 54 | DIZZY VH S | `04/66/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 55 | DIZZY VH+ | `04/6A/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 56 | DIZZY VH+ S | `04/6B/07` | 0:GAIN, 1:PRESENCE, 2:VOLUME, 3:BASS, 4:MIDDLE, 5:TREBLE |
| 57 | A BASSVT | `04/73/07` | 0:GAIN, 1:BASS, 2:MIDDLE, 3:MIDRANGE, 4:TREBLE, 5:VOLUME |
| 58 | VOKS BASS | `04/75/07` | 0:VOLUME, 1:BASS, 2:TREBLE |
| 59 | CALI BASS | `04/77/07` | 0:GAIN, 1:VOLUME, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 60 | A BASSFT | `04/75/08` | 0:VOLUME, 1:BASS, 2:TREBLE |
| 61 | F-2BASS | `04/76/08` | 0:VOLUME, 1:BRIGHT, 2:BASS, 3:MIDDLE, 4:TREBLE |
| 62 | AC PREAMP | `04/7A/08` | 0:VOLUME, 1:TONE, 2:BALANCE, 3:EQ FREQ, 4:EQ Q, 5:EQ GAIN |
| 63 | AC PREAMP 2 | `04/7B/08` | 0:VOLUME, 1:TONE, 2:BALANCE, 3:EQ FREQ, 4:EQ Q, 5:EQ GAIN |

## Lotes acelerados consolidados

- Fase 65: BOG XT RED, DOCTOR CL/OD, DRAGON CL/CL B/OD, SOL 100 CL/OD.
- Fase 66: SOL 100 LD e família BRIT 45/50/SLP/800.
- Fase 67: BRIT 900, FLYMAN 1/2, FLYMAN+ 1/2, CALIF IIC+ 1/2/3, CALIF IV LD 1.
- Fase 68: CALIF IV LD 2/3, CALIF DUAL V/M, TANGER R100, HALEN 51, ENG 120/+, DIZZY VH.
- Fase 69: DIZZY VH S/VH+/VH+ S, quatro amps de baixo e dois AC PREAMP.

Todos esses lotes foram testados no hardware usando o painel `--live`; os
valores finais incluíram diversos extremos 0/100, ajudando a confirmar tanto a
ordem dos seletores quanto as faixas numéricas.

## Validação offline de encerramento

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall tools tests
git diff --check
```

A suíte de encerramento inclui uma regressão específica que exige 63/63 modelos
AMP em `physically_validated` e 356 parâmetros AMP.

## Próximo passo recomendado

1. executar a suíte completa no ambiente Windows do projeto;
2. revisar o diff consolidado da classe AMP;
3. consolidar/commitir a branch `research/amp-parameters` somente após a
   aprovação local;
4. depois iniciar a próxima classe de parâmetros ainda pendente, com `CAB` como
   próximo grupo natural na ordem do catálogo.
