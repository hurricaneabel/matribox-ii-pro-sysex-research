"""Valida ao vivo o GAIN do DYN / M-BOOST em qualquer slot de 1 a 12.

Uso:

    python -m tools.experiments.validate_mboost_gain_live

O experimento reutiliza a inicialização e a leitura não destrutiva da cadeia
do monitor estável. Depois, apenas escuta respostas de parâmetro. Nenhum
comando de alteração de GAIN é enviado pelo script.
"""

from __future__ import annotations

import argparse
import sys
import time

import mido

from tools.commands.matribox_monitor import (
    DEFAULT_FULL_STARTUP_ATTEMPTS,
    initialize_monitor,
    refresh_current_chain,
)
from tools.commands.mboost_gain import (
    DYN_CLASS_ID,
    MBOOST_MODEL_ID,
    MBOOST_SECONDARY_SELECTOR,
    MBoostGainProtocolError,
    parse_mboost_gain_response,
)
from tools.commands.preset_monitor_core import PresetMonitorCore
from tools.commands.preset_monitor_live import (
    DEFAULT_CURRENT_PRESET_QUERY_RETRIES,
    DEFAULT_CURRENT_PRESET_RETRY_INTERVAL_SECONDS,
    DEFAULT_GLOBAL_QUERY_RETRIES,
    DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
    DEFAULT_INPUT_PORT,
    DEFAULT_OUTPUT_PORT,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_PRESET_DUMP_QUERY_RETRIES,
    DEFAULT_PRESET_DUMP_TIMEOUT_SECONDS,
    DEFAULT_PRESET_LOAD_DELAY_SECONDS,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    StartupTimeoutError,
    process_mido_message,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Escuta o GAIN do DYN / M-BOOST e confirma slot interno e "
            "posição visual sem alterar o preset."
        )
    )
    parser.add_argument("--input-port", default=DEFAULT_INPUT_PORT)
    parser.add_argument("--output-port", default=DEFAULT_OUTPUT_PORT)
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=DEFAULT_STARTUP_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--startup-attempts",
        type=int,
        default=DEFAULT_FULL_STARTUP_ATTEMPTS,
    )
    parser.add_argument(
        "--global-retry-interval",
        type=float,
        default=DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--global-query-retries",
        type=int,
        default=DEFAULT_GLOBAL_QUERY_RETRIES,
    )
    parser.add_argument(
        "--preset-retry-interval",
        type=float,
        default=DEFAULT_CURRENT_PRESET_RETRY_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--preset-query-retries",
        type=int,
        default=DEFAULT_CURRENT_PRESET_QUERY_RETRIES,
    )
    parser.add_argument(
        "--preset-load-delay",
        type=float,
        default=DEFAULT_PRESET_LOAD_DELAY_SECONDS,
    )
    parser.add_argument(
        "--dump-timeout",
        type=float,
        default=DEFAULT_PRESET_DUMP_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--dump-query-retries",
        type=int,
        default=DEFAULT_PRESET_DUMP_QUERY_RETRIES,
    )
    return parser.parse_args()


def print_available_ports() -> None:
    print("\nEntradas MIDI disponíveis:")
    for name in mido.get_input_names():
        print(f"  - {name}")

    print("\nSaídas MIDI disponíveis:")
    for name in mido.get_output_names():
        print(f"  - {name}")


def _is_mboost_record(record) -> bool:
    return (
        record.class_id == DYN_CLASS_ID
        and record.model_id == MBOOST_MODEL_ID
        and record.secondary_selector == MBOOST_SECONDARY_SELECTOR
    )


def _visual_position_for_internal_id(chain_state, internal_slot_id: int) -> int:
    return chain_state.internal_slot_ids.index(internal_slot_id) + 1


