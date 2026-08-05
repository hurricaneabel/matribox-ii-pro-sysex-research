"""Catálogo confirmado de classes e modelos de efeitos.

A ordem de ``EFFECT_CLASSES`` é apenas a ordem atual do utilitário de terminal.
A ordem visual do aplicativo final será definida separadamente quando todas as
classes forem catalogadas.
"""

from __future__ import annotations

from dataclasses import dataclass


DYN_CLASS_ID = 0x00
FREQ_CLASS_ID = 0x01
WAH_CLASS_ID = 0x02
DRV_CLASS_ID = 0x03
AMP_CLASS_ID = 0x04
CAB_CLASS_ID = 0x05
IR_CLASS_ID = 0x06
EQ_CLASS_ID = 0x07
MOD_CLASS_ID = 0x08
DLY_CLASS_ID = 0x09
RVB_CLASS_ID = 0x0A
CLONE_CLASS_ID = 0x0B
FX_LOOP_CLASS_ID = 0x0C
FX_SEND_CLASS_ID = 0x0D
FX_RETURN_CLASS_ID = 0x0E
VOL_CLASS_ID = 0x0F


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


WAH_MODELS = (
    EffectModel(1, "VOKS WAH", 0x01, 0x05),
    EffectModel(2, "CRY WAH", 0x08, 0x05),
    EffectModel(3, "RACK WAH", 0x0A, 0x05),
    EffectModel(4, "BASS WAH", 0x07, 0x05),
    EffectModel(5, "TOUCH WAH", 0x0F, 0x01),
    EffectModel(6, "AUTO WAH", 0x15, 0x01),
)


AMP_MODELS = (
    EffectModel(1, "TWD DELUXE", 0x01, 0x07),
    EffectModel(2, "B-MAN N", 0x03, 0x07),
    EffectModel(3, "B-MAN BRI", 0x24, 0x07),
    EffectModel(4, "DARK DOUBLE", 0x04, 0x07),
    EffectModel(5, "DARK DELUXE", 0x05, 0x07),
    EffectModel(6, "SUPERO 2 CL", 0x0F, 0x07),
    EffectModel(7, "SUPERO 2 OD", 0x28, 0x07),
    EffectModel(8, "VOKS 15TB", 0x10, 0x07),
    EffectModel(9, "VOKS 30N", 0x11, 0x07),
    EffectModel(10, "VOKS 30TB", 0x27, 0x07),
    EffectModel(11, "JAZZ 120", 0x14, 0x07),
    EffectModel(12, "SUPERB CL", 0x15, 0x07),
    EffectModel(13, "SUPERB OD", 0x48, 0x07),
    EffectModel(14, "CALIF STAR CL", 0x19, 0x07),
    EffectModel(15, "CALIF STAR OD", 0x4A, 0x07),
    EffectModel(16, "BOG SV CL", 0x1A, 0x07),
    EffectModel(17, "BOG SV OD", 0x3D, 0x07),
    EffectModel(18, "BOG XT BLUE", 0x43, 0x07),
    EffectModel(19, "BOG XT RED", 0x6E, 0x07),
    EffectModel(20, "DOCTOR CL", 0x1B, 0x07),
    EffectModel(21, "DOCTOR OD", 0x49, 0x07),
    EffectModel(22, "DRAGON CL", 0x1F, 0x07),
    EffectModel(23, "DRAGON CL B", 0x7B, 0x07),
    EffectModel(24, "DRAGON OD", 0x7C, 0x07),
    EffectModel(25, "SOL 100 CL", 0x23, 0x07),
    EffectModel(26, "SOL 100 OD", 0x47, 0x07),
    EffectModel(27, "SOL 100 LD", 0x59, 0x07),
    EffectModel(28, "BRIT 45", 0x2A, 0x07),
    EffectModel(29, "BRIT 45+", 0x2B, 0x07),
    EffectModel(30, "BRIT 45JP", 0x2C, 0x07),
    EffectModel(31, "BRIT 50", 0x2D, 0x07),
    EffectModel(32, "BRIT 50+", 0x2E, 0x07),
    EffectModel(33, "BRIT 50JP", 0x2F, 0x07),
    EffectModel(34, "BRIT SLP", 0x30, 0x07),
    EffectModel(35, "BRIT 800", 0x35, 0x07),
    EffectModel(36, "BRIT 900", 0x4E, 0x07),
    EffectModel(37, "FLYMAN 1", 0x40, 0x07),
    EffectModel(38, "FLYMAN 2", 0x41, 0x07),
    EffectModel(39, "FLYMAN+ 1", 0x5D, 0x07),
    EffectModel(40, "FLYMAN+ 2", 0x5E, 0x07),
    EffectModel(41, "CALIF IIC+ 1", 0x39, 0x07),
    EffectModel(42, "CALIF IIC+ 2", 0x3A, 0x07),
    EffectModel(43, "CALIF IIC+ 3", 0x3B, 0x07),
    EffectModel(44, "CALIF IV LD 1", 0x55, 0x07),
    EffectModel(45, "CALIF IV LD 2", 0x56, 0x07),
    EffectModel(46, "CALIF IV LD 3", 0x57, 0x07),
    EffectModel(47, "CALIF DUAL V", 0x68, 0x07),
    EffectModel(48, "CALIF DUAL M", 0x69, 0x07),
    EffectModel(49, "TANGER R100", 0x53, 0x07),
    EffectModel(50, "HALEN 51", 0x5A, 0x07),
    EffectModel(51, "ENG 120", 0x5F, 0x07),
    EffectModel(52, "ENG 120+", 0x60, 0x07),
    EffectModel(53, "DIZZY VH", 0x65, 0x07),
    EffectModel(54, "DIZZY VH S", 0x66, 0x07),
    EffectModel(55, "DIZZY VH+", 0x6A, 0x07),
    EffectModel(56, "DIZZY VH+ S", 0x6B, 0x07),
    EffectModel(57, "A BASSVT", 0x73, 0x07),
    EffectModel(58, "VOKS BASS", 0x75, 0x07),
    EffectModel(59, "CALI BASS", 0x77, 0x07),
    EffectModel(60, "A BASSFT", 0x75, 0x08),
    EffectModel(61, "F-2BASS", 0x76, 0x08),
    EffectModel(62, "AC PREAMP", 0x7A, 0x08),
    EffectModel(63, "AC PREAMP 2", 0x7B, 0x08),
)


