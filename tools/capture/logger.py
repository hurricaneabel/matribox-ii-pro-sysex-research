import mido
import time

PORTA = "Matribox II Pro Subdevice 0"

with mido.open_input(PORTA) as inport, open("log_matribox.txt", "a") as f:
    print("Escutando... (Ctrl+C pra parar)")
    try:
        for msg in inport:
            linha = f"{time.strftime('%H:%M:%S')} | {msg}"
            if msg.type == "sysex":
                hexstr = " ".join(f"{b:02X}" for b in msg.bin())
                linha += f" | HEX: {hexstr}"
            print(linha)
            f.write(linha + "\n")
            f.flush()
    except KeyboardInterrupt:
        print("\nParado pelo usuário.")