def print_mboost_inventory(core: PresetMonitorCore) -> None:
    chain = core.current_chain

    if chain is None:
        print("Cadeia ainda não disponível.")
        return

    found = []

    for internal_slot_id in chain.internal_slot_ids:
        record = chain.effect_records_by_internal_slot[internal_slot_id]

        if not _is_mboost_record(record):
            continue

        found.append(
            (
                internal_slot_id + 1,
                _visual_position_for_internal_id(chain, internal_slot_id),
            )
        )

    print("\nM-BOOSTs reconhecidos na cadeia:")

    if not found:
        print("  nenhum M-BOOST encontrado")
        return

    for internal_slot, visual_position in found:
        print(
            f"  slot interno {internal_slot} | "
            f"posição visual {visual_position}"
        )


def print_gain_event(core: PresetMonitorCore, event) -> None:
    chain = core.current_chain

    if chain is None:
        print(
            f"\nGAIN recebido no slot interno {event.human_slot}, "
            "mas a cadeia ainda não foi carregada."
        )
        return

    if event.internal_slot_id not in chain.internal_slot_ids:
        print(
            f"\nGAIN recebido no slot interno {event.human_slot}, "
            "mas esse slot não está ativo na cadeia atual."
        )
        return

    record = chain.effect_records_by_internal_slot[event.internal_slot_id]

    if not _is_mboost_record(record):
        print(
            f"\nMensagem 0x1C compatível com M-BOOST recebida no slot "
            f"interno {event.human_slot}, mas o dump atual identifica "
            "outro efeito nesse slot."
        )
        return

    visual_position = _visual_position_for_internal_id(
        chain,
        event.internal_slot_id,
    )

    print("\nM-BOOST / GAIN detectado")
    print(f"Preset: {core.current_event.label if core.current_event else '?'}")
    print(f"Slot interno: {event.human_slot}")
    print(f"Posição visual: {visual_position}")
    print(
        "Valor bruto: "
        + " ".join(f"{byte:02X}" for byte in event.encoded_gain)
    )
    print(f"GAIN: {event.gain}")
    print(f"Checksum observado: 0x{event.observed_checksum:02X}")


def main() -> int:
    arguments = parse_arguments()
    core = PresetMonitorCore()

    print("FASE 22 — VALIDADOR M-BOOST / GAIN")
    print("------------------------------------")
    print("Somente leitura: o script não altera o GAIN.")
    print(f"Entrada: {arguments.input_port}")
    print(f"Saída:   {arguments.output_port}")

    try:
        with mido.open_input(
            arguments.input_port
        ) as input_port, mido.open_output(
            arguments.output_port
        ) as output_port:
            initialize_monitor(
                input_port,
                output_port,
                core,
                arguments,
            )

            refresh_current_chain(
                input_port,
                output_port,
                core,
                arguments,
            )

            print_mboost_inventory(core)
            print(
                "\nAltere somente o GAIN de qualquer M-BOOST diretamente "
                "na pedaleira."
            )
            print("O slot pode ser qualquer um entre 1 e 12.")
            print("Pressione Ctrl+C para encerrar.")

            while True:
                message = input_port.poll()

                if message is None:
                    time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
                    continue

                if getattr(message, "type", None) == "sysex":
                    raw_message = bytes(message.bin())

                    try:
                        gain_event = parse_mboost_gain_response(raw_message)
                    except MBoostGainProtocolError as error:
                        print(f"\nResposta M-BOOST recusada: {error}")
                        gain_event = None

                    if gain_event is not None:
                        print_gain_event(core, gain_event)

                update = process_mido_message(core, message)

                if update is None:
                    continue

                if update.preset_event is not None:
                    refresh_current_chain(
                        input_port,
                        output_port,
                        core,
                        arguments,
                    )
                    print_mboost_inventory(core)
                    continue

                if update.chain_changed:
                    print_mboost_inventory(core)

    except KeyboardInterrupt:
        print("\n\nValidador encerrado pelo usuário.")
        return 0

    except StartupTimeoutError as error:
        print(f"\nERRO: {error}")
        return 2

    except (OSError, RuntimeError) as error:
        print(f"\nERRO MIDI: {error}")
        print_available_ports()
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
