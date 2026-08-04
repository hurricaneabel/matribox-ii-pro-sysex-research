import mido

PORTA_SAIDA = "Matribox II Pro Subdevice 1"

# baseado numa das suas mensagens capturadas, trocando o byte do volume (índice 39 no "data", sem contar F0/F7)
# vamos tentar setar o volume pra 20+16=... espera, vamos tentar valor bruto 20 -> deve virar 20+16=36 no display, se a hipótese estiver certa
dados = [33,37,77,80,0,0,58,0,20,0,0,0,0,1,0,0,0,0,1,0,0,12,0,0,0,0,0,0,1,9,0,3,0,0,0,5,0,1,1,20,0,0,0,0,0,0,1,1,0,0,0,0]

msg = mido.Message('sysex', data=dados)

with mido.open_output(PORTA_SAIDA) as outport:
    outport.send(msg)
    print("Mensagem enviada!")