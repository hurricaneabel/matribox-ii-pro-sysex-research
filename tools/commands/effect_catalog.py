"""Catálogo confirmado de classes e modelos de efeitos."""

from __future__ import annotations

from dataclasses import dataclass


FREQ_CLASS_ID = 0x01
DRV_CLASS_ID = 0x03


@dataclass(frozen=True)
class EffectModel:
    """Modelo pertencente a uma classe de efeitos."""

    menu_number: int
    name: str
    model_id: int


@dataclass(frozen=True)
class EffectClass:
    """Classe de efeitos disponível nos comandos confirmados."""

    menu_number: int
    name: str
    class_id: int
    models: tuple[EffectModel, ...]


FREQ_MODELS = (
    EffectModel(1, "Filter", 0x19),
    EffectModel(2, "Octaver", 0x21),
    EffectModel(3, "Dual Melody", 0x23),
    EffectModel(4, "Pitch", 0x24),
    EffectModel(5, "Harmony D", 0x4E),
    EffectModel(6, "Pitch S", 0x55),
    EffectModel(7, "Ring Mod", 0x2F),
    EffectModel(8, "Tape Mod", 0x33),
)


DRV_MODELS = (
    EffectModel(1, "Skreamer", 0x00),
    EffectModel(2, "Skreamer9", 0x01),
    EffectModel(3, "Butter OD", 0x02),
    EffectModel(4, "Warm OD", 0x04),
    EffectModel(5, "Super OD", 0x06),
    EffectModel(6, "Blues OD", 0x09),
    EffectModel(7, "Full OD", 0x0A),
    EffectModel(8, "Breaker OD", 0x0E),
    EffectModel(9, "Gerden OD", 0x10),
    EffectModel(10, "Timmy OD", 0x1E),
    EffectModel(11, "Master OD", 0x0F),
    EffectModel(12, "Solar Fuzz", 0x26),
    EffectModel(13, "Fuzz Cream", 0x22),
    EffectModel(14, "Red Fuzz", 0x24),
    EffectModel(15, "JP Dist", 0x2A),
    EffectModel(16, "Dark Mouse", 0x2B),
    EffectModel(17, "Plexi Dist", 0x2D),
    EffectModel(18, "Master Dist", 0x2E),
    EffectModel(19, "Dist Plus", 0x29),
    EffectModel(20, "Shark", 0x30),
    EffectModel(21, "Strive", 0x32),
    EffectModel(22, "Sardar Dist", 0x52),
    EffectModel(23, "Bass OD", 0x3F),
    EffectModel(24, "Bass Dist", 0x40),
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
)


def find_effect_class(value: str) -> EffectClass:
    """Localiza uma classe pelo menu, nome ou ID hexadecimal."""
    normalized = value.strip().lower()

    for effect_class in EFFECT_CLASSES:
        accepted_values = {
            str(effect_class.menu_number),
            effect_class.name.lower(),
            f"{effect_class.class_id:02x}",
            f"0x{effect_class.class_id:02x}",
        }

        if normalized in accepted_values:
            return effect_class

    raise ValueError(
        "Classe de efeito não encontrada."
    )


def find_effect_model(
    effect_class: EffectClass,
    value: str,
) -> EffectModel:
    """Localiza um modelo por menu, nome ou ID hexadecimal."""
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

    for model in effect_class.models:
        if model.model_id == model_id:
            return model

    raise ValueError(
        f"Modelo não encontrado na classe {effect_class.name}."
    )
