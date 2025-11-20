"""
Simple high-level-to-assembly translator for a minimal SPL subset.
Moved from tools/ to model/compilador.
"""
import re
from pathlib import Path

VAR_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)")
ASSIGN_RE = re.compile(r"M\[(\d+)\]\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)")
LOAD_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*M\[(\d+)\]")
WHILE_RE = re.compile(r"while\s+(.+):")
IF_RE = re.compile(r"if\s+(.+):")
COND_NE_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*!=\s*([a-zA-Z_][a-zA-Z0-9_]*)")
COND_GT_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*>\s*([a-zA-Z_][a-zA-Z0-9_]*)")


def compile_euclides(high_text: str) -> str:
    lines = [ln.split('//')[0].split(';')[0].rstrip() for ln in high_text.splitlines()]
    out = []
    reg_map = {'a': 4, 'b': 5}

    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        mload = LOAD_RE.fullmatch(ln)
        if mload:
            var = mload.group(1)
            addr = int(mload.group(2))
            if var in reg_map:
                out.append(f"CARGA R{reg_map[var]}, M[{addr}]")
            else:
                raise ValueError(f"Unknown variable {var} in load")
            i += 1
            continue
        mwh = WHILE_RE.fullmatch(ln)
        if mwh:
            cond = mwh.group(1).strip()
            mne = COND_NE_RE.fullmatch(cond)
            if not mne:
                raise ValueError('Unsupported while condition: ' + cond)
            var1, var2 = mne.group(1), mne.group(2)
            loop_label = 'loop'
            end_label = 'end'
            a_gt_label = 'a_gt'
            b_gt_label = 'b_gt'
            out.append(f"{loop_label}:")
            out.append(f"COMP R{reg_map[var1]}, R{reg_map[var2]}")
            out.append(f"SICERO {end_label}")
            out.append(f"SIPOS {a_gt_label}")
            out.append(f"SINEG {b_gt_label}")
            out.append(f"{a_gt_label}:")
            out.append(f"RESTA R{reg_map[var1]}, R{reg_map[var2]}")
            out.append(f"SALTA {loop_label}")
            out.append(f"{b_gt_label}:")
            out.append(f"RESTA R{reg_map[var2]}, R{reg_map[var1]}")
            out.append(f"SALTA {loop_label}")
            out.append(f"{end_label}:")
            i += 1
            continue
        mass = ASSIGN_RE.fullmatch(ln)
        if mass:
            addr = int(mass.group(1))
            var = mass.group(2)
            if var in reg_map:
                out.append(f"GUARD R{reg_map[var]}, M[{addr}]")
                out.append("PARA")
                i += 1
                continue
            else:
                raise ValueError('Unsupported assignment to memory from ' + var)
        if ln.upper().split()[0] in ('CARGA','GUARD','COMP','SIPOS','SINEG','RESTA','SALTA','PARA'):
            out.append(ln)
            i += 1
            continue
        i += 1
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    import sys
    txt = sys.stdin.read()
    asm = compile_euclides(txt)
    print(asm)
