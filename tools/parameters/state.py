"""Estado em memória dos últimos parâmetros recebidos por slot interno."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tools.catalog import EffectCatalog, ParameterDefinition, load_effect_catalog
from tools.parameters.codecs import ParameterValue
from tools.parameters.decoder import EffectParameterEvent


@dataclass(frozen=True, slots=True)
class ResolvedParameterValue:
    """Valor pronto para apresentação, incluindo defaults derivados do dispositivo."""

    value: ParameterValue | None
    origin: str | None
    domain_state: Mapping[str, Any] | None = None
    domain_ambiguous: bool = False


def _controller_state_for_value(
    parameter: ParameterDefinition,
    controller_value: ParameterValue,
) -> Mapping[str, Any] | None:
    states = parameter.value_domain.get("states", [])
    if not isinstance(states, list):
        return None
    for state in states:
        if not isinstance(state, dict):
            continue
        if state.get("controller_value") == controller_value:
            return state
    return None


def _state_accepts_observed_value(
    parameter: ParameterDefinition,
    state: Mapping[str, Any],
    value: ParameterValue,
) -> bool:
    presentation = state.get("presentation", {})
    if not isinstance(presentation, dict):
        return False
    kind = presentation.get("kind")
    if kind == "enum":
        choices = presentation.get("choices", [])
        if not isinstance(choices, list):
            return False
        return any(
            isinstance(choice, dict) and choice.get("value") == value
            for choice in choices
        )
    if kind == "numeric":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if parameter.minimum is not None and value < parameter.minimum:
            return False
        if parameter.maximum is not None and value > parameter.maximum:
            return False
        return True
    return False


class EffectParameterState:
    """Mantém valores observados e resolve defaults derivados sem fabricar SysEx."""

    def __init__(self, catalog: EffectCatalog | None = None) -> None:
        self.catalog = catalog if catalog is not None else load_effect_catalog()
        self._events_by_slot: dict[int, dict[str, EffectParameterEvent]] = {}
        self._origins_by_slot: dict[int, dict[str, str]] = {}

    def clear(self) -> None:
        self._events_by_slot.clear()
        self._origins_by_slot.clear()

    def _invalidate_dependents_for_controller(
        self,
        event: EffectParameterEvent,
        *,
        previous: EffectParameterEvent | None,
        origin: str,
    ) -> None:
        if previous is not None and previous.value == event.value:
            return
        try:
            effect = self.catalog.effect_by_key(event.effect_key)
        except KeyError:
            return
        slot_events = self._events_by_slot.setdefault(event.internal_slot_id, {})
        for parameter in effect.parameters:
            domain = parameter.value_domain
            if not domain:
                continue
            if domain.get("controller_parameter") != event.parameter_key:
                continue
            if domain.get("reset_on_controller_change", True):
                dependent_origin = self._origins_by_slot.get(
                    event.internal_slot_id, {}
                ).get(parameter.key)
                if (
                    origin == "saved_preset_dump"
                    and dependent_origin == "observed_usb"
                ):
                    continue
                slot_events.pop(parameter.key, None)
                self._origins_by_slot.setdefault(
                    event.internal_slot_id, {}
                ).pop(parameter.key, None)

    def apply(
        self,
        event: EffectParameterEvent,
        *,
        origin: str = "observed_usb",
    ) -> bool:
        slot_events = self._events_by_slot.setdefault(event.internal_slot_id, {})
        slot_origins = self._origins_by_slot.setdefault(
            event.internal_slot_id, {}
        )
        previous = slot_events.get(event.parameter_key)
        previous_origin = slot_origins.get(event.parameter_key)

        if previous is not None and previous.effect_key != event.effect_key:
            slot_events.clear()
            slot_origins.clear()
            previous = None
            previous_origin = None

        slot_events[event.parameter_key] = event
        slot_origins[event.parameter_key] = origin
        self._invalidate_dependents_for_controller(
            event,
            previous=previous,
            origin=origin,
        )
        return previous != event or previous_origin != origin

    def origin_for(
        self,
        internal_slot_id: int,
        effect_key: str,
        parameter_key: str,
    ) -> str | None:
        if self.event_for(
            internal_slot_id,
            effect_key,
            parameter_key,
        ) is None:
            return None
        return self._origins_by_slot.get(internal_slot_id, {}).get(parameter_key)

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

    def resolve_parameter(
        self,
        internal_slot_id: int,
        effect_key: str,
        parameter: ParameterDefinition,
    ) -> ResolvedParameterValue:
        """Resolve valor observado ou default implícito de um domínio condicionado."""

        event = self.event_for(internal_slot_id, effect_key, parameter.key)
        domain = parameter.value_domain
        if not domain:
            return ResolvedParameterValue(
                value=event.value if event is not None else None,
                origin=(
                    self._origins_by_slot.get(internal_slot_id, {}).get(
                        parameter.key
                    )
                    if event is not None
                    else None
                ),
            )

        controller_key = domain.get("controller_parameter")
        controller_event = (
            self.event_for(internal_slot_id, effect_key, controller_key)
            if isinstance(controller_key, str)
            else None
        )
        if controller_event is not None:
            state = _controller_state_for_value(parameter, controller_event.value)
            if event is not None:
                return ResolvedParameterValue(
                    value=event.value,
                    origin=self._origins_by_slot.get(
                        internal_slot_id, {}
                    ).get(parameter.key),
                    domain_state=state,
                )
            if state is not None:
                return ResolvedParameterValue(
                    value=state.get("default_value"),
                    origin="derived_device_rule",
                    domain_state=state,
                )
            return ResolvedParameterValue(value=None, origin=None)

        if event is None:
            return ResolvedParameterValue(value=None, origin=None)

        states = domain.get("states", [])
        matching_states = [
            state
            for state in states
            if isinstance(state, dict)
            and _state_accepts_observed_value(parameter, state, event.value)
        ] if isinstance(states, list) else []
        if len(matching_states) == 1:
            return ResolvedParameterValue(
                value=event.value,
                origin=self._origins_by_slot.get(
                    internal_slot_id, {}
                ).get(parameter.key),
                domain_state=matching_states[0],
            )
        return ResolvedParameterValue(
            value=event.value,
            origin=self._origins_by_slot.get(
                internal_slot_id, {}
            ).get(parameter.key),
            domain_ambiguous=True,
        )

    def retain_effects(self, effect_keys_by_internal_slot: Mapping[int, str]) -> None:
        for internal_slot_id in tuple(self._events_by_slot):
            expected_effect = effect_keys_by_internal_slot.get(internal_slot_id)
            events = self._events_by_slot[internal_slot_id]
            if expected_effect is None or any(
                event.effect_key != expected_effect for event in events.values()
            ):
                del self._events_by_slot[internal_slot_id]
                self._origins_by_slot.pop(internal_slot_id, None)

    def as_mapping(self) -> Mapping[int, Mapping[str, EffectParameterEvent]]:
        return {
            slot: dict(events)
            for slot, events in self._events_by_slot.items()
        }
