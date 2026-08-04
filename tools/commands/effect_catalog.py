"""Catálogo confirmado de classes e modelos de efeitos.

A ordem de ``EFFECT_CLASSES`` é apenas a ordem atual do utilitário de terminal.
A ordem visual do aplicativo final será definida separadamente quando todas as
classes forem catalogadas.
"""

from __future__ import annotations

from dataclasses import dataclass


DYN_CLASS_ID = 0x00
FREQ_CLASS_ID = 0x01
DRV_CLASS_ID = 0x03


@dataclass(frozen=True)
class EffectModel:
    """Modelo pertencente a uma classe de efeitos."""

    menu_number: int
    name: str
    model_id: int
    secondary_selector: int


@dataclass(frozen=True)
class EffectClass:
    """Classe de efeitos disponível nos comandos confirmados."""

    menu_number: int
    name: str
    class_id: int
    models: tuple[EffectModel, ...]


FREQ_MODELS = (
    EffectModel(1, "Filter", 0x19, 0x01),
    EffectModel(2, "Octaver", 0x21, 0x01),
    EffectModel(3, "Dual Melody", 0x23, 0x01),
    EffectModel(4, "Pitch", 0x24, 0x01),
    EffectModel(5, "Harmony D", 0x4E, 0x01),
    EffectModel(6, "Pitch S", 0x55, 0x01),
    EffectModel(7, "Ring Mod", 0x2F, 0x01),
    EffectModel(8, "Tape Mod", 0x33, 0x01),
)


DRV_MODELS = (
    EffectModel(1, "Skreamer", 0x00, 0x03),
    EffectModel(2, "Skreamer9", 0x01, 0x03),
    EffectModel(3, "Butter OD", 0x02, 0x03),
    EffectModel(4, "Warm OD", 0x04, 0x03),
    EffectModel(5, "Super OD", 0x06, 0x03),
    EffectModel(6, "Blues OD", 0x09, 0x03),
    EffectModel(7, "Full OD", 0x0A, 0x03),
    EffectModel(8, "Breaker OD", 0x0E, 0x03),
    EffectModel(9, "Gerden OD", 0x10, 0x03),
    EffectModel(10, "Timmy OD", 0x1E, 0x03),
    EffectModel(11, "Master OD", 0x0F, 0x03),
    EffectModel(12, "Solar Fuzz", 0x26, 0x03),
    EffectModel(13, "Fuzz Cream", 0x22, 0x03),
    EffectModel(14, "Red Fuzz", 0x24, 0x03),
    EffectModel(15, "JP Dist", 0x2A, 0x03),
    EffectModel(16, "Dark Mouse", 0x2B, 0x03),
    EffectModel(17, "Plexi Dist", 0x2D, 0x03),
    EffectModel(18, "Master Dist", 0x2E, 0x03),
    EffectModel(19, "Dist Plus", 0x29, 0x03),
    EffectModel(20, "Shark", 0x30, 0x03),
    EffectModel(21, "Strive", 0x32, 0x03),
    EffectModel(22, "Sardar Dist", 0x52, 0x03),
    EffectModel(23, "Bass OD", 0x3F, 0x03),
    EffectModel(24, "Bass Dist", 0x40, 0x03),
)


DYN_MODELS = (
    EffectModel(1, "COMP1", 0x00, 0x00),
    EffectModel(2, "COMP2", 0x01, 0x00),
    EffectModel(3, "COMP3", 0x03, 0x00),
    EffectModel(4, "M-BOOST", 0x14, 0x00),
    EffectModel(5, "E-BOOST", 0x1A, 0x00),
    EffectModel(6, "AC-BOOST", 0x0A, 0x00),
    EffectModel(7, "BB-BOOST", 0x0B, 0x00),
    EffectModel(8, "RC-BOOST", 0x0C, 0x00),
    EffectModel(9, "FAT BOOST", 0x19, 0x00),
    EffectModel(10, "AC WOODY", 0x00, 0x01),
    EffectModel(11, "AC SIM", 0x01, 0x01),
    EffectModel(12, "GATE 1", 0x1B, 0x00),
    EffectModel(13, "GATE 2", 0x1D, 0x00),
    EffectModel(14, "GATE 3", 0x21, 0x00),
)


EFFECT_CLASSES = (
    EffectClass(
        menu_number=1,
        name="FREQ",
        class_id=FREQ_CLASS_ID,
        models=FREQ_MODELS,
    ),
    EffectClass(
        menu_number=2,
        name="DRV",
        class_id=DRV_CLASS_ID,
        models=DRV_MODELS,
    ),
    EffectClass(
        menu_number=3,
        name="DYN",
        class_id=DYN_CLASS_ID,
        models=DYN_MODELS,
    ),
)


def find_effect_class(value: str) -> EffectClass:
    """Localiza uma classe pelo menu, nome ou ID hexadecimal."""
    normalized = value.strip().lower()

    if normalized.isdigit():
        menu_number = int(normalized, 10)

        for effect_class in EFFECT_CLASSES:
            if effect_class.menu_number == menu_number:
                return effect_class

    for effect_class in EFFECT_CLASSES:
        if normalized == effect_class.name.lower():
            return effect_class

    hexadecimal = normalized.removeprefix("0x")

    try:
        class_id = int(hexadecimal, 16)
    except ValueError as error:
        raise ValueError(
            "Classe de efeito não encontrada."
        ) from error

    for effect_class in EFFECT_CLASSES:
        if effect_class.class_id == class_id:
            return effect_class

    raise ValueError(
        "Classe de efeito não encontrada."
    )


def find_effect_model(
    effect_class: EffectClass,
    value: str,
) -> EffectModel:
    """Localiza um modelo por menu, nome ou ID hexadecimal.

    Alguns modelos DYN compartilham o mesmo ID principal. Nesses casos, a
    busca por ID é ambígua e o usuário deve selecionar pelo número do menu ou
    pelo nome.
    """
    normalized = value.strip().lower()

    if normalized.isdigit():
        menu_number = int(normalized, 10)

        for model in effect_class.models:
            if model.menu_number == menu_number:
                return model

    for model in effect_class.models:
        if normalized == model.name.lower():
            return model

    hexadecimal = normalized.removeprefix("0x")

    try:
        model_id = int(hexadecimal, 16)
    except ValueError as error:
        raise ValueError(
            f"Modelo não encontrado na classe {effect_class.name}."
        ) from error

    matches = tuple(
        model
        for model in effect_class.models
        if model.model_id == model_id
    )

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            "Esse ID pertence a mais de um modelo. "
            "Escolha pelo número do menu ou pelo nome."
        )

    raise ValueError(
        f"Modelo não encontrado na classe {effect_class.name}."
    )
