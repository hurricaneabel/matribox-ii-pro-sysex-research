"""Fase 15: resolve modelo e seletor nos slots internos 4 e 5.

A Fase 14 confirmou:

- classe por slot nos índices fixos 58, 60, 62, 64 e 66;
- modelos dos slots 1–4 nas amostras diretas;
- respostas estruturais variáveis de 164, 166, 168 e 176 bytes;
- necessidade de não aplicar offsets de bypass do layout 168B a outros tamanhos.

Esta fase faz comparações controladas nos slots 4 e 5:

1. mesmo class_id e mesmo model_id, alterando apenas secondary_selector;
2. mesmo class_id e mesmo secondary_selector, alterando apenas model_id;
3. DLY/WARM -> DLY/MAG no slot 5, evitando o modelo zero usado antes.

Nenhuma alteração é salva. O preset 56A é recarregado ao final.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import csv
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
from tools.commands.effect_chain import (
    build_replace_effect_message,
)
from tools.commands.effect_model import (
    build_set_effect_model_message,
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

TARGET_PRESET = "56A"
RESET_PRESET = "55D"

POLL_INTERVAL_SECONDS = 0.01
PRESET_TIMEOUT_SECONDS = 3.0
STRUCTURAL_TIMEOUT_SECONDS = 4.0
PRESET_SETTLE_SECONDS = 0.6
ACTION_SETTLE_SECONDS = 0.45

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = PROJECT_ROOT / "data" / "dumps"

NORMAL_ORDER = (1, 2, 3, 4, 5)
SWAPPED_ORDER = (1, 2, 3, 5, 4)


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Identidade enviada ao protocolo."""

    class_name: str
    model_name: str
    class_id: int
    model_id: int
    secondary_selector: int


@dataclass(frozen=True, slots=True)
class Capture:
    """Resposta estrutural aprovada."""

    label: str
    slot_number: int | None
    operation: str
    model: ModelSpec | None
    state: ChainOrderState
    received_messages: tuple[bytes, ...]


DLY_WARM = ModelSpec(
    "DLY",
    "WARM",
    0x09,
    0x01,
    0x0B,
)

DLY_MAG = ModelSpec(
    "DLY",
    "MAG",
    0x09,
    0x02,
    0x0B,
)

MOD_E_CHORUS = ModelSpec(
    "MOD",
    "E-CHORUS",
    0x08,
    0x01,
    0x04,
)

AMP_VOKS_BASS = ModelSpec(
    "AMP",
    "VOKS BASS",
    0x04,
    0x75,
    0x07,
)

AMP_A_BASSFT = ModelSpec(
    "AMP",
    "A BASSFT",
    0x04,
    0x75,
    0x08,
)

AMP_B_MAN_N = ModelSpec(
    "AMP",
    "B-MAN N",
    0x04,
    0x03,
    0x07,
)


def full_bytes_to_mido(message: bytes) -> mido.Message:
    """Converte SysEx completo em mensagem Mido."""

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


def wait_for_preset(
    input_port,
    expected_label: str,
) -> None:
    """Aguarda confirmação do preset."""

    deadline = time.monotonic() + PRESET_TIMEOUT_SECONDS

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
            "  Evento de preset:",
            event.label,
        )

        if event.label == expected_label:
            return

    raise RuntimeError(
        f"A confirmação do preset {expected_label} não chegou."
    )


def select_preset(
    input_port,
    output_port,
    label: str,
) -> None:
    """Seleciona e confirma um preset."""

    clear_pending_messages(input_port)

    output_port.send(
        full_bytes_to_mido(
            build_select_preset(label)
        )
    )

    wait_for_preset(
        input_port,
        label,
    )

    time.sleep(PRESET_SETTLE_SECONDS)


def reload_56a(
    input_port,
    output_port,
) -> None:
    """Descarta alterações não salvas."""

    print(
        "  Recarregando 56A -> 55D -> 56A"
    )

    select_preset(
        input_port,
        output_port,
        RESET_PRESET,
    )

    select_preset(
        input_port,
        output_port,
        TARGET_PRESET,
    )


