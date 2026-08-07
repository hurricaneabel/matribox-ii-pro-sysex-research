# Melhoria pós-Fase 35 — modo `--live` do monitor

## Objetivo

Evitar que o monitor principal imprima um novo snapshot completo a cada evento
durante o uso cotidiano, sem remover o comportamento append-only usado nas
validações físicas e sem alterar a comunicação MIDI/SysEx.

## Implementação

O comando histórico continua inalterado:

```powershell
python -m tools.commands.matribox_monitor
```

O novo modo de painel é ativado explicitamente:

```powershell
python -m tools.commands.matribox_monitor --live
```

A versão fisicamente aprovada:

- entra no buffer alternativo ANSI do terminal;
- oculta o cursor durante a execução;
- limpa o quadro inteiro antes de cada redesenho;
- retorna o cursor ao topo antes de escrever o novo snapshot;
- não acrescenta newline ao final do quadro;
- silencia mensagens internas de progresso somente no modo painel;
- restaura cursor e buffer normal quando o monitor encerra.

A limpeza completa do quadro foi necessária porque apenas reposicionar o cursor
deixava sufixos de linhas antigas quando a nova linha era menor, produzindo
artefatos como texto de parâmetros misturado.

## Log compacto

`--log` grava eventos já processados pelo monitor em texto UTF-8:

```powershell
python -m tools.commands.matribox_monitor --live --log data/dumps/monitor_live.txt
```

Exemplo de formato:

```text
04:15:20 slot=9 Dual Melody LOW PITCH -12
04:15:21 slot=9 Dual Melody LOW PITCH -11
04:15:24 slot=9 Dual Melody LOW PITCH 0
```

Também são registrados eventos compactos de bypass, preset e mudanças
estruturais reconhecidas. O log não envia comandos adicionais à pedaleira.

## Compatibilidade

O modo tradicional permanece append-only e continua sendo o modo recomendado
para guardar evidências de pesquisa. A mudança não toca em parser estrutural,
catálogo, codecs, estado de parâmetros ou protocolo SysEx.

## Validação

A candidata final foi aprovada fisicamente no Windows Terminal/PowerShell: o
painel permaneceu em uma única tela e atualizou os valores sem restos de
caracteres de quadros anteriores.

Validação offline:

```text
Ran 428 tests
OK
compileall: aprovado
git diff --check: aprovado
```

Os testes novos cobrem compatibilidade do modo padrão, parsing de `--live` e
`--log`, buffer alternativo, limpeza completa de quadro, renderização do painel,
formatação de eventos compactos e escrita/flush do arquivo de log.

## Limitação fora do escopo

O painel não resolve a hidratação inicial dos valores salvos dos parâmetros. Ao
carregar um preset, parâmetros conhecidos continuam exibindo `aguardando
alteração` até o primeiro evento `0x1C`. Essa questão pertence a uma pesquisa
separada do dump de preset `0x10`.
