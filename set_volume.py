"""
Define o volume do preset da Matribox II Pro por SysEx.

O pacote utilizado foi obtido da comunicação real entre
o editor oficial e a pedaleira.
"""

from __future__ import annotations

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7
VOLUME_HIGH_INDEX = 39
VOLUME_LOW_INDEX = 40


# Pacote real de escrita capturado com volume 49.
# Mantemos F0 e F7 nesta lista para facilitar o estudo dos índices.
MESSAGE_TEMPLATE = [
    0xF0,
    0x21,
    0x25,
    0x4D,
    0x50,
    0x00,
    0x00,
    0x27,
    0x12,
    0x14,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x00,
    0x00,
    0x0C,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x09,
    0x00,
    0x03,
    0x00,
    0x00,
    0x00,
    0x05,
    0x00,
    0x01,
    0x03,
    0x01,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01,
    0x01,
    0x00,
    0x00,
    0x00,
    0x00,
    0xF7,
]


def split_into_nibbles(value: int) -> tuple[int, int]:
    """
    Separa um valor nos dois nibbles hexadecimais.

    Exemplo:
        75 decimal = 0x4B
        resultado = 0x04, 0x0B
    """
    high_nibble = (value >> 4) & 0x0F
    low_nibble = value & 0x0F

    return high_nibble, low_nibble


def calculate_checksum(message: list[int]) -> int:
    """
    Calcula o checksum observado nos comandos de escrita.

    A soma considera os índices 14 até 48.
    """
    return sum(message[14:49]) & 0x7F


def build_volume_message(volume: int) -> mido.Message:
    """Monta uma mensagem SysEx válida para o volume informado."""
    if not 0 <= volume <= 100:
        raise ValueError(
            "O volume deve estar entre 0 e 100."
        )

    full_message = MESSAGE_TEMPLATE.copy()

    high_nibble, low_nibble = split_into_nibbles(
        volume,
    )

    full_message[VOLUME_HIGH_INDEX] = high_nibble
    full_message[VOLUME_LOW_INDEX] = low_nibble

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message,
    )

    print(
        "Checksum calculado: "
        f"{full_message[CHECKSUM_INDEX]:02X}"
    )

    print(
        "Valor codificado: "
        f"{high_nibble:02X} {low_nibble:02X}"
    )

    print(
        "Mensagem completa:"
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
    """Solicita o volume e envia o comando."""
    try:
        volume = int(
            input(
                "Digite o volume entre 0 e 100: "
            ).strip()
        )

        message = build_volume_message(volume)

        with mido.open_output(OUTPUT_PORT) as output:
            output.send(message)

        print(
            f"Comando enviado para volume {volume}."
        )

    except ValueError as error:
        print(f"Erro: {error}")

    except OSError as error:
        print(
            "Erro ao abrir a porta MIDI: "
            f"{error}"
        )


if __name__ == "__main__":
    main()