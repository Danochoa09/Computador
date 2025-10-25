"""
Pipeline that takes source SPL/assembly text and produces a binary image (list of 64-bit strings).
This is a lightweight Python replacement for the FLEX-based pipeline.
"""
from pathlib import Path
import re
from .assembler_from_as import assemble_text, MNEMONIC_TABLE
from .parser_spl import compile_high_level

ROOT = Path(__file__).resolve().parents[1]


def pipeline_from_text(source_text: str, out_dir: Path = None, basename: str = 'image'):
    """Process source_text through preprocessor (identity), assembler and linker (concatenate) .
    Returns list of 64-bit strings (the final image).
    Writes intermediate files in out_dir if provided.
    """
    if out_dir is None:
        out_dir = ROOT / 'Ejemplos' / 'SPL'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Preprocessor step: run high-level preprocessor/parser which will
    # either translate high-level SPL (euclides-like) to assembly or
    # return the original assembly text after light validation.
    s_text = compile_high_level(source_text)
    s_path = out_dir / f'{basename}.s'
    s_path.write_text(s_text, encoding='utf-8')

    # Assembler step: convert .s to inst list and collect labels
    # use assembler to produce insts; we also compute label map to write a simple .o
    insts = assemble_text(s_text)
    # write object-like file (.o) including INST and SYM entries for the linker
    o_path = out_dir / f'{basename}.o'
    with o_path.open('w', encoding='utf-8') as f:
        for inst in insts:
            f.write(f'INST: {inst}\n')
        # attempt to extract labels from assembler (two-pass)
        try:
            from .assembler_from_as import load_tables
            # re-run a simple label extraction to get label positions
            # (assembler_from_as computes label positions internally; replicate minimal parse)
            raw_lines = [raw.split('//')[0].split(';')[0].rstrip() for raw in s_text.splitlines()]
            instr_count = 0
            for raw in raw_lines:
                line = raw.strip()
                if not line:
                    continue
                if line.endswith(':'):
                    lbl = line[:-1].strip()
                    f.write(f'SYM: {lbl},{instr_count},local\n')
                    continue
                if line.startswith('.data'):
                    parts = [p.strip() for p in re.split('[,\\s]+', line) if p.strip()]
                    instr_count += max(0, len(parts) - 1)
                    continue
                instr_count += 1
        except Exception:
            pass

    # Linker step: since single object, we just produce final image as insts
    # Append a PARA instruction at the end to avoid execution falling into
    # uninitialized (zero) memory which decodes as ICARGA R0, ... and can
    # attempt to write special registers. PARA is a 64-bit 'stop' instruction.
    try:
        para_bits = MNEMONIC_TABLE.get('PARA')
        if para_bits is not None:
            # MNEMONIC_TABLE entry: (length, idx, bits)
            insts.append(para_bits[2])
    except Exception:
        # if unable to append PARA, continue without it
        pass

    image_path = out_dir / f'{basename}.i'
    image_path.write_text('\n'.join(insts) + '\n', encoding='utf-8')

    return insts, str(image_path)
