"""Validador genérico somente de leitura para parâmetros catalogados.

Uso:

    python -m tools.experiments.validate_effect_parameters_live

O script usa o mesmo motor da Fase 23B e mostra qualquer parâmetro que exista
no catálogo JSON. Nenhum comando de escrita de parâmetro é enviado.
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
        description="Escuta parâmetros definidos no catálogo JSON da Matribox."
    )
    parser.add_argument("--input-port", default=DEFAULT_INPUT_PORT)
    parser.add_argument("--output-port", default=DEFAULT_OUTPUT_PORT)
    parser.add_argument("--startup-timeout", type=float, default=DEFAULT_STARTUP_TIMEOUT_SECONDS)
    parser.add_argument("--startup-attempts", type=int, default=DEFAULT_FULL_STARTUP_ATTEMPTS)
    parser.add_argument("--global-retry-interval", type=float, default=DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS)
    parser.add_argument("--global-query-retries", type=int, default=DEFAULT_GLOBAL_QUERY_RETRIES)
    parser.add_argument("--preset-retry-interval", type=float, default=DEFAULT_CURRENT_PRESET_RETRY_INTERVAL_SECONDS)
    parser.add_argument("--preset-query-retries", type=int, default=DEFAULT_CURRENT_PRESET_QUERY_RETRIES)
    parser.add_argument("--preset-load-delay", type=float, default=DEFAULT_PRESET_LOAD_DELAY_SECONDS)
    parser.add_argument("--dump-timeout", type=float, default=DEFAULT_PRESET_DUMP_TIMEOUT_SECONDS)
    parser.add_argument("--dump-query-retries", type=int, default=DEFAULT_PRESET_DUMP_QUERY_RETRIES)
    return parser.parse_args()


def print_cataloged_inventory(core: PresetMonitorCore) -> None:
    snapshot = core.snapshot
    print("\nParâmetros catalogados na cadeia atual:")
    if snapshot is None or not snapshot.effects_ready:
        print("  cadeia ainda não disponível")
        return

    found = False
    for effect in snapshot.effects:
        for parameter in effect.parameters:
            found = True
            print(
                f"  posição {effect.visual_position} | slot interno "
                f"{effect.internal_slot} | {effect.class_name} / "
                f"{effect.model_name} / {parameter.name}"
            )
    if not found:
        print("  nenhum parâmetro catalogado neste preset")


def print_parameter_event(core: PresetMonitorCore, event) -> None:
    visual_position = "?"
    snapshot = core.snapshot
    if snapshot is not None:
        for effect in snapshot.effects:
            if effect.internal_slot == event.human_slot:
                visual_position = str(effect.visual_position)
                break

    print("\nParâmetro catalogado detectado")
    print(f"Preset: {core.current_event.label if core.current_event else '?'}")
    print(f"Slot interno: {event.human_slot}")
    print(f"Posição visual: {visual_position}")
    print(f"Efeito: {event.class_name} / {event.effect_name}")
    print(f"Parâmetro: {event.parameter_name}")
    print(f"Valor: {event.display_value}")
    print("Valor bruto: " + " ".join(f"{byte:02X}" for byte in event.encoded_value))
    print(f"Perfil: {event.protocol_profile}")
    print(f"Codec: {event.value_codec}")
    print(f"Checksum observado: 0x{event.observed_checksum:02X}")


def main() -> int:
    arguments = parse_arguments()
    core = PresetMonitorCore()

    print("FASE 23B — VALIDADOR GENÉRICO DE PARÂMETROS")
    print("------------------------------------------------")
    print("Somente leitura: nenhum parâmetro será alterado.")
    print(f"Entrada: {arguments.input_port}")
    print(f"Saída:   {arguments.output_port}")

    try:
        with mido.open_input(arguments.input_port) as input_port, mido.open_output(
            arguments.output_port
        ) as output_port:
            initialize_monitor(input_port, output_port, core, arguments)
            refresh_current_chain(input_port, output_port, core, arguments)
            print_cataloged_inventory(core)
            print("\nAltere diretamente na pedaleira um parâmetro já catalogado.")
            print("Pressione Ctrl+C para encerrar.")

            while True:
                message = input_port.poll()
                if message is None:
                    time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
                    continue

                update = process_mido_message(core, message)
                if update is None:
                    continue

                if update.parameter_event is not None:
                    print_parameter_event(core, update.parameter_event)

                if update.preset_event is not None:
                    refresh_current_chain(input_port, output_port, core, arguments)
                    print_cataloged_inventory(core)
                    continue

                if update.chain_changed:
                    print_cataloged_inventory(core)

    except KeyboardInterrupt:
        print("\n\nValidador encerrado pelo usuário.")
        return 0
    except StartupTimeoutError as error:
        print(f"\nERRO: {error}")
        return 2
    except (OSError, RuntimeError) as error:
        print(f"\nERRO MIDI: {error}")
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
