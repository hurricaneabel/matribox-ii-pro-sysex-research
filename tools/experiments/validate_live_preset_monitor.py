"""Validação física do monitor ao vivo da Matribox II Pro."""

from __future__ import annotations

import argparse
import sys

import mido

from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    format_monitor_snapshot,
)
from tools.commands.preset_monitor_live import (
    DEFAULT_GLOBAL_QUERY_RETRIES,
    DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
    DEFAULT_INPUT_PORT,
    DEFAULT_OUTPUT_PORT,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    StartupTimeoutError,
    clear_pending_messages,
    iter_monitor_updates,
    send_global_metadata_query,
    send_startup_sequence,
    wait_for_initial_snapshot,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inicializa a Matribox II Pro, carrega os metadados "
            "globais e monitora mudanças de preset."
        )
    )

    parser.add_argument(
        "--input-port",
        default=DEFAULT_INPUT_PORT,
        help="Nome da porta MIDI de entrada.",
    )
    parser.add_argument(
        "--output-port",
        default=DEFAULT_OUTPUT_PORT,
        help="Nome da porta MIDI de saída.",
    )
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=DEFAULT_STARTUP_TIMEOUT_SECONDS,
        help="Prazo em segundos para obter o primeiro estado completo.",
    )
    parser.add_argument(
        "--global-retry-interval",
        type=float,
        default=DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
        help=(
            "Tempo sem avanço antes de reenviar a consulta global."
        ),
    )
    parser.add_argument(
        "--global-query-retries",
        type=int,
        default=DEFAULT_GLOBAL_QUERY_RETRIES,
        help=(
            "Quantidade máxima de reenvios automáticos "
            "da consulta global."
        ),
    )

    return parser.parse_args()


def print_available_ports() -> None:
    print("\nPortas MIDI disponíveis:")

    print("\nEntradas:")
    for name in mido.get_input_names():
        print(f"  - {name}")

    print("\nSaídas:")
    for name in mido.get_output_names():
        print(f"  - {name}")


def main() -> int:
    arguments = parse_arguments()
    core = PresetMonitorCore()

    print("Monitor ao vivo da Matribox II Pro")
    print("---------------------------------")
    print(f"Entrada: {arguments.input_port}")
    print(f"Saída:   {arguments.output_port}")

    try:
        with mido.open_input(
            arguments.input_port
        ) as input_port, mido.open_output(
            arguments.output_port
        ) as output_port:
            removed = clear_pending_messages(
                input_port
            )

            if removed:
                print(
                    "\nMensagens antigas removidas:",
                    removed,
                )

            print("\nInicializando sessão...")

            send_startup_sequence(
                output_port,
                on_handshake=lambda current, total: print(
                    f"Handshake enviado: {current}/{total}"
                ),
            )

            print("Consulta global enviada.")
            print("Consulta do preset atual enviada.")
            print("\nAguardando respostas...")

            last_progress: tuple[int, int, int] | None = None

            def report_progress(update) -> None:
                nonlocal last_progress

                collector = update.collector_update

                if (
                    collector.accepted
                    and collector.total_size is not None
                ):
                    progress = (
                        core.fragment_count,
                        collector.covered_bytes,
                        collector.total_size,
                    )

                    if progress != last_progress:
                        print(
                            "Fragmentos globais:",
                            progress[0],
                            "|",
                            f"{progress[1]}/{progress[2]} bytes",
                        )
                        last_progress = progress

                if update.preset_event is not None:
                    print(
                        "Evento de preset recebido:",
                        update.preset_event.label,
                    )

            def report_retry(
                attempt: int,
                total: int,
                diagnostic: str,
            ) -> None:
                print(
                    "\nResposta global parou de avançar."
                )
                print(
                    "Reenviando consulta global:",
                    f"{attempt}/{total}",
                )
                print(
                    "Estado antes do reenvio:",
                    diagnostic,
                )

            initial = wait_for_initial_snapshot(
                input_port,
                core,
                timeout_seconds=arguments.startup_timeout,
                on_update=report_progress,
                retry_global_query=lambda: send_global_metadata_query(
                    output_port
                ),
                global_retry_interval_seconds=(
                    arguments.global_retry_interval
                ),
                max_global_query_retries=(
                    arguments.global_query_retries
                ),
                on_global_retry=report_retry,
            )

            print("\nMatribox II Pro conectada")
            print(
                "Metadados carregados:",
                initial.metadata_count,
                "presets",
            )
            print(
                "Fragmentos recebidos:",
                initial.fragment_count,
            )
            print(
                "Bloco global:",
                initial.global_block_size,
                "bytes",
            )
            print(
                "Reenvios da consulta global:",
                initial.global_query_retries,
            )
            print()
            print(
                format_monitor_snapshot(
                    initial.snapshot
                )
            )

            print(
                "\nMonitorando mudanças. "
                "Troque o preset na pedaleira."
            )
            print("Pressione Ctrl+C para encerrar.")

            for update in iter_monitor_updates(
                input_port,
                core,
            ):
                if (
                    update.snapshot_changed
                    and update.snapshot is not None
                ):
                    print("\n------------------------------")
                    print(
                        format_monitor_snapshot(
                            update.snapshot
                        )
                    )

    except KeyboardInterrupt:
        print("\n\nMonitor encerrado pelo usuário.")
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
