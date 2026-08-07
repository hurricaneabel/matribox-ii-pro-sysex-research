# Fase 47 — WAH / AUTO WAH, SYNC e dois domínios de RATE

Quatro capturas controladas confirmaram a identidade `class_id 0x02`,
`model_id 0x15`, seletor secundário `0x01` e sete parâmetros consecutivos.

| Seletor | Parâmetro | Domínio | Padrão salvo |
|---:|---|---|---:|
| 0 | DEPTH | 0–100 | 50 |
| 1 | RATE | condicionado por SYNC | 1/4 |
| 2 | VOLUME | 0–100 | 50 |
| 3 | LOW | 0–100 | 25 |
| 4 | Q | 0–100 | 70 |
| 5 | HIGH | 0–100 | 60 |
| 6 | SYNC | OFF/ON | ON |

Com SYNC desligado, RATE é um `float32` completo de 0,1 a 10,0 Hz em passos de
0,1. A captura e o dump salvo confirmaram 3,7 sem conversão para inteiro. Com
SYNC ligado, o mesmo seletor usa valores inteiros:

```text
0  1/1    1  1/2    2  1/2D   3  1/2T
4  1/4    5  1/4D   6  1/4T   7  1/8
8  1/8D   9  1/8T  10  1/16
```

Os dumps após reabrir o aplicativo preservaram exatamente:

```text
padrão:   50 / 4   / 50 / 25 / 70 / 60 / ON
SYNC OFF: 21 / 3.7 / 43 / 65 / 87 / 32 / OFF
SYNC ON:  22 / 8   / 44 / 66 / 88 / 33 / ON
```

A implementação reutiliza a regra de domínio condicionado da Fase 33. SYNC é
hidratado antes de RATE; uma mudança de SYNC invalida o RATE anterior e resolve
o padrão do novo domínio sem fabricar evento USB. No domínio livre, o monitor
formata RATE com uma casa decimal e unidade Hz.

O catálogo passa à versão 25, com 28 efeitos parametrizados, 113 parâmetros e
239 efeitos pendentes. A análise física das capturas está concluída; a
integração final no monitor foi aprovada.

## Correção da quantização decimal

O primeiro candidato comparava a divisão pelo passo 0,1 com tolerância absoluta
pequena demais. Alguns `float32`, como 4,2 e 4,8, chegavam como
`4.199999809265137` e `4.800000190734863` e eram descartados. A validação agora
compara o valor com o múltiplo mais próximo usando tolerância adequada ao
float32 e normaliza o resultado. A regressão cobre todos os 100 valores de 0,1
a 10,0; valores fora do passo, como 4,25, continuam rejeitados.

## Validação física final

O monitor acompanhou corretamente alterações em tempo real depois da correção,
inclusive os valores decimais antes descartados. Uma instância no fim de uma
cadeia cheia preservou DEPTH 58, RATE 8,7 Hz, VOLUME 100, LOW 54, Q 70, HIGH 60
e SYNC desligado. O domínio sincronizado também foi confirmado com SYNC ligado.

A Fase 47 está aprovada e encerra a pesquisa de parâmetros da classe WAH.
