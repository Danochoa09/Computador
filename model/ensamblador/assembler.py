"""Full assembler moved from tools/ to model/ensamblador with root fix."""
import json
import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start
    for p in [cur] + list(cur.parents):
        if (p / 'opcodes.json').exists() and (p / 'ISA.json').exists():
            return p
    return cur.parent


ROOT = _find_repo_root(Path(__file__).resolve())
OPCODES_PATH = ROOT / 'opcodes.json'
ISA_PATH = ROOT / 'ISA.json'


def load_tables():
    with open(OPCODES_PATH, 'r', encoding='utf-8') as f:
        opcodes = json.load(f)
    with open(ISA_PATH, 'r', encoding='utf-8') as f:
        isa = json.load(f)
    table = {}
    for length, names in isa.items():
        for idx, name in enumerate(names):
            bits = opcodes[length][idx]
            table[name.upper()] = (length, idx, bits)
    return table


MNEMONIC_TABLE = load_tables()

reg_re = re.compile(r"R(\d+)", re.IGNORECASE)
mem_re = re.compile(r"M\[(\d+)\]", re.IGNORECASE)
ident_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def to_nbits(val: int, bits: int) -> str:
    if val < 0:
        val = (1 << bits) + val
    fmt = '{:0' + str(bits) + 'b}'
    s = fmt.format(val & ((1 << bits) - 1))
    if len(s) != bits:
        raise ValueError(f'Value {val} does not fit in {bits} bits')
    return s


def parse_register(tok: str) -> int:
    m = reg_re.fullmatch(tok.strip())
    if not m:
        raise ValueError(f'Invalid register token: {tok}')
    return int(m.group(1))


def parse_memory(tok: str) -> int:
    m = mem_re.fullmatch(tok.strip())
    if not m:
        raise ValueError(f'Invalid memory token: {tok}')
    return int(m.group(1))


def assemble_line(parts, table, label_map, relocations, instr_index):
    if not parts:
        return None
    mnemonic = parts[0].upper()
    if mnemonic not in table:
        raise ValueError(f'Unknown mnemonic: {mnemonic} (parts={parts})')
    length, offset, opcode = table[mnemonic]

    def resolve_token(tok, allow_label=True):
        tok = tok.strip()
        if reg_re.fullmatch(tok):
            return ('reg', parse_register(tok))
        if mem_re.fullmatch(tok):
            return ('mem', parse_memory(tok))
        try:
            if tok.startswith(('0x','0X')):
                return ('imm', int(tok, 16))
            if tok.startswith(('0b','0B')):
                return ('imm', int(tok, 2))
            return ('imm', int(tok, 0))
        except Exception:
            pass
        if allow_label and ident_re.fullmatch(tok):
            if tok in label_map:
                return ('imm', label_map[tok])
            else:
                relocations.append((instr_index, tok))
                return ('imm', 0)
        raise ValueError(f'Cannot resolve token: {tok}')

    if length == '54':
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects two register operands')
        r = resolve_token(parts[1])
        rp = resolve_token(parts[2])
        if r[0] != 'reg' or rp[0] != 'reg':
            raise ValueError(f'{mnemonic} expects register operands')
        return opcode + to_nbits(r[1], 5) + to_nbits(rp[1], 5)
    elif length == '59':
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects one register operand')
        r = resolve_token(parts[1])
        if r[0] != 'reg':
            raise ValueError(f'{mnemonic} expects a register operand')
        return opcode + to_nbits(r[1], 5)
    elif length == '35':
        if len(parts) == 2 and mem_re.fullmatch(parts[1]):
            m = resolve_token(parts[1])
            if m[0] != 'mem' and m[0] != 'imm':
                raise ValueError(f'{mnemonic} expects memory operand')
            return opcode + to_nbits(0, 5) + to_nbits(m[1], 24)
        if len(parts) >= 3:
            r = resolve_token(parts[1])
            m = resolve_token(parts[2])
            if r[0] != 'reg':
                raise ValueError(f'{mnemonic} expects register as first operand')
            if m[0] not in ('mem','imm'):
                raise ValueError(f'{mnemonic} expects memory/imm as second operand')
            return opcode + to_nbits(r[1], 5) + to_nbits(m[1], 24)
        raise ValueError(f'Instruction {mnemonic} expects memory operand')
    elif length == '27':
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects R and immediate')
        r = resolve_token(parts[1])
        v = resolve_token(parts[2])
        if r[0] != 'reg' or v[0] not in ('imm', 'mem'):
            raise ValueError(f'{mnemonic} expects R and immediate')
        return opcode + to_nbits(r[1], 5) + to_nbits(v[1], 32)
    elif length == '40':
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects memory operand')
        m = resolve_token(parts[1])
        if m[0] not in ('mem','imm'):
            raise ValueError(f'{mnemonic} expects memory/imm')
        return opcode + to_nbits(m[1], 24)
    elif length == '64':
        return opcode
    else:
        raise ValueError(f'Unsupported instruction length: {length} for {mnemonic}')


def assemble_to_object(text: str, out_o_path: str or Path):
    raw_lines = [raw.split('//')[0].split(';')[0].rstrip() for raw in text.splitlines()]
    label_map = {}
    instr_count = 0
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        if line.endswith(':'):
            lbl = line[:-1].strip()
            if not lbl:
                raise ValueError('Empty label')
            if lbl in label_map:
                raise ValueError(f'Duplicate label: {lbl}')
            label_map[lbl] = instr_count
            continue
        if line.startswith('.data'):
            parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
            data_vals = parts[1:]
            instr_count += len(data_vals)
            continue
        instr_count += 1

    insts = []
    relocations = []
    table = MNEMONIC_TABLE
    idx = 0
    for raw in raw_lines:
        line = raw.split('//')[0].split(';')[0].strip()
        if not line:
            continue
        if line.endswith(':'):
            continue
        if line.startswith('.data'):
            parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
            data_vals = parts[1:]
            for dv in data_vals:
                if dv.startswith(('0x','0X')):
                    v = int(dv, 16)
                elif dv.startswith(('0b','0B')):
                    v = int(dv, 2)
                else:
                    v = int(dv, 0)
                b = to_nbits(v, 64)
                insts.append(b)
                idx += 1
            continue

        parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
        for i in (1, 2):
            if i < len(parts):
                tok = parts[i]
                if ident_re.fullmatch(tok) and tok in label_map:
                    parts[i] = str(label_map[tok])

        b = assemble_line(parts, table, label_map, relocations, idx)
        if b:
            if len(b) != 64:
                raise ValueError(f'Assembled instruction not 64 bits at line: {line}')
            insts.append(b)
            idx += 1

    para = MNEMONIC_TABLE.get('PARA')
    if para:
        para_bits = para[2]
        if not insts or insts[-1] != para_bits:
            insts.append(para_bits)

    outp = Path(out_o_path)
    with outp.open('w', encoding='utf-8') as f:
        f.write('ENTRY: main\n')
        f.write(f'SEGMENT: CODE,SIZE={len(insts)},BASE=0\n')
        f.write('SEGMENT: DATA, SIZE=0, BASE=0\n')
        for name, addr in label_map.items():
            f.write(f'SYM: {name},{addr},local\n')
        for inst in insts:
            f.write(f'INST: {inst}\n')
        for instr_idx, sym in relocations:
            f.write(f'RELOC: {instr_idx}, TYPE=ABS, SYMBOL={sym}\n')


if __name__ == '__main__':
    import sys
    txt = sys.stdin.read()
    out = Path('out.o')
    assemble_to_object(txt, out)
    print('Wrote', out)
