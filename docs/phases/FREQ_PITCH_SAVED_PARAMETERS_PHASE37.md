# Fase 37 — FREQ / Pitch e hidratação de cinco parâmetros salvos

## Objetivo

Cadastrar o quarto efeito FREQ usando quatro capturas de reabertura do editor
oficial. A investigação foi feita sobre o dump completo `0x10`, sem introduzir
comandos de escrita.

## Identidade e layout confirmados

O efeito salvo aparece no slot interno 0 com `class_id = 0x01`,
`model_id = 0x24` e `secondary_selector = 0x01`. Os cinco valores ficam no
primeiro bloco de parâmetros, a partir do offset 273:

| Seletor | Parâmetro | Faixa | Default salvo |
|---:|---|---:|---:|
| 0 | HI PITCH | 0–12 | 12 |
| 1 | LOW PITCH | -12–0 | 0 |
| 2 | WET | 0–100 | 50 |
| 3 | DRY | 0–100 | 50 |
| 4 | RANGE | 0–100 | 50 |

Todos são `float32` little-endian no dump. LOW PITCH preserva diretamente os
valores negativos; foram observados `-12`, `-9`, `-8` e `0`, sem offset ou
enumeração intermediária.

## Evidência física

As quatro capturas produziram dumps descomprimidos completos de 1.211 bytes:

```text
PITCH_SLOT1_IMPLICIT_DEFAULT_REOPEN_SAVED_DUMP.pcapng
PITCH_SLOT1_3_NEG9_21_43_65_REOPEN_SAVED_DUMP.pcapng
PITCH_SLOT1_4_NEG8_22_44_66_REOPEN_SAVED_DUMP.pcapng
PITCH_SLOT1_LIMITS_12_NEG12_0_100_50_REOPEN_SAVED_DUMP.pcapng
```

Os conjuntos controlados mudaram somente os seletores 0–4. A captura de
limites confirmou `12 / -12 / 0 / 100 / 50`; a captura implícita confirmou
`12 / 0 / 50 / 50 / 50`.

## Implementação

O catálogo passou para a versão 14 e ganhou os cinco parâmetros de
`freq.pitch`. A hidratação usa o mecanismo genérico da Fase 36; não foi criado
parser, codec ou condição específica para Pitch. Foram adicionados testes do
catálogo, reprodução pelo exportador e hidratação com LOW PITCH negativo.

Validação offline da candidata:

```text
Ran 445 tests
OK
compileall: aprovado
git diff --check: aprovado
```

As capturas desta fase observam o dump salvo, não transições ao vivo `0x1C`.
A integração foi posteriormente aprovada no monitor físico: duas instâncias de
Pitch mantiveram valores independentes, coexistiram com Filter e COMP1, novos
efeitos foram hidratados e os cinco controles acompanharam alterações em tempo
real. A Fase 37 está fisicamente aprovada.

## Segurança

A implementação continua somente leitura. Nenhum novo pacote SysEx de escrita
foi criado ou enviado.