CAB_MODELS = (
    EffectModel(1, "SUPERO 1X6", 0x00, 0x0A),
    EffectModel(2, "CHAP 1X8", 0x01, 0x0A),
    EffectModel(3, "PRINCE 1X10", 0x02, 0x0A),
    EffectModel(4, "TWD 2X10", 0x14, 0x0A),
    EffectModel(5, "TWD LUX 1X12", 0x0B, 0x0A),
    EffectModel(6, "DARK LUX 1X12", 0x03, 0x0A),
    EffectModel(7, "TWIN VERB 2X12", 0x12, 0x0A),
    EffectModel(8, "CUSTOM 2X12", 0x1B, 0x0A),
    EffectModel(9, "B-MAN 2X10", 0x16, 0x0A),
    EffectModel(10, "B-MAN 4X10", 0x1E, 0x0A),
    EffectModel(11, "JAZZ 2X12", 0x11, 0x0A),
    EffectModel(12, "BRIT 1X12", 0x0E, 0x0A),
    EffectModel(13, "BRIT GN 2X12", 0x13, 0x0A),
    EffectModel(14, "BRIT LD 4X12", 0x1F, 0x0A),
    EffectModel(15, "BRIT TD 4X12", 0x20, 0x0A),
    EffectModel(16, "BRIT MD 4X12", 0x21, 0x0A),
    EffectModel(17, "BRIT GN 4X12", 0x22, 0x0A),
    EffectModel(18, "BRIT 75 4X12", 0x30, 0x0A),
    EffectModel(19, "BRIT BK 4X12", 0x2B, 0x0A),
    EffectModel(20, "VOKS 1X12", 0x08, 0x0A),
    EffectModel(21, "VOKS 2X12", 0x0F, 0x0A),
    EffectModel(22, "BOG SV 1X12", 0x06, 0x0A),
    EffectModel(23, "CHIEF 2X12", 0x10, 0x0A),
    EffectModel(24, "CALIF DUAL 4X12", 0x24, 0x0A),
    EffectModel(25, "CALIF STAR 1X12", 0x09, 0x0A),
    EffectModel(26, "CALIF STAR 2X12", 0x19, 0x0A),
    EffectModel(27, "CALIF 1X12", 0x0C, 0x0A),
    EffectModel(28, "SUPERO 2X12", 0x17, 0x0A),
    EffectModel(29, "SUPERB 2X12", 0x18, 0x0A),
    EffectModel(30, "BLUE 2X12", 0x1D, 0x0A),
    EffectModel(31, "HALEN 4X12", 0x23, 0x0A),
    EffectModel(32, "BOG 4X12", 0x25, 0x0A),
    EffectModel(33, "ENG 4X12", 0x26, 0x0A),
    EffectModel(34, "BOG UB 4X12", 0x27, 0x0A),
    EffectModel(35, "SOL 4X12", 0x28, 0x0A),
    EffectModel(36, "TANGER 4X12", 0x29, 0x0A),
    EffectModel(37, "WATT 4X12", 0x2A, 0x0A),
    EffectModel(38, "WAM 4X12", 0x2C, 0x0A),
    EffectModel(39, "HUMBLE 4X12", 0x2D, 0x0A),
    EffectModel(40, "DIZZY 4X12", 0x2E, 0x0A),
    EffectModel(41, "CALIF 4X12", 0x31, 0x0A),
    EffectModel(42, "DV 1X15", 0x32, 0x0A),
    EffectModel(43, "DV 4X10", 0x37, 0x0A),
    EffectModel(44, "WORK 1X15", 0x33, 0x0A),
    EffectModel(45, "WORK 4X10", 0x39, 0x0A),
    EffectModel(46, "CALIF 2X10", 0x35, 0x0A),
    EffectModel(47, "MAK 2X10", 0x36, 0x0A),
    EffectModel(48, "A BASS 1X15", 0x34, 0x0A),
    EffectModel(49, "A BASS 4X10", 0x38, 0x0A),
    EffectModel(50, "A BASS 8X10", 0x3B, 0x0A),
    EffectModel(51, "HART 4X12", 0x3A, 0x0A),
    EffectModel(52, "D 1", 0x3C, 0x0A),
    EffectModel(53, "D 2", 0x3D, 0x0A),
    EffectModel(54, "OM", 0x3E, 0x0A),
    EffectModel(55, "JUMBO", 0x3F, 0x0A),
    EffectModel(56, "BIRD", 0x40, 0x0A),
    EffectModel(57, "GA", 0x41, 0x0A),
    EffectModel(58, "CLASSICAL AC", 0x42, 0x0A),
    EffectModel(59, "MANDOLIN", 0x43, 0x0A),
    EffectModel(60, "FRETLESS BASS", 0x44, 0x0A),
    EffectModel(61, "DOUBLE BASS", 0x45, 0x0A),
)


