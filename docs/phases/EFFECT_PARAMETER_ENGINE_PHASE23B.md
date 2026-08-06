# Fase 23B — motor genérico de parâmetros

## Objetivo

Substituir a interpretação exclusiva de `DYN / M-BOOST / GAIN` por uma camada
orientada pelo catálogo JSON, reutilizável por todas as classes e efeitos.

A fase permanece somente de leitura: nenhum comando de escrita `0x1C` foi
implementado ou enviado.

> **Correção posterior da Fase 24:** as capturas do COMP1 provaram que a
> mensagem `0x1C` não contém um `model_id` confiável nos índices `21–22`.
> O decoder atual primeiro produz `EffectParameterSignal`; a cadeia estrutural
> identifica o efeito do slot e só então é produzido `EffectParameterEvent`.

## Arquitetura implementada

```text
catalog/effects/*/*.json
        │ efeito, parâmetros e regras de identificação
        ▼
catalog/protocol_profiles/*.json
        │ campos e formato da mensagem
        ▼
catalog/value_codecs/*.json
        │ conversão dos nibbles para valor humano
        ▼
tools/parameters/decoder.py
        │ EffectParameterEvent genérico
        ▼
tools/parameters/state.py
        │ último valor por slot, efeito e parâmetro
        ▼
tools/commands/preset_monitor_core.py
        │ cruza evento com a cadeia estrutural atual
        ▼
monitor principal / futura interface
```

## Componentes

### `tools/parameters/codecs.py`

Executa codecs declarados pelo JSON. O primeiro codec implementado é:

```text
upper_float32_nibbles_v1
```

Ele reconstrói o valor usando os 16 bits superiores de um `float32`
little-endian enviados como quatro nibbles e valida tipo, faixa e passo do
parâmetro.

### `tools/parameters/decoder.py`

Produz um evento neutro em relação ao efeito:

```python
EffectParameterEvent(
    internal_slot_id=1,
    effect_key="dyn.m_boost",
    parameter_key="gain",
    value=50,
    protocol_profile="effect_parameter_response_1c_v1",
    value_codec="upper_float32_nibbles_v1",
)
```

O decoder não contém condicionais como `if effect == "M-BOOST"`. Na versão
corrigida pela Fase 24, ele consulta:

- slot e seletor recebidos;
- efeito real identificado pela cadeia estrutural;
- parâmetros cadastrados naquele efeito;
- perfil de mensagem;
- campos `message_match`;
- codec do valor.

### `tools/parameters/state.py`

Mantém valores independentes para múltiplas instâncias do mesmo efeito. Valores
antigos são descartados quando o efeito do slot muda ou quando ocorre troca de
preset.

### Compatibilidade da Fase 22

`tools/commands/mboost_gain.py` tornou-se uma fachada sobre o motor genérico.
O validador histórico e seus testes continuam usando a mesma API.

## Integração ao monitor

O monitor principal agora mostra os parâmetros definidos no JSON.

Antes do primeiro evento ao vivo:

```text
2. DYN / M-BOOST — ligado
     GAIN: aguardando alteração
```

Depois de alterar o controle na pedaleira:

```text
2. DYN / M-BOOST — ligado
     GAIN: 51
```

O evento só é aceito se o slot da cadeia atual realmente contiver o efeito
resolvido pelo catálogo. Isso impede que uma mensagem aparentemente compatível
seja atribuída a outro bloco.

## Validador genérico

```powershell
python -m tools.experiments.validate_effect_parameters_live
```

Mostra:

- preset;
- slot interno;
- posição visual;
- classe e efeito;
- parâmetro e valor;
- bytes brutos;
- perfil e codec;
- checksum observado.

Ele não envia alterações de parâmetros.

## Evidência offline

As 27 respostas físicas preservadas na Fase 22 foram decodificadas pelo novo
motor e comparadas com a API histórica.

Também foram testados:

- múltiplas instâncias com valores independentes;
- descarte de valores antigos ao trocar o efeito do slot;
- rejeição de valor fora da faixa;
- rejeição de segmentos fixos incompatíveis;
- cruzamento do evento com a cadeia atual;
- limpeza na troca de preset;
- apresentação no monitor antes e depois do primeiro evento.

```text
Ran 340 tests
OK
```

## Validação física concluída

A validação física foi aprovada em 6 de agosto de 2026 com o validador genérico
e o monitor principal.

Foi confirmado:

1. `GAIN: aguardando alteração` antes do primeiro evento ao vivo;
2. atualização imediata de `GAIN` ao movimentar o controle;
3. manutenção da identidade pelo slot interno após mudança de posição visual;
4. duas instâncias simultâneas de M-BOOST com valores independentes;
5. atualização isolada do slot interno 2 sem alterar o slot interno 3;
6. atualização isolada do slot interno 3 sem alterar o slot interno 2;
7. decodificação correta dos valores 50, 51, 52, 53 e 54;
8. uso real do perfil `effect_parameter_response_1c_v1` e do codec
   `upper_float32_nibbles_v1` carregados pelo catálogo JSON;
9. operação somente de leitura, sem envio de comando de escrita `0x1C`.

Resultado físico: **APROVADO**.

## Limitação consciente

O valor inicial do parâmetro ainda não é extraído do dump de preset. Por isso,
após carregar ou trocar o preset, o monitor mostra `aguardando alteração` até a
pedaleira emitir o primeiro evento daquele parâmetro.

Essa limitação não impede a catalogação dos próximos efeitos e deverá ser
investigada separadamente quando o layout de parâmetros dentro do dump for
mapeado.
