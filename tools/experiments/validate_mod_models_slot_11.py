"""Valida os 23 modelos confirmados da classe MOD no slot 11.

Mapeamento extraído da captura USB/Wireshark:
- classe MOD: 0x08
- flag estrutural: 0x00
- seletor 0x04 para os modelos 1 a 21
- seletor 0x01 para DETUNE e LOFI BIT

A sequência automática começa considerando o slot 11 em E-CHORUS,
percorre os outros 22 modelos e termina novamente em E-CHORUS.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7
SLOT_HIGH_INDEX = 39
SLOT_LOW_INDEX = 40
CLASS_HIGH_INDEX = 41
CLASS_LOW_INDEX = 42
MODEL_HIGH_INDEX = 43
MODEL_LOW_INDEX = 44
EFFECT_INSTANCE_FLAG_INDEX = 47
SECONDARY_SELECTOR_INDEX = 50

EXPECTED_MESSAGE_LENGTH = 58
EXPECTED_COMMAND_TYPE = 0x16

SLOT_NUMBER = 11
PROTOCOL_SLOT = SLOT_NUMBER - 1

MOD_CLASS_ID = 0x08
MOD_INSTANCE_FLAG = 0x00
STEP_DELAY_SECONDS = 2.0

# Pacote 0x16 capturado na volta final para E-CHORUS.
E_CHORUS_TEMPLATE_HEX = (
    "f021254d5000003c12160000000001000000000100000e"
    "000000000000010b0002000000040001000a0008000100"
    "0000000004010100000000f7"
)


@dataclass(frozen=True)
class ModModel:
    menu_number: int
    name: str
    model_id: int
    secondary_selector: int
    expected_checksum: int


MOD_MODELS = (
    ModModel(1, "E-CHORUS",       0x01, 0x04, 0x3C),
    ModModel(2, "D-CHORUS",       0x02, 0x04, 0x3D),
    ModModel(3, "B-CHORUS",       0x08, 0x04, 0x43),
    ModModel(4, "M-CHORUS",       0x0F, 0x04, 0x4A),
    ModModel(5, "FLANGER",        0x11, 0x04, 0x3D),
    ModModel(6, "FLANGER N",      0x13, 0x04, 0x3F),
    ModModel(7, "TREM JET",       0x14, 0x04, 0x40),
    ModModel(8, "BASS JET",       0x12, 0x04, 0x3E),
    ModModel(9, "VIBRATO",        0x17, 0x04, 0x43),
    ModModel(10, "BBD ROTO",      0x15, 0x04, 0x41),
    ModModel(11, "CE-ROTO",       0x16, 0x04, 0x42),
    ModModel(12, "PHASER",        0x19, 0x04, 0x45),
    ModModel(13, "BBD PHASER",    0x1A, 0x04, 0x46),
    ModModel(14, "PHASER ST",     0x1B, 0x04, 0x47),
    ModModel(15, "PAN PHASER",    0x1E, 0x04, 0x4A),
    ModModel(16, "VIBE",          0x1F, 0x04, 0x4B),
    ModModel(17, "U-VIBE",        0x20, 0x04, 0x3D),
    ModModel(18, "TREMOLO",       0x21, 0x04, 0x3E),
    ModModel(19, "SINE TREM",     0x26, 0x04, 0x43),
    ModModel(20, "TRIANGULE TREM",0x27, 0x04, 0x44),
    ModModel(21, "BIAS TREM",     0x28, 0x04, 0x45),
    ModModel(22, "DETUNE",        0x29, 0x01, 0x43),
    ModModel(23, "LOFI BIT",      0x2E, 0x01, 0x48),
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    if not 0 <= value <= 0xFF:
        raise ValueError(
            "O valor deve estar entre 0x00 e 0xFF."
        )

    return (
        (value >> 4) & 0x0F,
        value & 0x0F,
    )


def calculate_checksum(message: list[int]) -> int:
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise ValueError(
            "A mensagem deve possuir "
            f"{EXPECTED_MESSAGE_LENGTH} bytes."
        )

    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    return sum(
        message[payload_start:payload_end]
    ) & 0x7F


def build_mod_message(
    mod_model: ModModel,
) -> mido.Message:
    full_message = list(
        bytes.fromhex(
            E_CHORUS_TEMPLATE_HEX
        )
    )

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError(
            "Tamanho inesperado do pacote-base."
        )

    if full_message[9] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError(
            "Tipo de comando inesperado."
        )

    slot_high, slot_low = split_into_nibbles(
        PROTOCOL_SLOT
    )
    class_high, class_low = split_into_nibbles(
        MOD_CLASS_ID
    )
    model_high, model_low = split_into_nibbles(
        mod_model.model_id
    )

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = (
        MOD_INSTANCE_FLAG
    )
    full_message[SECONDARY_SELECTOR_INDEX] = (
        mod_model.secondary_selector
    )

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    if full_message[CHECKSUM_INDEX] != mod_model.expected_checksum:
        raise RuntimeError(
            f"Checksum de {mod_model.name} inesperado: "
            f"0x{full_message[CHECKSUM_INDEX]:02X}. "
            f"Esperado: 0x{mod_model.expected_checksum:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def validate_all_packets() -> None:
    for mod_model in MOD_MODELS:
        packet = bytes(
            build_mod_message(
                mod_model
            ).bin()
        )

        if packet[SLOT_HIGH_INDEX:SLOT_LOW_INDEX + 1] != bytes((0x00, 0x0A)):
            raise RuntimeError(
                f"Slot incorreto em {mod_model.name}."
            )

        if packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1] != bytes((0x00, 0x08)):
            raise RuntimeError(
                f"Classe incorreta em {mod_model.name}."
            )

        if packet[EFFECT_INSTANCE_FLAG_INDEX] != 0x00:
            raise RuntimeError(
                f"Flag incorreta em {mod_model.name}."
            )

        if packet[SECONDARY_SELECTOR_INDEX] != mod_model.secondary_selector:
            raise RuntimeError(
                f"Seletor incorreto em {mod_model.name}."
            )

    print(
        "\nValidação local concluída: "
        "23 pacotes reproduzem os campos e checksums capturados."
    )


def print_models() -> None:
    print(
        "MOD — 23 modelos confirmados:"
    )

    for mod_model in MOD_MODELS:
        print(
            f"{mod_model.menu_number:>2}. "
            f"{mod_model.name:<15} "
            f"modelo 0x{mod_model.model_id:02X} "
            f"seletor 0x{mod_model.secondary_selector:02X} "
            f"checksum 0x{mod_model.expected_checksum:02X}"
        )


def send_mod_model(
    output,
    mod_model: ModModel,
) -> None:
    message = build_mod_message(
        mod_model
    )
    packet = bytes(
        message.bin()
    )

    print(
        f"\n{mod_model.name}"
    )
    print(
        f"modelo: 0x{mod_model.model_id:02X}"
    )
    print(
        f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}"
    )
    print(
        "seletor secundário: "
        f"0x{packet[SECONDARY_SELECTOR_INDEX]:02X}"
    )
    print(
        f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
    )

    output.send(
        message
    )


def run_all_models(output) -> None:
    print(
        "\nIniciando o teste automático dos 23 MODs."
    )

    for mod_model in MOD_MODELS[1:]:
        send_mod_model(
            output,
            mod_model,
        )
        time.sleep(
            STEP_DELAY_SECONDS
        )

    send_mod_model(
        output,
        MOD_MODELS[0],
    )

    print(
        "\nSequência concluída. "
        "Estado final: E-CHORUS."
    )


def main() -> None:
    try:
        print(
            "Validação MOD — slot 11"
        )
        print(
            "Comece com o slot 11 em E-CHORUS."
        )
        print()

        print_models()

        print(
            "\nDigite um número de 1 a 23 para testar individualmente."
        )
        print(
            "Digite A para percorrer todos automaticamente."
        )
        print(
            "Digite V para validar os pacotes sem enviar à pedaleira."
        )

        option = input(
            "\nEscolha: "
        ).strip().lower()

        if option == "v":
            validate_all_packets()
            return

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            if option == "a":
                run_all_models(
                    output
                )
                return

            menu_number = int(
                option
            )

            mod_model = next(
                (
                    item
                    for item in MOD_MODELS
                    if item.menu_number == menu_number
                ),
                None,
            )

            if mod_model is None:
                raise ValueError(
                    "Escolha um número entre 1 e 23."
                )

            send_mod_model(
                output,
                mod_model,
            )

            print(
                "\nComando enviado."
            )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            f"\nErro: {error}"
        )

    except KeyboardInterrupt:
        print(
            "\nTeste interrompido."
        )


if __name__ == "__main__":
    main()
