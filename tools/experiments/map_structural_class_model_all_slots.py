"""Mapeia classe, modelo e seletor por slot na resposta estrutural.

Preset salvo esperado: 56A

1. DYN / GATE 3
2. AMP / TWD DELUXE
3. DRV / SKREAMER
4. MOD / E-CHORUS
5. DLY / WARM

Para cada slot interno, o experimento coleta:

- modelo alternativo dentro da mesma classe, usando 0x16;
- restauração do modelo original, usando 0x16;
- substituição temporária por FREQ / Filter, usando 0x17;
- restauração da classe e do modelo originais, usando 0x17.

A resposta estrutural imediata é usada quando disponível. Se ela não chegar,
o programa força uma leitura por meio dos movimentos reversíveis 5 -> 4 e
4 -> 5. Todas as amostras principais terminam na ordem visual normal.

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
STRUCTURAL_TIMEOUT_SECONDS = 5.0
IMMEDIATE_RESPONSE_TIMEOUT_SECONDS = 1.5
PRESET_SETTLE_SECONDS = 0.6
ACTION_SETTLE_SECONDS = 0.45

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = PROJECT_ROOT / "data" / "dumps"

NORMAL_ORDER = (
    1,
    2,
    3,
    4,
    5,
)

SWAPPED_ORDER = (
    1,
    2,
    3,
    5,
    4,
)


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Identidade de classe/modelo usada no teste."""

    class_name: str
    model_name: str
    class_id: int
    model_id: int
    secondary_selector: int


@dataclass(frozen=True, slots=True)
class StructuralCapture:
    """Amostra estrutural preservada."""

    label: str
    slot_number: int | None
    operation: str
    model: ModelSpec | None
    state: ChainOrderState
    received_messages: tuple[bytes, ...]
    capture_source: str


BASELINE_MODELS = {
    1: ModelSpec(
        "DYN",
        "GATE 3",
        0x00,
        0x21,
        0x00,
    ),
    2: ModelSpec(
        "AMP",
        "TWD DELUXE",
        0x04,
        0x01,
        0x07,
    ),
    3: ModelSpec(
        "DRV",
        "SKREAMER",
        0x03,
        0x00,
        0x03,
    ),
    4: ModelSpec(
        "MOD",
        "E-CHORUS",
        0x08,
        0x01,
        0x04,
    ),
    5: ModelSpec(
        "DLY",
        "WARM",
        0x09,
        0x01,
        0x0B,
    ),
}

SAME_CLASS_ALTERNATES = {
    1: ModelSpec(
        "DYN",
        "GATE 2",
        0x00,
        0x1D,
        0x00,
    ),
    2: ModelSpec(
        "AMP",
        "B-MAN N",
        0x04,
        0x03,
        0x07,
    ),
    3: ModelSpec(
        "DRV",
        "SKREAMER9",
        0x03,
        0x01,
        0x03,
    ),
    4: ModelSpec(
        "MOD",
        "D-CHORUS",
        0x08,
        0x02,
        0x04,
    ),
    5: ModelSpec(
        "DLY",
        "PURE",
        0x09,
        0x00,
        0x0B,
    ),
}

CROSS_CLASS_MODEL = ModelSpec(
    "FREQ",
    "FILTER",
    0x01,
    0x19,
    0x01,
)


