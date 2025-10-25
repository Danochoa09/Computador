"""Simple assembler for a subset of the project's ISA.
Reads assembly-like lines (one instruction per line) and emits 64-bit binary strings, one per instruction.
Supports the mnemonics used in the Euclides example.

Usage:
    from tools.assembler_from_as import assemble_text
    bits = assemble_text(text)  # returns list of 64-char strings
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPCODES_PATH = ROOT / 'opcodes.json'
ISA_PATH = ROOT / 'ISA.json'

# helpers
def load_tables():
    with open(OPCODES_PATH, 'r', encoding='utf-8') as f:
        opcodes = json.load(f)
    with open(ISA_PATH, 'r', encoding='utf-8') as f:
        isa = json.load(f)
    # build mnemonic -> (length, offset, opcode_bits)
    table = {}
    for length, names in isa.items():
        for idx, name in enumerate(names):
            bits = opcodes[length][idx]
            table[name.upper()] = (length, idx, bits)
    return table

MNEMONIC_TABLE = load_tables()

reg_re = re.compile(r"R(\d+)", re.IGNORECASE)
mem_re = re.compile(r"M\[(\d+)\]", re.IGNORECASE)


def to_nbits(val: int, bits: int) -> str:
    if val < 0:
        # two's complement for negative values
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


def assemble_line(line: str, table: dict) -> str:
    # Strip comments and whitespace
    line = line.strip()
    if not line or line.startswith(';') or line.startswith('//'):
        return None
    # tokens split by spaces and commas
    parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
    if len(parts) == 0:
        return None
    mnemonic = parts[0].upper()
    if mnemonic not in table:
        raise ValueError(f'Unknown mnemonic: {mnemonic} (line: {line})')
    length, offset, opcode = table[mnemonic]

    if length == '54':
        # opcode (54) + R (5) + R' (5)
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects two register operands')
        r = parse_register(parts[1])
        rp = parse_register(parts[2])
        return opcode + to_nbits(r, 5) + to_nbits(rp, 5)
    elif length == '59':
        # opcode (59) + R (5)
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects one register operand')
        r = parse_register(parts[1])
        return opcode + to_nbits(r, 5)
    elif length == '35':
        # opcode (35) + R (5) + M (24)
        # Some instructions (like GUARD) might have only M; check parts
        if mnemonic in ('CARGA', 'SIREGCERO', 'SIREGNCERO'):
            # form: CARGA R4 M[375]
            if len(parts) < 3:
                raise ValueError(f'Instruction {mnemonic} expects R and M')
            r = parse_register(parts[1])
            m = parse_memory(parts[2])
            return opcode + to_nbits(r, 5) + to_nbits(m, 24)
        else:
            # GUARD maybe encoded as GUARD R?, M? but in examples used as GUARD M[n]
            # If only one operand and it's memory, use R=0
            if len(parts) == 2 and mem_re.fullmatch(parts[1]):
                m = parse_memory(parts[1])
                r = 0
                return opcode + to_nbits(r, 5) + to_nbits(m, 24)
            elif len(parts) >= 3:
                r = parse_register(parts[1])
                m = parse_memory(parts[2])
                return opcode + to_nbits(r, 5) + to_nbits(m, 24)
            else:
                raise ValueError(f'Instruction {mnemonic} expects memory operand')
    elif length == '27':
        # opcode (27) + R (5) + V (32)
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects R and immediate')
        r = parse_register(parts[1])
        # immediate token might be decimal/hex/bin
        v_tok = parts[2]
        if v_tok.startswith('0x') or v_tok.startswith('0X'):
            v = int(v_tok, 16)
        elif v_tok.startswith('0b') or v_tok.startswith('0B'):
            v = int(v_tok, 2)
        else:
            v = int(v_tok, 0)
        return opcode + to_nbits(r, 5) + to_nbits(v, 32)
    elif length == '40':
        # opcode (40) + M (24)
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects memory operand')
        # parts[1] could be M[123] or a number
        if mem_re.fullmatch(parts[1]):
            m = parse_memory(parts[1])
        else:
            m = int(parts[1], 0)
        return opcode + to_nbits(m, 24)
    elif length == '64':
        # no operands
        return opcode
    else:
        raise ValueError(f'Unsupported instruction length: {length} for {mnemonic}')


def assemble_text(text: str) -> list:
    table = MNEMONIC_TABLE
    # Two-pass support for labels: first collect labels (lines ending with ':')
    raw_lines = [raw.split('//')[0].split(';')[0].rstrip() for raw in text.splitlines()]
    label_map = {}
    instr_count = 0
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        # label line
        if line.endswith(':'):
            lbl = line[:-1].strip()
            if not lbl:
                raise ValueError('Empty label')
            if lbl in label_map:
                raise ValueError(f'Duplicate label: {lbl}')
            label_map[lbl] = instr_count
            continue
        # directive .data increases instr_count by number of data words
        if line.startswith('.data'):
            parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
            # .data followed by numbers
            data_vals = parts[1:]
            instr_count += len(data_vals)
            continue
        # otherwise it is an instruction or directive
        instr_count += 1

    # Second pass: assemble, resolving label operands when present
    lines = []
    for raw in raw_lines:
        line = raw.split('//')[0].split(';')[0].strip()
        if not line:
            continue
        # skip label declarations
        if line.endswith(':'):
            continue

        # handle .data directive: emit 64-bit binaries for each value
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
                lines.append(b)
            continue

        # replace label operands: a token that matches an identifier and exists in label_map
        parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
        if parts:
            # possible jump instructions or memory targets in position 1 or 2
            for i in (1, 2):
                if i < len(parts):
                    tok = parts[i]
                    # if token is a label name
                    if tok in label_map:
                        parts[i] = str(label_map[tok])
            # reconstruct line
            line = ' '.join(parts)

        inst = assemble_line(line, table)
        if inst:
            if len(inst) != 64:
                raise ValueError(f'Assembled instruction not 64 bits: {inst} length {len(inst)}')
            lines.append(inst)
    # Ensure program terminates cleanly by appending PARA when available
    return ensure_para(lines)


def ensure_para(lines: list) -> list:
    """Ensure the instruction list ends with a PARA (64-bit) instruction if available.

    This prevents execution from falling into zeroed memory which may decode as
    an instruction that writes special registers (e.g., ICARGA R0, ...).
    """
    try:
        para = MNEMONIC_TABLE.get('PARA')
        if para:
            para_bits = para[2]
            if not lines or lines[-1] != para_bits:
                lines.append(para_bits)
    except Exception:
        pass
    return lines


if __name__ == '__main__':
    import sys
    txt = sys.stdin.read()
    out = assemble_text(txt)
    for l in out:
        print(l)