IR_MODELS = (
    EffectModel(1, "IR 1", 0x00, 0x0A),
    EffectModel(2, "IR 2", 0x01, 0x0A),
    EffectModel(3, "IR 3", 0x02, 0x0A),
    EffectModel(4, "IR 4", 0x03, 0x0A),
    EffectModel(5, "IR 5", 0x04, 0x0A),
    EffectModel(6, "IR 6", 0x05, 0x0A),
    EffectModel(7, "IR 7", 0x06, 0x0A),
    EffectModel(8, "IR 8", 0x07, 0x0A),
    EffectModel(9, "IR 9", 0x08, 0x0A),
    EffectModel(10, "IR 10", 0x09, 0x0A),
    EffectModel(11, "IR 11", 0x0A, 0x0A),
    EffectModel(12, "IR 12", 0x0B, 0x0A),
    EffectModel(13, "IR 13", 0x0C, 0x0A),
    EffectModel(14, "IR 14", 0x0D, 0x0A),
    EffectModel(15, "IR 15", 0x0E, 0x0A),
    EffectModel(16, "IR 16", 0x0F, 0x0A),
    EffectModel(17, "IR 17", 0x10, 0x0A),
    EffectModel(18, "IR 18", 0x11, 0x0A),
    EffectModel(19, "IR 19", 0x12, 0x0A),
    EffectModel(20, "IR 20", 0x13, 0x0A),
)