def full_bytes_to_mido(
    message: bytes,
) -> mido.Message:
    """Converte um SysEx completo em mensagem Mido."""

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
    """Aguarda a confirmação do preset solicitado."""

    deadline = (
        time.monotonic()
        + PRESET_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(
                POLL_INTERVAL_SECONDS
            )
            continue

        if message.type != "sysex":
            continue

        event = parse_preset_event(
            bytes(
                message.bin()
            )
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
        "A confirmação do preset "
        f"{expected_label} não chegou."
    )


def select_preset(
    input_port,
    output_port,
    label: str,
) -> None:
    """Seleciona e confirma um preset."""

    clear_pending_messages(
        input_port
    )

    output_port.send(
        full_bytes_to_mido(
            build_select_preset(
                label
            )
        )
    )

    wait_for_preset(
        input_port,
        label,
    )

    time.sleep(
        PRESET_SETTLE_SECONDS
    )


def reload_56a(
    input_port,
    output_port,
) -> None:
    """Descarta alterações não salvas e recarrega o preset alvo."""

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


def wait_for_expected_chain_response(
    input_port,
    expected_order: tuple[int, ...],
    timeout_seconds: float = STRUCTURAL_TIMEOUT_SECONDS,
) -> tuple[
    ChainOrderState | None,
    tuple[bytes, ...],
]:
    """Aguarda a cadeia esperada e preserva respostas auxiliares.

    Algumas escritas 0x16 devolvem uma estrutura de 128 bytes. Ela possui
    cabeçalho e comprimento válidos, mas não contém a lista completa da
    cadeia. O parser genérico pode representá-la como uma cadeia vazia.
    Essa resposta é relevante para o mapeamento de classe/modelo e deve ser
    preservada, porém não pode encerrar a espera pela cadeia de cinco efeitos.
    """

    received: list[bytes] = []

    deadline = (
        time.monotonic()
        + timeout_seconds
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(
                POLL_INTERVAL_SECONDS
            )
            continue

        if message.type != "sysex":
            continue

        raw = bytes(
            message.bin()
        )

        received.append(
            raw
        )

        print(
            "    SysEx:",
            len(raw),
            "bytes",
        )

        try:
            state = parse_chain_order_response(
                raw
            )
        except ChainOrderProtocolError as error:
            print(
                "    Estrutura auxiliar preservada:",
                error,
            )
            continue

        if state is not None:
            observed_order = tuple(
                state.human_slots
            )

            if (
                observed_order == expected_order
                and state.effect_count
                == len(
                    expected_order
                )
            ):
                return (
                    state,
                    tuple(
                        received
                    ),
                )

            print(
                "    Resposta estrutural auxiliar preservada:",
                len(raw),
                "bytes | ordem interpretada:",
                observed_order,
            )
            continue

        event = parse_preset_event(
            raw
        )

        if event is not None:
            print(
                "    Evento intermediário:",
                event.label,
            )

    return (
        None,
        tuple(
            received
        ),
    )


def validate_normal_state(
    label: str,
    state: ChainOrderState,
) -> None:
    """Valida somente a ordem da cadeia nesta fase.

    O campo de bypass nos índices absolutos 136–145 foi validado fisicamente
    no layout estrutural de 168 bytes. Alterações de classe/modelo podem
    reserializar a mensagem com 164 bytes ou outros tamanhos, deslocando esse
    campo. Portanto, a Fase 14 não usa ``visual_enabled_states`` como critério
    de aprovação fora do layout de 168 bytes.
    """

    observed_order = tuple(
        state.human_slots
    )

    if observed_order != NORMAL_ORDER:
        raise RuntimeError(
            f"{label}: ordem inesperada. "
            f"Recebido {observed_order}."
        )

    message_length = len(
        state.raw_message
    )

    if message_length == 168:
        observed_enabled = tuple(
            state.visual_enabled_states
        )

        if observed_enabled != (
            True,
            True,
            True,
            True,
            True,
        ):
            raise RuntimeError(
                f"{label}: no layout validado de 168 bytes, "
                "algum efeito não está ligado. "
                f"Recebido {observed_enabled}."
            )

        print(
            "    Bypass:",
            "layout 168B validado |",
            observed_enabled,
        )
        return

    print(
        "    Bypass:",
        f"não avaliado no layout de {message_length} bytes",
        "| leitura bruta do parser:",
        state.visual_enabled_states,
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
    """Executa um movimento e exige resposta estrutural."""

    clear_pending_messages(
        input_port
    )

    output_port.send(
        build_move_message(
            source_position=source_position,
            destination_position=destination_position,
        )
    )

    state, received = wait_for_expected_chain_response(
        input_port,
        expected_order,
    )

    if state is None:
        raise RuntimeError(
            "A resposta estrutural do movimento não chegou."
        )

    if tuple(
        state.human_slots
    ) != expected_order:
        raise RuntimeError(
            "Ordem inesperada após o movimento. "
            f"Esperado {expected_order}; "
            f"recebido {state.human_slots}."
        )

    time.sleep(
        ACTION_SETTLE_SECONDS
    )

    return (
        state,
        received,
    )


def force_normal_structural_capture(
    input_port,
    output_port,
) -> tuple[
    ChainOrderState,
    tuple[bytes, ...],
]:
    """Força uma resposta estrutural e termina na ordem normal."""

    _, first_received = execute_move(
        input_port,
        output_port,
        5,
        4,
        SWAPPED_ORDER,
    )

    state, second_received = execute_move(
        input_port,
        output_port,
        4,
        5,
        NORMAL_ORDER,
    )

    return (
        state,
        first_received
        + second_received,
    )


def capture_baseline(
    input_port,
    output_port,
) -> StructuralCapture:
    """Coleta a referência estrutural do preset salvo."""

    print()
    print(
        "BASELINE: coletando estado original"
    )

    state, received = force_normal_structural_capture(
        input_port,
        output_port,
    )

    validate_normal_state(
        "BASELINE",
        state,
    )

    return StructuralCapture(
        label="BASELINE",
        slot_number=None,
        operation="baseline",
        model=None,
        state=state,
        received_messages=received,
        capture_source="movimento_reversivel",
    )


def send_write_and_capture(
    input_port,
    output_port,
    label: str,
    slot_number: int,
    operation: str,
    model: ModelSpec,
    message: mido.Message,
) -> StructuralCapture:
    """Envia uma escrita e captura a estrutura resultante."""

    print()
    print(
        label,
        f"| slot {slot_number}",
        f"| {model.class_name}/{model.model_name}",
    )

    clear_pending_messages(
        input_port
    )

    output_port.send(
        message
    )

    state, received = wait_for_expected_chain_response(
        input_port,
        NORMAL_ORDER,
        timeout_seconds=(
            IMMEDIATE_RESPONSE_TIMEOUT_SECONDS
        ),
    )

    capture_source = (
        "resposta_imediata"
    )

    if state is None:
        print(
            "    Resposta estrutural imediata ausente."
        )
        print(
            "    Forçando leitura por movimento reversível."
        )

        forced_state, forced_received = (
            force_normal_structural_capture(
                input_port,
                output_port,
            )
        )

        state = forced_state
        received = (
            received
            + forced_received
        )

        capture_source = (
            "movimento_reversivel"
        )

    validate_normal_state(
        label,
        state,
    )

    print(
        "    Captura:",
        capture_source,
        "|",
        len(
            state.raw_message
        ),
        "bytes",
    )

    time.sleep(
        ACTION_SETTLE_SECONDS
    )

    return StructuralCapture(
        label=label,
        slot_number=slot_number,
        operation=operation,
        model=model,
        state=state,
        received_messages=received,
        capture_source=capture_source,
    )


def build_same_class_message(
    slot_number: int,
    model: ModelSpec,
) -> mido.Message:
    """Monta uma escrita 0x16."""

    return build_set_effect_model_message(
        slot_number=slot_number,
        class_id=model.class_id,
        model_id=model.model_id,
        secondary_selector=(
            model.secondary_selector
        ),
    )


def build_cross_class_message(
    slot_number: int,
    model: ModelSpec,
) -> mido.Message:
    """Monta uma substituição 0x17."""

    return build_replace_effect_message(
        slot_number=slot_number,
        class_id=model.class_id,
        model_id=model.model_id,
        secondary_selector=(
            model.secondary_selector
        ),
    )


def save_messages(
    path: Path,
    messages: tuple[bytes, ...],
) -> None:
    """Salva mensagens SysEx em formato hexadecimal."""

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
                f"Mensagem {index} - "
                f"{len(message)} bytes\n"
            )
            output.write(
                message.hex(" ").upper()
            )
            output.write(
                "\n\n"
            )


def save_capture(
    output_directory: Path,
    capture: StructuralCapture,
) -> None:
    """Salva uma captura completa."""

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
        capture.state.raw_message.hex(" ").upper()
        + "\n",
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
        ).write_bytes(
            message
        )


def byte_differences(
    baseline: bytes,
    candidate: bytes,
) -> list[
    tuple[
        int,
        int | None,
        int | None,
    ]
]:
    """Retorna diferenças absolutas, incluindo mudanças de tamanho."""

    maximum_length = max(
        len(
            baseline
        ),
        len(
            candidate
        ),
    )

    differences: list[
        tuple[
            int,
            int | None,
            int | None,
        ]
    ] = []

    for index in range(
        maximum_length
    ):
        baseline_value = (
            baseline[index]
            if index < len(
                baseline
            )
            else None
        )

        candidate_value = (
            candidate[index]
            if index < len(
                candidate
            )
            else None
        )

        if baseline_value != candidate_value:
            differences.append(
                (
                    index,
                    baseline_value,
                    candidate_value,
                )
            )

    return differences


def format_optional_byte(
    value: int | None,
) -> str:
    """Formata um byte que pode estar ausente."""

    if value is None:
        return "--"

    return f"{value:02X}"


def build_reports(
    output_directory: Path,
    captures: list[StructuralCapture],
    error_text: str | None,
) -> None:
    """Gera CSV, relatório textual e manifesto."""

    baseline_capture = next(
        (
            capture
            for capture in captures
            if capture.label == "BASELINE"
        ),
        None,
    )

    manifest = {
        "preset": TARGET_PRESET,
        "captures": [],
        "error": error_text,
    }

    csv_rows: list[
        dict[
            str,
            str | int,
        ]
    ] = []

    lines = [
        "# Mapeamento estrutural de classe e modelo",
        "",
        f"Capturas coletadas: {len(captures)}/21",
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

    for capture in captures:
        difference_rows: list[
            tuple[
                int,
                int | None,
                int | None,
            ]
        ] = []

        if (
            baseline_capture is not None
            and capture.label != "BASELINE"
        ):
            difference_rows = byte_differences(
                baseline_capture.state.raw_message,
                capture.state.raw_message,
            )

        model_description = (
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
        )

        manifest["captures"].append(
            {
                "label": capture.label,
                "slot_number": capture.slot_number,
                "operation": capture.operation,
                "model": model_description,
                "capture_source": capture.capture_source,
                "received_message_lengths": [
                    len(message)
                    for message in capture.received_messages
                ],
                "message_length": len(
                    capture.state.raw_message
                ),
                "order": list(
                    capture.state.human_slots
                ),
                "visual_enabled_raw_parser": list(
                    capture.state.visual_enabled_states
                ),
                "bypass_layout_validated": (
                    len(
                        capture.state.raw_message
                    )
                    == 168
                ),
                "difference_indices_from_baseline": [
                    index
                    for (
                        index,
                        _baseline_value,
                        _candidate_value,
                    ) in difference_rows
                ],
            }
        )

        lines.extend(
            [
                f"## {capture.label}",
                "",
                (
                    f"- slot: {capture.slot_number}"
                    if capture.slot_number is not None
                    else "- slot: referência"
                ),
                f"- operação: {capture.operation}",
                f"- origem da captura: {capture.capture_source}",
                (
                    "- modelo: "
                    + (
                        "estado salvo"
                        if capture.model is None
                        else (
                            f"{capture.model.class_name}/"
                            f"{capture.model.model_name} "
                            f"(classe 0x{capture.model.class_id:02X}, "
                            f"modelo 0x{capture.model.model_id:02X}, "
                            f"seletor 0x{capture.model.secondary_selector:02X})"
                        )
                    )
                ),
                (
                    "- bypass: "
                    + (
                        "avaliado no layout validado de 168 bytes"
                        if len(
                            capture.state.raw_message
                        ) == 168
                        else (
                            "não avaliado neste layout de "
                            f"{len(capture.state.raw_message)} bytes"
                        )
                    )
                ),
                (
                    "- leitura bruta de bypass do parser: "
                    + str(
                        list(
                            capture.state.visual_enabled_states
                        )
                    )
                ),
                (
                    "- diferenças contra baseline: "
                    + (
                        "nenhuma"
                        if not difference_rows
                        else ", ".join(
                            str(
                                index
                            )
                            for (
                                index,
                                _baseline_value,
                                _candidate_value,
                            ) in difference_rows
                        )
                    )
                ),
                "",
            ]
        )

        for (
            index,
            baseline_value,
            candidate_value,
        ) in difference_rows:
            csv_rows.append(
                {
                    "label": capture.label,
                    "slot": (
                        ""
                        if capture.slot_number is None
                        else capture.slot_number
                    ),
                    "operation": capture.operation,
                    "index": index,
                    "baseline_hex": format_optional_byte(
                        baseline_value
                    ),
                    "candidate_hex": format_optional_byte(
                        candidate_value
                    ),
                }
            )

    if baseline_capture is not None:
        lines.extend(
            [
                "# Validação das restaurações",
                "",
            ]
        )

        for slot_number in range(
            1,
            6,
        ):
            for restore_kind in (
                "SAME_RESTORE",
                "CROSS_RESTORE",
            ):
                label = (
                    f"S{slot_number}_{restore_kind}"
                )

                capture = next(
                    (
                        item
                        for item in captures
                        if item.label == label
                    ),
                    None,
                )

                exact = (
                    capture is not None
                    and (
                        capture.state.raw_message
                        == baseline_capture.state.raw_message
                    )
                )

                lines.append(
                    f"- {label}: "
                    + (
                        "idêntica ao baseline"
                        if exact
                        else "diferente ou ausente"
                    )
                )

        lines.append(
            ""
        )

        lines.extend(
            [
                "# Índices candidatos por slot",
                "",
                "O índice 7 é o checksum/valor derivado e deve ser analisado separadamente.",
                "",
            ]
        )

        for slot_number in range(
            1,
            6,
        ):
            same_label = (
                f"S{slot_number}_SAME_ALT"
            )

            cross_label = (
                f"S{slot_number}_CROSS_FILTER"
            )

            same_capture = next(
                (
                    item
                    for item in captures
                    if item.label == same_label
                ),
                None,
            )

            cross_capture = next(
                (
                    item
                    for item in captures
                    if item.label == cross_label
                ),
                None,
            )

            same_indices: list[int] = []
            cross_indices: list[int] = []

            if same_capture is not None:
                same_indices = [
                    index
                    for (
                        index,
                        _baseline_value,
                        _candidate_value,
                    ) in byte_differences(
                        baseline_capture.state.raw_message,
                        same_capture.state.raw_message,
                    )
                    if index != 7
                ]

            if cross_capture is not None:
                cross_indices = [
                    index
                    for (
                        index,
                        _baseline_value,
                        _candidate_value,
                    ) in byte_differences(
                        baseline_capture.state.raw_message,
                        cross_capture.state.raw_message,
                    )
                    if index != 7
                ]

            lines.extend(
                [
                    f"## Slot {slot_number}",
                    "",
                    (
                        "- mudança somente de modelo: "
                        + (
                            ", ".join(
                                str(index)
                                for index in same_indices
                            )
                            if same_indices
                            else "nenhum índice"
                        )
                    ),
                    (
                        "- mudança de classe/modelo: "
                        + (
                            ", ".join(
                                str(index)
                                for index in cross_indices
                            )
                            if cross_indices
                            else "nenhum índice"
                        )
                    ),
                    "",
                ]
            )

    (
        output_directory
        / "REPORT_STRUCTURAL_CLASS_MODEL.md"
    ).write_text(
        "\n".join(
            lines
        ),
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
        / "structural_class_model_diffs.csv"
    ).open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=(
                "label",
                "slot",
                "operation",
                "index",
                "baseline_hex",
                "candidate_hex",
            ),
        )

        writer.writeheader()
        writer.writerows(
            csv_rows
        )


def create_zip(
    output_directory: Path,
) -> Path:
    """Compacta e valida os resultados."""

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
            "Arquivo danificado no ZIP: "
            + damaged
        )

    return zip_path


