"""Test lexer tokenization"""
from model.compilador import lex_spl

# Test with both assembly and SPL code
test_code_asm = """ICARGA R4 375
GUARD R4 M[131072]
SUMA R5, R6
CARGAIND R7 R8
"""

test_code_spl = """i = 0
while i < 10 :
    print("value: ", i)
    i = i + 1
end
para
"""

def print_tokens(code, title):
    print(f"\n{title}")
    print("=" * 50)
    lexer = lex_spl.build_lexer()
    lexer.input(code)
    
    print("Token Type      | Value")
    print("-" * 40)
    tok = lexer.token()
    while tok:
        print(f"{tok.type:15} | {tok.value}")
        tok = lexer.token()

print_tokens(test_code_asm, "Assembly Code Tokens")
print_tokens(test_code_spl, "SPL Code Tokens")
