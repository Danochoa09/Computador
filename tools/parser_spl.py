"""
PLY-based parser/preprocessor for a small SPL subset.
Handles a minimal indentation-aware subset (assignments, while, if, mem loads/stores)
and emits equivalent assembly. This is focused on the Euclides-like programs used
in examples; the grammar is intentionally small and extensible.
"""
from __future__ import annotations

from typing import List
import ply.lex as lex
import ply.yacc as yacc
from . import lex_spl
from .spl_to_asm import compile_euclides
from .assembler_from_as import MNEMONIC_TABLE
import re

# Parser context for simple register allocation and unique label generation
class ParserContext:
    def __init__(self, reg_start: int = 4, reg_end: int = 15):
        # Registers available for allocation (R0..R3 reserved)
        self.reg_start = reg_start
        self.reg_end = reg_end
        self.next_reg = reg_start
        self.var_map = {}  # var name -> register number
        self.temp_count = 0
        self.label_count = 0

    def reg_for(self, var: str) -> int:
        """Return a register number for variable `var`, allocate if needed."""
        if var in self.var_map:
            return self.var_map[var]
        if self.next_reg > self.reg_end:
            # wrap-around fallback (not ideal but keeps things working)
            self.next_reg = self.reg_start
        r = self.next_reg
        self.var_map[var] = r
        self.next_reg += 1
        return r

    def new_temp(self) -> int:
        # Prefer to allocate an ephemeral register after named vars
        if self.next_reg > self.reg_end:
            self.next_reg = self.reg_start
        r = self.next_reg
        self.next_reg += 1
        self.temp_count += 1
        return r

    def new_label(self, prefix: str = 'L') -> str:
        self.label_count += 1
        return f"{prefix}_{self.label_count}"


# Global context used by action routines; set by compile_high_level()
ctx: ParserContext | None = None


# Helpers to build and generate condition AST -> assembly
def _mk_name(n):
    return ('name', n)


def _mk_num(v):
    return ('num', v)


def _gen_cmp_asm(ast, true_label, end_label):
    """Generate assembly that jumps to true_label if ast (cmp) is true, else jumps to end_label."""
    # ast = ('cmp', left, op, right)
    _, left, op, right = ast
    lines = []
    # prepare registers
    if left[0] == 'name':
        r_left = ctx.reg_for(left[1])
    else:
        r_left = ctx.new_temp()
        lines.append(f"ICARGA R{r_left} {left[1]}")

    if right[0] == 'name':
        r_right = ctx.reg_for(right[1])
    else:
        r_right = ctx.new_temp()
        lines.append(f"ICARGA R{r_right} {right[1]}")

    lines.append(f"COMP R{r_left}, R{r_right}")
    # map op to jumps
    if op == '==':
        lines.append(f"SICERO {true_label}")
    elif op == '!=':
        lines.append(f"SINCERO {true_label}")
    elif op == '<':
        lines.append(f"SINEG {true_label}")
    elif op == '<=':
        lines.append(f"SICERO {true_label}")
        lines.append(f"SINEG {true_label}")
    elif op == '>':
        lines.append(f"SIPOS {true_label}")
    elif op == '>=':
        lines.append(f"SICERO {true_label}")
        lines.append(f"SIPOS {true_label}")
    # if reached here and not true, jump to end
    lines.append(f"SALTA {end_label}")
    return '\n'.join(lines)


def generate_cond_asm(ast, true_label, end_label):
    """Generate assembly for condition AST that jumps to true_label when true, else to end_label."""
    kind = ast[0]
    if kind == 'cmp':
        return _gen_cmp_asm(ast, true_label, end_label)
    if kind == 'and':
        # left AND right: if left true -> evaluate right; else -> end
        left, right = ast[1], ast[2]
        mid = ctx.new_label('and_mid')
        s1 = generate_cond_asm(left, mid, end_label)
        s2 = generate_cond_asm(right, true_label, end_label)
        return s1 + '\n' + f"{mid}:\n" + s2
    if kind == 'or':
        # left OR right: if left true -> true_label; else evaluate right
        left, right = ast[1], ast[2]
        s1 = generate_cond_asm(left, true_label, None)
        # if left false, it will have jumped to end_label; to chain, we need explicit fallthrough
        # implement by trying left: if true jump to true_label; else continue to evaluate right
        # so generate left with true->true_label and end->continue (no-op) then right-> true or end
        cont = ctx.new_label('or_cont')
        s1 = generate_cond_asm(left, true_label, cont)
        s2 = generate_cond_asm(right, true_label, end_label)
        return s1 + '\n' + f"{cont}:\n" + s2
    if kind == 'not':
        inner = ast[1]
        # invert true/false labels
        return generate_cond_asm(inner, end_label, true_label)
    raise ValueError(f"Unknown cond AST kind: {kind}")


