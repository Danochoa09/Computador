#!/usr/bin/env python3
"""
Simple linker/loader skeleton for the SPL toolchain.
Reads simple textual object files and emits a loadable binary image (text with 64-bit binary words per line)

Usage:
    python tools/linker.py a.o b.o -o image.bin

Object file format (textual) assumed:
- Lines starting with INST: <64-bit-binary>
- Lines starting with SYM: name,offset,local|global
- Lines starting with RELOC: offset,TYPE=ABS, SYMBOL=name
- Lines starting with SEGMENT: NAME,SIZE=nn,BASE=0

This is a simplified example for the course.
"""
import sys
import argparse
from pathlib import Path


def parse_obj(path: Path):
    objs = {'inst': [], 'sym': [], 'reloc': []}
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        if ln.startswith('INST:'):
            _, val = ln.split(':', 1)
            objs['inst'].append(val.strip())
        elif ln.startswith('SYM:'):
            _, rest = ln.split(':', 1)
            name, off, kind = [p.strip() for p in rest.split(',')]
            objs['sym'].append((name, int(off), kind))
        elif ln.startswith('RELOC:'):
            _, rest = ln.split(':', 1)
            off_part, rest2 = rest.split(',', 1)
            off = int(off_part.strip())
            # simple parsing TYPE=..., SYMBOL=...
            parts = [p.strip() for p in rest2.split(',')]
            info = {}
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    info[k.strip()] = v.strip()
            objs['reloc'].append((off, info))
    return objs


def main():
    p = argparse.ArgumentParser()
    p.add_argument('objects', nargs='+')
    p.add_argument('-o', '--output', default='image.bin')
    args = p.parse_args()

    all_insts = []
    all_symbols = {}
    all_relocs = []

    # Simple concatenation layout: each object placed sequentially
    base = 0
    for objfile in args.objects:
        obj = parse_obj(Path(objfile))
        # record symbols with offset+base
        for name, off, kind in obj['sym']:
            all_symbols[name] = base + off
        # record insts
        for inst in obj['inst']:
            all_insts.append(inst)
        # record relocs adjusted
        for off, info in obj['reloc']:
            all_relocs.append((base + off, info))
        base += len(obj['inst'])

    # Apply relocations (only ABS -> replace instruction at offset with symbol address encoded in 64-bit binary)
    for off, info in all_relocs:
        if info.get('TYPE') == 'ABS' and 'SYMBOL' in info:
            sym = info['SYMBOL']
            if sym not in all_symbols:
                print(f"Undefined symbol: {sym}")
                sys.exit(1)
            addr = all_symbols[sym]
            # encode addr as 64-bit binary string
            b = format(addr, '064b')
            # replace the instruction at offset (naive)
            if 0 <= off < len(all_insts):
                all_insts[off] = b

    # Write output image as lines of 64-bit binary
    out = Path(args.output)
    out.write_text('\n'.join(all_insts) + '\n')
    print(f"Wrote {len(all_insts)} words to {out}")

if __name__ == '__main__':
    main()
