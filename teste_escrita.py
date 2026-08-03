"""Testa os pacotes SysEx reais para ligar e desligar o DYN - COMP 1."""

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


DYN_ON_HEX = (
    "f021254d5000001c121800000000010000000001000100000000000000010d"
    "000200000005000100000000000000000001000000000000010100000000f7"
)

DYN_OFF_HEX = (
    "f021254d5000001b121800000000010000000001000100000000000000010d"
    "000200000005000100000000000000000000000000000000010100000000f7"
)


def create_sysex_message(hex_message: str) -> mido.Message:
    """Converte o pacote hexadecimal completo em mensagem SysEx do Mido."""
    full_message = bytes.fromhex(hex_message)

    if len(full_message) != 62:
        raise ValueError(
            f"O pacote deveria ter 62 bytes, mas possui {len(full_message)}."
        )

    if full_message[0] != 0xF0:
        raise ValueError("O pacote não começa com F0.")

    if full_message[-1] != 0xF7:
        raise ValueError("O pacote não termina com F7.")

    print(
        "Pacote validado:",
        " ".join(f"{byte:02X}" for byte in full_message),
    )

    # O Mido adiciona F0 e F7 automaticamente.
    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def main() -> None:
    """Envia os comandos capturados para o DYN."""
    dyn_on_message = create_sysex_message(DYN_ON_HEX)
    dyn_off_message = create_sysex_message(DYN_OFF_HEX)

    with mido.open_output(OUTPUT_PORT) as output:
        input(
            "\nDeixe o preset 56A com o DYN desligado.\n"
            "Pressione Enter para LIGAR o DYN..."
        )

        output.send(dyn_on_message)
        print("Comando LIGAR enviado.")

        input(
            "\nConfira se o DYN ligou.\n"
            "Pressione Enter para DESLIGAR o DYN..."
        )

        output.send(dyn_off_message)
        print("Comando DESLIGAR enviado.")


if __name__ == "__main__":
    main()