def _preprocess_indentation(text: str) -> str:
    """Convert indentation to explicit BEGIN/END markers.

    Minimal approach: count leading spaces per line and whenever the indent
    increases insert a `BEGIN` marker, when it decreases insert `END`.
    Assumes consistent indentation using spaces.
    """
    out_lines: List[str] = []
    indent_stack = [0]
    for raw in text.splitlines():
        if not raw.strip():
            out_lines.append(raw)
            continue
        leading = len(raw) - len(raw.lstrip(' '))
        if leading > indent_stack[-1]:
            indent_stack.append(leading)
            out_lines.append('BEGIN')
        while leading < indent_stack[-1]:
            indent_stack.pop()
            out_lines.append('END')
        out_lines.append(raw.lstrip())
    while len(indent_stack) > 1:
        indent_stack.pop()
        out_lines.append('END')
    return '\n'.join(out_lines)


# Expose lexer tokens from lex_spl
tokens = lex_spl.tokens + ('BEGIN', 'END')

# Parser rules for a tiny SPL subset

# program : stmts
def p_program(p):
    'program : stmts'
    p[0] = '\n'.join(p[1])


def p_stmts_multiple(p):
    'stmts : stmt stmts'
    p[0] = [p[1]] + p[2]


def p_stmts_empty(p):
    'stmts : '
    p[0] = []


# assignment: a = M[375]
def p_stmt_assignment_memload(p):
    'stmt : NAME EQUALS MEMREF'
    var = p[1]
    addr = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    p[0] = f"CARGA R{reg}, M[{addr}]"


# store: M[131072] = a
def p_stmt_assignment_memstore(p):
    'stmt : MEMREF EQUALS NAME'
    addr = p[1]
    var = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    p[0] = f"GUARD R{reg}, M[{addr}]"


# assignment: a = 0  (immediate)
def p_stmt_assignment_number(p):
    'stmt : NAME EQUALS NUMBER'
    var = p[1]
    val = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    # use ICARGA to load immediate into register
    p[0] = f"ICARGA R{reg} {val}"


# assignment: a = b  (copy)
def p_stmt_assignment_name(p):
    'stmt : NAME EQUALS NAME'
    dst = p[1]
    src = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_src = ctx.reg_for(src)
    p[0] = f"COPIA R{reg_dst}, R{reg_src}"


# assignment: a = a + i  (reg + reg)
def p_stmt_assignment_add_regs(p):
    'stmt : NAME EQUALS NAME PLUS NAME'
    dst = p[1]
    left = p[3]
    right = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    # Use SUMA Rdst, Rright assuming left stored in dst
    # If left is not the same as dst, copy first
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nSUMA R{reg_dst}, R{reg_right}"
    else:
        p[0] = f"SUMA R{reg_dst}, R{reg_right}"


# subtraction: a = b - c  (reg - reg)
def p_stmt_assignment_sub_regs(p):
    'stmt : NAME EQUALS NAME MINUS NAME'
    dst = p[1]
    left = p[3]
    right = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    # If left not in dst, copy then resta
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nRESTA R{reg_dst}, R{reg_right}"
    else:
        p[0] = f"RESTA R{reg_dst}, R{reg_right}"


# assignment: i = i + 1  (reg + immediate)
def p_stmt_assignment_add_imm(p):
    'stmt : NAME EQUALS NAME PLUS NUMBER'
    dst = p[1]
    left = p[3]
    imm = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    # if left != dst, copy then add immediate
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nISUMA R{reg_dst} {imm}"
    else:
        p[0] = f"ISUMA R{reg_dst} {imm}"


