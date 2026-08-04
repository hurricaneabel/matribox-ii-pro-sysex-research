"""Gerenciador interativo da cadeia de efeitos da Matribox II Pro.

Permite adicionar, substituir e excluir qualquer slot interno de 1 a 12
usando todas as classes e modelos já confirmados no catálogo.
"""

from __future__ import annotations

import mido

from tools.commands.effect_catalog import (
    EFFECT_CLASSES,
    EffectClass,
    EffectModel,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    DESTINATION_SLOT_HIGH_INDEX,
    DESTINATION_SLOT_LOW_INDEX,
    SOURCE_SLOT_HIGH_INDEX,
    SOURCE_SLOT_LOW_INDEX,
    build_add_effect_message,
    build_remove_effect_message,
    build_replace_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


def read_number(prompt: str, minimum: int, maximum: int) -> int:
    while True:
        value = input(prompt).strip()

        try:
            number = int(value)
        except ValueError:
            print("Digite somente um número.")
            continue

        if minimum <= number <= maximum:
            return number

        print(
            f"Escolha um número entre {minimum} e {maximum}."
        )


def choose_slot() -> int:
    return read_number(
        "Escolha o slot interno, de 1 a 12: ",
        1,
        12,
    )


def choose_effect() -> tuple[EffectClass, EffectModel]:
    print("\nClasses catalogadas:")

    for effect_class in EFFECT_CLASSES:
        print(
            f"{effect_class.menu_number}. "
            f"{effect_class.name:<4} "
            f"({len(effect_class.models)} efeitos)"
        )

    class_number = read_number(
        "Escolha a classe: ",
        1,
        len(EFFECT_CLASSES),
    )
    effect_class = EFFECT_CLASSES[class_number - 1]

    print(
        f"\nModelos da classe {effect_class.name}:"
    )

    for model in effect_class.models:
        print(
            f"{model.menu_number:2}. "
            f"{model.name:<20} "
            f"modelo 0x{model.model_id:02X} "
            f"seletor 0x{model.secondary_selector:02X}"
        )

    model_number = read_number(
        "Escolha o efeito: ",
        1,
        len(effect_class.models),
    )

    return (
        effect_class,
        effect_class.models[model_number - 1],
    )


def print_summary(
    operation: str,
    slot_number: int,
    message: mido.Message,
    effect_class: EffectClass | None = None,
    model: EffectModel | None = None,
) -> None:
    packet = full_message_bytes(message)

    print("\n" + "=" * 68)
    print(f"Operação: {operation}")
    print(f"Slot interno: {slot_number}")

    if effect_class is not None and model is not None:
        print(
            f"Efeito: {effect_class.name} / {model.name}"
        )
        print(
            f"Classe: 0x{effect_class.class_id:02X}"
        )
        print(f"Modelo: 0x{model.model_id:02X}")
        print(
            f"Seletor: 0x{model.secondary_selector:02X}"
        )

    print(
        "Origem codificada: "
        f"{packet[SOURCE_SLOT_HIGH_INDEX]:02X} "
        f"{packet[SOURCE_SLOT_LOW_INDEX]:02X}"
    )
    print(
        "Destino codificado: "
        f"{packet[DESTINATION_SLOT_HIGH_INDEX]:02X} "
        f"{packet[DESTINATION_SLOT_LOW_INDEX]:02X}"
    )
    print(
        f"Checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
    )


def confirmed() -> bool:
    return (
        input(
            "Digite S para enviar ou outra tecla para cancelar: "
        )
        .strip()
        .casefold()
        == "s"
    )


def add_effect(output) -> None:
    slot_number = choose_slot()
    effect_class, model = choose_effect()

    message = build_add_effect_message(
        slot_number=slot_number,
        class_id=effect_class.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )

    print_summary(
        "ADICIONAR",
        slot_number,
        message,
        effect_class,
        model,
    )
    print("\nO slot precisa estar AUSENTE.")

    if confirmed():
        output.send(message)
        print("Efeito adicionado.")
    else:
        print("Operação cancelada.")


def replace_effect(output) -> None:
    slot_number = choose_slot()
    effect_class, model = choose_effect()

    message = build_replace_effect_message(
        slot_number=slot_number,
        class_id=effect_class.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )

    print_summary(
        "SUBSTITUIR",
        slot_number,
        message,
        effect_class,
        model,
    )
    print("\nO slot precisa EXISTIR.")

    if confirmed():
        output.send(message)
        print("Efeito substituído.")
    else:
        print("Operação cancelada.")


def remove_effect(output) -> None:
    slot_number = choose_slot()
    message = build_remove_effect_message(slot_number)

    print_summary(
        "EXCLUIR",
        slot_number,
        message,
    )
    print("\nO slot precisa EXISTIR.")

    if confirmed():
        output.send(message)
        print("Slot excluído.")
    else:
        print("Operação cancelada.")


def show_catalog() -> None:
    total = sum(
        len(effect_class.models)
        for effect_class in EFFECT_CLASSES
    )
    print(
        f"\nCATÁLOGO CONFIRMADO — {total} efeitos"
    )

    for effect_class in EFFECT_CLASSES:
        print(
            f"\n{effect_class.name} "
            f"— {len(effect_class.models)} efeitos"
        )
        for model in effect_class.models:
            print(
                f"  {model.menu_number:2}. "
                f"{model.name:<20} "
                f"0x{model.model_id:02X} "
                f"sel 0x{model.secondary_selector:02X}"
            )

    input("\nPressione Enter para voltar...")


def run_menu(output) -> None:
    while True:
        print("\n" + "=" * 68)
        print(
            "MATRIBOX — GERENCIADOR FLEXÍVEL DA CADEIA"
        )
        print("1. Adicionar efeito em slot vazio")
        print(
            "2. Substituir efeito de slot existente"
        )
        print("3. Excluir slot existente")
        print("4. Consultar catálogo")
        print("0. Sair")

        option = input("\nEscolha: ").strip()

        try:
            if option == "0":
                return
            if option == "1":
                add_effect(output)
            elif option == "2":
                replace_effect(output)
            elif option == "3":
                remove_effect(output)
            elif option == "4":
                show_catalog()
            else:
                print("Escolha 0, 1, 2, 3 ou 4.")
        except (RuntimeError, ValueError) as error:
            print(f"\nErro: {error}")


def main() -> None:
    try:
        with mido.open_output(OUTPUT_PORT) as output:
            run_menu(output)
    except (OSError, RuntimeError) as error:
        print(f"\nNão foi possível iniciar: {error}")
    except KeyboardInterrupt:
        print("\nGerenciador interrompido.")


if __name__ == "__main__":
    main()
