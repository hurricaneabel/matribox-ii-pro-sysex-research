# Fase 33 — FREQ / FILTER e domínio condicionado de RATE

## Objetivo

Iniciar a classe FREQ com o primeiro modelo parametrizado, preservando o método
validado na classe DYN e tratando corretamente a interação física entre `SYNC`
e `RATE` sem inventar mensagens USB que a pedaleira não transmite.

## Efeito e parâmetros

O modelo estrutural confirmado é:

```text
classe: FREQ
class_id estrutural: 1
modelo: Filter
model_id: 25 (0x19)
secondary_selector: 1
```

O comando de parâmetro continua sendo `0x1C`, 70 bytes, com slot interno em
`39–40`, seletor em `48`, valor físico nos nibbles já conhecidos e marcador/tipo
`01 01` em `63–64`.

Seletores confirmados:

```text
0 → STEP 1 → 0–100
1 → STEP 2 → 0–100
2 → STEP 3 → 0–100
3 → STEP 4 → 0–100
4 → RATE
5 → SYNC → OFF/ON
```

## RATE com dois domínios

`RATE` mantém o mesmo seletor 4, mas sua interpretação depende do `SYNC`.

Com `SYNC = OFF`:

```text
RATE: 0–100
default implícito ao entrar no domínio: 10
```

Com `SYNC = ON`:

```text
0  → 1/1
1  → 1/2
2  → 1/2d
3  → 1/2t
4  → 1/4
5  → 1/4d
6  → 1/4t
7  → 1/8
8  → 1/8d
9  → 1/8t
10 → 1/16

default implícito ao entrar no domínio: 1/4 (wire 4)
```

A captura isolada de transição confirmou que `SYNC OFF → ON → OFF` transmite
somente os eventos do seletor 5. A pedaleira altera visualmente o RATE para
`1/4` ao ligar SYNC e para `10` ao desligar, mas não emite um segundo evento de
seletor 4 para esses defaults.

## Regra de estado derivado

A implementação não fabrica um `EffectParameterEvent` de RATE. Em vez disso,
`value_domain` declara no catálogo o controlador, os dois domínios e seus
defaults. `EffectParameterState` invalida um RATE observado quando o controlador
SYNC muda e a camada de snapshot resolve o default como:

```text
origin = derived_device_rule
```

Um RATE realmente recebido continua marcado como:

```text
origin = observed_usb
```

Isso preserva a distinção entre estado confirmado por pacote e estado derivado
de comportamento físico reproduzível do dispositivo.

Se RATE chegar antes de qualquer evento de SYNC e o wire value estiver na área
ambígua `0–10`, o monitor mostra `aguardando SYNC` em vez de escolher um domínio
por suposição. Valores acima de 10 podem ser identificados unicamente como o
domínio numérico.

## Nova descoberta sobre o envelope 0x1C

As capturas FREQ mantêm os índices `41–42` em `00 00`, embora a classe
estrutural FREQ tenha `class_id = 1`. Isso prova que o campo historicamente
chamado `class_id` no envelope de parâmetro não representa a classe estrutural.

Consequência: o decoder não rejeita mais uma mensagem `0x1C` comparando esse
campo com a classe do catálogo. A identidade do efeito e da classe continua
obrigatoriamente vindo da cadeia estrutural atual, exatamente como já ocorria
para a identidade do modelo.

## Evidências físicas preservadas

Foram usadas dez fontes controladas:

```text
4 capturas individuais de STEP
1 captura RATE numérico com SYNC OFF
1 captura SYNC toggle
1 captura de todas as 11 divisões com SYNC ON
1 captura corrigida OFF → ON → OFF para defaults implícitos
1 captura combinada no slot humano 1
1 captura curta no slot humano 2
```

Foram preservadas 55 fixtures semânticas únicas:

```text
slot humano 1 → 41
slot humano 2 → 14
```

O manifesto registra também que o arquivo original chamado
`FILTER_SYNC_OFF_ON_OFF_DEFAULT_RATE_TRANSITION.pcapng` contém, na realidade,
a sequência de divisões de RATE; a captura corrigida posterior é a evidência da
transição do SYNC.

## Arquitetura alterada

- `ParameterDefinition.value_domain` descreve domínios condicionados;
- o schema JSON aceita controlador, estados, defaults e apresentação enum/numeric;
- o loader valida controlador existente, defaults e choices;
- `EffectParameterState` invalida dependentes em mudança de controlador;
- snapshots carregam `value_origin`;
- defaults derivados não criam eventos SysEx sintéticos;
- decoder 0x1C deixa de tratar os índices `41–42` como classe estrutural.

Não foi criado código específico `if effect == FILTER` no monitor.

## Estado da candidata

Validação offline da candidata:

```text
Ran 409 tests
OK
```

Também devem passar `python -m compileall tools tests`, validação de todos os
JSONs, reexportação do catálogo e `git diff --check` antes da entrega.

## Validação física aprovada

O monitor principal foi validado com `DYN / COMP1` no slot humano 1 e
`FREQ / Filter` no slot humano 2. STEP 1–4 e RATE numérico atualizaram de forma
independente. Com `SYNC = ON`, o monitor derivou `RATE: 1/4` sem inventar evento
USB; movimentos seguintes exibiram corretamente `1/4d` e `1/4`. Com
`SYNC = OFF`, o monitor derivou `RATE: 10`, novamente sem pacote RATE separado.

A sessão também comprovou coexistência DYN/FREQ após a correção da interpretação
dos índices `41–42` do envelope `0x1C`. Bypass e reordenação visual não fizeram
parte do log ao vivo desta validação; os slots humanos 1 e 2 permanecem cobertos
pelas fixtures físicas controladas da fase.

Status da Fase 33: **fisicamente aprovada e pronta para commit**.