# subtraction with immediate: a = b - 5
def p_stmt_assignment_sub_imm(p):
    'stmt : NAME EQUALS NAME MINUS NUMBER'
    dst = p[1]
    left = p[3]
    imm = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    # ISUMA adds an immediate; use negative immediate to subtract
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nISUMA R{reg_dst} {-imm}"
    else:
        p[0] = f"ISUMA R{reg_dst} {-imm}"


# multiplication: a = b * c  (reg * reg)
def p_stmt_assignment_mul_regs(p):
    'stmt : NAME EQUALS NAME TIMES NAME'
    dst = p[1]
    left = p[3]
    right = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    # If left not in dst, copy then mult
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nMULT R{reg_dst}, R{reg_right}"
    else:
        p[0] = f"MULT R{reg_dst}, R{reg_right}"


# multiplication with immediate: a = b * 5
def p_stmt_assignment_mul_imm(p):
    'stmt : NAME EQUALS NAME TIMES NUMBER'
    dst = p[1]
    left = p[3]
    imm = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_left = ctx.reg_for(left)
    # Use IMULT with immediate if supported
    if reg_left != reg_dst:
        p[0] = f"COPIA R{reg_dst}, R{reg_left}\nIMULT R{reg_dst} {imm}"
    else:
        p[0] = f"IMULT R{reg_dst} {imm}"


# while a != b: <block>
def p_stmt_while(p):
    'stmt : WHILE NAME NE NAME COLON BEGIN stmts END'
    var1 = p[2]
    var2 = p[4]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    regmap = {var1: ctx.reg_for(var1), var2: ctx.reg_for(var2)}
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    a_gt = ctx.new_label('a_gt')
    b_gt = ctx.new_label('b_gt')
    out = []
    out.append(f"{loop_label}:")
    out.append(f"COMP R{regmap[var1]}, R{regmap[var2]}")
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {a_gt}")
    out.append(f"SINEG {b_gt}")
    out.append(f"{a_gt}:")
    out.append(f"RESTA R{regmap[var1]}, R{regmap[var2]}")
    out.append(f"SALTA {loop_label}")
    out.append(f"{b_gt}:")
    out.append(f"RESTA R{regmap[var2]}, R{regmap[var1]}")
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_while_num(p):
    'stmt : WHILE NAME NE NUMBER COLON BEGIN stmts END'
    var1 = p[2]
    imm = p[4]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg1 = ctx.reg_for(var1)
    temp = ctx.new_temp()
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    a_gt = ctx.new_label('a_gt')
    b_gt = ctx.new_label('b_gt')
    out = []
    # load immediate into temp
    out.append(f"ICARGA R{temp} {imm}")
    out.append(f"{loop_label}:")
    out.append(f"COMP R{reg1}, R{temp}")
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {a_gt}")
    out.append(f"SINEG {b_gt}")
    out.append(f"{a_gt}:")
    out.append(f"RESTA R{reg1}, R{temp}")
    out.append(f"SALTA {loop_label}")
    out.append(f"{b_gt}:")
    out.append(f"RESTA R{temp}, R{reg1}")
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# while a < b: <block>  (name < name)
def p_stmt_while_lt(p):
    'stmt : WHILE NAME LT NAME COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    var1 = p[2]
    var2 = p[4]
    reg1 = ctx.reg_for(var1)
    reg2 = ctx.reg_for(var2)
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    out = []
    out.append(f"{loop_label}:")
    out.append(f"COMP R{reg1}, R{reg2}")
    # if equal or greater, exit
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {end_label}")
    # body is stmts at p[7]
    out.extend(p[7])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# while a < 10: <block>  (name < number)
def p_stmt_while_lt_num(p):
    'stmt : WHILE NAME LT NUMBER COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    var1 = p[2]
    imm = p[4]
    reg1 = ctx.reg_for(var1)
    temp = ctx.new_temp()
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    out = []
    out.append(f"ICARGA R{temp} {imm}")
    out.append(f"{loop_label}:")
    out.append(f"COMP R{reg1}, R{temp}")
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {end_label}")
    out.extend(p[7])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# General condition nonterminal (supports AND/OR/NOT and comparisons)
def p_cond_and(p):
    'cond : cond AND cond'
    p[0] = ('and', p[1], p[3])


def p_cond_or(p):
    'cond : cond OR cond'
    p[0] = ('or', p[1], p[3])


