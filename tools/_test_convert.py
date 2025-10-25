import sys, os
# ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

s = '''a = 7
b = 21

while a != b:
    if a > b:
        a = a - b
    else:
        b = b - a
M[131072] = a
'''

# Import modules by path to avoid package name collisions with top-level tools.py
import importlib.util
root = os.path.dirname(os.path.dirname(__file__))
def load_module(name, relpath):
    path = os.path.join(root, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

parser_spl = load_module('parser_spl', 'tools/parser_spl.py')
assembler_from_as = load_module('assembler_from_as', 'tools/assembler_from_as.py')

asm = parser_spl.compile_high_level(s)
print('--- ASSEMBLY ---')
print(asm)
print('\n--- BINARY LINES (64-bit) ---')
for i, b in enumerate(assembler_from_as.assemble_text(asm)):
    print(f"{i:03}: {b}")