EQ_MODELS = (
    EffectModel(1, "GUITAR EQ 1", 0x35, 0x01),
    EffectModel(2, "GUITAR EQ 2", 0x36, 0x01),
    EffectModel(3, "BASS EQ 1", 0x39, 0x01),
    EffectModel(4, "BASS EQ 2", 0x3A, 0x01),
    EffectModel(5, "CALIF EQ", 0x3C, 0x01),
)


MOD_MODELS = (
    EffectModel(1, "E-CHORUS", 0x01, 0x04),
    EffectModel(2, "D-CHORUS", 0x02, 0x04),
    EffectModel(3, "B-CHORUS", 0x08, 0x04),
    EffectModel(4, "M-CHORUS", 0x0F, 0x04),
    EffectModel(5, "FLANGER", 0x11, 0x04),
    EffectModel(6, "FLANGER N", 0x13, 0x04),
    EffectModel(7, "TREM JET", 0x14, 0x04),
    EffectModel(8, "BASS JET", 0x12, 0x04),
    EffectModel(9, "VIBRATO", 0x17, 0x04),
    EffectModel(10, "BBD ROTO", 0x15, 0x04),
    EffectModel(11, "CE-ROTO", 0x16, 0x04),
    EffectModel(12, "PHASER", 0x19, 0x04),
    EffectModel(13, "BBD PHASER", 0x1A, 0x04),
    EffectModel(14, "PHASER ST", 0x1B, 0x04),
    EffectModel(15, "PAN PHASER", 0x1E, 0x04),
    EffectModel(16, "VIBE", 0x1F, 0x04),
    EffectModel(17, "U-VIBE", 0x20, 0x04),
    EffectModel(18, "TREMOLO", 0x21, 0x04),
    EffectModel(19, "SINE TREM", 0x26, 0x04),
    EffectModel(20, "TRIANGULE TREM", 0x27, 0x04),
    EffectModel(21, "BIAS TREM", 0x28, 0x04),
    EffectModel(22, "DETUNE", 0x29, 0x01),
    EffectModel(23, "LOFI BIT", 0x2E, 0x01),
)


DLY_MODELS = (
    EffectModel(1, "WARM", 0x01, 0x0B),
    EffectModel(2, "PURE", 0x00, 0x0B),
    EffectModel(3, "MAG", 0x02, 0x0B),
    EffectModel(4, "TUBE", 0x0B, 0x0B),
    EffectModel(5, "BBD", 0x1D, 0x0B),
    EffectModel(6, "PING PONG", 0x04, 0x0B),
    EffectModel(7, "SLAPBACK", 0x05, 0x0B),
    EffectModel(8, "SWEEP", 0x06, 0x0B),
    EffectModel(9, "RING", 0x09, 0x0B),
    EffectModel(10, "MULTI TAPE", 0x0C, 0x0B),
    EffectModel(11, "SWEET", 0x0D, 0x0B),
    EffectModel(12, "999 ECHO", 0x12, 0x0B),
    EffectModel(13, "RACK", 0x14, 0x0B),
    EffectModel(14, "LO-FI", 0x26, 0x0B),
    EffectModel(15, "REVERSE", 0x28, 0x0B),
    EffectModel(16, "EKO D", 0x03, 0x0B),
    EffectModel(17, "ICE DELAY", 0x2C, 0x0B),
)