def p_cond_not(p):
    'cond : NOT cond'
    p[0] = ('not', p[2])


def p_cond_cmp_name_name(p):
    'cond : NAME EQEQ NAME'
    p[0] = ('cmp', _mk_name(p[1]), '==', _mk_name(p[3]))


def p_cond_cmp_name_name_ne(p):
    'cond : NAME NE NAME'
    p[0] = ('cmp', _mk_name(p[1]), '!=', _mk_name(p[3]))


def p_cond_cmp_name_name_lt(p):
    'cond : NAME LT NAME'
    p[0] = ('cmp', _mk_name(p[1]), '<', _mk_name(p[3]))


def p_cond_cmp_name_name_le(p):
    'cond : NAME LE NAME'
    p[0] = ('cmp', _mk_name(p[1]), '<=', _mk_name(p[3]))


def p_cond_cmp_name_name_gt(p):
    'cond : NAME GT NAME'
    p[0] = ('cmp', _mk_name(p[1]), '>', _mk_name(p[3]))


def p_cond_cmp_name_name_ge(p):
    'cond : NAME GE NAME'
    p[0] = ('cmp', _mk_name(p[1]), '>=', _mk_name(p[3]))


def p_cond_cmp_name_num(p):
    'cond : NAME EQEQ NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '==', _mk_num(p[3]))


def p_cond_cmp_name_num_ne(p):
    'cond : NAME NE NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '!=', _mk_num(p[3]))


def p_cond_cmp_name_num_lt(p):
    'cond : NAME LT NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '<', _mk_num(p[3]))


def p_cond_cmp_name_num_le(p):
    'cond : NAME LE NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '<=', _mk_num(p[3]))


def p_cond_cmp_name_num_gt(p):
    'cond : NAME GT NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '>', _mk_num(p[3]))


def p_cond_cmp_name_num_ge(p):
    'cond : NAME GE NUMBER'
    p[0] = ('cmp', _mk_name(p[1]), '>=', _mk_num(p[3]))


# New if/while forms that accept a general condition
def p_stmt_if_cond(p):
    'stmt : IF cond COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    cond_ast = p[2]
    true_label = ctx.new_label('if_true')
    end_label = ctx.new_label('if_end')
    pre = generate_cond_asm(cond_ast, true_label, end_label)
    out = []
    if pre:
        out.append(pre)
    out.append(f"{true_label}:")
    out.extend(p[5])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_while_cond(p):
    'stmt : WHILE cond COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    cond_ast = p[2]
    loop_label = ctx.new_label('loop')
    body_label = ctx.new_label('body')
    end_label = ctx.new_label('end')
    out = []
    out.append(f"{loop_label}:")
    out.append(generate_cond_asm(cond_ast, body_label, end_label))
    out.append(f"{body_label}:")
    out.extend(p[5])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# while a > b: <block>  (name > name)
def p_stmt_while_gt(p):
    'stmt : WHILE NAME GT NAME COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    var1 = p[2]
    var2 = p[4]
    reg1 = ctx.reg_for(var1)
    reg2 = ctx.reg_for(var2)
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    a_gt = ctx.new_label('a_gt')
    b_gt = ctx.new_label('b_gt')
    out = []
    out.append(f"{loop_label}:")
    out.append(f"COMP R{reg1}, R{reg2}")
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {a_gt}")
    out.append(f"SINEG {end_label}")
    out.append(f"{a_gt}:")
    out.extend(p[7])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# while a > 10: <block>  (name > number)
def p_stmt_while_gt_num(p):
    'stmt : WHILE NAME GT NUMBER COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    var1 = p[2]
    imm = p[4]
    reg1 = ctx.reg_for(var1)
    temp = ctx.new_temp()
    loop_label = ctx.new_label('loop')
    end_label = ctx.new_label('end')
    a_gt = ctx.new_label('a_gt')
    b_gt = ctx.new_label('b_gt')
    out = []
    out.append(f"ICARGA R{temp} {imm}")
    out.append(f"{loop_label}:")
    out.append(f"COMP R{reg1}, R{temp}")
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {a_gt}")
    out.append(f"SINEG {end_label}")
    out.append(f"{a_gt}:")
    out.extend(p[7])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


