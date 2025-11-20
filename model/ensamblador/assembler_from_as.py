"""Simple assembler for a subset of the project's ISA.
Moved from tools/ to model/ensamblador; updated repo root detection.
"""
import json
import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start
    for p in [cur] + list(cur.parents):
        if (p / 'opcodes.json').exists() and (p / 'ISA.json').exists():
            return p
    return cur.parent  # best effort


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


def assemble_line(line: str, table: dict, label_map: dict = None) -> str:
    line = line.strip()
    if not line or line.startswith(';') or line.startswith('//'):
        return None
    parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
    if len(parts) == 0:
        return None
    mnemonic = parts[0].upper()
    if mnemonic not in table:
        raise ValueError(f'Unknown mnemonic: {mnemonic} (line: {line})')
    length, offset, opcode = table[mnemonic]
    if label_map is None:
        label_map = {}

    if length == '54':
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects two register operands')
        r = parse_register(parts[1])
        rp = parse_register(parts[2])
        return opcode + to_nbits(r, 5) + to_nbits(rp, 5)
    elif length == '59':
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects one register operand')
        r = parse_register(parts[1])
        return opcode + to_nbits(r, 5)
    elif length == '35':
        if mnemonic in ('CARGA', 'SIREGCERO', 'SIREGNCERO'):
            if len(parts) < 3:
                raise ValueError(f'Instruction {mnemonic} expects R and M')
            r = parse_register(parts[1])
            m = parse_memory(parts[2])
            return opcode + to_nbits(r, 5) + to_nbits(m, 24)
        else:
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
        if len(parts) < 3:
            raise ValueError(f'Instruction {mnemonic} expects R and immediate')
        r = parse_register(parts[1])
        v_tok = parts[2]
        # Check if it's a label reference
        if v_tok in label_map:
            v = label_map[v_tok]
        elif v_tok.startswith('0x') or v_tok.startswith('0X'):
            v = int(v_tok, 16)
        elif v_tok.startswith('0b') or v_tok.startswith('0B'):
            v = int(v_tok, 2)
        else:
            try:
                v = int(v_tok, 0)
            except ValueError:
                raise ValueError(f'Invalid immediate value or unknown label: {v_tok}')
        return opcode + to_nbits(r, 5) + to_nbits(v, 32)
    elif length == '40':
        if len(parts) < 2:
            raise ValueError(f'Instruction {mnemonic} expects memory operand')
        if mem_re.fullmatch(parts[1]):
            m = parse_memory(parts[1])
        else:
            m = int(parts[1], 0)
        return opcode + to_nbits(m, 24)
    elif length == '64':
        return opcode
    else:
        raise ValueError(f'Unsupported instruction length: {length} for {mnemonic}')


def assemble_text(text: str) -> list:
    table = MNEMONIC_TABLE
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

    lines = []
    result_addr = None
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
                lines.append(b)
            continue

        def replace_mem_label(match):
            inner = match.group(1)
            if '+' in inner or '-' in inner:
                m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)((?:\+|\-)\d+)$", inner)
                if not m:
                    return match.group(0)
                lbl = m.group(1)
                off = int(m.group(2))
                if lbl in label_map:
                    return f"M[{label_map[lbl] + off}]"
                else:
                    return match.group(0)
            else:
                lbl = inner
                if lbl in label_map:
                    return f"M[{label_map[lbl]}]"
                else:
                    return match.group(0)

        line = re.sub(r"M\[([^\]]+)\]", replace_mem_label, line)

        parts = [p.strip() for p in re.split('[,\s]+', line) if p.strip()]
        if parts:
            for i in (1, 2):
                if i < len(parts):
                    tok = parts[i]
                    if tok in label_map:
                        parts[i] = str(label_map[tok])
            line = ' '.join(parts)

        try:
            p0 = parts[0].upper()
            if p0 == 'GUARD':
                mem_tok = None
                if len(parts) == 2 and mem_re.fullmatch(parts[1]):
                    mem_tok = parts[1]
                elif len(parts) >= 3 and mem_re.fullmatch(parts[2]):
                    mem_tok = parts[2]
                elif len(parts) >= 2 and parts[1].isdigit():
                    mem_tok = f"M[{parts[1]}]"
                if mem_tok:
                    mval = parse_memory(mem_tok)
                    if result_addr is None:
                        result_addr = mval
        except Exception:
            pass

        inst = assemble_line(line, table, label_map)
        if inst:
            if len(inst) != 64:
                raise ValueError(f'Assembled instruction not 64 bits: {inst} length {len(inst)}')
            lines.append(inst)
    lines = ensure_para(lines)
    meta = {}
    if result_addr is not None:
        meta['result_addr'] = int(result_addr)

    # Determine a sensible entry index for the image.
    # Prefer a label named 'main' if present; otherwise use the first non-zero word.
    try:
        if 'main' in label_map:
            meta['entry_index'] = int(label_map['main'])
        else:
            zero_word = '0' * 64
            first_nonzero = next((i for i, l in enumerate(lines) if l != zero_word), 0)
            meta['entry_index'] = int(first_nonzero)
    except Exception:
        pass
    return lines, meta


def ensure_para(lines: list) -> list:
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
    basename = None
    if len(sys.argv) > 1:
        basename = sys.argv[1]
    maybe = assemble_text(txt)
    if isinstance(maybe, tuple) and len(maybe) == 2:
        lines, meta = maybe
    else:
        lines = maybe
        meta = {}
    for l in lines:
        print(l)
    try:
        import json, os
        if meta:
            meta_path = None
            if basename:
                meta_path = Path(basename).with_suffix('.meta.json')
            else:
                meta_path = Path(os.getcwd()) / 'assembler.meta.json'
            meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    except Exception:
        pass
