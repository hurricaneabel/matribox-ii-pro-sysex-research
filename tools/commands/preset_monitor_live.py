"""Adaptador MIDI ao vivo para o monitor de presets.

A lógica de protocolo e de reconstrução permanece nos módulos puros. Este
arquivo é apenas a borda de entrada/saída:

- converte bytes SysEx para mensagens do mido;
- envia a sequência de inicialização;
- entrega mensagens recebidas ao PresetMonitorCore;
- aguarda o primeiro snapshot enriquecido;
- reenvia a consulta global quando a resposta para de avançar;
- produz atualizações enquanto o usuário troca presets.

Nenhuma porta é aberta automaticamente ao importar este módulo.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Iterator, Protocol

import mido

from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    PresetMonitorSnapshot,
    PresetMonitorUpdate,
    build_monitor_startup_plan,
)


DEFAULT_INPUT_PORT = "Matribox II Pro Subdevice 0"
DEFAULT_OUTPUT_PORT = "Matribox II Pro Subdevice 1"

DEFAULT_STARTUP_TIMEOUT_SECONDS = 12.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.01
DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS = 1.5
DEFAULT_GLOBAL_QUERY_RETRIES = 3


class InputPortProtocol(Protocol):
    """Contrato mínimo usado pelas portas de entrada reais e falsas."""

    def poll(self):
        ...


class OutputPortProtocol(Protocol):
    """Contrato mínimo usado pelas portas de saída reais e falsas."""

    def send(self, message) -> None:
        ...


class LivePresetMonitorError(RuntimeError):
    """Erro da camada MIDI ao vivo."""


class StartupTimeoutError(LivePresetMonitorError):
    """O monitor não obteve metadados e preset atual dentro do prazo."""


@dataclass(frozen=True, slots=True)
class StartupTransmissionSummary:
    """Resumo da sequência transmitida à pedaleira."""

    handshake_count: int
    global_query_sent: bool
    current_preset_query_sent: bool


@dataclass(frozen=True, slots=True)
class InitialSnapshotResult:
    """Primeiro estado completo obtido da sessão."""

    snapshot: PresetMonitorSnapshot
    fragment_count: int
    global_block_size: int
    metadata_count: int
    global_query_retries: int


def create_mido_sysex(
    full_message: bytes | bytearray,
) -> mido.Message:
    """Converte uma mensagem completa F0...F7 para o formato do mido."""
    raw = bytes(full_message)

    if len(raw) < 2:
        raise ValueError(
            "Mensagem SysEx vazia ou incompleta."
        )

    if raw[0] != 0xF0:
        raise ValueError(
            "A mensagem SysEx não começa com F0."
        )

    if raw[-1] != 0xF7:
        raise ValueError(
            "A mensagem SysEx não termina com F7."
        )

    if any(value > 0x7F for value in raw[1:-1]):
        raise ValueError(
            "O corpo SysEx contém byte acima de 0x7F."
        )

    return mido.Message(
        "sysex",
        data=raw[1:-1],
    )


def clear_pending_messages(
    input_port: InputPortProtocol,
) -> int:
    """Remove mensagens antigas que já estavam aguardando."""
    removed = 0

    while input_port.poll() is not None:
        removed += 1

    return removed


def send_global_metadata_query(
    output_port: OutputPortProtocol,
) -> None:
    """Reenvia somente a consulta global, preservando a montagem parcial."""
    plan = build_monitor_startup_plan()

    output_port.send(
        create_mido_sysex(
            plan.global_metadata_query
        )
    )


def send_current_preset_query(
    output_port: OutputPortProtocol,
) -> None:
    """Envia somente a consulta do preset atual."""
    plan = build_monitor_startup_plan()

    output_port.send(
        create_mido_sysex(
            plan.current_preset_query
        )
    )


def send_startup_sequence(
    output_port: OutputPortProtocol,
    *,
    sleeper: Callable[[float], None] = time.sleep,
    on_handshake: Callable[[int, int], None] | None = None,
) -> StartupTransmissionSummary:
    """Envia handshake, consulta global e consulta do preset atual."""
    plan = build_monitor_startup_plan()

    handshake = create_mido_sysex(
        plan.handshake_message
    )

    for attempt in range(
        1,
        plan.handshake_repetitions + 1,
    ):
        output_port.send(handshake)

        if on_handshake is not None:
            on_handshake(
                attempt,
                plan.handshake_repetitions,
            )

        if attempt < plan.handshake_repetitions:
            sleeper(
                plan.handshake_interval_seconds
            )

    sleeper(
        plan.stabilization_seconds
    )

    send_global_metadata_query(
        output_port
    )

    send_current_preset_query(
        output_port
    )

    return StartupTransmissionSummary(
        handshake_count=plan.handshake_repetitions,
        global_query_sent=True,
        current_preset_query_sent=True,
    )


def process_mido_message(
    core: PresetMonitorCore,
    message,
) -> PresetMonitorUpdate | None:
    """Entrega ao núcleo apenas mensagens SysEx completas."""
    if getattr(message, "type", None) != "sysex":
        return None

    full_message = bytes(
        message.bin()
    )

    return core.feed(
        full_message
    )


def describe_startup_progress(
    core: PresetMonitorCore,
) -> str:
    """Gera diagnóstico compacto para timeout ou logs."""
    progress = core.metadata_progress

    if progress is None:
        progress_text = "nenhum fragmento global aceito"
    else:
        covered, total = progress
        progress_text = (
            f"{covered}/{total} bytes globais"
        )

    assembly = core.collector.best_assembly()

    if assembly is None or assembly.complete:
        missing_text = ""
    else:
        missing_text = (
            f", lacunas={assembly.missing_ranges}"
        )

    return (
        f"metadados={'sim' if core.metadata_ready else 'não'}, "
        f"preset={'sim' if core.current_preset_known else 'não'}, "
        f"fragmentos={core.fragment_count}, "
        f"{progress_text}"
        f"{missing_text}"
    )


def wait_for_initial_snapshot(
    input_port: InputPortProtocol,
    core: PresetMonitorCore,
    *,
    timeout_seconds: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    on_update: Callable[[PresetMonitorUpdate], None] | None = None,
    retry_global_query: Callable[[], None] | None = None,
    global_retry_interval_seconds: float = (
        DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS
    ),
    max_global_query_retries: int = DEFAULT_GLOBAL_QUERY_RETRIES,
    on_global_retry: (
        Callable[[int, int, str], None]
        | None
    ) = None,
) -> InitialSnapshotResult:
    """Aguarda o estado inicial e recupera respostas globais incompletas.

    Quando a cobertura global deixa de avançar pelo intervalo configurado,
    a consulta global pode ser reenviada. A montagem parcial é preservada:
    fragmentos repetidos são ignorados e o fragmento ausente completa o bloco.
    """
    if timeout_seconds <= 0:
        raise ValueError(
            "O timeout deve ser maior que zero."
        )

    if poll_interval_seconds <= 0:
        raise ValueError(
            "O intervalo de polling deve ser maior que zero."
        )

    if global_retry_interval_seconds <= 0:
        raise ValueError(
            "O intervalo de reenvio global deve ser maior que zero."
        )

    if max_global_query_retries < 0:
        raise ValueError(
            "A quantidade de reenvios globais não pode ser negativa."
        )

    started_at = monotonic()
    deadline = started_at + timeout_seconds
    next_global_retry = (
        started_at
        + global_retry_interval_seconds
    )

    retries = 0
    last_covered_bytes = 0

    while monotonic() < deadline:
        now = monotonic()

        if (
            retry_global_query is not None
            and not core.metadata_ready
            and retries < max_global_query_retries
            and now >= next_global_retry
        ):
            retries += 1
            diagnostic = describe_startup_progress(
                core
            )

            retry_global_query()

            if on_global_retry is not None:
                on_global_retry(
                    retries,
                    max_global_query_retries,
                    diagnostic,
                )

            next_global_retry = (
                now
                + global_retry_interval_seconds
            )

        message = input_port.poll()

        if message is None:
            sleeper(
                poll_interval_seconds
            )
            continue

        update = process_mido_message(
            core,
            message,
        )

        if update is None:
            continue

        if (
            update.collector_update.accepted
            and update.collector_update.covered_bytes
            > last_covered_bytes
        ):
            last_covered_bytes = (
                update.collector_update.covered_bytes
            )
            next_global_retry = (
                monotonic()
                + global_retry_interval_seconds
            )

        if on_update is not None:
            on_update(update)

        if update.snapshot is not None and core.ready:
            if core.global_block is None or core.metadata is None:
                raise AssertionError(
                    "Snapshot pronto sem metadados completos."
                )

            return InitialSnapshotResult(
                snapshot=update.snapshot,
                fragment_count=core.fragment_count,
                global_block_size=len(
                    core.global_block
                ),
                metadata_count=len(
                    core.metadata.presets
                ),
                global_query_retries=retries,
            )

    raise StartupTimeoutError(
        "Tempo esgotado aguardando o estado inicial: "
        + describe_startup_progress(core)
        + f", reenvios globais={retries}"
    )


def iter_monitor_updates(
    input_port: InputPortProtocol,
    core: PresetMonitorCore,
    *,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
) -> Iterator[PresetMonitorUpdate]:
    """Produz atualizações SysEx indefinidamente até o chamador interromper."""
    if poll_interval_seconds <= 0:
        raise ValueError(
            "O intervalo de polling deve ser maior que zero."
        )

    while True:
        message = input_port.poll()

        if message is None:
            sleeper(
                poll_interval_seconds
            )
            continue

        update = process_mido_message(
            core,
            message,
        )

        if update is not None:
            yield update
