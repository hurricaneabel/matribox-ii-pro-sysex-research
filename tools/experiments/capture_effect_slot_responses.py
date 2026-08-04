"""Captura as respostas imediatas da Matribox ao ligar/desligar um slot.

Este teste não solicita o dump do preset. Ele observa apenas as mensagens
SysEx que a pedaleira envia logo após cada comando:

1. slot 1 desligado;
2. slot 1 ligado;
3. slot 1 desligado novamente.
"""

from __future__ import annotations

import time
from pathlib import Path

import mido

from tools.commands.request_preset_dump import (
    INPUT_PORT,
    OUTPUT_PORT,
    PRESET_LOAD_DELAY_SECONDS,
    SELECT_PRESET_45B_HEX,
    SESSION_STABILIZATION_SECONDS,
    clear_pending_messages,
    create_sysex_message,
    select_preset_with_confirmation,
    send_session_handshake,
)
from tools.commands.set_effect_slot import build_effect_message


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

EFFECT_SLOT = 1

RESPONSE_TIMEOUT_SECONDS = 1.5
POLL_INTERVAL_SECONDS = 0.01
QUIET_PERIOD_SECONDS = 0.25
RESTORE_DELAY_SECONDS = 0.5

REPORT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_slot_01_immediate_responses.txt"
)


def format_hex(data: bytes) -> str:
    """Formata bytes em hexadecimal."""
    return " ".join(
        f"{byte:02X}"
        for byte in data
    )


def message_to_bytes(message: mido.Message) -> bytes:
    """Converte uma mensagem Mido para bytes completos."""
    return bytes(
        message.bin()
    )


def collect_sysex_responses(
    input_port,
) -> list[bytes]:
    """Coleta respostas SysEx até o timeout ou período de silêncio."""
    responses: list[bytes] = []

    started_at = time.monotonic()
    last_response_at: float | None = None

    while True:
        now = time.monotonic()

        for message in input_port.iter_pending():
            if message.type != "sysex":
                continue

            responses.append(
                message_to_bytes(message)
            )

            last_response_at = time.monotonic()

        if (
            last_response_at is not None
            and now - last_response_at
            >= QUIET_PERIOD_SECONDS
        ):
            break

        if (
            now - started_at
            >= RESPONSE_TIMEOUT_SECONDS
        ):
            break

        time.sleep(
            POLL_INTERVAL_SECONDS
        )

    return responses


def capture_state(
    input_port,
    output_port,
    enabled: bool,
    label: str,
) -> list[bytes]:
    """Envia o estado e captura somente as respostas imediatas."""
    removed = clear_pending_messages(
        input_port
    )

    if removed:
        print(
            f"\nMensagens antigas removidas antes de {label}:",
            removed,
        )

    state_name = (
        "LIGADO"
        if enabled
        else "DESLIGADO"
    )

    print(
        f"\nEnviando {label}: slot interno "
        f"{EFFECT_SLOT} {state_name}..."
    )

    output_port.send(
        build_effect_message(
            effect_position=EFFECT_SLOT,
            enabled=enabled,
        )
    )

    responses = collect_sysex_responses(
        input_port
    )

    print(
        f"Respostas SysEx recebidas em {label}:",
        len(responses),
    )

    for index, response in enumerate(
        responses,
        start=1,
    ):
        print(
            f"\n{label} — resposta {index} "
            f"({len(response)} bytes)"
        )

        print(
            format_hex(response)
        )

    if not responses:
        print(
            "Nenhuma resposta SysEx foi recebida."
        )

    return responses


