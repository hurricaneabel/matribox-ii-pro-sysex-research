"""Troca modelos de efeito da classe FREQ na Matribox II Pro.

Modelos confirmados por captura USB real:

- Filter       = 0x19
- Octaver      = 0x21
- Dual Melody  = 0x23
- Pitch        = 0x24
- Harmony D    = 0x4E
- Pitch S      = 0x55
- Ring Mod     = 0x2F
- Tape Mod     = 0x33

Nesta etapa, o comando está liberado somente para o slot interno 1,
que foi validado diretamente nas capturas e nos testes reais.
"""

from __future__ import annotations

from dataclasses import dataclass

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7
SLOT_HIGH_INDEX = 39
SLOT_LOW_INDEX = 40
MODEL_HIGH_INDEX = 43
MODEL_LOW_INDEX = 44

EXPECTED_MESSAGE_LENGTH = 58
CONFIRMED_SLOT = 1


@dataclass(frozen=True)
class EffectModel:
    """Representa um modelo de efeito confirmado no protocolo."""

    name: str
    model_id: int


FREQ_MODELS = (
    EffectModel("Filter", 0x19),
    EffectModel("Octaver", 0x21),
    EffectModel("Dual Melody", 0x23),
    EffectModel("Pitch", 0x24),
    EffectModel("Harmony D", 0x4E),
    EffectModel("Pitch S", 0x55),
    EffectModel("Ring Mod", 0x2F),
    EffectModel("Tape Mod", 0x33),
)


# Pacote real de 58 bytes capturado com:
# - slot interno 1;
# - classe FREQ;
# - modelo Filter.
MESSAGE_TEMPLATE_HEX = (
    "f021254d5000003112160000000001000000000100000e"
    "000000000000010b0002000000040001000000010109"
    "000000000001010100000000f7"
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    """Separa um byte nos nibbles alto e baixo."""
    if not 0 <= value <= 0xFF:
        raise ValueError(
            "O valor deve estar entre 0x00 e 0xFF."
        )

    return (
        (value >> 4) & 0x0F,
        value & 0x0F,
    )


def calculate_checksum(message: list[int]) -> int:
    """Calcula o checksum observado nos comandos de escrita."""
    if len(message) < 10:
        raise ValueError(
            "A mensagem é curta demais para calcular o checksum."
        )

    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    if payload_end > len(message) - 1:
        raise ValueError(
            "O tamanho declarado no pacote ultrapassa a mensagem."
        )

    return sum(
        message[payload_start:payload_end]
    ) & 0x7F


def normalize_model_text(value: str) -> str:
    """Remove espaços e pontuação para comparar nomes."""
    return "".join(
        character
        for character in value.casefold()
        if character.isalnum()
    )


def find_model(model_value: str | int) -> EffectModel:
    """Localiza um modelo pelo número do menu, nome ou ID."""
    if isinstance(model_value, int):
        for model in FREQ_MODELS:
            if model.model_id == model_value:
                return model

        raise ValueError(
            f"ID de modelo não confirmado: 0x{model_value:02X}."
        )

    text = model_value.strip()

    if not text:
        raise ValueError(
            "Informe o número, nome ou ID do modelo."
        )

    if text.isdecimal():
        option = int(text)

        if 1 <= option <= len(FREQ_MODELS):
            return FREQ_MODELS[option - 1]

        for model in FREQ_MODELS:
            if model.model_id == option:
                return model

    hexadecimal_text = text.casefold()

    if hexadecimal_text.startswith("0x"):
        try:
            return find_model(
                int(hexadecimal_text, 16)
            )
        except ValueError as error:
            raise ValueError(
                f"ID hexadecimal inválido: {text}."
            ) from error

    if hexadecimal_text.endswith("h"):
        try:
            return find_model(
                int(hexadecimal_text[:-1], 16)
            )
        except ValueError as error:
            raise ValueError(
                f"ID hexadecimal inválido: {text}."
            ) from error

    normalized_text = normalize_model_text(
        text
    )

    for model in FREQ_MODELS:
        if normalize_model_text(
            model.name
        ) == normalized_text:
            return model

    supported_models = ", ".join(
        model.name
        for model in FREQ_MODELS
    )

    raise ValueError(
        "Modelo FREQ não confirmado. "
        f"Use somente: {supported_models}."
    )


def build_effect_model_message(
    effect_position: int,
    model_value: str | int,
) -> mido.Message:
    """Monta o SysEx para trocar o modelo FREQ do slot interno 1."""
    if effect_position != CONFIRMED_SLOT:
        raise ValueError(
            "Nesta etapa, use somente o slot interno 1."
        )

    model = find_model(
        model_value
    )

    full_message = list(
        bytes.fromhex(
            MESSAGE_TEMPLATE_HEX
        )
    )

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError(
            "O modelo de pacote deveria ter "
            f"{EXPECTED_MESSAGE_LENGTH} bytes, mas possui "
            f"{len(full_message)}."
        )

    protocol_position = effect_position - 1
    slot_high, slot_low = split_into_nibbles(
        protocol_position
    )
    model_high, model_low = split_into_nibbles(
        model.model_id
    )

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    print("Classe: FREQ")
    print(
        "Tamanho do pacote:",
        len(full_message),
        "bytes",
    )
    print(
        "Slot interno codificado:",
        f"{slot_high:02X} {slot_low:02X}",
    )
    print(
        "Modelo selecionado:",
        model.name,
    )
    print(
        "ID do modelo:",
        f"0x{model.model_id:02X}",
    )
    print(
        "Modelo codificado:",
        f"{model_high:02X} {model_low:02X}",
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

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def print_model_menu() -> None:
    """Mostra os modelos FREQ confirmados."""
    print(
        "\nModelos confirmados da classe FREQ:"
    )

    for index, model in enumerate(
        FREQ_MODELS,
        start=1,
    ):
        print(
            f"{index}. {model.name} "
            f"(0x{model.model_id:02X})"
        )


def main() -> None:
    """Solicita o modelo e envia o comando para o slot interno 1."""
    try:
        print(
            "Slot interno confirmado nesta etapa: 1"
        )

        print_model_menu()

        option = input(
            "\nDigite o número, nome ou ID do modelo: "
        ).strip()

        model = find_model(
            option
        )

        message = build_effect_model_message(
            effect_position=CONFIRMED_SLOT,
            model_value=model.model_id,
        )

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            output.send(
                message
            )

        print(
            f"\nComando enviado: slot interno 1 "
            f"-> {model.name}."
        )

    except (
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"Erro: {error}"
        )

    except OSError as error:
        print(
            "Erro ao abrir a porta MIDI:",
            error,
        )


if __name__ == "__main__":
    main()