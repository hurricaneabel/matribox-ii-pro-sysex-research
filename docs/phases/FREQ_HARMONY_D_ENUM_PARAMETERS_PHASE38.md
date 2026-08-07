# Fase 38 — FREQ / Harmony D e três domínios enum

## Objetivo

Cadastrar os seis parâmetros do `FREQ / Harmony D`, incluindo KEY, MODE e os
dois INTERVALS nomeados, preservando o layout físico do dump e das respostas
ao vivo. A pesquisa permaneceu somente leitura.

## Identidade e seletores

Os dumps completos confirmaram `class_id = 0x01`, `model_id = 0x4E` e
`secondary_selector = 0x01` no slot interno 0.

| Seletor | Parâmetro | Domínio | Default |
|---:|---|---|---|
| 0 | MIX | 0–100 | 50 |
| 1 | KEY | C até B | C |
| 2 | MODE | 8 modos | MAJOR |
| 3 | INTERVAL 1 | 14 intervalos | +3RD |
| 4 | INTERVAL 2 | 14 intervalos | +5TH |
| 5 | — | não utilizado | — |
| 6 | SMOOTH | desligado/ligado | desligado |

## Enums confirmados

```text
KEY: 0 C, 1 C#, 2 D, 3 D#, 4 E, 5 F, 6 F#, 7 G, 8 G#, 9 A, 10 A#, 11 B
MODE: 0 MAJOR, 1 MINOR, 2 H. MINOR, 3 DORIAN, 4 PHRYGIAN,
      5 LYDIAN, 6 MIXOLYDIAN, 7 LOCRIAN
INTERVAL: 0 -OCT, 1 -7TH, 2 -6TH, 3 -5TH, 4 -4TH, 5 -3RD, 6 -2ND,
          7 +2ND, 8 +3RD, 9 +4TH, 10 +5TH, 11 +6TH, 12 +7TH, 13 +OCT
```

A varredura ao vivo produziu 50 respostas device->host `0x1C`: quatro mudanças
de MIX, onze de KEY, sete de MODE, treze para cada INTERVAL e duas de SMOOTH.
Os valores iniciais zero não geraram nova resposta porque já estavam ativos;
a sequência controlada e os dumps estabelecem os pontos iniciais.

## Dumps salvos

Três capturas de reabertura produziram payloads descomprimidos completos de
1.211 bytes. Defaults: `50 / 0 / 0 / 8 / 10 / 0`. O conjunto A confirmou
`23 / 3 / 3 / 3 / 11 / 0`. O arquivo nomeado `LIMITS` contém, na realidade, o
conjunto B `24 / 4 / 4 / 4 / 12 / 1`; ele foi mantido como evidência válida e
documentado sem reinterpretar seu nome.

## Implementação e segurança

O catálogo passou para a versão 15. O mecanismo genérico existente resolve os
enums para rótulos e hidrata os valores pelo seletor físico, inclusive a lacuna
5. Nenhum parser específico, codec novo ou comando SysEx de escrita foi criado.

Validação offline:

```text
Ran 447 tests
OK
compileall: aprovado
git diff --check: aprovado
```

## Validação física final

A integração foi aprovada no monitor `--live`. Duas instâncias simultâneas de
Harmony D mantiveram estados independentes e valores distintos para todos os
seis parâmetros. Foram confirmados enums em diferentes regiões dos domínios,
SMOOTH ligado/desligado, hidratação e alterações em tempo real. Harmony D
coexistiu com COMP1, efeitos WAH e DRV sem colisão de estado.

A Fase 38 está fisicamente aprovada.