def require_confirmation() -> None:
    """Confirma o preset e a cadeia inicial."""

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
    """Executa o mapeamento estrutural dos cinco slots."""

    print()
    print("MAPEAMENTO ESTRUTURAL — CLASSE E MODELO")
    print("---------------------------------------")
    print()
    print("Tempo estimado: aproximadamente 3 minutos.")
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
        / f"structural_class_model_56A_{timestamp}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    captures: list[StructuralCapture] = []
    error_text: str | None = None

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

            reload_56a(
                input_port,
                output_port,
            )

            require_confirmation()

            baseline = capture_baseline(
                input_port,
                output_port,
            )

            captures.append(
                baseline
            )

            save_capture(
                output_directory,
                baseline,
            )

            for slot_number in range(
                1,
                6,
            ):
                original = BASELINE_MODELS[
                    slot_number
                ]

                alternate = SAME_CLASS_ALTERNATES[
                    slot_number
                ]

                same_alt = send_write_and_capture(
                    input_port,
                    output_port,
                    f"S{slot_number}_SAME_ALT",
                    slot_number,
                    "same_class_alternate",
                    alternate,
                    build_same_class_message(
                        slot_number,
                        alternate,
                    ),
                )

                captures.append(
                    same_alt
                )

                save_capture(
                    output_directory,
                    same_alt,
                )

                same_restore = send_write_and_capture(
                    input_port,
                    output_port,
                    f"S{slot_number}_SAME_RESTORE",
                    slot_number,
                    "same_class_restore",
                    original,
                    build_same_class_message(
                        slot_number,
                        original,
                    ),
                )

                captures.append(
                    same_restore
                )

                save_capture(
                    output_directory,
                    same_restore,
                )

                cross_filter = send_write_and_capture(
                    input_port,
                    output_port,
                    f"S{slot_number}_CROSS_FILTER",
                    slot_number,
                    "cross_class_filter",
                    CROSS_CLASS_MODEL,
                    build_cross_class_message(
                        slot_number,
                        CROSS_CLASS_MODEL,
                    ),
                )

                captures.append(
                    cross_filter
                )

                save_capture(
                    output_directory,
                    cross_filter,
                )

                cross_restore = send_write_and_capture(
                    input_port,
                    output_port,
                    f"S{slot_number}_CROSS_RESTORE",
                    slot_number,
                    "cross_class_restore",
                    original,
                    build_cross_class_message(
                        slot_number,
                        original,
                    ),
                )

                captures.append(
                    cross_restore
                )

                save_capture(
                    output_directory,
                    cross_restore,
                )

    except KeyboardInterrupt:
        error_text = (
            "Operação cancelada pelo usuário."
        )

        print()
        print(
            error_text
        )

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
                mido.open_input(
                    INPUT_PORT
                ) as input_port,
                mido.open_output(
                    OUTPUT_PORT
                ) as output_port,
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
            print(
                restore_text
            )

            error_text = (
                restore_text
                if error_text is None
                else (
                    error_text
                    + "\n"
                    + restore_text
                )
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
        "/ 21",
    )
    print(
        "Status:",
        (
            "APROVADO"
            if (
                len(captures) == 21
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
