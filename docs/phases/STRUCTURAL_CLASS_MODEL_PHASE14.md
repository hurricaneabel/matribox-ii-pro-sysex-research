# Segunda correção da Fase 14

A troca do slot 2 para `AMP / B-MAN N` produziu uma resposta estrutural de `164 bytes`. A ordem continuou correta, mas o parser de bypass leu os índices fixos do layout de 168 bytes e apresentou falsamente os slots 4 e 5 como desligados.

Esta correção mantém o parser estável intocado e, somente neste experimento, valida o bypass quando a resposta tem exatamente 168 bytes. Nos demais tamanhos, valida apenas a ordem e preserva a mensagem bruta para mapear o layout variável de classe/modelo.

# Correção da Fase 14

A primeira execução recebeu uma resposta estrutural auxiliar de `128 bytes` após o comando `0x16`. Essa mensagem foi interpretada pelo parser genérico como uma cadeia vazia e encerrou o teste.

A correção preserva essa resposta de 128 bytes para análise e continua aguardando especificamente a cadeia completa de cinco efeitos. Quando ela não chega imediatamente, o programa usa o movimento reversível para obter a resposta completa.

# Fase 14 — classe e modelo na resposta estrutural

O repositório deve começar limpo:

```powershell
git status --short
```

Nenhuma saída significa que está correto.

## Objetivo

Mapear, para os slots internos 1–5:

```text
campo de classe
campo de modelo
campo de seletor secundário
```

O teste usa os comandos estáveis:

```text
0x16 — troca de modelo dentro da mesma classe
0x17 — substituição entre classes
```

Para cada slot, será feito:

```text
modelo alternativo da mesma classe
restauração do modelo original
substituição temporária por FREQ / FILTER
restauração da classe e do modelo originais
```

A cadeia inicial esperada é:

```text
1. DYN / GATE 3
2. AMP / TWD DELUXE
3. DRV / SKREAMER
4. MOD / E-CHORUS
5. DLY / WARM
```

Todos devem estar ligados.

## Preparação

1. Troque para outro preset e volte ao `56A`.
2. Confirme a cadeia acima.
3. Feche completamente o editor oficial.
4. Não salve o preset.

## Extração

Na raiz do repositório:

```powershell
Expand-Archive `
  "$env:USERPROFILE\Downloads\matribox_structural_class_model_phase14.zip" `
  -DestinationPath . `
  -Force
```

## Execução

```powershell
python -m tools.experiments.map_structural_class_model_all_slots
```

O programa tenta usar a resposta estrutural imediata de cada escrita. Quando
ela não chega, força a leitura por movimentos reversíveis `5 -> 4 -> 5`.

A restauração final é feita por:

```text
56A -> 55D -> 56A
```

O resultado será salvo em:

```text
data\dumps\structural_class_model_56A_AAAAMMDD-HHMMSS.zip
```

Envie o ZIP completo.

Não execute `git add` nem faça commit deste experimento.
