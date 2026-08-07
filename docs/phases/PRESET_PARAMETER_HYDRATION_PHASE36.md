# Fase 36 — hidratação inicial de parâmetros pelo dump de preset

## Objetivo

Eliminar o estado `aguardando alteração` ao carregar um preset, reutilizando o
dump somente leitura `0x10` já empregado para cadeia e bypass. Nenhum comando
SysEx novo foi criado.

## Descoberta física

Capturas controladas confirmaram que o payload descomprimido de 1.211 bytes
possui o bloco fixo `273–992`:

```text
12 slots internos × 60 bytes
15 posições float32 little-endian × 4 bytes por slot
```

O endereço de cada valor é:

```text
slot_base = 273 + internal_slot_id * 60
offset = slot_base + parameter_selector * 4
```

A posição usa `parameter_selector`, não `display_order`. O Dual Melody provou
essa distinção: o seletor 3 não é catalogado, enquanto HI VOL e LOW VOL ocupam
os seletores 4 e 5.

## Evidências controladas

- M-BOOST nos slots 1/2, confirmando o stride de 60 bytes;
- COMP1 com dois parâmetros consecutivos;
- E-BOOST com booleanos em float32 0/1;
- Dual Melody com valor negativo e lacuna no seletor 3;
- FILTER com RATE/SYNC e defaults persistidos 4/ON e 10/OFF;
- dump físico histórico 56A com os cinco parâmetros do GATE 3.

O aplicativo oficial pode reabrir `SYNC ON / RATE bruto 4` mostrando `4` em
vez de `1/4`. O dump está correto; o monitor resolve RATE somente após conhecer
SYNC.

## Implementação

- o decoder usa somente efeitos e parâmetros confirmados pelo catálogo;
- valores inválidos são ignorados individualmente;
- controladores de domínio são aplicados antes dos dependentes;
- valores hidratados usam origem `saved_preset_dump`;
- eventos `0x1C` usam `observed_usb` e prevalecem durante a montagem do dump;
- cadeia, bypass e parâmetros são aplicados a partir da mesma resposta `0x10`.

## Validação offline

```text
Ran 443 tests
OK
```

Os quinze testes novos cobrem layout, tipos, FILTER, precedência ao vivo, um
dump físico completo e a nova leitura após mudança estrutural.

## Validação física e refinamento

A carga inicial foi aprovada fisicamente com GATE 3, Dual Melody e FILTER: os
valores apareceram imediatamente, sem `aguardando alteração`. Ao adicionar um
COMP1 à cadeia, a resposta estrutural informou o novo efeito, mas não continha
seus valores. A candidata passou então a solicitar novamente o dump somente
leitura `0x10` após mudanças estruturais e a aguardar o dump completo mesmo se
outras respostas estruturais chegarem durante a coleta.

A candidata refinada foi aprovada fisicamente no painel `--live`. Foram
confirmados:

- carregamento inicial imediato de GATE 3, FILTER e Dual Melody;
- adição de COMP1 com SUSTAIN/VOLUME já hidratados;
- coexistência de FILTER, COMP1 e Dual Melody no mesmo preset;
- alteração de efeitos, classes e parâmetros em tempo real;
- substituição e reordenação sem conservar estado do efeito anterior;
- RATE/SYNC apresentados no domínio correto após a hidratação;
- ausência de `aguardando alteração` para efeitos catalogados após o novo dump.

Status da Fase 36: **fisicamente aprovada e pronta para consolidação**.