def build_report(
    captures: list[
        tuple[
            str,
            list[bytes],
        ]
    ],
) -> str:
    """Cria relatório textual das respostas capturadas."""
    lines = [
        "RESPOSTAS IMEDIATAS DO SLOT INTERNO 1",
        "=" * 78,
    ]

    for label, responses in captures:
        lines.extend(
            [
                "",
                label,
                "-" * 78,
                f"Quantidade: {len(responses)}",
            ]
        )

        for index, response in enumerate(
            responses,
            start=1,
        ):
            lines.extend(
                [
                    "",
                    (
                        f"Resposta {index}: "
                        f"{len(response)} bytes"
                    ),
                    format_hex(response),
                ]
            )

    lines.extend(
        [
            "",
            "=" * 78,
            "RESUMO",
        ]
    )

    off_a = captures[0][1]
    on = captures[1][1]
    off_b = captures[2][1]

    lines.append(
        f"OFF A: {len(off_a)} resposta(s)"
    )
    lines.append(
        f"ON: {len(on)} resposta(s)"
    )
    lines.append(
        f"OFF B: {len(off_b)} resposta(s)"
    )

    if off_a == off_b:
        lines.append(
            "As respostas OFF A e OFF B são idênticas."
        )
    else:
        lines.append(
            "As respostas OFF A e OFF B não são idênticas."
        )

    if off_a != on:
        lines.append(
            "A resposta ON difere da resposta OFF A."
        )
    else:
        lines.append(
            "A resposta ON é idêntica à resposta OFF A."
        )

    lines.append("")

    return "\n".join(
        lines
    )


def main() -> None:
    """Executa a captura OFF -> ON -> OFF."""
    input(
        "Deixe o preset 45A selecionado. O programa escolherá o 45B "
        "e o slot interno 1 terminará DESLIGADO. "
        "Pressione Enter para iniciar..."
    )

    select_preset = create_sysex_message(
        SELECT_PRESET_45B_HEX
    )

    slot_was_modified = False

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

            print(
                "\nAguardando a sessão estabilizar..."
            )

            time.sleep(
                SESSION_STABILIZATION_SECONDS
            )

            clear_pending_messages(
                input_port
            )

            confirmed = select_preset_with_confirmation(
                input_port,
                output_port,
                select_preset,
            )

            if not confirmed:
                print(
                    "\nTeste cancelado: não foi possível "
                    "confirmar o preset 45B."
                )

                return

            print(
                "\nAguardando o preset terminar "
                "de carregar..."
            )

            time.sleep(
                PRESET_LOAD_DELAY_SECONDS
            )

            clear_pending_messages(
                input_port
            )

            try:
                off_a = capture_state(
                    input_port,
                    output_port,
                    enabled=False,
                    label="OFF A",
                )

                slot_was_modified = True

                time.sleep(
                    RESTORE_DELAY_SECONDS
                )

                on = capture_state(
                    input_port,
                    output_port,
                    enabled=True,
                    label="ON",
                )

                time.sleep(
                    RESTORE_DELAY_SECONDS
                )

                off_b = capture_state(
                    input_port,
                    output_port,
                    enabled=False,
                    label="OFF B",
                )

                report = build_report(
                    [
                        (
                            "OFF A — slot desligado",
                            off_a,
                        ),
                        (
                            "ON — slot ligado",
                            on,
                        ),
                        (
                            "OFF B — slot desligado novamente",
                            off_b,
                        ),
                    ]
                )

                REPORT_FILE.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                REPORT_FILE.write_text(
                    report,
                    encoding="utf-8",
                )

                print(
                    "\n",
                    report,
                    sep="",
                )

                print(
                    "Relatório salvo em:",
                    REPORT_FILE,
                )

            finally:
                if slot_was_modified:
                    print(
                        "\nGarantindo que o slot interno "
                        "1 termine DESLIGADO..."
                    )

                    clear_pending_messages(
                        input_port
                    )

                    output_port.send(
                        build_effect_message(
                            effect_position=EFFECT_SLOT,
                            enabled=False,
                        )
                    )

                    time.sleep(
                        RESTORE_DELAY_SECONDS
                    )

                    clear_pending_messages(
                        input_port
                    )

                    print(
                        "Slot interno 1 restaurado "
                        "para DESLIGADO."
                    )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            "\nErro durante o teste:",
            error,
        )

    except KeyboardInterrupt:
        print(
            "\nTeste cancelado pelo usuário."
        )


if __name__ == "__main__":
    main()