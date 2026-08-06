# Fase 20 — leitura não destrutiva da cadeia no monitor

## Problema corrigido

A troca de preset produz espontaneamente o evento de endereço, mas não produz a
resposta estrutural completa usada nas Fases 14–18. Por isso a Fase 19 exibia
nome e etiqueta, porém permanecia em `Efeitos: aguardando resposta estrutural`.

## Solução

O monitor agora usa o pedido de dump de preset já validado no projeto:

1. aguarda o preset terminar de carregar;
2. solicita o dump do endereço atual com comando de leitura `0x10`;
3. reconstrói os fragmentos SysEx;
4. descomprime o contêiner LZO1X `00 00 00 10`;
5. valida o payload fixo de 1.211 bytes;
6. extrai ordem, classe, modelo, seletor e bypass;
7. atualiza a tela do monitor.

Nenhum comando de movimento, substituição, bypass ou salvamento é enviado.

## Layout confirmado no dump descomprimido

- bytes `185–260`: prefixo estrutural, ordem, classes e registros;
- bytes `993–1004`: bypass dos 12 slots;
- tamanho descomprimido: `1.211 bytes`.

A extração foi validada offline em 100 dumps físicos de presets diferentes,
além das fixtures específicas de alteração de classe, modelo e bypass.

## Robustez

- reenvio do dump quando um fragmento se perde;
- preservação da montagem parcial entre os reenvios;
- interrupção segura quando o usuário muda novamente de preset;
- nova leitura automática para o endereço mais recente;
- repetição automática após cold boot;
- dados ocultos em slots fora da ordem visual são ignorados.

## Comando oficial

```powershell
python -m tools.commands.matribox_monitor
```

## Validação automática

```text
294 testes aprovados
```
