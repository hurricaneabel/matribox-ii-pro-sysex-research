"""Validação física da resposta estrutural variável com cinco efeitos.

O experimento usa movimentos visuais controlados, interpreta a ordem devolvida
pela Matribox e restaura automaticamente a cadeia inicial.

O editor oficial deve permanecer completamente fechado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time
import zipfile

import mido

from tools.commands.chain_order import (
    ChainOrderState,
    apply_visual_move,
    parse_chain_order_response,
)
from tools.commands.move_effect_position import (
    build_move_message,
)
from tools.commands.preset_state import (
    build_select_preset,
    parse_preset_event,
)
from tools.commands.request_preset_dump import (
    SESSION_STABILIZATION_SECONDS,
    clear_pending_messages,
    send_session_handshake,
)


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"
PRESET_LABEL = "56A"

EXPECTED_EFFECT_COUNT = 5
POLL_INTERVAL_SECONDS = 0.01
SELECTION_TIMEOUT_SECONDS = 3.0
RESPONSE_TIMEOUT_SECONDS = 5.0

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = PROJECT_ROOT / "data" / "dumps"


@dataclass(frozen=True, slots=True)
class MovementResult:
    """Resultado recebido após um movimento."""

    label: str
    source_position: int
    destination_position: int
    state: ChainOrderState
    received_messages: tuple[bytes, ...]


def full_bytes_to_mido(
    message: bytes,
) -> mido.Message:
    """Converte SysEx completo para mensagem Mido."""

    if (
        len(message) < 2
        or message[0] != 0xF0
        or message[-1] != 0xF7
    ):
        raise ValueError(
            "Mensagem SysEx completa inválida."
        )

    return mido.Message(
        "sysex",
        data=message[1:-1],
    )


def wait_for_preset_confirmation(
    input_port,
    expected_label: str,
) -> None:
    """Aguarda confirmação do preset selecionado."""

    deadline = (
        time.monotonic()
        + SELECTION_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if message.type != "sysex":
            continue

        event = parse_preset_event(
            bytes(message.bin())
        )

        if event is None:
            continue

        print(
            "Evento de preset recebido:",
            event.label,
        )

        if event.label == expected_label:
            return

    raise RuntimeError(
        "A confirmação do preset "
        f"{expected_label} não chegou."
    )


def select_preset(
    input_port,
    output_port,
) -> None:
    """Seleciona o 56A e exige confirmação."""

    clear_pending_messages(input_port)

    output_port.send(
        full_bytes_to_mido(
            build_select_preset(
                PRESET_LABEL
            )
        )
    )

    wait_for_preset_confirmation(
        input_port,
        PRESET_LABEL,
    )


def wait_for_chain_state(
    input_port,
) -> tuple[
    ChainOrderState,
    tuple[bytes, ...],
]:
    """Aguarda uma resposta estrutural de cadeia variável."""

    received: list[bytes] = []
    deadline = (
        time.monotonic()
        + RESPONSE_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if message.type != "sysex":
            continue

        raw_message = bytes(message.bin())
        received.append(raw_message)

        state = parse_chain_order_response(
            raw_message
        )

        if state is not None:
            return (
                state,
                tuple(received),
            )

        event = parse_preset_event(
            raw_message
        )

        if event is not None:
            print(
                "  Evento intermediário:",
                event.label,
            )
        else:
            print(
                "  SysEx intermediário:",
                len(raw_message),
                "bytes",
            )
            print(
                "  ",
                raw_message.hex(" ").upper(),
            )

    raise RuntimeError(
        "A resposta estrutural de cadeia não chegou."
    )


def perform_move(
    input_port,
    output_port,
    label: str,
    source_position: int,
    destination_position: int,
) -> MovementResult:
    """Envia movimento e lê a nova ordem."""

    clear_pending_messages(input_port)

    print()
    print(
        f"{label}: posição visual "
        f"{source_position} → {destination_position}"
    )

    output_port.send(
        build_move_message(
            source_position=source_position,
            destination_position=destination_position,
        )
    )

    state, received_messages = (
        wait_for_chain_state(
            input_port
        )
    )

    print(
        "  Slots internos recebidos:",
        state.human_slots,
    )

    return MovementResult(
        label=label,
        source_position=source_position,
        destination_position=destination_position,
        state=state,
        received_messages=received_messages,
    )


def infer_initial_order(
    first_result_order: tuple[int, ...],
) -> tuple[int, ...]:
    """Desfaz logicamente o movimento inicial 1 → 5."""

    if len(first_result_order) != EXPECTED_EFFECT_COUNT:
        raise RuntimeError(
            "A resposta deveria conter exatamente "
            f"{EXPECTED_EFFECT_COUNT} efeitos, mas contém "
            f"{len(first_result_order)}."
        )

    return (
        first_result_order[-1],
        *first_result_order[:-1],
    )


def assert_order(
    label: str,
    observed: tuple[int, ...],
    expected: tuple[int, ...],
) -> None:
    """Compara ordem observada e prevista."""

    if observed != expected:
        raise RuntimeError(
            f"{label}: ordem inesperada. "
            f"Esperada {expected}; recebida {observed}."
        )

    print(
        f"  {label}: ordem confirmada."
    )


def require_visual_confirmation(
    instruction: str,
) -> None:
    """Pede confirmação humana."""

    print()
    print(instruction)

    answer = input(
        "Digite S depois de confirmar: "
    ).strip().upper()

    if answer != "S":
        raise RuntimeError(
            "Confirmação visual não concedida."
        )


def save_results(
    results: list[MovementResult],
    initial_order: tuple[int, ...],
) -> Path:
    """Salva relatório, mensagens e ZIP."""

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )
    output_directory = (
        RESULTS_ROOT
        / f"chain_order_56A_five_{timestamp}"
    )
    output_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    report_lines = [
        "# Validação da cadeia com cinco efeitos",
        "",
        f"- preset: {PRESET_LABEL}",
        (
            "- ordem interna inicial: "
            + repr(
                tuple(
                    value + 1
                    for value in initial_order
                )
            )
        ),
        "",
    ]

    for result in results:
        report_lines.extend(
            [
                f"## {result.label}",
                "",
                (
                    "- movimento visual: "
                    f"{result.source_position} → "
                    f"{result.destination_position}"
                ),
                (
                    "- slots internos humanos: "
                    + repr(
                        result.state.human_slots
                    )
                ),
                (
                    "- checksum observado: "
                    f"0x{result.state.observed_checksum:02X}"
                ),
                "",
            ]
        )

        message_path = (
            output_directory
            / f"{result.label}_messages.txt"
        )

        with message_path.open(
            "w",
            encoding="utf-8",
        ) as output:
            for index, message in enumerate(
                result.received_messages,
                start=1,
            ):
                output.write(
                    f"Mensagem {index} - "
                    f"{len(message)} bytes\n"
                )
                output.write(
                    message.hex(" ").upper()
                )
                output.write("\n\n")

    report_path = (
        output_directory
        / "REPORT_CHAIN_ORDER_FIVE.md"
    )
    report_path.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    zip_path = output_directory.with_suffix(
        ".zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(
            output_directory.rglob("*")
        ):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(
                        output_directory
                    ).as_posix(),
                )

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as archive:
        damaged = archive.testzip()

    if damaged is not None:
        raise RuntimeError(
            "Arquivo corrompido no ZIP: "
            + damaged
        )

    return zip_path


def main() -> None:
    """Executa cinco movimentos controlados."""

    print()
    print("VALIDAÇÃO DA CADEIA — CINCO EFEITOS")
    print("------------------------------")
    print()
    print("Prepare o 56A com exatamente cinco efeitos.")
    print("Mantenha o editor oficial fechado.")
    print()
    print("Sequência:")
    print("1. posição 1 → 5")
    print("2. posição 3 → 1")
    print("3. posição 5 → 2")
    print("4. posição 2 → 1")
    print("5. posição 2 → 4")
    print()

    input(
        "Pressione Enter quando estiver preparado..."
    )

    results: list[MovementResult] = []
    initial_order: tuple[int, ...] | None = None

    try:
        with (
            mido.open_input(
                INPUT_PORT
            ) as input_port,
            mido.open_output(
                OUTPUT_PORT
            ) as output_port,
        ):
            clear_pending_messages(
                input_port
            )

            send_session_handshake(
                output_port
            )

            time.sleep(
                SESSION_STABILIZATION_SECONDS
            )

            clear_pending_messages(
                input_port
            )

            select_preset(
                input_port,
                output_port,
            )

            require_visual_confirmation(
                "Confirme que o 56A possui "
                "exatamente cinco efeitos."
            )

            first = perform_move(
                input_port,
                output_port,
                "M1",
                1,
                5,
            )
            results.append(first)

            initial_order = infer_initial_order(
                first.state.internal_slot_ids
            )

            print(
                "  Ordem inicial inferida:",
                tuple(
                    value + 1
                    for value in initial_order
                ),
            )

            expected = apply_visual_move(
                initial_order,
                1,
                5,
            )
            assert_order(
                "M1",
                first.state.internal_slot_ids,
                expected,
            )

            require_visual_confirmation(
                "Confirme que o primeiro efeito "
                "foi para o final."
            )

            second = perform_move(
                input_port,
                output_port,
                "M2",
                3,
                1,
            )
            results.append(second)

            expected = apply_visual_move(
                expected,
                3,
                1,
            )
            assert_order(
                "M2",
                second.state.internal_slot_ids,
                expected,
            )

            require_visual_confirmation(
                "Confirme que o terceiro efeito "
                "foi para o início."
            )

            third = perform_move(
                input_port,
                output_port,
                "M3",
                5,
                2,
            )
            results.append(third)

            expected = apply_visual_move(
                expected,
                5,
                2,
            )
            assert_order(
                "M3",
                third.state.internal_slot_ids,
                expected,
            )

            require_visual_confirmation(
                "Confirme que o último efeito "
                "foi para a segunda posição."
            )

            fourth = perform_move(
                input_port,
                output_port,
                "R1",
                2,
                1,
            )
            results.append(fourth)

            expected = apply_visual_move(
                expected,
                2,
                1,
            )
            assert_order(
                "R1",
                fourth.state.internal_slot_ids,
                expected,
            )

            fifth = perform_move(
                input_port,
                output_port,
                "R2",
                2,
                4,
            )
            results.append(fifth)

            expected = apply_visual_move(
                expected,
                2,
                4,
            )
            assert_order(
                "R2",
                fifth.state.internal_slot_ids,
                expected,
            )

            if expected != initial_order:
                raise RuntimeError(
                    "A restauração não retornou "
                    "à ordem inicial."
                )

            assert_order(
                "restauração final",
                fifth.state.internal_slot_ids,
                initial_order,
            )

            require_visual_confirmation(
                "Confirme que a cadeia voltou "
                "à ordem inicial."
            )

    except KeyboardInterrupt:
        print()
        print("Operação cancelada.")
        print(
            "Confira manualmente a ordem do 56A."
        )
        return

    except Exception as error:
        print()
        print("ERRO:", error)
        print(
            "Confira manualmente a ordem do 56A."
        )
        return

    assert initial_order is not None

    zip_path = save_results(
        results,
        initial_order,
    )

    print()
    print("VALIDAÇÃO CONCLUÍDA")
    print("-------------------")
    print(
        "As respostas coincidiram "
        "com os movimentos previstos."
    )
    print(
        "A cadeia voltou à ordem inicial."
    )
    print(
        "ZIP para enviar:",
        zip_path,
    )


if __name__ == "__main__":
    main()
