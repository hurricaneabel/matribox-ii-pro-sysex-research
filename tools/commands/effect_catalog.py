"""Fachada compatível para o catálogo JSON de efeitos da Matribox.

Desde a Fase 23A, classes, modelos, IDs, seletores e parâmetros são carregados
de ``catalog/``. Este módulo preserva a API histórica usada pelos comandos,
experimentos e testes existentes.
"""

from __future__ import annotations

from tools.catalog import EffectClass, EffectModel, load_effect_catalog


CATALOG = load_effect_catalog()
EFFECT_CLASSES = CATALOG.classes


def _class(key: str) -> EffectClass:
    return CATALOG.class_by_key(key)


# IDs históricos preservados, agora derivados do JSON.
DYN_CLASS_ID = _class("dyn").class_id
FREQ_CLASS_ID = _class("freq").class_id
WAH_CLASS_ID = _class("wah").class_id
DRV_CLASS_ID = _class("drv").class_id
AMP_CLASS_ID = _class("amp").class_id
CAB_CLASS_ID = _class("cab").class_id
IR_CLASS_ID = _class("ir").class_id
EQ_CLASS_ID = _class("eq").class_id
MOD_CLASS_ID = _class("mod").class_id
DLY_CLASS_ID = _class("dly").class_id
RVB_CLASS_ID = _class("rvb").class_id
CLONE_CLASS_ID = _class("clone").class_id
FX_LOOP_CLASS_ID = _class("fx_loop").class_id
FX_SEND_CLASS_ID = _class("fx_send").class_id
FX_RETURN_CLASS_ID = _class("fx_return").class_id
VOL_CLASS_ID = _class("vol").class_id


# Tuplas históricas preservadas, agora derivadas do JSON.
FREQ_MODELS = _class("freq").models
DRV_MODELS = _class("drv").models
DYN_MODELS = _class("dyn").models
WAH_MODELS = _class("wah").models
AMP_MODELS = _class("amp").models
CAB_MODELS = _class("cab").models
IR_MODELS = _class("ir").models
EQ_MODELS = _class("eq").models
MOD_MODELS = _class("mod").models
DLY_MODELS = _class("dly").models
RVB_MODELS = _class("rvb").models
CLONE_MODELS = _class("clone").models
FX_LOOP_MODELS = _class("fx_loop").models
FX_SEND_MODELS = _class("fx_send").models
FX_RETURN_MODELS = _class("fx_return").models
VOL_MODELS = _class("vol").models


def find_effect_class(value: str) -> EffectClass:
    """Localiza uma classe pelo menu, nome, chave ou ID hexadecimal."""

    normalized = value.strip().lower()

    if normalized.isdigit():
        menu_number = int(normalized, 10)
        for effect_class in EFFECT_CLASSES:
            if effect_class.menu_number == menu_number:
                return effect_class

    for effect_class in EFFECT_CLASSES:
        if normalized in {effect_class.name.lower(), effect_class.key}:
            return effect_class

    hexadecimal = normalized.removeprefix("0x")

    try:
        class_id = int(hexadecimal, 16)
    except ValueError as error:
        raise ValueError("Classe de efeito não encontrada.") from error

    for effect_class in EFFECT_CLASSES:
        if effect_class.class_id == class_id:
            return effect_class

    raise ValueError("Classe de efeito não encontrada.")


def find_effect_model(
    effect_class: EffectClass,
    value: str,
) -> EffectModel:
    """Localiza um modelo por menu, nome, chave ou ID hexadecimal.

    Alguns modelos compartilham o mesmo ID principal. Nesses casos, a busca
    por ID permanece ambígua e deve ser feita pelo menu, nome ou chave estável.
    """

    normalized = value.strip().lower()

    if normalized.isdigit():
        menu_number = int(normalized, 10)
        for model in effect_class.models:
            if model.menu_number == menu_number:
                return model

    for model in effect_class.models:
        if normalized in {model.name.lower(), model.key}:
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
            "Escolha pelo número do menu, nome ou chave."
        )

    raise ValueError(
        f"Modelo não encontrado na classe {effect_class.name}."
    )