RVB_MODELS = (
    EffectModel(1, "STUDIO", 0x0B, 0x0C),
    EffectModel(2, "CLUB", 0x0C, 0x0C),
    EffectModel(3, "ROOM", 0x00, 0x0C),
    EffectModel(4, "HALL", 0x01, 0x0C),
    EffectModel(5, "CHURCH", 0x02, 0x0C),
    EffectModel(6, "PLATE", 0x03, 0x0C),
    EffectModel(7, "SPRING", 0x04, 0x0C),
    EffectModel(8, "SKY", 0x06, 0x0C),
    EffectModel(9, "SEA", 0x07, 0x0C),
    EffectModel(10, "MOD REVERB", 0x08, 0x0C),
    EffectModel(11, "SHIMMER", 0x09, 0x0C),
    EffectModel(12, "HAZE", 0x15, 0x0C),
)


CLONE_MODELS = (
    EffectModel(1, "CLONE 1", 0x00, 0x0F),
    EffectModel(2, "CLONE 2", 0x01, 0x0F),
    EffectModel(3, "CLONE 3", 0x02, 0x0F),
    EffectModel(4, "CLONE 4", 0x03, 0x0F),
    EffectModel(5, "CLONE 5", 0x04, 0x0F),
    EffectModel(6, "CLONE 6", 0x05, 0x0F),
    EffectModel(7, "CLONE 7", 0x06, 0x0F),
    EffectModel(8, "CLONE 8", 0x07, 0x0F),
    EffectModel(9, "CLONE 9", 0x08, 0x0F),
    EffectModel(10, "CLONE 10", 0x09, 0x0F),
)


FX_LOOP_MODELS = (
    EffectModel(1, "FX LOOP", 0x00, 0x06),
)


FX_SEND_MODELS = (
    EffectModel(1, "SND", 0x01, 0x06),
)


FX_RETURN_MODELS = (
    EffectModel(1, "RTN", 0x02, 0x06),
)


VOL_MODELS = (
    EffectModel(1, "VOL", 0x03, 0x06),
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
    EffectClass(
        menu_number=4,
        name="WAH",
        class_id=WAH_CLASS_ID,
        models=WAH_MODELS,
    ),
    EffectClass(
        menu_number=5,
        name="AMP",
        class_id=AMP_CLASS_ID,
        models=AMP_MODELS,
    ),
    EffectClass(
        menu_number=6,
        name="CAB",
        class_id=CAB_CLASS_ID,
        models=CAB_MODELS,
    ),
    EffectClass(
        menu_number=7,
        name="IR",
        class_id=IR_CLASS_ID,
        models=IR_MODELS,
    ),
    EffectClass(
        menu_number=8,
        name="EQ",
        class_id=EQ_CLASS_ID,
        models=EQ_MODELS,
    ),
    EffectClass(
        menu_number=9,
        name="MOD",
        class_id=MOD_CLASS_ID,
        models=MOD_MODELS,
    ),
    EffectClass(
        menu_number=10,
        name="DLY",
        class_id=DLY_CLASS_ID,
        models=DLY_MODELS,
    ),
    EffectClass(
        menu_number=11,
        name="RVB",
        class_id=RVB_CLASS_ID,
        models=RVB_MODELS,
    ),
    EffectClass(
        menu_number=12,
        name="CLONE",
        class_id=CLONE_CLASS_ID,
        models=CLONE_MODELS,
    ),
    EffectClass(
        menu_number=13,
        name="FX LOOP",
        class_id=FX_LOOP_CLASS_ID,
        models=FX_LOOP_MODELS,
    ),
    EffectClass(
        menu_number=14,
        name="FX SEND",
        class_id=FX_SEND_CLASS_ID,
        models=FX_SEND_MODELS,
    ),
    EffectClass(
        menu_number=15,
        name="FX RETURN",
        class_id=FX_RETURN_CLASS_ID,
        models=FX_RETURN_MODELS,
    ),
    EffectClass(
        menu_number=16,
        name="VOL",
        class_id=VOL_CLASS_ID,
        models=VOL_MODELS,
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

    Alguns modelos de efeitos compartilham o mesmo ID principal. Nesses casos, a
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