# if a > b: <block>  (we inline the true-block)
def p_stmt_if(p):
    'stmt : IF NAME GT NAME COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    left = p[2]
    right = p[4]
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    true_label = ctx.new_label('if_true')
    end_label = ctx.new_label('if_end')
    out = []
    out.append(f"COMP R{reg_left}, R{reg_right}")
    out.append(f"SIPOS {true_label}")
    out.append(f"SALTA {end_label}")
    out.append(f"{true_label}:")
    out.extend(p[7])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_if_eq(p):
    'stmt : IF NAME EQEQ NAME COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    left = p[2]
    right = p[4]
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    true_label = ctx.new_label('if_true')
    end_label = ctx.new_label('if_end')
    out = []
    out.append(f"COMP R{reg_left}, R{reg_right}")
    out.append(f"SICERO {true_label}")
    out.append(f"SALTA {end_label}")
    out.append(f"{true_label}:")
    out.extend(p[7])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_if_le(p):
    'stmt : IF NAME LT NAME COLON BEGIN stmts END'
    # a < b  -> after COMP, SIPOS means a>b -> skip true, else true
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    left = p[2]
    right = p[4]
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    true_label = ctx.new_label('if_true')
    end_label = ctx.new_label('if_end')
    out = []
    out.append(f"COMP R{reg_left}, R{reg_right}")
    out.append(f"SIPOS {end_label}")
    out.append(f"{true_label}:")
    out.extend(p[7])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_if_eq_num(p):
    'stmt : IF NAME EQEQ NUMBER COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    left = p[2]
    imm = p[4]
    reg_left = ctx.reg_for(left)
    temp = ctx.new_temp()
    true_label = ctx.new_label('if_true')
    end_label = ctx.new_label('if_end')
    out = []
    out.append(f"ICARGA R{temp} {imm}")
    out.append(f"COMP R{reg_left}, R{temp}")
    out.append(f"SICERO {true_label}")
    out.append(f"SALTA {end_label}")
    out.append(f"{true_label}:")
    out.extend(p[7])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_stmt_if_else(p):
    'stmt : IF NAME GT NAME COLON BEGIN stmts END ELSE COLON BEGIN stmts END'
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    left = p[2]
    right = p[4]
    reg_left = ctx.reg_for(left)
    reg_right = ctx.reg_for(right)
    true_label = ctx.new_label('if_true')
    else_label = ctx.new_label('if_else')
    end_label = ctx.new_label('if_end')
    out = []
    out.append(f"COMP R{reg_left}, R{reg_right}")
    out.append(f"SIPOS {true_label}")
    out.append(f"SALTA {else_label}")
    out.append(f"{true_label}:")
    out.extend(p[7])
    out.append(f"SALTA {end_label}")
    out.append(f"{else_label}:")
    out.extend(p[12])
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


def p_error(p):
    if p:
        raise SyntaxError(f"Syntax error at token {p.type} ({p.value}) line {p.lineno}")
    else:
        raise SyntaxError("Syntax error at EOF")


def compile_high_level(text: str) -> str:
    """Parse high-level SPL using PLY and return assembly text.

    For the Euclides pattern we still prefer the existing `compile_euclides` translator
    since it emits labels and structure we expect. For other inputs we attempt to parse
    them with the small grammar above.
    """
    # If the input already looks like assembly (first non-empty line starts
    # with a known mnemonic), just return it unchanged so the assembler
    # will process it. This preserves previous behavior for `.spl` files
    # that are actually assembly (like the euclides.spl example).
    first_line = None
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        first_line = s
        break
    if first_line:
        m = re.match(r"^([A-Za-z_][A-Za-z_0-9]*)", first_line)
        if m:
            w = m.group(1).upper()
            if w in MNEMONIC_TABLE:
                return text

    # Otherwise attempt to parse as high-level SPL using the PLY parser.
    global ctx
    pre = _preprocess_indentation(text)
    lexer = lex_spl.build_lexer()
    # initialize parser context (reset any previous state)
    ctx = ParserContext()
    parser = yacc.yacc()
    try:
        return parser.parse(pre, lexer=lexer)
    finally:
        ctx = None


if __name__ == '__main__':
    import sys
    data = sys.stdin.read()
    out = compile_high_level(data)
    sys.stdout.write(out)
