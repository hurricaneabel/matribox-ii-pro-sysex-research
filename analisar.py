def parse_hex(linha):
    hex_part = linha.split("HEX: ")[1].strip()
    return [int(b, 16) for b in hex_part.split()]

def mostra_byte(linha, indice):
    bytes_msg = parse_hex(linha)
    return bytes_msg[indice] if indice < len(bytes_msg) else None

# cola aqui as linhas do seu log_matribox.txt que tiverem "HEX:"
linhas = [
    "... cole a linha completa aqui ...",
]

for linha in linhas:
    print("Byte 40:", mostra_byte(linha, 40))