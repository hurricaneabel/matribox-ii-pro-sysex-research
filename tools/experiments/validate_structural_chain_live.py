"""Fase 18: validação física final do parser estrutural integrado.

O teste usa somente um movimento visual reversível no preset 56A:

1. recarrega 56A por 56A -> 55D -> 56A;
2. move a posição visual 5 para 4;
3. confirma ordem, classe, modelo, seletor e bypass no parser estável;
4. move a posição visual 4 para 5;
5. confirma novamente o estado original completo;
6. recarrega 56A ao final para descartar qualquer alteração não salva.

O preset nunca é salvo por este script.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import time
import zipfile

import mido

from tools.commands.chain_order import (
    ChainOrderProtocolError,
    ChainOrderState,
    parse_chain_order_response,
)
from tools.commands.move_effect_position import build_move_message
from tools.commands.preset_state import (
    build_select_preset,
    parse_preset_event,
)
from tools.commands.request_preset_dump import (
    SESSION_STABILIZATION_SECONDS,
    clear_pending_messages,
    send_session_handshake,
)
from tools.commands.structural_effect_state import (
    DECOMPRESSED_PAYLOAD_SIZE,
)


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"

TARGET_PRESET = "56A"
RESET_PRESET = "55D"

POLL_INTERVAL_SECONDS = 0.01
PRESET_TIMEOUT_SECONDS = 3.0
STRUCTURAL_TIMEOUT_SECONDS = 4.0
PRESET_SETTLE_SECONDS = 0.6
PRESET_SELECTION_ATTEMPTS = 3
PRESET_RETRY_DELAY_SECONDS = 0.5
ACTION_SETTLE_SECONDS = 0.45

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = PROJECT_ROOT / "data" / "dumps"

NORMAL_ORDER = (1, 2, 3, 4, 5)
SWAPPED_ORDER = (1, 2, 3, 5, 4)


@dataclass(frozen=True, slots=True)
class ExpectedEffect:
    """Identidade estrutural esperada de um slot ativo."""

    class_name: str
    model_name: str
    class_id: int
    model_id: int
    secondary_selector: int


EXPECTED_EFFECTS = {
    1: ExpectedEffect("DYN", "GATE 3", 0x00, 0x21, 0x00),
    2: ExpectedEffect("AMP", "TWD DELUXE", 0x04, 0x01, 0x07),
    3: ExpectedEffect("DRV", "SKREAMER", 0x03, 0x00, 0x03),
    4: ExpectedEffect("MOD", "E-CHORUS", 0x08, 0x01, 0x04),
    5: ExpectedEffect("DLY", "WARM", 0x09, 0x01, 0x0B),
}


@dataclass(frozen=True, slots=True)
class LiveCapture:
    """Captura estrutural aprovada durante o teste físico."""

    label: str
    expected_order: tuple[int, ...]
    state: ChainOrderState
    received_messages: tuple[bytes, ...]


def full_bytes_to_mido(message: bytes) -> mido.Message:
    """Converte uma mensagem SysEx completa para Mido."""

    if len(message) < 2 or message[0] != 0xF0 or message[-1] != 0xF7:
        raise ValueError("Mensagem SysEx completa inválida.")

    return mido.Message("sysex", data=message[1:-1])


def wait_for_preset(input_port, expected_label: str) -> None:
    """Aguarda a confirmação do preset solicitado."""

    deadline = time.monotonic() + PRESET_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if message.type != "sysex":
            continue

        event = parse_preset_event(bytes(message.bin()))

        if event is None:
            continue

        print("  Evento de preset:", event.label)

        if event.label == expected_label:
            return

    raise RuntimeError(
        f"A confirmação do preset {expected_label} não chegou."
    )


def select_preset(input_port, output_port, label: str) -> None:
    """Seleciona um preset com reenvio automático após cold boot."""

    last_error: RuntimeError | None = None

    for attempt in range(1, PRESET_SELECTION_ATTEMPTS + 1):
        clear_pending_messages(input_port)

        if attempt > 1:
            print(
                f"  Reenviando seleção de {label}: "
                f"tentativa {attempt}/{PRESET_SELECTION_ATTEMPTS}"
            )

        output_port.send(full_bytes_to_mido(build_select_preset(label)))

        try:
            wait_for_preset(input_port, label)
        except RuntimeError as error:
            last_error = error

            if attempt < PRESET_SELECTION_ATTEMPTS:
                time.sleep(PRESET_RETRY_DELAY_SECONDS)
                continue

            raise

        time.sleep(PRESET_SETTLE_SECONDS)
        return

    if last_error is not None:
        raise last_error


def reload_56a(input_port, output_port) -> None:
    """Descarta alterações não salvas e recarrega o preset alvo."""

    print("  Recarregando 56A -> 55D -> 56A")
    select_preset(input_port, output_port, RESET_PRESET)
    select_preset(input_port, output_port, TARGET_PRESET)


def validate_structural_state(
    state: ChainOrderState,
    expected_order: tuple[int, ...],
    *,
    label: str,
) -> None:
    """Valida o estado físico completo esperado do preset 56A."""

    if tuple(state.human_slots) != expected_order:
        raise RuntimeError(
            f"{label}: ordem inesperada: {state.human_slots}; "
            f"esperada: {expected_order}."
        )

    if state.effect_count != 5:
        raise RuntimeError(
            f"{label}: quantidade inesperada de efeitos: "
            f"{state.effect_count}."
        )

    if len(state.decompressed_payload or b"") != DECOMPRESSED_PAYLOAD_SIZE:
        raise RuntimeError(
            f"{label}: payload descomprimido não possui "
            f"{DECOMPRESSED_PAYLOAD_SIZE} bytes."
        )

    if not state.has_complete_bypass_state:
        raise RuntimeError(f"{label}: bypass incompleto.")

    for human_slot, expected in EXPECTED_EFFECTS.items():
        record = state.record_for_internal_slot(human_slot)

        observed = (
            record.class_id,
            record.model_id,
            record.secondary_selector,
        )
        wanted = (
            expected.class_id,
            expected.model_id,
            expected.secondary_selector,
        )

        if observed != wanted:
            raise RuntimeError(
                f"{label}: slot {human_slot} inesperado: "
                f"classe/modelo/seletor={observed}; esperado={wanted}."
            )

        if record.enabled is not True:
            raise RuntimeError(
                f"{label}: slot {human_slot} não está ligado."
            )

    visual_slots = tuple(
        record.human_slot
        for record in state.visual_effect_records
    )

    if visual_slots != expected_order:
        raise RuntimeError(
            f"{label}: os registros visuais não acompanham a ordem: "
            f"{visual_slots}."
        )


def execute_move_and_capture(
    input_port,
    output_port,
    *,
    label: str,
    source_position: int,
    destination_position: int,
    expected_order: tuple[int, ...],
) -> LiveCapture:
    """Executa um movimento reversível e exige a resposta integrada."""

    print()
    print(
        f"{label}: posição {source_position} -> {destination_position}"
    )

    clear_pending_messages(input_port)
    output_port.send(
        build_move_message(
            source_position=source_position,
            destination_position=destination_position,
        )
    )

    received: list[bytes] = []
    deadline = time.monotonic() + STRUCTURAL_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if message.type != "sysex":
            continue

        raw = bytes(message.bin())
        received.append(raw)
        print("  SysEx:", len(raw), "bytes")

        try:
            state = parse_chain_order_response(raw)
        except ChainOrderProtocolError as error:
            print("  Resposta estrutural recusada:", error)
            continue

        if state is None:
            print("  Resposta auxiliar ignorada.")
            continue

        if tuple(state.human_slots) != expected_order:
            print("  Ordem intermediária:", state.human_slots)
            continue

        validate_structural_state(
            state,
            expected_order,
            label=label,
        )

        time.sleep(ACTION_SETTLE_SECONDS)

        print("  Ordem:", state.human_slots)
        print("  Payload descomprimido: 89 bytes")
        print("  Classe/modelo/seletor: aprovados")
        print("  Bypass: cinco efeitos ligados")

        return LiveCapture(
            label=label,
            expected_order=expected_order,
            state=state,
            received_messages=tuple(received),
        )

    raise RuntimeError(
        f"{label}: a resposta estrutural esperada não chegou."
    )


def require_confirmation() -> None:
    """Pede confirmação visual do preset salvo antes do teste."""

    print()
    print("Confirme o preset 56A salvo:")
    print("1. DYN / GATE 3 — ligado")
    print("2. AMP / TWD DELUXE — ligado")
    print("3. DRV / SKREAMER — ligado")
    print("4. MOD / E-CHORUS — ligado")
    print("5. DLY / WARM — ligado")
    print()

    answer = input(
        "Digite S somente depois de confirmar: "
    ).strip().upper()

    if answer != "S":
        raise RuntimeError("Estado inicial não confirmado.")


def save_messages(path: Path, messages: tuple[bytes, ...]) -> None:
    """Preserva todas as mensagens observadas durante uma etapa."""

    with path.open("w", encoding="utf-8") as output:
        for index, message in enumerate(messages, start=1):
            output.write(f"Mensagem {index} - {len(message)} bytes\n")
            output.write(message.hex(" ").upper())
            output.write("\n\n")


def save_capture(output_directory: Path, capture: LiveCapture) -> None:
    """Salva o SysEx aprovado, o payload e as respostas auxiliares."""

    prefix = output_directory / capture.label
    prefix.with_suffix(".bin").write_bytes(capture.state.raw_message)
    prefix.with_suffix(".hex").write_text(
        capture.state.raw_message.hex(" ").upper() + "\n",
        encoding="utf-8",
    )
    (output_directory / f"{capture.label}_payload.bin").write_bytes(
        capture.state.decompressed_payload or b""
    )
    save_messages(
        output_directory / f"{capture.label}_received.txt",
        capture.received_messages,
    )


def build_report(
    output_directory: Path,
    captures: list[LiveCapture],
    error_text: str | None,
) -> None:
    """Gera relatório legível e manifesto da validação física."""

    status = (
        "APROVADO"
        if len(captures) == 2 and error_text is None
        else "INCOMPLETO"
    )

    manifest = {
        "phase": 18,
        "preset": TARGET_PRESET,
        "status": status,
        "error": error_text,
        "captures": [
            {
                "label": capture.label,
                "message_length": len(capture.state.raw_message),
                "order": list(capture.state.human_slots),
                "response_slot_marker": capture.state.response_slot_marker,
                "records": [
                    {
                        "slot": record.human_slot,
                        "class_id": record.class_id,
                        "model_id": record.model_id,
                        "secondary_selector": record.secondary_selector,
                        "enabled": record.enabled,
                    }
                    for record in capture.state.effect_records_by_internal_slot
                    if record.active
                ],
            }
            for capture in captures
        ],
    }

    (output_directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Fase 18 — validação física final do parser estrutural",
        "",
        f"Status: {status}",
        f"Capturas aprovadas: {len(captures)}/2",
        f"Erro: {error_text or 'nenhum'}",
        "",
        "O teste moveu a posição 5 para 4 e retornou 4 para 5.",
        "Nenhuma alteração foi salva.",
        "O preset 56A foi recarregado ao final.",
        "",
    ]

    for capture in captures:
        lines.extend(
            [
                f"## {capture.label}",
                "",
                f"- tamanho SysEx: {len(capture.state.raw_message)} bytes",
                f"- ordem: {capture.state.human_slots}",
                "- payload: 89 bytes",
                "- classe/modelo/seletor: aprovados",
                "- bypass: cinco efeitos ligados",
                "",
            ]
        )

    (output_directory / "REPORT_PHASE18.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def create_zip(output_directory: Path) -> Path:
    """Compacta e verifica os resultados do teste físico."""

    zip_path = output_directory.with_suffix(".zip")

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(output_directory.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    path.relative_to(output_directory).as_posix(),
                )

    with zipfile.ZipFile(zip_path, "r") as archive:
        damaged = archive.testzip()

    if damaged is not None:
        raise RuntimeError(f"Arquivo danificado no ZIP: {damaged}")

    return zip_path


def main() -> None:
    """Executa o único teste físico final da integração estrutural."""

    print()
    print("FASE 18 — VALIDAÇÃO FÍSICA FINAL DO PARSER ESTRUTURAL")
    print("----------------------------------------------------")
    print()
    print("O editor oficial deve permanecer fechado.")
    print("Não salve o preset durante o teste.")
    print("O teste faz um movimento visual reversível e recarrega 56A ao final.")
    print()

    input("Pressione Enter para iniciar...")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_directory = (
        RESULTS_ROOT / f"structural_chain_live_56A_{timestamp}"
    )
    output_directory.mkdir(parents=True, exist_ok=False)

    captures: list[LiveCapture] = []
    error_text: str | None = None

    try:
        with (
            mido.open_input(INPUT_PORT) as input_port,
            mido.open_output(OUTPUT_PORT) as output_port,
        ):
            clear_pending_messages(input_port)
            send_session_handshake(output_port)
            time.sleep(SESSION_STABILIZATION_SECONDS)

            reload_56a(input_port, output_port)
            require_confirmation()

            captures.append(
                execute_move_and_capture(
                    input_port,
                    output_port,
                    label="SWAPPED_5_TO_4",
                    source_position=5,
                    destination_position=4,
                    expected_order=SWAPPED_ORDER,
                )
            )

            captures.append(
                execute_move_and_capture(
                    input_port,
                    output_port,
                    label="RESTORED_4_TO_5",
                    source_position=4,
                    destination_position=5,
                    expected_order=NORMAL_ORDER,
                )
            )

    except KeyboardInterrupt:
        error_text = "Operação cancelada pelo usuário."
        print()
        print(error_text)

    except Exception as error:
        error_text = f"{type(error).__name__}: {error}"
        print()
        print("ERRO:", error)

    finally:
        try:
            with (
                mido.open_input(INPUT_PORT) as input_port,
                mido.open_output(OUTPUT_PORT) as output_port,
            ):
                reload_56a(input_port, output_port)

            print()
            print("Restauração final concluída por recarga do 56A.")

        except Exception as restore_error:
            restore_text = (
                "Falha na restauração final: "
                f"{type(restore_error).__name__}: {restore_error}"
            )
            print()
            print(restore_text)
            error_text = (
                restore_text
                if error_text is None
                else error_text + "\n" + restore_text
            )

    for capture in captures:
        save_capture(output_directory, capture)

    build_report(output_directory, captures, error_text)
    zip_path = create_zip(output_directory)

    approved = len(captures) == 2 and error_text is None

    print()
    print("RESULTADOS PRESERVADOS")
    print("---------------------")
    print("Capturas:", len(captures), "/ 2")
    print("Status:", "APROVADO" if approved else "INCOMPLETO")
    print("ZIP para enviar:", zip_path)

    if not approved:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
