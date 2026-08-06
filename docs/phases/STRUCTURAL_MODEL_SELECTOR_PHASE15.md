# Fase 15 — modelo e seletor nos slots 4 e 5

A Fase 14 foi aprovada com 21/21 capturas.

Ela confirmou a classe dos cinco slots, mas os tamanhos estruturais variáveis
mostraram que ainda não é seguro integrar um parser geral de modelo e seletor
para os slots 4 e 5.

Esta fase faz mudanças controladas:

```text
somente o modelo muda
somente o seletor secundário muda
```

Também troca `DLY/WARM` por `DLY/MAG`, usando um modelo não zero para localizar
o campo do slot 5 sem ambiguidade.

## Preparação

1. Mantenha o preset salvo `56A`.
2. Confirme os cinco efeitos originais ligados.
3. Feche completamente o editor oficial.
4. Não salve o preset.

## Extração

```powershell
Expand-Archive `
  "$env:USERPROFILE\Downloads\matribox_structural_model_selector_phase15.zip" `
  -DestinationPath . `
  -Force
```

## Execução

```powershell
python -m tools.experiments.map_structural_model_selector_slots4_5
```

O resultado será salvo em:

```text
data\dumps\model_selector_slots4_5_56A_AAAAMMDD-HHMMSS.zip
```

Envie esse ZIP completo.

Não execute `git add` nem faça commit deste experimento.
