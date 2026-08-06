# Fase 17 — integração do estado estrutural

## Objetivo

Promover o decodificador LZO1X validado na Fase 16 para o caminho estável e
integrá-lo a `parse_chain_order_response()` sem quebrar a API existente.

## Alterações

- implementação estável em `tools/commands/structural_effect_state.py`;
- fachada de compatibilidade em `tools/analysis/structural_effect_state.py`;
- `tools/commands/chain_order.py` passa a ler o payload descomprimido;
- ordem e bypass continuam disponíveis pelas propriedades históricas;
- classe, modelo, auxiliares e seletor ficam disponíveis por slot interno;
- resposta auxiliar de 128 bytes continua sendo ignorada;
- testes das 34 capturas das Fases 14 e 15 passam também pelo parser estável.

## API acrescentada

```python
record = state.record_for_internal_slot(4)
record.class_id
record.model_id
record.auxiliary_1
record.auxiliary_2
record.secondary_selector
record.enabled

state.record_at_visual_position(1)
state.visual_effect_records
state.class_ids_by_internal_slot
state.model_ids_by_internal_slot
state.secondary_selectors_by_internal_slot
state.response_slot_marker
state.decompressed_payload
```

## Validação local

```text
python -m unittest discover -s tests -p "test_*.py"

Ran 269 tests
OK
```

Nenhum comando MIDI é executado por esta integração.
