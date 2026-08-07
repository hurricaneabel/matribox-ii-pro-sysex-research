# Fase 44 — WAH / RACK WAH e EQ booleano

Uma única captura combinada confirmou o dump salvo e as alterações ao vivo do
RACK WAH. A identidade é `class_id 0x02`, `model_id 0x0A` e seletor secundário
`0x05`.

| Seletor | Parâmetro | Domínio | Padrão |
|---:|---|---|---:|
| 0 | RANGE | 0–100 | 50 |
| 1 | Q | 0–100 | 50 |
| 2 | VOLUME | 0–100 | 50 |
| 3 | POSITION | 0–100 | 50 |
| 4 | EQ | OFF/ON | ON |

O dump reaberto preservou `21 / 43 / 65 / 87 / OFF`. Na mesma captura, os
controles mudaram para `22 / 44 / 66 / 88` e o EQ percorreu `ON → OFF → ON`,
com respostas `0x1C` correspondentes. O EQ usa o seletor 4; os valores 100 e 1
dos seletores 5 e 6 são residuais e ficam fora do catálogo.

O catálogo passa à versão 21, com 25 efeitos parametrizados, 97 parâmetros e
242 efeitos pendentes. A integração permanece somente leitura.

## Validação física final

O preset 56C foi validado com os doze slots ocupados. O RACK WAH na posição
visual 12 foi hidratado corretamente:

```text
RANGE 66, Q 39, VOLUME 34, POSITION 66, EQ OFF
```

O efeito coexistiu com múltiplos COMP1 e manteve o estado booleano desligado.
A Fase 44 está fisicamente aprovada.
