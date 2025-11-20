import sys
import traceback
from pathlib import Path
# Ensure repo root is on sys.path so imports using package-relative modules work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.util

# Load parser_spl and lex_spl by path to avoid name collisions
ROOT = Path(__file__).resolve().parents[1]
ps_path = ROOT / 'tools' / 'parser_spl.py'
lex_path = ROOT / 'tools' / 'lex_spl.py'

spec = importlib.util.spec_from_file_location('parser_spl', str(ps_path))
ps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps)

spec2 = importlib.util.spec_from_file_location('lex_spl', str(lex_path))
lex_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(lex_mod)
tokenize = lex_mod.tokenize
build_lexer = lex_mod.build_lexer

import ply.yacc as yacc
import inspect

p = Path(__file__).parents[1] / 'Ejemplos' / 'SPL' / 'proc_example.spl'
text = p.read_text(encoding='utf-8')
print('=== Source ===')
print(text)
print('=== Preprocessed ===')
pre = ps._preprocess_indentation(text)
print(pre)
print('=== Tokens ===')
for t in tokenize(pre):
    print(t)

print('=== Using compile_high_level() ===')
try:
    out = ps.compile_high_level(text)
    print('--- COMPILED ASSEMBLY ---')
    print(out)
except Exception:
    traceback.print_exc()
