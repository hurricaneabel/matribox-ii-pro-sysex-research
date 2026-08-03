import mido

PORTA_SAIDA = "Matribox II Pro Subdevice 1"

hex_completo = "f021254d5000003112140000000001000000000100000c00000000000001090003000000050001030b000000000000010100000000f7"

todos_bytes = bytes.fromhex(hex_completo)
dados = list(todos_bytes[1:-1])  # remove o F0 do início e o F7 do final (mido adiciona sozinho)

msg = mido.Message('sysex', data=dados)

with mido.open_output(PORTA_SAIDA) as outport:
    outport.send(msg)
    print("Mensagem enviada! Bytes:", len(dados))