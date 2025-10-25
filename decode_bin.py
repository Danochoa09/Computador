# save as decode_bin.py y ejecútalo con python decode_bin.py
import json
from bitarray import bitarray

# Cargar opcodes/ISA (ajusta la ruta si tu repo está en otra carpeta)
with open("opcodes.json","r",encoding="utf-8") as f:
    opcodes = json.load(f)
with open("ISA.json","r",encoding="utf-8") as f:
    isa = json.load(f)

# construir lookup: opcode_bits -> (length, mnemonic)
opcode_map = {}
for length_str, instr_list in opcodes.items():
    length = int(length_str)
    for i, opcode_bits in enumerate(instr_list):
        mnemonic = isa[length_str][i] if length_str in isa and i < len(isa[length_str]) else f"OP_{length}_{i}"
        opcode_map[opcode_bits] = (length, mnemonic)

def detect_instruction(word):
    # buscar el opcode más largo que coincida con el inicio de word
    for L in sorted(opcode_map.keys(), key=lambda x: -len(x)):
        if word.startswith(L):
            length, mnemonic = opcode_map[L]
            # extraer campos según length como hace el emulador
            if length == 64:
                return mnemonic, {}
            elif length == 54:
                r = int(word[54:59],2)
                rp = int(word[59:64],2)
                return mnemonic, {"R":r, "R'":rp}
            elif length == 59:
                r = int(word[59:64],2)
                return mnemonic, {"R":r}
            elif length == 35:
                r = int(word[35:40],2)
                m = int(word[40:64],2)
                return mnemonic, {"R":r,"M":m}
            elif length == 27:
                r = int(word[27:32],2)
                v = int(word[32:64],2)
                return mnemonic, {"R":r,"V":v}
            elif length == 40:
                m = int(word[40:64],2)
                return mnemonic, {"M":m}
    return ("UNKNOWN", {})

# pega aquí tus 64-bit lines (o léelas de un archivo)
lines = [
    "0000000000000000000000010100000010001010000000000001110010000101",
]

for i,w in enumerate(lines):
    mnemonic, fields = detect_instruction(w)
    print(i, mnemonic, fields, "dest special?" , fields.get("R") in (0,1,2,3) )
