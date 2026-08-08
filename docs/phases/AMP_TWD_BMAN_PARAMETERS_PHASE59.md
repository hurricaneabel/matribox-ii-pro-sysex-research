# Fase 59 — AMP / TWD Deluxe, B-Man N e B-Man Bri

## Objetivo

Iniciar a pesquisa dos 63 amplificadores com dois layouts físicos: um modelo de
três controles e a família B-Man de seis controles.

## TWD Deluxe

Identidade: `amp.twd_deluxe`, modelo `01`, seletor secundário `07`.

- 0: GAIN, padrão 30
- 1: TONE, padrão 50
- 2: VOLUME, padrão 50

Os dumps diferenciais confirmaram 21/43/65 e 22/44/66. O sweep ao vivo
confirmou somente os seletores 0–2 e o intervalo 0–100. Os campos persistidos
3–5 contêm 50 residual e são ignorados pelo catálogo.

## B-Man N e B-Man Bri

Identidades: `amp.b_man_n` (`03/07`) e `amp.b_man_bri` (`24/07`). Ambos usam:

- 0: GAIN
- 1: PRESENCE
- 2: VOLUME
- 3: BASS
- 4: MIDDLE
- 5: TREBLE

Todos os controles usam 0–100. B-Man N tem defaults 30/50/50/50/50/50; B-Man
Bri usa 35/50/50/50/50/50. O primeiro foi confirmado por defaults, dois dumps
diferenciais e sweep completo. O segundo foi confirmado por dump salvo
23/34/45/56/67/78 e alterações ao vivo em todos os seletores.

## Validação final no monitor

A integração visual foi aprovada no `matribox_monitor --live` com os três amps
simultâneos no preset 56B. A hidratação exibida foi:

- TWD Deluxe: `GAIN 2 / TONE 0 / VOLUME 6`;
- B-Man N: `GAIN 33 / PRESENCE 88 / VOLUME 100 / BASS 78 / MIDDLE 84 / TREBLE 90`;
- B-Man Bri: `GAIN 78 / PRESENCE 100 / VOLUME 90 / BASS 100 / MIDDLE 90 / TREBLE 100`.

O TWD Deluxe mostrou somente os três controles válidos, sem expor os campos
residuais 3–5. Valores extremos `0` e `100` também apareceram corretamente,
confirmando a hidratação e a apresentação do monitor.

## Estado

Os três modelos estão `physically_validated` e a integração do monitor está
`approved`. O catálogo permanece na versão 40, com 55 efeitos parametrizados,
214 parâmetros e 212 pendentes.

## Próximo passo exato

1. manter a pesquisa em `research/amp-parameters`;
2. iniciar o próximo layout AMP por `DARK DOUBLE` (`04 / 04 / 07`);
3. identificar os controles reais antes de reutilizar qualquer layout por inferência;
4. usar captura curta/dump diferencial quando o layout ainda não estiver comprovado;
5. validar no monitor antes de promover o próximo modelo.
