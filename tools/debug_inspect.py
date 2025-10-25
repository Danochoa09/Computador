import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from tools.spl_to_asm import compile_euclides
from tools.assembler_from_as import assemble_text

s = open('Ejemplos/SPL/euclides_high.spl').read()
print('--- Source ---')
print(s)
asm = compile_euclides(s)
print('--- ASM ---')
print(asm)
insts = assemble_text(asm)
print('--- INSTS (count=%d) ---' % len(insts))
op = json.load(open('opcodes.json'))
isa = json.load(open('ISA.json'))
rev = {}
for length,names in isa.items():
    for idx,name in enumerate(names):
        bits = op[length][idx]
        rev.setdefault(length,[]).append((bits,name))

for i,inst in enumerate(insts):
    found=False
    for length,arr in rev.items():
        for bits,name in arr:
            if inst.startswith(bits):
                found=True; mnemonic=name; l=length; break
        if found: break
    if not found:
        mnemonic='UNKNOWN'; l='?'
    if l=='54': r=int(inst[54:59],2); rp=int(inst[59:64],2); opstr=f'R{r}, R{rp}'
    elif l=='59': r=int(inst[59:64],2); opstr=f'R{r}'
    elif l=='35': r=int(inst[35:40],2); m=int(inst[40:64],2); opstr=f'R{r}, M[{m}]'
    elif l=='27': r=int(inst[27:32],2); v=int(inst[32:64],2); opstr=f'R{r}, {v}'
    elif l=='40': m=int(inst[40:64],2); opstr=f'M[{m}]'
    elif l=='64': opstr=''
    else: opstr=''
    print(f"{i:02d}: {mnemonic} {opstr}")

# Show the numeric values for jump targets
print('\n-- Jump targets decoded --')
for i,inst in enumerate(insts):
    # check for 40-type
    for bits,name in rev.get('40',[]):
        if inst.startswith(bits):
            m = int(inst[40:64],2)
            print(f'{i:02d}: {name} -> target {m}')
            break

# show 35-type targets (M values)
print('\n-- 35-type memory operands --')
for i,inst in enumerate(insts):
    for bits,name in rev.get('35',[]):
        if inst.startswith(bits):
            r = int(inst[35:40],2); m=int(inst[40:64],2)
            print(f'{i:02d}: {name} R{r},M[{m}]')
            break
