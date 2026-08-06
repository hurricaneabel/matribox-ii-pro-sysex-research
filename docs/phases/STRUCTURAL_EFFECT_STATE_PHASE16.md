# Fase 16 — decodificador estrutural LZO1X isolado

A análise das 34 capturas físicas das Fases 14 e 15 confirmou que a resposta
estrutural completa não usa índices variáveis para modelo e seletor. Ela contém
um contêiner LZO1X codificado em nibbles.

## Camadas confirmadas

```text
SysEx
  -> pares de nibbles a partir do índice bruto 13
  -> contêiner 01 00 00 10
  -> tamanho comprimido uint32 little-endian
  -> fluxo LZO1X
  -> payload fixo de 89 bytes
```

Layout descomprimido:

```text
4–15   ordem visual dos slots internos
16–27  classe por slot interno
28–75  12 registros de quatro bytes
76–87  bypass por slot interno
88     marcador do slot da resposta ou FF
```

Registro de quatro bytes:

```text
modelo | auxiliar 1 | auxiliar 2 | seletor secundário
```

## Escopo desta fase

Esta fase adiciona somente:

```text
tools/analysis/structural_effect_state.py
tests/test_structural_effect_state.py
tests/fixtures/structural_effect_state/
```

O parser estável `tools/commands/chain_order.py` permanece intocado.
Nenhum comando MIDI é executado e nenhum teste físico é necessário.

## Testes

Execute primeiro:

```powershell
python -m pytest -q tests/test_structural_effect_state.py
```

Resultado esperado:

```text
6 passed, 34 subtests passed
```

Depois execute a suíte oficial:

```powershell
python -m pytest -q tests
```

Resultado esperado após esta fase:

```text
263 passed, 352 subtests passed
```

Não execute `git add`, não faça commit e não remova os experimentos das Fases
14 e 15. A integração com o parser estável será feita somente depois desta
validação local.
