import mido

print("Entradas MIDI encontradas:")
for nome in mido.get_input_names():
    print(" -", nome)

print("\nSaídas MIDI encontradas:")
for nome in mido.get_output_names():
    print(" -", nome)