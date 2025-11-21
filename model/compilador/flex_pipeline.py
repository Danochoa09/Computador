"""
Pipeline that takes source SPL/assembly text and produces a binary image (list of 64-bit strings).
Moved from tools/ to model/compilador with updated imports.

Flujo completo:
1. Preprocesador: Expansión de macros #define e #include
2. Compilador: Análisis sintáctico, semántico y generación de código ensamblador
3. Ensamblador: Conversión a código objeto
4. Enlazador-Cargador: Resolución de símbolos y carga en memoria
"""
from pathlib import Path
import re

from model.preprocesador.preprocessor import preprocess
from model.ensamblador.assembler_from_as import assemble_text, MNEMONIC_TABLE
from model.compilador.parser_spl import compile_high_level


def _find_repo_root(start: Path) -> Path:
    cur = start
    for p in [cur] + list(cur.parents):
        if (p / 'opcodes.json').exists() and (p / 'ISA.json').exists():
            return p
    # fallback to parent of model if present
    for p in [cur] + list(cur.parents):
        if (p / 'model').exists():
            return p
    return cur


ROOT = _find_repo_root(Path(__file__).resolve())


def pipeline_from_text(source_text: str, out_dir: Path = None, basename: str = 'image', source_file: Path = None):
    """Process source_text through preprocessor, compiler, assembler and linker.
    Returns list of 64-bit strings (the final image) and writes an image file.
    
    Flujo:
    1. PREPROCESADOR: Expande macros y procesa includes
    2. COMPILADOR: Traduce SPL a ensamblador (sintaxis + semántica + generación)
    3. ENSAMBLADOR: Convierte ensamblador a código objeto
    4. ENLAZADOR: Resuelve símbolos y genera imagen ejecutable
    """
    if out_dir is None:
        out_dir = ROOT / 'Ejemplos' / 'SPL'
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. PREPROCESADOR: Expande #define e #include
    preprocessed_text = preprocess(source_text, source_file)
    
    # Guardar código preprocesado para debugging
    pp_path = out_dir / f'{basename}.pp'
    pp_path.write_text(preprocessed_text, encoding='utf-8')

    # 2. COMPILADOR: SPL -> ASM (incluye análisis sintáctico y semántico)
    s_text = compile_high_level(preprocessed_text)
    s_path = out_dir / f'{basename}.s'
    s_path.write_text(s_text, encoding='utf-8')

    # Assemble
    maybe = assemble_text(s_text)
    if isinstance(maybe, tuple) and len(maybe) == 2 and isinstance(maybe[1], dict):
        insts, meta = maybe
    else:
        insts = maybe
        meta = {}

    # Write minimal object-like file (.o) with INST and SYM entries
    o_path = out_dir / f'{basename}.o'
    with o_path.open('w', encoding='utf-8') as f:
        for inst in insts:
            f.write(f'INST: {inst}\n')
        try:
            # re-run a simple label extraction to get label positions
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

    # Ensure PARA at the end when available
    try:
        para_bits = MNEMONIC_TABLE.get('PARA')
        if para_bits is not None:
            insts.append(para_bits[2])
    except Exception:
        pass

    image_path = out_dir / f'{basename}.i'
    image_path.write_text('\n'.join(insts) + '\n', encoding='utf-8')

    if meta:
        meta_path = out_dir / f'{basename}.meta.json'
        try:
            import json
            meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
        except Exception:
            pass

    return insts, str(image_path)
