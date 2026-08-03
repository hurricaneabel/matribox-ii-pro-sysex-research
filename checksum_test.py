def parse_hex(hex_str):
    return [int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)]

mensagens_hex = [
    "f021254d5000002412140000000001000000000100000c000000000000010900030000000500010001000000000000010100000000f7",  # valor=1
    "f021254d5000002512140000000001000000000100000c000000000000010900030000000500010002000000000000010100000000f7",  # valor=2
    "f021254d5000002612140000000001000000000100000c000000000000010900030000000500010003000000000000010100000000f7",  # valor=3
    "f021254d5000002712140000000001000000000100000c000000000000010900030000000500010004000000000000010100000000f7",  # valor=4
    "f021254d5000002812140000000001000000000100000c000000000000010900030000000500010005000000000000010100000000f7",  # valor=5
    "f021254d5000002712140000000001000000000100000c000000000000010900030000000500010301000000000000010100000000f7",  # valor=49
    "f021254d5000003112140000000001000000000100000c00000000000001090003000000050001030b000000000000010100000000f7",  # valor=59
]

mensagens = [parse_hex(m) for m in mensagens_hex]
CHECKSUM_IDX = 7

def testa_range(inicio, fim, formula):
    for b in mensagens:
        corpo = b[inicio:fim]
        if formula(corpo) != b[CHECKSUM_IDX]:
            return False
    return True

import functools
formulas = {
    "soma mod 128": lambda c: sum(c) & 0x7F,
    "soma mod 256": lambda c: sum(c) & 0xFF,
    "xor": lambda c: functools.reduce(lambda a, b: a ^ b, c, 0),
    "soma negada mod 128": lambda c: (-sum(c)) & 0x7F,
    "soma negada mod 256": lambda c: (-sum(c)) & 0xFF,
    "128 - soma mod 128": lambda c: (128 - (sum(c) % 128)) % 128,
}

tamanho_msg = len(mensagens[0])
encontrados = []
for inicio in range(0, tamanho_msg):
    for fim in range(inicio + 1, tamanho_msg + 1):
        if inicio <= CHECKSUM_IDX < fim:
            continue
        for nome, formula in formulas.items():
            if testa_range(inicio, fim, formula):
                encontrados.append((inicio, fim, nome))

if encontrados:
    print("Combinações que bateram em TODAS as 7 mensagens:")
    for inicio, fim, nome in encontrados:
        print(f"  bytes[{inicio}:{fim}] com '{nome}'")
else:
    print("Nenhuma fórmula simples bateu — o checksum deve ser mais complexo (CRC, tabela, etc).")