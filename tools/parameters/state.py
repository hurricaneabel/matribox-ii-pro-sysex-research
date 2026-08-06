"""Estado em memória dos últimos parâmetros recebidos por slot interno."""

from __future__ import annotations

from collections.abc import Mapping

from tools.parameters.decoder import EffectParameterEvent


class EffectParameterState:
    """Mantém o último valor conhecido sem misturar protocolo e apresentação."""

    def __init__(self) -> None:
        self._events_by_slot: dict[int, dict[str, EffectParameterEvent]] = {}

    def clear(self) -> None:
        self._events_by_slot.clear()

    def apply(self, event: EffectParameterEvent) -> bool:
        slot_events = self._events_by_slot.setdefault(event.internal_slot_id, {})
        previous = slot_events.get(event.parameter_key)

        if previous is not None and previous.effect_key != event.effect_key:
            slot_events.clear()
            previous = None

        slot_events[event.parameter_key] = event
        return previous != event

    def event_for(
        self,
        internal_slot_id: int,
        effect_key: str,
        parameter_key: str,
    ) -> EffectParameterEvent | None:
        event = self._events_by_slot.get(internal_slot_id, {}).get(parameter_key)
        if event is None or event.effect_key != effect_key:
            return None
        return event

    def retain_effects(self, effect_keys_by_internal_slot: Mapping[int, str]) -> None:
        for internal_slot_id in tuple(self._events_by_slot):
            expected_effect = effect_keys_by_internal_slot.get(internal_slot_id)
            events = self._events_by_slot[internal_slot_id]
            if expected_effect is None or any(
                event.effect_key != expected_effect for event in events.values()
            ):
                del self._events_by_slot[internal_slot_id]

    def as_mapping(self) -> Mapping[int, Mapping[str, EffectParameterEvent]]:
        return {
            slot: dict(events)
            for slot, events in self._events_by_slot.items()
        }
