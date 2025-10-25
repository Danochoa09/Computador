"""
Minimal SPL/ASM lexer using PLY (lex).
Provides a `tokenize(text)` helper that returns a list of tokens (type, value, lineno).
This lexer is intentionally small and conservative: it recognizes labels, directives,
mnemonics/names, registers, numbers (decimal/hex), commas and brackets, and comments.

It is meant to be extended by the parser (`parser_spl.py`) later.
"""
from __future__ import annotations

try:
    import ply.lex as lex
except Exception as e:
    raise ImportError("PLY is required for tools/lex_spl.py. Install it with `pip install ply`. Original error: %s" % e)

# Token names
tokens = (
    'LABEL',       # mylabel:
    'DIRECTIVE',   # .data, .text, etc.
    'NAME',        # mnemonics or identifiers / also reserved words
    'REGISTER',    # R0, R1, R10
    'NUMBER',      # 123, 0x1A, 0b1010
    'COMMA',
    'LBRACKET',
    'RBRACKET',
    'MEMREF',      # M[123] or M[0xFF]
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
)

# Simple tokens
t_COMMA = r','
t_LBRACKET = r'\['
t_RBRACKET = r'\]'

# Directives start with a dot
def t_DIRECTIVE(t):
    r"\.[A-Za-z_][A-Za-z_0-9]*"
    t.value = t.value
    return t

# Labels: match an identifier that is followed by a colon, but don't consume the colon.
# Use a lookahead so the COLON token remains available to the parser. Return as NAME
# so parser productions that expect NAME work uniformly.
def t_LABEL(t):
    r"[A-Za-z_][A-Za-z_0-9]*(?=:)"
    # do not consume the trailing ':'; emit as NAME so grammar doesn't need
    # separate handling for LABEL vs NAME in most productions.
    val = t.value
    low = val.lower()
    # map a few reserved words that might appear as labels (e.g., 'else:')
    if low == 'while':
        t.type = 'WHILE'
        t.value = low
    elif low == 'if':
        t.type = 'IF'
        t.value = low
    elif low == 'else':
        t.type = 'ELSE'
        t.value = low
    elif low == 'begin':
        t.type = 'BEGIN'
        t.value = low
    elif low == 'end':
        t.type = 'END'
        t.value = low
    else:
        t.type = 'NAME'
        t.value = val
    return t

# Memory reference like M[123] or M[0x1A]
def t_MEMREF(t):
    r"M\[(0x[0-9A-Fa-f]+|0b[01]+|[0-9]+)\]"
    inner = t.value[2:-1]
    # parse number
    if inner.startswith('0x') or inner.startswith('0X'):
        t.value = int(inner, 16)
    elif inner.startswith('0b') or inner.startswith('0B'):
        t.value = int(inner, 2)
    else:
        t.value = int(inner, 10)
    return t

# Register like R4
def t_REGISTER(t):
    r"R[0-9]+"
    t.value = int(t.value[1:])
    return t

# Number: hex, binary, decimal
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

# Operators and punctuation
t_EQUALS = r"="
t_COLON = r":"
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
# Two-char comparison tokens must be before single-char
t_LE = r"<="
t_GE = r">="
t_GT = r">"
t_LT = r"<"
t_NE = r"!="
t_EQEQ = r"=="


# Mnemonics and names (ICARGA, GUARD, keywords like while/if)
reserved = {
    'while': 'WHILE',
    'if': 'IF',
    'else': 'ELSE',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
}

# Include BEGIN/END as keywords produced by the indentation preprocessor
reserved.update({'begin': 'BEGIN', 'end': 'END'})

def t_NAME(t):
    r"[A-Za-z_][A-Za-z_0-9]*"
    val = t.value
    low = val.lower()
    if low in reserved:
        t.type = reserved[low]
        t.value = low
    else:
        t.type = 'NAME'
        t.value = val
    return t

# Comments (start with ; or #) - skip
# use ignore patterns to avoid regex verbosity issues
t_ignore_COMMENT = r";[^\n]*"
t_ignore_HASH = r"\#[^\n]*"

# Ignored characters (spaces and tabs)
t_ignore = ' \t\r'

# Newlines
def t_newline(t):
    r"\n+"
    t.lexer.lineno += len(t.value)

# Error handling
def t_error(t):
    # raise a descriptive exception so upstream tools can report location
    raise SyntaxError(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}")


def build_lexer(**kwargs):
    """Build and return a PLY lexer instance."""
    return lex.lex(**kwargs)


def tokenize(text: str):
    """Tokenize input text and return a list of (type, value, lineno).

    Useful for quick tests and for feeding into a parser.
    """
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
    # quick smoke test when run directly
    sample = """
    inicio:
        ICARGA R4, 375 ; carga
        GUARD R4, M[131072]
    .data 0xFF
    """
    for t in tokenize(sample):
        print(t)
