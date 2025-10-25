from pathlib import Path
import sys
from importlib.util import spec_from_file_location, module_from_spec

# Load assembler_from_as and parser_spl directly and implement a small pipeline here
ROOT = Path(__file__).resolve().parents[1]

def load_module_from_tools(name, filename):
    spec = spec_from_file_location(name, str(ROOT / 'tools' / filename))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

assembler_mod = load_module_from_tools('assembler_from_as', 'assembler_from_as.py')
# Use the existing ad-hoc translator for euclides (spl_to_asm) to avoid package-relative imports
spl_mod = load_module_from_tools('spl_to_asm', 'spl_to_asm.py')

def pipeline_from_text(source_text: str, out_dir: Path = None, basename: str = 'image'):
    if out_dir is None:
        out_dir = ROOT / 'Ejemplos' / 'SPL'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Heuristic: if looks like euclides, use spl_to_asm translator, else treat as assembly
    lowered = source_text.lower()
    if 'while' in lowered and 'a =' in lowered and 'b =' in lowered:
        s_text = spl_mod.compile_euclides(source_text)
    else:
        s_text = source_text
    s_path = out_dir / f'{basename}.s'
    s_path.write_text(s_text, encoding='utf-8')

    insts = assembler_mod.assemble_text(s_text)
    o_path = out_dir / f'{basename}.o'
    with o_path.open('w', encoding='utf-8') as f:
        for inst in insts:
            f.write(f'INST: {inst}\n')

    image_path = out_dir / f'{basename}.i'
    image_path.write_text('\n'.join(insts) + '\n', encoding='utf-8')
    return insts, str(image_path)

root = Path(__file__).resolve().parents[1]
# Euclides high-level
p = root / 'Ejemplos' / 'SPL' / 'euclides_high.spl'
print('--- EUCLIDES HIGH (source) -> binary ---')
text = p.read_text(encoding='utf-8')
insts, image_path = pipeline_from_text(text, out_dir=root / 'tools' / 'tests', basename='euclides_bin')
for i,l in enumerate(insts):
    print(f'{i:03}: {l}')

# Factorial (assembly) if exists
f = root / 'Ejemplos' / 'factorial.as'
if f.exists():
    print('\n--- FACTORIAL (asm) -> binary ---')
    text = f.read_text(encoding='utf-8')
    insts2, image_path2 = pipeline_from_text(text, out_dir=root / 'tools' / 'tests', basename='factorial_bin')
    for i,l in enumerate(insts2):
        print(f'{i:03}: {l}')
else:
    print('factorial.as not found')
