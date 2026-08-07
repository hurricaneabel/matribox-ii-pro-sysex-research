"""Monitor final de preset, etiqueta e cadeia da Matribox II Pro.

Uso:

    python -m tools.commands.matribox_monitor
    python -m tools.commands.matribox_monitor --live
    python -m tools.commands.matribox_monitor --live --log monitor.txt

O monitor carrega os metadados globais, identifica o preset atual e processa
respostas estruturais, bypass e parâmetros catalogados para exibir os efeitos
na ordem visual e atualizar estado e valores em tempo real. A inicialização
possui reenvios automáticos para o primeiro comando perdido após cold boot.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import time
from typing import Callable, TextIO

import mido

from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    format_monitor_snapshot,
)
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
    clear_pending_messages,
    process_mido_message,
    read_preset_chain_state,
    send_current_preset_query,
    send_global_metadata_query,
    send_startup_sequence,
    wait_for_initial_snapshot,
)


DEFAULT_FULL_STARTUP_ATTEMPTS = 2
CURSOR_HOME_SEQUENCE = "\033[H"
CLEAR_SCREEN_SEQUENCE = "\033[2J"
CLEAR_TO_END_SEQUENCE = "\033[J"
ALTERNATE_SCREEN_ENTER_SEQUENCE = "\033[?1049h"
ALTERNATE_SCREEN_EXIT_SEQUENCE = "\033[?1049l"
HIDE_CURSOR_SEQUENCE = "\033[?25l"
SHOW_CURSOR_SEQUENCE = "\033[?25h"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mostra o preset atual, nome, etiqueta e cadeia de efeitos "
            "da Matribox II Pro."
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
        help="Prazo de cada tentativa para obter o estado inicial.",
    )
    parser.add_argument(
        "--startup-attempts",
        type=int,
        default=DEFAULT_FULL_STARTUP_ATTEMPTS,
        help="Quantidade de tentativas completas após cold boot.",
    )
    parser.add_argument(
        "--global-retry-interval",
        type=float,
        default=DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
        help="Intervalo para reenviar a consulta global.",
    )
    parser.add_argument(
        "--global-query-retries",
        type=int,
        default=DEFAULT_GLOBAL_QUERY_RETRIES,
        help="Quantidade máxima de reenvios da consulta global.",
    )
    parser.add_argument(
        "--preset-retry-interval",
        type=float,
        default=DEFAULT_CURRENT_PRESET_RETRY_INTERVAL_SECONDS,
        help="Intervalo para reenviar a consulta do preset atual.",
    )
    parser.add_argument(
        "--preset-query-retries",
        type=int,
        default=DEFAULT_CURRENT_PRESET_QUERY_RETRIES,
        help="Quantidade máxima de reenvios do preset atual.",
    )
    parser.add_argument(
        "--preset-load-delay",
        type=float,
        default=DEFAULT_PRESET_LOAD_DELAY_SECONDS,
        help="Atraso antes de solicitar a cadeia após uma troca.",
    )
    parser.add_argument(
        "--dump-timeout",
        type=float,
        default=DEFAULT_PRESET_DUMP_TIMEOUT_SECONDS,
        help="Prazo de cada tentativa para receber o dump do preset.",
    )
    parser.add_argument(
        "--dump-query-retries",
        type=int,
        default=DEFAULT_PRESET_DUMP_QUERY_RETRIES,
        help="Quantidade máxima de reenvios do dump do preset.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Atualiza a mesma tela a cada mudança em vez de imprimir "
            "um novo bloco de estado."
        ),
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        metavar="ARQUIVO",
        help=(
            "Salva eventos compactos em um arquivo de texto. Pode ser "
            "combinado com --live para manter a tela limpa e preservar "
            "um histórico das alterações."
        ),
    )

    arguments = parser.parse_args(argv)

    if arguments.startup_attempts <= 0:
        parser.error("--startup-attempts deve ser maior que zero.")

    if arguments.preset_load_delay < 0:
        parser.error("--preset-load-delay não pode ser negativo.")

    if arguments.dump_timeout <= 0:
        parser.error("--dump-timeout deve ser maior que zero.")

    if arguments.dump_query_retries < 0:
        parser.error("--dump-query-retries não pode ser negativo.")

    return arguments


def enter_live_screen(*, stream: TextIO | None = None) -> None:
    """Entra no buffer alternativo para não poluir o scrollback normal."""

    target = stream if stream is not None else sys.stdout
    target.write(ALTERNATE_SCREEN_ENTER_SEQUENCE)
    target.write(HIDE_CURSOR_SEQUENCE)
    target.flush()


def exit_live_screen(*, stream: TextIO | None = None) -> None:
    """Restaura cursor e buffer normal do terminal."""

    target = stream if stream is not None else sys.stdout
    target.write(SHOW_CURSOR_SEQUENCE)
    target.write(ALTERNATE_SCREEN_EXIT_SEQUENCE)
    target.flush()


def redraw_screen(text: str, *, stream: TextIO | None = None) -> None:
    """Redesenha o quadro inteiro sem deixar caracteres da tela anterior."""

    target = stream if stream is not None else sys.stdout
    # Limpar o display antes de reposicionar o cursor evita restos de linhas
    # quando o novo snapshot possui textos menores que o quadro anterior.
    target.write(CLEAR_SCREEN_SEQUENCE)
    target.write(CURSOR_HOME_SEQUENCE)
    target.write(text.rstrip("\n"))
    target.flush()


def format_live_screen(
    snapshot,
    *,
    input_port_name: str,
    output_port_name: str,
    log_path: Path | None = None,
) -> str:
    """Monta o painel estável usado pelo modo ``--live``."""

    lines = [
        "Matribox SysCon — monitor ao vivo",
        "---------------------------------",
        f"Entrada: {input_port_name}",
        f"Saída:   {output_port_name}",
        "",
        format_monitor_snapshot(snapshot),
        "",
        "Modo: painel ao vivo (--live)",
    ]

    if log_path is not None:
        lines.append(f"Log: {log_path}")

    lines.append("Pressione Ctrl+C para encerrar.")
    return "\n".join(lines)


def _effect_name_for_slot(snapshot, human_slot: int) -> str | None:
    if snapshot is None:
        return None
    for effect in snapshot.effects:
        if effect.internal_slot == human_slot:
            return effect.model_name
    return None


def format_compact_log_entries(update) -> tuple[str, ...]:
    """Converte uma atualização do monitor em eventos compactos de log."""

    entries: list[str] = []

    if update.preset_event is not None:
        entries.append(f"preset={update.preset_event.label}")

    if update.parameter_event is not None:
        event = update.parameter_event
        entries.append(
            f"slot={event.human_slot} {event.effect_name} "
            f"{event.parameter_name} {event.display_value}"
        )

    if update.bypass_event is not None:
        event = update.bypass_event
        effect_name = _effect_name_for_slot(update.snapshot, event.human_slot)
        effect_prefix = f" {effect_name}" if effect_name else ""
        state = "ligado" if event.enabled else "desligado"
        entries.append(
            f"slot={event.human_slot}{effect_prefix} BYPASS {state}"
        )

    # Uma resposta estrutural sem evento de preset/bypass também pode mudar
    # ordem, modelo ou ocupação de slots. Registramos isso sem duplicar os
    # eventos mais específicos acima.
    if (
        update.chain_changed
        and update.preset_event is None
        and update.bypass_event is None
    ):
        entries.append("chain=updated")

    return tuple(entries)


def write_compact_log_entries(
    stream: TextIO,
    update,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> None:
    """Acrescenta ao arquivo apenas as mudanças relevantes da atualização."""

    entries = format_compact_log_entries(update)
    if not entries:
        return

    timestamp = now().strftime("%H:%M:%S")
    for entry in entries:
        stream.write(f"{timestamp} {entry}\n")
    stream.flush()


def print_available_ports() -> None:
    print("\nPortas MIDI disponíveis:")

    print("\nEntradas:")
    for name in mido.get_input_names():
        print(f"  - {name}")

    print("\nSaídas:")
    for name in mido.get_output_names():
        print(f"  - {name}")


def initialize_monitor(
    input_port,
    output_port,
    core: PresetMonitorCore,
    arguments: argparse.Namespace,
    *,
    verbose: bool = True,
):
    """Executa uma inicialização robusta, incluindo cold boot."""

    last_error: StartupTimeoutError | None = None

    for startup_attempt in range(1, arguments.startup_attempts + 1):
        core.reset()
        clear_pending_messages(input_port)

        if verbose:
            print(
                f"\nInicializando sessão: tentativa "
                f"{startup_attempt}/{arguments.startup_attempts}"
            )

        send_startup_sequence(
            output_port,
            on_handshake=(
                (lambda current, total: print(
                    f"Handshake enviado: {current}/{total}"
                ))
                if verbose
                else None
            ),
        )

        if verbose:
            print("Consulta global enviada.")
            print("Consulta do preset atual enviada.")
            print("Aguardando respostas...")

        last_progress: tuple[int, int, int] | None = None

        def report_progress(update) -> None:
            nonlocal last_progress

            collector = update.collector_update

            if collector.accepted and collector.total_size is not None:
                progress = (
                    core.fragment_count,
                    collector.covered_bytes,
                    collector.total_size,
                )

                if progress != last_progress:
                    if verbose:
                        print(
                            "Fragmentos globais:",
                            progress[0],
                            "|",
                            f"{progress[1]}/{progress[2]} bytes",
                        )
                    last_progress = progress

            if verbose and update.preset_event is not None:
                print(
                    "Evento de preset recebido:",
                    update.preset_event.label,
                )

            if (
                verbose
                and update.chain_changed
                and update.chain_state is not None
            ):
                print(
                    "Cadeia estrutural recebida:",
                    update.chain_state.effect_count,
                    "efeitos",
                )

        def report_global_retry(
            attempt: int,
            total: int,
            diagnostic: str,
        ) -> None:
            if not verbose:
                return
            print(
                "Consulta global sem avanço; reenviando:",
                f"{attempt}/{total}",
            )
            print("Estado:", diagnostic)

        def report_preset_retry(
            attempt: int,
            total: int,
            diagnostic: str,
        ) -> None:
            if not verbose:
                return
            print(
                "Preset atual ainda não respondeu; reenviando:",
                f"{attempt}/{total}",
            )
            print("Estado:", diagnostic)

        try:
            return wait_for_initial_snapshot(
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
                on_global_retry=report_global_retry,
                retry_current_preset_query=lambda: send_current_preset_query(
                    output_port
                ),
                current_preset_retry_interval_seconds=(
                    arguments.preset_retry_interval
                ),
                max_current_preset_query_retries=(
                    arguments.preset_query_retries
                ),
                on_current_preset_retry=report_preset_retry,
            )
        except StartupTimeoutError as error:
            last_error = error

            if startup_attempt < arguments.startup_attempts:
                if verbose:
                    print("\nA primeira inicialização não completou.")
                    print("Repetindo automaticamente a sessão completa...")
                continue

            raise

    assert last_error is not None
    raise last_error


def print_snapshot(snapshot) -> None:
    """Imprime uma atualização visual separada no terminal."""

    print("\n---------------------------------")
    print(format_monitor_snapshot(snapshot))


def should_refresh_after_structural_change(update) -> bool:
    """Indica mudança que exige novo dump para hidratar efeitos adicionados."""

    return (
        update.preset_event is None
        and update.chain_changed
        and update.chain_state is not None
    )


def refresh_current_chain(
    input_port,
    output_port,
    core: PresetMonitorCore,
    arguments: argparse.Namespace,
    *,
    on_snapshot: Callable[[object], None] = print_snapshot,
    verbose: bool = True,
) -> bool:
    """Lê a cadeia do preset mais recente, reiniciando se ele mudar."""

    while core.current_event is not None:
        target_index = core.current_event.index
        target_label = core.current_event.label

        if verbose:
            print(f"\nLendo cadeia de efeitos de {target_label}...")

        result = read_preset_chain_state(
            input_port,
            output_port,
            core,
            target_index,
            load_delay_seconds=arguments.preset_load_delay,
            timeout_seconds=arguments.dump_timeout,
            max_query_retries=arguments.dump_query_retries,
            on_query=(
                (lambda current, total: print(
                    "Pedido do dump:",
                    f"{current}/{total}",
                ))
                if verbose
                else None
            ),
            on_progress=(
                (lambda covered, total: print(
                    "Dump do preset:",
                    f"{covered}/{total} bytes",
                ))
                if verbose
                else None
            ),
            require_complete_dump=True,
        )

        if result.interrupted:
            snapshot = core.snapshot

            if snapshot is not None:
                on_snapshot(snapshot)

            continue

        if result.complete:
            snapshot = core.snapshot

            if snapshot is not None:
                on_snapshot(snapshot)

            return True

        progress = (
            f"{result.covered_bytes}/{result.total_size} bytes"
            if result.total_size is not None
            else "nenhum fragmento aceito"
        )
        if verbose:
            print(
                f"Não foi possível ler a cadeia de {target_label}: {progress}."
            )
        return False

    return False


def main() -> int:
    arguments = parse_arguments()
    core = PresetMonitorCore()
    log_stream: TextIO | None = None

    if arguments.log is not None:
        try:
            log_stream = arguments.log.open(
                "a",
                encoding="utf-8",
                newline="\n",
            )
        except OSError as error:
            print(f"ERRO AO ABRIR LOG: {error}")
            return 4

    def present_snapshot(snapshot) -> None:
        if arguments.live:
            redraw_screen(
                format_live_screen(
                    snapshot,
                    input_port_name=arguments.input_port,
                    output_port_name=arguments.output_port,
                    log_path=arguments.log,
                )
            )
        else:
            print_snapshot(snapshot)

    live_screen_active = False
    if arguments.live:
        enter_live_screen()
        live_screen_active = True
        redraw_screen(
            "Matribox SysCon — monitor ao vivo\n"
            "---------------------------------\n"
            f"Entrada: {arguments.input_port}\n"
            f"Saída:   {arguments.output_port}\n\n"
            "Inicializando sessão..."
        )
    else:
        print("Matribox SysCon — monitor ao vivo")
        print("---------------------------------")
        print(f"Entrada: {arguments.input_port}")
        print(f"Saída:   {arguments.output_port}")

    exit_message: str | None = None
    exit_code = 0

    try:
        with mido.open_input(
            arguments.input_port
        ) as input_port, mido.open_output(
            arguments.output_port
        ) as output_port:
            initial = initialize_monitor(
                input_port,
                output_port,
                core,
                arguments,
                verbose=not arguments.live,
            )

            if arguments.live:
                redraw_screen(
                    format_live_screen(
                        initial.snapshot,
                        input_port_name=arguments.input_port,
                        output_port_name=arguments.output_port,
                        log_path=arguments.log,
                    )
                )
            else:
                print("\nMatribox II Pro conectada")
                print(
                    "Metadados carregados:",
                    initial.metadata_count,
                    "presets",
                )
                print(
                    "Reenvios da consulta global:",
                    initial.global_query_retries,
                )
                print(
                    "Reenvios do preset atual:",
                    initial.current_preset_query_retries,
                )
                print()
                print(format_monitor_snapshot(initial.snapshot))

            refresh_current_chain(
                input_port,
                output_port,
                core,
                arguments,
                on_snapshot=present_snapshot,
                verbose=not arguments.live,
            )

            if not arguments.live:
                print(
                    "\nMonitorando mudanças. "
                    "Troque o preset diretamente na pedaleira."
                )
                print("Pressione Ctrl+C para encerrar.")

            while True:
                message = input_port.poll()

                if message is None:
                    time.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
                    continue

                update = process_mido_message(
                    core,
                    message,
                )

                if update is None:
                    continue

                if log_stream is not None:
                    write_compact_log_entries(log_stream, update)

                if update.preset_event is not None:
                    if update.snapshot is not None:
                        present_snapshot(update.snapshot)

                    refresh_current_chain(
                        input_port,
                        output_port,
                        core,
                        arguments,
                        on_snapshot=present_snapshot,
                        verbose=not arguments.live,
                    )
                    continue

                if should_refresh_after_structural_change(update):
                    refresh_current_chain(
                        input_port,
                        output_port,
                        core,
                        arguments,
                        on_snapshot=present_snapshot,
                        verbose=not arguments.live,
                    )
                    continue

                if (
                    update.snapshot_changed
                    and update.snapshot is not None
                ):
                    present_snapshot(update.snapshot)

    except KeyboardInterrupt:
        exit_message = "Monitor encerrado pelo usuário."
        exit_code = 0

    except StartupTimeoutError as error:
        exit_message = f"ERRO: {error}"
        exit_code = 2

    except (OSError, RuntimeError) as error:
        exit_message = f"ERRO MIDI: {error}"
        exit_code = 3

    finally:
        if live_screen_active:
            exit_live_screen()
        if log_stream is not None:
            log_stream.close()

    if exit_message is not None:
        print(exit_message)

    if exit_code == 3:
        print_available_ports()

    return exit_code



if __name__ == "__main__":
    sys.exit(main())