def wait_for_normal_chain(
    input_port,
) -> tuple[
    ChainOrderState | None,
    tuple[bytes, ...],
]:
    """Aguarda uma resposta com a cadeia normal completa."""

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

        print(
            "    SysEx:",
            len(raw),
            "bytes",
        )

        try:
            state = parse_chain_order_response(raw)
        except ChainOrderProtocolError as error:
            print(
                "    Estrutura auxiliar preservada:",
                error,
            )
            continue

        if state is None:
            continue

        observed_order = tuple(state.human_slots)

        if observed_order == NORMAL_ORDER:
            return (
                state,
                tuple(received),
            )

        print(
            "    Resposta auxiliar preservada | ordem:",
            observed_order,
        )

    return (
        None,
        tuple(received),
    )


def execute_move(
    input_port,
    output_port,
    source_position: int,
    destination_position: int,
    expected_order: tuple[int, ...],
) -> tuple[
    ChainOrderState,
    tuple[bytes, ...],
]:
    """Move e exige a ordem esperada."""

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

        print(
            "    SysEx:",
            len(raw),
            "bytes",
        )

        try:
            state = parse_chain_order_response(raw)
        except ChainOrderProtocolError:
            continue

        if (
            state is not None
            and tuple(state.human_slots) == expected_order
        ):
            time.sleep(ACTION_SETTLE_SECONDS)
            return (
                state,
                tuple(received),
            )

    raise RuntimeError(
        "A resposta estrutural do movimento não chegou."
    )


def force_normal_capture(
    input_port,
    output_port,
) -> tuple[
    ChainOrderState,
    tuple[bytes, ...],
]:
    """Força leitura estrutural e termina na ordem normal."""

    _, first = execute_move(
        input_port,
        output_port,
        5,
        4,
        SWAPPED_ORDER,
    )

    state, second = execute_move(
        input_port,
        output_port,
        4,
        5,
        NORMAL_ORDER,
    )

    return (
        state,
        first + second,
    )


def validate_state(
    label: str,
    state: ChainOrderState,
) -> None:
    """Exige somente a ordem normal nesta fase."""

    observed_order = tuple(state.human_slots)

    if observed_order != NORMAL_ORDER:
        raise RuntimeError(
            f"{label}: ordem inesperada: {observed_order}."
        )


def capture_after_write(
    input_port,
    output_port,
    *,
    label: str,
    slot_number: int,
    operation: str,
    model: ModelSpec,
    message: mido.Message,
) -> Capture:
    """Envia escrita e coleta a estrutura resultante."""

    print()
    print(
        label,
        f"| slot {slot_number}",
        f"| {model.class_name}/{model.model_name}",
        f"| modelo 0x{model.model_id:02X}",
        f"| seletor 0x{model.secondary_selector:02X}",
    )

    clear_pending_messages(input_port)
    output_port.send(message)

    state, received = wait_for_normal_chain(input_port)

    if state is None:
        print(
            "    Resposta completa ausente; forçando leitura reversível."
        )

        forced_state, forced_received = force_normal_capture(
            input_port,
            output_port,
        )

        state = forced_state
        received = received + forced_received

    validate_state(
        label,
        state,
    )

    print(
        "    Captura aprovada:",
        len(state.raw_message),
        "bytes",
    )

    time.sleep(ACTION_SETTLE_SECONDS)

    return Capture(
        label=label,
        slot_number=slot_number,
        operation=operation,
        model=model,
        state=state,
        received_messages=received,
    )


def same_class_message(
    slot_number: int,
    model: ModelSpec,
) -> mido.Message:
    """Monta comando 0x16."""

    return build_set_effect_model_message(
        slot_number=slot_number,
        class_id=model.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )


def cross_class_message(
    slot_number: int,
    model: ModelSpec,
) -> mido.Message:
    """Monta comando 0x17."""

    return build_replace_effect_message(
        slot_number=slot_number,
        class_id=model.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )


def save_messages(
    path: Path,
    messages: tuple[bytes, ...],
) -> None:
    """Salva mensagens recebidas."""

    with path.open(
        "w",
        encoding="utf-8",
    ) as output:
        if not messages:
            output.write(
                "Nenhuma mensagem observada.\n"
            )
            return

        for index, message in enumerate(
            messages,
            start=1,
        ):
            output.write(
                f"Mensagem {index} - {len(message)} bytes\n"
            )
            output.write(
                message.hex(" ").upper()
            )
            output.write("\n\n")


