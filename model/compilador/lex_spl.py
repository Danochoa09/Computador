"""
Minimal SPL/ASM lexer using PLY (lex).
Moved from tools/ to model/compilador.
"""
from __future__ import annotations

try:
    import ply.lex as lex
except Exception as e:
    raise ImportError("PLY is required for model/compilador/lex_spl.py. Install it with `pip install ply`. Original error: %s" % e)

# Token names
tokens = (
    'LABEL',
    'DIRECTIVE',
    'NAME',
    'REGISTER',
    'NUMBER',
    'COMMA',
    'DOT',
    'LBRACKET',
    'RBRACKET',
    'MEMREF',
    'EQUALS',
    'COLON',
    'PLUS',
    'MINUS',
    'TIMES',
    'LE',
    'GE',
    'GT',
    'LT',
    'NE',
    'EQEQ',
    'AND',
    'OR',
    'NOT',
    'WHILE',
    'IF',
    'ELSE',
    'BEGIN',
    'END',
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'SEMI',
    'STRING',
    'TRUE',
    'FALSE',
    'TYPE',
    'STRUCT',
    'RECORD',
    'CLASS',
    'NEW',
    'DELETE',
    'PRIVATE',
    'PUBLIC',
    'PROTECTED',
    'INTERFACE',
    'ABSTRACT',
    'MODULE',
    'IMPORT',
    'EXPORT',
    'PRINT',
    'INPUT',
    'FOR',
    'PROC',
    'RETURN',
    'VAR',
    'ARRAY',
    'MATRIX',
    'CALL',
    'ASSIGN_OP',
    'AND_SYM',
    'OR_SYM',
    'RESEV',
    'PARA',
)

# Simple tokens
t_COMMA = r','
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LBRACE = r"\{"
t_RBRACE = r"\}"
t_SEMI = r";"
t_DOT = r"\."

# Order matters in PLY! More specific patterns must come first.
# REGISTER and MEMREF must be before NAME to avoid being matched as NAME.

def t_DIRECTIVE(t):
    r"^\.[A-Za-z_][A-Za-z_0-9]*"
    t.value = t.value
    return t

def t_MEMREF(t):
    r"M\[(0x[0-9A-Fa-f]+|0b[01]+|[0-9]+)\]"
    inner = t.value[2:-1]
    if inner.startswith('0x') or inner.startswith('0X'):
        t.value = int(inner, 16)
    elif inner.startswith('0b') or inner.startswith('0B'):
        t.value = int(inner, 2)
    else:
        t.value = int(inner, 10)
    return t

def t_REGISTER(t):
    r"R[0-9]+"
    t.value = int(t.value[1:])
    return t

def t_LABEL(t):
    r"[A-Za-z_][A-Za-z_0-9]*(?=:)"
    val = t.value
    low = val.lower()
    if low == 'while':
        t.type = 'WHILE'; t.value = low
    elif low == 'if':
        t.type = 'IF'; t.value = low
    elif low == 'else':
        t.type = 'ELSE'; t.value = low
    elif low == 'begin':
        t.type = 'BEGIN'; t.value = low
    elif low == 'end':
        t.type = 'END'; t.value = low
    else:
        t.type = 'NAME'; t.value = val
    return t

def t_NUMBER(t):
    r"0x[0-9A-Fa-f]+|0b[01]+|[0-9]+"
    s = t.value
    if s.startswith(('0x', '0X')):
        t.value = int(s, 16)
    elif s.startswith(('0b', '0B')):
        t.value = int(s, 2)
    else:
        t.value = int(s, 10)
    return t


def t_STRING(t):
    r'"([^"\\]|\\.)*"'
    t.value = t.value[1:-1]
    return t

t_EQUALS = r"="
t_COLON = r":"
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_LE = r"<="
t_GE = r">="
t_GT = r">"
t_LT = r"<"
t_NE = r"!="
t_EQEQ = r"=="
t_ASSIGN_OP = r":="
t_AND_SYM = r"&&"
t_OR_SYM = r"\|\|"

reserved = {
    'while': 'WHILE', 'if': 'IF', 'else': 'ELSE', 'and': 'AND', 'or': 'OR',
    'not': 'NOT', 'for': 'FOR', 'proc': 'PROC', 'return': 'RETURN', 'var': 'VAR',
    'array': 'ARRAY', 'matrix': 'MATRIX', 'true': 'TRUE', 'false': 'FALSE', 'call': 'CALL',
}
reserved.update({'type': 'TYPE', 'struct': 'STRUCT', 'record': 'RECORD', 'class': 'CLASS'})
reserved.update({'new': 'NEW', 'delete': 'DELETE'})
reserved.update({'private': 'PRIVATE', 'public': 'PUBLIC', 'protected': 'PROTECTED'})
reserved.update({'interface': 'INTERFACE', 'abstract': 'ABSTRACT'})
reserved.update({'module': 'MODULE', 'import': 'IMPORT', 'export': 'EXPORT'})
reserved.update({'print': 'PRINT', 'input': 'INPUT'})
reserved.update({'begin': 'BEGIN', 'end': 'END'})
reserved.update({'para': 'PARA'})

# ISA mnemonics from ISA.json - mark as RESEV
isa_mnemonics = {
    # 64-bit
    'procrastina': 'RESEV', 'vuelve': 'RESEV',
    # 54-bit
    'suma': 'RESEV', 'resta': 'RESEV', 'mult': 'RESEV', 'divi': 'RESEV',
    'copia': 'RESEV', 'comp': 'RESEV', 'cargaind': 'RESEV', 'guardind': 'RESEV',
    # 59-bit
    'limp': 'RESEV', 'incre': 'RESEV', 'decre': 'RESEV', 'apila': 'RESEV', 'desapila': 'RESEV',
    # 35-bit
    'carga': 'RESEV', 'guard': 'RESEV', 'siregcero': 'RESEV', 'siregncero': 'RESEV',
    # 27-bit
    'icarga': 'RESEV', 'isuma': 'RESEV', 'iresta': 'RESEV', 'imult': 'RESEV',
    'idivi': 'RESEV', 'iand': 'RESEV', 'ior': 'RESEV', 'ixor': 'RESEV', 'icomp': 'RESEV',
    # 40-bit
    'salta': 'RESEV', 'llama': 'RESEV', 'sicero': 'RESEV', 'sincero': 'RESEV',
    'sipos': 'RESEV', 'sineg': 'RESEV', 'sioverfl': 'RESEV', 'simayor': 'RESEV',
    'simenor': 'RESEV', 'interrup': 'RESEV',
}

def t_NAME(t):
    r"[A-Za-z_][A-Za-z_0-9]*"
    val = t.value; low = val.lower()
    if low in reserved:
        t.type = reserved[low]; t.value = low
    elif low in isa_mnemonics:
        t.type = 'RESEV'; t.value = val
    else:
        t.type = 'NAME'; t.value = val
    return t

def t_COMMENT(t):
    r"//[^\n]*|/\*([^*]|\*+[^*/])*\*/|\#[^\n]*"
    pass

t_ignore = ' \t\r'

def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}")


def build_lexer(**kwargs):
    return lex.lex(**kwargs)


def tokenize(text: str):
    lexer = build_lexer()
    lexer.input(text)
    out = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        out.append((tok.type, tok.value, tok.lineno))
    return out


if __name__ == '__main__':
    sample = """
    inicio:
        ICARGA R4, 375 ; carga
        GUARD R4, M[131072]
    .data 0xFF
    """
    for t in tokenize(sample):
        print(t)
