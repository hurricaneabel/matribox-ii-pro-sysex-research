"""Liga ou desliga um efeito pelo slot interno da Matribox II Pro."""

from __future__ import annotations

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7

SLOT_HIGH_INDEX = 39
SLOT_LOW_INDEX = 40

STATE_HIGH_INDEX = 47
STATE_LOW_INDEX = 48


# Pacote real capturado com:
# primeiro efeito da cadeia desligado.
MESSAGE_TEMPLATE_HEX = (
    "f021254d5000001b121800000000010000000001000100000000000000010d"
    "000200000005000100000000000000000000000000000000010100000000f7"
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    """Separa um valor nos nibbles alto e baixo."""
    high_nibble = (value >> 4) & 0x0F
    low_nibble = value & 0x0F

    return high_nibble, low_nibble


def calculate_checksum(message: list[int]) -> int:
    """Calcula o checksum usando o tamanho informado no índice 9."""
    payload_start = 10

    # O índice 9 informa quantos bytes existem depois de juntar
    # cada par de nibbles. Por isso multiplicamos o tamanho por 2.
    payload_end = payload_start + (message[9] * 2)

    return sum(message[payload_start:payload_end]) & 0x7F


def build_effect_message(
    effect_position: int,
    enabled: bool,
) -> mido.Message:
    """Monta o SysEx para ligar ou desligar uma posição da cadeia."""
    if not 1 <= effect_position <= 12:
        raise ValueError(
            "Nesta etapa, use somente as posições 1 até 12 "
            "que já foram confirmadas nas capturas."
        )

    full_message = list(
        bytes.fromhex(MESSAGE_TEMPLATE_HEX)
    )

    # A interface mostra posições começando em 1.
    # O protocolo começa em 0.
    protocol_position = effect_position - 1

    slot_high, slot_low = split_into_nibbles(
        protocol_position
    )

    state_value = 1 if enabled else 0
    state_high, state_low = split_into_nibbles(
        state_value
    )

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low

    full_message[STATE_HIGH_INDEX] = state_high
    full_message[STATE_LOW_INDEX] = state_low

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    print(
        "Slot Interno Codificado:",
        f"{slot_high:02X} {slot_low:02X}",
    )

    print(
        "Estado codificado:",
        f"{state_high:02X} {state_low:02X}",
    )

    print(
        "Checksum calculado:",
        f"{full_message[CHECKSUM_INDEX]:02X}",
    )

    print(
        "Pacote completo:"
    )

    print(
        " ".join(
            f"{byte:02X}"
            for byte in full_message
        )
    )

    # O Mido acrescenta F0 e F7 automaticamente.
    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def main() -> None:
    """Solicita a posição e o estado e envia o comando."""
    try:
        effect_position = int(
            input(
                "Digite o slot interno do efeito (1 até 12): "
            ).strip()
        )

        state_text = input(
            "Digite L para ligar ou D para desligar: "
        ).strip().upper()

        if state_text not in {"L", "D"}:
            raise ValueError(
                "Digite somente L para ligar ou D para desligar."
            )

        enabled = state_text == "L"

        message = build_effect_message(
            effect_position=effect_position,
            enabled=enabled,
        )

        with mido.open_output(OUTPUT_PORT) as output:
            output.send(message)

        state_name = "ligado" if enabled else "desligado"

        print(
            f"Efeito de slot interno {effect_position} "
            f"{state_name}."
        )

    except ValueError as error:
        print(f"Erro: {error}")

    except OSError as error:
        print(
            "Erro ao abrir a porta MIDI:",
            error,
        )


if __name__ == "__main__":
    main()