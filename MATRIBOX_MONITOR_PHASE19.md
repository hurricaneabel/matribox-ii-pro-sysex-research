# Fase 19 — monitor consolidado e recuperação de cold boot

## Objetivo

Esta fase encerra a separação entre os monitores de metadados e o parser da
cadeia. O comando consolidado é:

```text
python -m tools.commands.matribox_monitor
```

A saída reúne:

- endereço do preset atual;
- nome;
- etiqueta;
- efeitos na ordem visual;
- classe e modelo resolvidos pelo catálogo;
- estado ligado ou desligado.

## Cold boot

A primeira consulta ou seleção enviada logo após ligar a Matribox pode não
produzir confirmação. O programa agora executa automaticamente:

- reenvio da consulta global;
- reenvio da consulta do preset atual;
- até duas tentativas completas de inicialização;
- três tentativas ao selecionar presets no validador da Fase 18.

A segunda execução manual não deve mais ser necessária.

## Estado estrutural

O monitor não altera a cadeia para obter dados. Ele processa passivamente as
respostas estruturais emitidas pela Matribox. Quando o endereço e a etiqueta já
estão disponíveis, mas a resposta estrutural ainda não chegou, a tela informa:

```text
Efeitos: aguardando resposta estrutural.
```

Assim que a resposta chega, a mesma tela é atualizada com os efeitos.
