import importlib.util
import os

root = os.path.dirname(os.path.dirname(__file__))
lex_path = os.path.join(root, 'tools', 'lex_spl.py')
spec = importlib.util.spec_from_file_location('lex_spl', lex_path)
lex_mod = importlib.util.module_from_spec(spec)
import sys
# register in sys.modules so inspect and PLY can find the module source
sys.modules['lex_spl'] = lex_mod
spec.loader.exec_module(lex_mod)
tokenize = lex_mod.tokenize

sample = '''proc foo(a, b) {
  var x := 10;
  if (x >= 5 && a == 0) {
    return "done";
  }
}
// comment
M[0x10]
'''

import ply.lex as pyllex
lexer = pyllex.lex(module=lex_mod)
lexer.input(sample)
while True:
  tok = lexer.token()
  if not tok:
    break
  print((tok.type, tok.value, tok.lineno))
