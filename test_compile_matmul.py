"""Test compilation of matmul_input_dynamic.spl"""
from model.compilador.flex_pipeline import pipeline_from_text
import json
from pathlib import Path

with open('Ejemplos/SPL/matmul_input_dynamic.spl', encoding='utf-8') as f:
    code = f.read()

try:
    insts, image_path = pipeline_from_text(code, basename='matmul_input_dynamic')
    print('✓ Compilation successful')
    print(f'Binary image: {image_path}')
    print(f'Binary image size: {len(insts)} words')
    
    # Try to read metadata
    meta_path = Path(image_path).with_suffix('.meta.json')
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        print(f'Entry index: {meta.get("entry_index")}')
        print(f'Result addr: {meta.get("result_addr")}')
    else:
        print('No metadata file found')
except Exception as e:
    print(f'✗ Compilation failed: {e}')
    import traceback
    traceback.print_exc()
