from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.commands.chain_order import parse_chain_order_response
from tools.experiments.validate_structural_chain_live import (
    NORMAL_ORDER,
    SWAPPED_ORDER,
    select_preset,
    validate_structural_state,
)


FIXTURES_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "structural_effect_state"
)


class FakeInputPort:
    def poll(self):
        return None


class FakeOutputPort:
    def __init__(self) -> None:
        self.messages = []

    def send(self, message) -> None:
        self.messages.append(message)


class ValidateStructuralChainLiveTests(unittest.TestCase):
    def load_baseline(self):
        message = (
            FIXTURES_ROOT / "phase15" / "BASELINE.bin"
        ).read_bytes()
        state = parse_chain_order_response(message)
        self.assertIsNotNone(state)
        assert state is not None
        return state

    def test_accepts_confirmed_baseline(self) -> None:
        validate_structural_state(
            self.load_baseline(),
            NORMAL_ORDER,
            label="BASELINE",
        )

    def test_accepts_confirmed_swapped_order(self) -> None:
        state = self.load_baseline()
        swapped = replace(
            state,
            internal_slot_ids=(0, 1, 2, 4, 3),
        )

        validate_structural_state(
            swapped,
            SWAPPED_ORDER,
            label="SWAPPED",
        )

    def test_rejects_wrong_model(self) -> None:
        state = self.load_baseline()
        records = list(state.effect_records_by_internal_slot)
        records[4] = replace(records[4], model_id=0x02)
        changed = replace(
            state,
            effect_records_by_internal_slot=tuple(records),
        )

        with self.assertRaisesRegex(RuntimeError, "slot 5 inesperado"):
            validate_structural_state(
                changed,
                NORMAL_ORDER,
                label="INVALID",
            )

    def test_rejects_disabled_effect(self) -> None:
        state = self.load_baseline()
        records = list(state.effect_records_by_internal_slot)
        records[2] = replace(records[2], enabled=False)
        enabled = list(state.enabled_by_internal_slot)
        enabled[2] = False
        changed = replace(
            state,
            effect_records_by_internal_slot=tuple(records),
            enabled_by_internal_slot=tuple(enabled),
        )

        with self.assertRaisesRegex(RuntimeError, "slot 3 não está ligado"):
            validate_structural_state(
                changed,
                NORMAL_ORDER,
                label="INVALID",
            )


    @patch(
        "tools.experiments.validate_structural_chain_live.time.sleep"
    )
    @patch(
        "tools.experiments.validate_structural_chain_live.wait_for_preset",
        side_effect=[
            RuntimeError("primeiro comando perdido"),
            None,
        ],
    )
    def test_select_preset_retries_after_cold_boot(
        self,
        wait_mock,
        _sleep_mock,
    ) -> None:
        output = FakeOutputPort()

        select_preset(
            FakeInputPort(),
            output,
            "55D",
        )

        self.assertEqual(wait_mock.call_count, 2)
        self.assertEqual(len(output.messages), 2)



if __name__ == "__main__":
    unittest.main()