def save_capture(
    output_directory: Path,
    capture: Capture,
) -> None:
    """Preserva estrutura e respostas auxiliares."""

    (
        output_directory
        / f"{capture.label}_structural.bin"
    ).write_bytes(
        capture.state.raw_message
    )

    (
        output_directory
        / f"{capture.label}_structural.hex"
    ).write_text(
        capture.state.raw_message.hex(" ").upper() + "\n",
        encoding="utf-8",
    )

    save_messages(
        output_directory
        / f"{capture.label}_received.txt",
        capture.received_messages,
    )

    for message_index, message in enumerate(
        capture.received_messages,
        start=1,
    ):
        (
            output_directory
            / (
                f"{capture.label}_message_"
                f"{message_index:02d}_"
                f"{len(message)}B.bin"
            )
        ).write_bytes(message)


def difference_rows(
    left: bytes,
    right: bytes,
) -> list[
    tuple[
        int,
        int | None,
        int | None,
    ]
]:
    """Compara duas mensagens por índice absoluto."""

    maximum = max(
        len(left),
        len(right),
    )

    rows: list[
        tuple[
            int,
            int | None,
            int | None,
        ]
    ] = []

    for index in range(maximum):
        left_value = (
            left[index]
            if index < len(left)
            else None
        )

        right_value = (
            right[index]
            if index < len(right)
            else None
        )

        if left_value != right_value:
            rows.append(
                (
                    index,
                    left_value,
                    right_value,
                )
            )

    return rows


def optional_hex(value: int | None) -> str:
    """Formata byte opcional."""

    if value is None:
        return "--"

    return f"{value:02X}"


def build_reports(
    output_directory: Path,
    captures: list[Capture],
    error_text: str | None,
) -> None:
    """Gera relatório das comparações controladas."""

    by_label = {
        capture.label: capture
        for capture in captures
    }

    comparisons = (
        (
            "S5_DLY_MODEL_ONLY",
            "BASELINE",
            "S5_DLY_MAG",
            "Slot 5: DLY/WARM -> DLY/MAG; modelo muda 0x01 -> 0x02 e seletor permanece 0x0B.",
        ),
        (
            "S4_SELECTOR_ONLY",
            "S4_AMP_SEL7",
            "S4_AMP_SEL8",
            "Slot 4: mesmo AMP e mesmo modelo 0x75; seletor muda 0x07 -> 0x08.",
        ),
        (
            "S4_MODEL_ONLY",
            "S4_AMP_SEL7_RESTORE",
            "S4_AMP_MODEL03",
            "Slot 4: mesmo AMP e seletor 0x07; modelo muda 0x75 -> 0x03.",
        ),
        (
            "S5_SELECTOR_ONLY",
            "S5_AMP_SEL7",
            "S5_AMP_SEL8",
            "Slot 5: mesmo AMP e mesmo modelo 0x75; seletor muda 0x07 -> 0x08.",
        ),
        (
            "S5_MODEL_ONLY",
            "S5_AMP_SEL7_RESTORE",
            "S5_AMP_MODEL03",
            "Slot 5: mesmo AMP e seletor 0x07; modelo muda 0x75 -> 0x03.",
        ),
    )

    manifest = {
        "preset": TARGET_PRESET,
        "captures": [],
        "comparisons": [],
        "error": error_text,
    }

    for capture in captures:
        manifest["captures"].append(
            {
                "label": capture.label,
                "slot_number": capture.slot_number,
                "operation": capture.operation,
                "message_length": len(
                    capture.state.raw_message
                ),
                "received_message_lengths": [
                    len(message)
                    for message in capture.received_messages
                ],
                "order": list(
                    capture.state.human_slots
                ),
                "model": (
                    None
                    if capture.model is None
                    else {
                        "class_name": capture.model.class_name,
                        "model_name": capture.model.model_name,
                        "class_id": capture.model.class_id,
                        "model_id": capture.model.model_id,
                        "secondary_selector": (
                            capture.model.secondary_selector
                        ),
                    }
                ),
            }
        )

    lines = [
        "# Fase 15 — modelo e seletor dos slots 4 e 5",
        "",
        f"Capturas: {len(captures)}/13",
        (
            "Erro: "
            + (
                "nenhum"
                if error_text is None
                else error_text
            )
        ),
        "",
    ]

    csv_data: list[
        dict[
            str,
            str | int,
        ]
    ] = []

    for (
        comparison_name,
        left_label,
        right_label,
        description,
    ) in comparisons:
        left_capture = by_label.get(left_label)
        right_capture = by_label.get(right_label)

        if (
            left_capture is None
            or right_capture is None
        ):
            lines.extend(
                [
                    f"## {comparison_name}",
                    "",
                    description,
                    "",
                    "Comparação incompleta.",
                    "",
                ]
            )
            continue

        differences = difference_rows(
            left_capture.state.raw_message,
            right_capture.state.raw_message,
        )

        manifest["comparisons"].append(
            {
                "name": comparison_name,
                "left": left_label,
                "right": right_label,
                "description": description,
                "left_length": len(
                    left_capture.state.raw_message
                ),
                "right_length": len(
                    right_capture.state.raw_message
                ),
                "difference_indices": [
                    index
                    for (
                        index,
                        _left_value,
                        _right_value,
                    ) in differences
                ],
            }
        )

        lines.extend(
            [
                f"## {comparison_name}",
                "",
                description,
                "",
                (
                    f"- tamanhos: "
                    f"{len(left_capture.state.raw_message)} -> "
                    f"{len(right_capture.state.raw_message)} bytes"
                ),
                (
                    "- índices diferentes: "
                    + (
                        ", ".join(
                            str(index)
                            for (
                                index,
                                _left_value,
                                _right_value,
                            ) in differences
                        )
                        if differences
                        else "nenhum"
                    )
                ),
                "",
            ]
        )

        for (
            index,
            left_value,
            right_value,
        ) in differences:
            csv_data.append(
                {
                    "comparison": comparison_name,
                    "left_label": left_label,
                    "right_label": right_label,
                    "index": index,
                    "left_hex": optional_hex(
                        left_value
                    ),
                    "right_hex": optional_hex(
                        right_value
                    ),
                }
            )

    (
        output_directory
        / "REPORT_MODEL_SELECTOR_SLOTS4_5.md"
    ).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    (
        output_directory
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with (
        output_directory
        / "model_selector_controlled_diffs.csv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=(
                "comparison",
                "left_label",
                "right_label",
                "index",
                "left_hex",
                "right_hex",
            ),
        )

        writer.writeheader()
        writer.writerows(csv_data)


