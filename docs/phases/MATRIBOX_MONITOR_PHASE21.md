# Fase 21 — bypass em tempo real no monitor

## Problema confirmado

A Fase 20 lia corretamente o dump completo ao iniciar e a cada troca de
preset. Mudanças de ordem também eram atualizadas porque a Matribox enviava uma
resposta estrutural completa.

Ao ligar ou desligar um efeito, porém, a pedaleira envia uma resposta imediata
de 62 bytes contendo somente:

- o slot interno afetado;
- o novo estado de bypass (`0` ou `1`).

Essa resposta já havia sido capturada fisicamente nos cinco primeiros slots,
mas ainda não era interpretada pelo monitor.

## Implementação

A Fase 21 acrescenta:

- parser puro de respostas imediatas de bypass;
- atualização imutável do estado de um slot interno;
- sincronização do registro estrutural, vetor de bypass e payload de 89 bytes;
- atualização do snapshot do monitor sem solicitar novamente o dump completo;
- preservação da ordem visual atual;
- retenção de um evento de bypass recebido enquanto o dump ainda está sendo
  montado, fazendo o evento mais recente prevalecer;
- descarte de eventos pendentes quando o preset muda.

O checksum dessas respostas não é validado porque capturas fisicamente
idênticas apresentaram valores diferentes nesse byte. Todos os outros bytes
fixos do formato são confrontados com as capturas reais.

## Resultado esperado

Com o monitor aberto, ligar ou desligar um efeito deve redesenhar imediatamente
a cadeia:

```text
1. DYN / GATE 3 — ligado
```

passando para:

```text
1. DYN / GATE 3 — desligado
```

A atualização não move efeitos, não altera modelos, não salva o preset e não
solicita um novo dump completo.

## Validação offline

- 10 respostas físicas: slots 1–5, ligado e desligado;
- resposta auxiliar de 54 bytes ignorada;
- slot e estado inválidos rejeitados;
- mudança aplicada com ordem normal e ordem invertida;
- evento durante o dump preservado;
- evento repetido não redesenha a tela;
- suíte completa: 306 testes aprovados.
