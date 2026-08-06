# Fase 22 — validação isolada do M-BOOST / GAIN

## Objetivo

Preservar e validar a leitura em tempo real do parâmetro `GAIN` do efeito
`DYN / M-BOOST` sem modificar o monitor funcional e sem enviar comandos de
alteração de parâmetro.

## Status

**Aprovado offline e fisicamente em 6 de agosto de 2026.**

O validador reconheceu corretamente uma ou várias instâncias de M-BOOST na
mesma cadeia, atribuiu cada alteração ao slot interno correto e decodificou o
GAIN em tempo real.

## Descobertas confirmadas

As quatro capturas controladas com Wireshark/USBPcap e a validação ao vivo
confirmaram:

- comando de parâmetro: `0x1C`;
- resposta SysEx: 70 bytes;
- classe DYN: `0x00`;
- modelo M-BOOST: `0x14`;
- slot interno zero-based: índices `39–40`;
- GAIN: índices `59–62`;
- faixa confirmada: `0–100`;
- ordem visual não altera o endereço do slot interno;
- a composição da cadeia não altera o formato do parâmetro;
- várias instâncias de M-BOOST podem ser diferenciadas pelo slot interno;
- os quatro nibbles do GAIN representam os 16 bits superiores de um
  `float32` little-endian;
- o parser aceita os endereços esperados dos 12 slots internos, de `00 00` a
  `00 0B`.

## Capturas controladas preservadas

As fixtures mínimas de regressão foram extraídas destas capturas:

```text
MBOOST_GAIN_SLOT1_50_0_1_2_10_25_50_75_99_100_50.pcapng
MBOOST_GAIN_SLOT2_50_0_1_2_10_25_50_75_99_100_50.pcapng
MBOOST_GAIN_SLOT2_50_0_1_2_10_25_50_75_99_100_50_WITH_DRVSKREAMERONSLOT1.pcapng
MBOOST_GAIN_REORDERED_TO_POSITION1_WITH_SKREAMER_POSITION2.pcapng
```

Os PCAPs completos permanecem fora do Git por tamanho. O repositório preserva
27 mensagens SysEx físicas de 70 bytes em `tests/fixtures/mboost_gain/`.

## Validação física ao vivo

Preset usado: `56B`.

Foram observados e aprovados:

- M-BOOST no slot interno 2;
- adição simultânea de M-BOOSTs nos slots internos 8, 10 e 12;
- múltiplas instâncias presentes ao mesmo tempo;
- valores contínuos próximos de 50;
- valores mais distantes, incluindo 55, 64, 85 e 100;
- remoção e adição de blocos durante a sessão;
- reconhecimento correto do slot interno e da posição visual;
- ausência de envio de comandos `0x1C` pelo validador.

A evidência textual completa está em:

```text
tests/fixtures/mboost_gain/live_validation_slots_2_8_10_12.txt
```

O manifesto das evidências e do protocolo fica em:

```text
tests/fixtures/mboost_gain/manifest.json
```

## Arquivos implementados

```text
tools/commands/mboost_gain.py
tools/experiments/validate_mboost_gain_live.py
tests/test_mboost_gain.py
tests/fixtures/mboost_gain/
```

`tools/commands/mboost_gain.py` é um parser puro. Ele não abre portas MIDI e
não envia comandos.

`tools/experiments/validate_mboost_gain_live.py` reutiliza a inicialização e a
leitura não destrutiva da cadeia já validadas, depois apenas escuta eventos de
parâmetro.

## Execução

Teste específico:

```powershell
python -m unittest discover -s tests -p "test_mboost_gain.py" -v
```

Validador ao vivo:

```powershell
python -m tools.experiments.validate_mboost_gain_live
```

Suíte completa no fechamento da fase:

```text
Ran 316 tests
OK
```

Também foram validados:

```powershell
python -m compileall tools tests
git diff --check
```

## Limitação deliberada

O parser desta fase é específico do M-BOOST e permanece separado do monitor
principal. Ele foi criado como prova física segura antes de iniciar uma
arquitetura genérica para centenas de efeitos e parâmetros.

## Próximo passo aprovado

A Fase 23 deve criar um catálogo declarativo e multiplataforma em JSON:

1. definir schemas versionados para classes, efeitos e parâmetros;
2. exportar automaticamente as 16 classes e 267 posições/modelos atualmente
   armazenados em `effect_catalog.py`;
3. comparar o catálogo Python legado com o JSON registro por registro;
4. criar um carregador genérico mantendo `effect_catalog.py` como fachada de
   compatibilidade;
5. cadastrar o M-BOOST/GAIN como o primeiro parâmetro fisicamente validado;
6. criar codecs e perfis de protocolo reutilizáveis;
7. somente depois integrar parâmetros ao monitor e à futura interface.
