import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from model.compilador import parser_spl as p
s = open('Ejemplos/SPL/matmul_input_dynamic.spl','r',encoding='utf-8').read()
pre = p._preprocess_indentation(s)
print('---PREPROCESS---')
print(pre)
print('---PREPROCESS END---')
out = p.compile_high_level(s)
print('---ASM START---')
print(out)
print('---ASM END---')
