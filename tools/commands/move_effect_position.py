"""Move um efeito entre posições visuais da cadeia da Matribox II Pro."""

from __future__ import annotations

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7

SOURCE_HIGH_INDEX = 39
SOURCE_LOW_INDEX = 40

DESTINATION_HIGH_INDEX = 41
DESTINATION_LOW_INDEX = 42


# Pacote real capturado ao mover:
# posição visual 1 → posição visual 12.
MESSAGE_TEMPLATE_HEX = (
    "f021254d5000004712170000000001000000000100000f000000000000010c"
    "00010000000400010000000b0f0f0f0f0f0f0f0f0f0f010100000000f7"
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    """Separa um número nos nibbles alto e baixo."""
    high_nibble = (value >> 4) & 0x0F
    low_nibble = value & 0x0F

    return high_nibble, low_nibble


def calculate_checksum(message: list[int]) -> int:
    """Calcula o checksum usando o tamanho informado no índice 9."""
    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    return sum(message[payload_start:payload_end]) & 0x7F


def build_move_message(
    source_position: int,
    destination_position: int,
) -> mido.Message:
    """Monta o SysEx que move um efeito entre posições visuais."""
    if not 1 <= source_position <= 12:
        raise ValueError(
            "A posição de origem deve estar entre 1 e 12."
        )

    if not 1 <= destination_position <= 12:
        raise ValueError(
            "A posição de destino deve estar entre 1 e 12."
        )

    if source_position == destination_position:
        raise ValueError(
            "A origem e o destino não podem ser iguais."
        )

    full_message = list(
        bytes.fromhex(MESSAGE_TEMPLATE_HEX)
    )

    # A interface apresenta posições começando em 1.
    # O protocolo SysEx utiliza posições começando em 0.
    protocol_source = source_position - 1
    protocol_destination = destination_position - 1

    source_high, source_low = split_into_nibbles(
        protocol_source
    )

    destination_high, destination_low = split_into_nibbles(
        protocol_destination
    )

    full_message[SOURCE_HIGH_INDEX] = source_high
    full_message[SOURCE_LOW_INDEX] = source_low

    full_message[DESTINATION_HIGH_INDEX] = destination_high
    full_message[DESTINATION_LOW_INDEX] = destination_low

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    print(
        "Origem codificada:",
        f"{source_high:02X} {source_low:02X}",
    )

    print(
        "Destino codificado:",
        f"{destination_high:02X} {destination_low:02X}",
    )

    print(
        "Checksum calculado:",
        f"{full_message[CHECKSUM_INDEX]:02X}",
    )

    print("Pacote completo:")

    print(
        " ".join(
            f"{byte:02X}"
            for byte in full_message
        )
    )

    # O Mido adiciona F0 e F7 automaticamente.
    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def main() -> None:
    """Solicita origem e destino e envia o movimento."""
    try:
        source_position = int(
            input(
                "Digite a posição visual de origem (1 até 12): "
            ).strip()
        )

        destination_position = int(
            input(
                "Digite a posição visual de destino (1 até 12): "
            ).strip()
        )

        message = build_move_message(
            source_position=source_position,
            destination_position=destination_position,
        )

        confirmation = input(
            f"Confirmar movimento de {source_position} "
            f"para {destination_position}? Digite S: "
        ).strip().upper()

        if confirmation != "S":
            print("Movimento cancelado.")
            return

        with mido.open_output(OUTPUT_PORT) as output:
            output.send(message)

        print(
            f"Efeito movido da posição visual "
            f"{source_position} para {destination_position}."
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