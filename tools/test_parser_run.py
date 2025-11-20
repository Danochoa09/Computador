import sys, os
root = os.path.dirname(os.path.dirname(__file__))
if root not in sys.path:
	sys.path.insert(0, root)

from model.compilador.parser_spl import compile_high_level

sample = '''
a = (b + 3) * M[0x10]
'''
print('SOURCE:')
print(sample)
out = compile_high_level(sample)
print('\nOUTPUT:\n')
print(out)