def create_zip(
    output_directory: Path,
) -> Path:
    """Compacta e valida os resultados."""

    zip_path = output_directory.with_suffix(".zip")

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
            f"Arquivo danificado no ZIP: {damaged}"
        )

    return zip_path


def require_confirmation() -> None:
    """Confirma o estado inicial."""

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
        raise RuntimeError(
            "Estado inicial não confirmado."
        )


def main() -> None:
    """Executa as comparações controladas."""

    print()
    print("FASE 15 — MODELO E SELETOR NOS SLOTS 4 E 5")
    print("-------------------------------------------")
    print()
    print("Tempo estimado: aproximadamente 2 minutos.")
    print("O editor oficial deve permanecer fechado.")
    print("Não salve o preset durante o teste.")
    print()

    input(
        "Pressione Enter para iniciar..."
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    output_directory = (
        RESULTS_ROOT
        / f"model_selector_slots4_5_56A_{timestamp}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    captures: list[Capture] = []
    error_text: str | None = None

    try:
        with (
            mido.open_input(INPUT_PORT) as input_port,
            mido.open_output(OUTPUT_PORT) as output_port,
        ):
            clear_pending_messages(input_port)
            send_session_handshake(output_port)

            time.sleep(
                SESSION_STABILIZATION_SECONDS
            )

            reload_56a(
                input_port,
                output_port,
            )

            require_confirmation()

            print()
            print("BASELINE")

            baseline_state, baseline_received = (
                force_normal_capture(
                    input_port,
                    output_port,
                )
            )

            validate_state(
                "BASELINE",
                baseline_state,
            )

            baseline = Capture(
                label="BASELINE",
                slot_number=None,
                operation="baseline",
                model=None,
                state=baseline_state,
                received_messages=baseline_received,
            )

            captures.append(baseline)
            save_capture(
                output_directory,
                baseline,
            )

            sequence = (
                (
                    "S5_DLY_MAG",
                    5,
                    "dly_model_only",
                    DLY_MAG,
                    same_class_message(
                        5,
                        DLY_MAG,
                    ),
                ),
                (
                    "S5_DLY_RESTORE",
                    5,
                    "dly_restore",
                    DLY_WARM,
                    same_class_message(
                        5,
                        DLY_WARM,
                    ),
                ),
                (
                    "S4_AMP_SEL7",
                    4,
                    "replace_amp_selector_07",
                    AMP_VOKS_BASS,
                    cross_class_message(
                        4,
                        AMP_VOKS_BASS,
                    ),
                ),
                (
                    "S4_AMP_SEL8",
                    4,
                    "selector_only_07_to_08",
                    AMP_A_BASSFT,
                    same_class_message(
                        4,
                        AMP_A_BASSFT,
                    ),
                ),
                (
                    "S4_AMP_SEL7_RESTORE",
                    4,
                    "selector_restore_08_to_07",
                    AMP_VOKS_BASS,
                    same_class_message(
                        4,
                        AMP_VOKS_BASS,
                    ),
                ),
                (
                    "S4_AMP_MODEL03",
                    4,
                    "model_only_75_to_03",
                    AMP_B_MAN_N,
                    same_class_message(
                        4,
                        AMP_B_MAN_N,
                    ),
                ),
                (
                    "S4_ORIGINAL_RESTORE",
                    4,
                    "restore_mod_e_chorus",
                    MOD_E_CHORUS,
                    cross_class_message(
                        4,
                        MOD_E_CHORUS,
                    ),
                ),
                (
                    "S5_AMP_SEL7",
                    5,
                    "replace_amp_selector_07",
                    AMP_VOKS_BASS,
                    cross_class_message(
                        5,
                        AMP_VOKS_BASS,
                    ),
                ),
                (
                    "S5_AMP_SEL8",
                    5,
                    "selector_only_07_to_08",
                    AMP_A_BASSFT,
                    same_class_message(
                        5,
                        AMP_A_BASSFT,
                    ),
                ),
                (
                    "S5_AMP_SEL7_RESTORE",
                    5,
                    "selector_restore_08_to_07",
                    AMP_VOKS_BASS,
                    same_class_message(
                        5,
                        AMP_VOKS_BASS,
                    ),
                ),
                (
                    "S5_AMP_MODEL03",
                    5,
                    "model_only_75_to_03",
                    AMP_B_MAN_N,
                    same_class_message(
                        5,
                        AMP_B_MAN_N,
                    ),
                ),
                (
                    "S5_ORIGINAL_RESTORE",
                    5,
                    "restore_dly_warm",
                    DLY_WARM,
                    cross_class_message(
                        5,
                        DLY_WARM,
                    ),
                ),
            )

            for (
                label,
                slot_number,
                operation,
                model,
                message,
            ) in sequence:
                capture = capture_after_write(
                    input_port,
                    output_port,
                    label=label,
                    slot_number=slot_number,
                    operation=operation,
                    model=model,
                    message=message,
                )

                captures.append(capture)
                save_capture(
                    output_directory,
                    capture,
                )

    except KeyboardInterrupt:
        error_text = (
            "Operação cancelada pelo usuário."
        )

        print()
        print(error_text)

    except Exception as error:
        error_text = (
            f"{type(error).__name__}: {error}"
        )

        print()
        print(
            "ERRO:",
            error,
        )

    finally:
        try:
            with (
                mido.open_input(INPUT_PORT) as input_port,
                mido.open_output(OUTPUT_PORT) as output_port,
            ):
                reload_56a(
                    input_port,
                    output_port,
                )

            print()
            print(
                "Restauração final concluída por recarga do 56A."
            )

        except Exception as restore_error:
            restore_text = (
                "Falha na restauração final: "
                f"{type(restore_error).__name__}: "
                f"{restore_error}"
            )

            print()
            print(restore_text)

            error_text = (
                restore_text
                if error_text is None
                else error_text + "\n" + restore_text
            )

    build_reports(
        output_directory,
        captures,
        error_text,
    )

    zip_path = create_zip(
        output_directory
    )

    print()
    print("RESULTADOS PRESERVADOS")
    print("---------------------")
    print(
        "Capturas:",
        len(captures),
        "/ 13",
    )
    print(
        "Status:",
        (
            "APROVADO"
            if (
                len(captures) == 13
                and error_text is None
            )
            else "INCOMPLETO"
        ),
    )
    print(
        "ZIP para enviar:",
        zip_path,
    )


if __name__ == "__main__":
    main()
