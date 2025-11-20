"""
PLY-based parser/preprocessor for a small SPL subset.
Handles a minimal indentation-aware subset (assignments, while, if, mem loads/stores)
and emits equivalent assembly. Moved from tools/ to model/compilador with imports
adapted to model packages.
"""
from __future__ import annotations

from typing import List
import ply.lex as lex
import ply.yacc as yacc
from . import lex_spl
from .spl_to_asm import compile_euclides
from model.ensamblador.assembler_from_as import MNEMONIC_TABLE
import re


class ParserContext:
    def __init__(self, reg_start: int = 4, reg_end: int = 15):
        self.reg_start = reg_start
        self.reg_end = reg_end
        self.next_reg = reg_start
        self.var_map = {}
        self.temp_count = 0
        self.label_count = 0

    def reg_for(self, var: str) -> int:
        if var in self.var_map:
            return self.var_map[var]
        if self.next_reg > self.reg_end:
            self.next_reg = self.reg_start
        r = self.next_reg
        self.var_map[var] = r
        self.next_reg += 1
        return r

    def new_temp(self) -> int:
        if self.next_reg > self.reg_end:
            self.next_reg = self.reg_start
        r = self.next_reg
        self.next_reg += 1
        self.temp_count += 1
        return r

    def new_label(self, prefix: str = 'L') -> str:
        self.label_count += 1
        return f"{prefix}_{self.label_count}"


ctx: ParserContext | None = None

# Type system: map type name -> ordered list of field names
type_table: dict = {}
# Data section lines collected during parsing (.data and labels)
_data_section: list = []
# Array dimension registry: name -> list of dimensions (e.g. [rows] or [rows,cols])
array_dims: dict = {}


def _mk_name(n):
    return ('name', n)


def _mk_num(v):
    return ('num', v)


def _gen_cmp_asm(ast, true_label, end_label):
    _, left, op, right = ast
    lines = []
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
    lines.append(f"SALTA {end_label}")
    return '\n'.join(lines)


def generate_cond_asm(ast, true_label, end_label):
    kind = ast[0]
    if kind == 'cmp':
        return _gen_cmp_asm(ast, true_label, end_label)
    if kind == 'and':
        left, right = ast[1], ast[2]
        mid = ctx.new_label('and_mid')
        s1 = generate_cond_asm(left, mid, end_label)
        s2 = generate_cond_asm(right, true_label, end_label)
        return s1 + '\n' + f"{mid}:\n" + s2
    if kind == 'or':
        left, right = ast[1], ast[2]
        cont = ctx.new_label('or_cont')
        s1 = generate_cond_asm(left, true_label, cont)
        s2 = generate_cond_asm(right, true_label, end_label)
        return s1 + '\n' + f"{cont}:\n" + s2
    if kind == 'not':
        inner = ast[1]
        return generate_cond_asm(inner, end_label, true_label)
    raise ValueError(f"Unknown cond AST kind: {kind}")


def _preprocess_indentation(text: str) -> str:
    out_lines: List[str] = []
    indent_stack = [0]
    prev_stripped = ''
    for raw in text.splitlines():
        if not raw.strip():
            out_lines.append(raw)
            continue
        leading = len(raw) - len(raw.lstrip(' '))
        next_stripped = raw.lstrip().lower()
        if leading > indent_stack[-1]:
            indent_stack.append(leading)
            if not prev_stripped.startswith('begin'):
                out_lines.append('BEGIN')
        skip_one_end = raw.lstrip().lower().startswith('end')
        while leading < indent_stack[-1]:
            indent_stack.pop()
            if skip_one_end:
                skip_one_end = False
                continue
            out_lines.append('END')
        out_lines.append(raw.lstrip())
        prev_stripped = next_stripped
    while len(indent_stack) > 1:
        indent_stack.pop()
        out_lines.append('END')
    return '\n'.join(out_lines)


tokens = lex_spl.tokens + ('BEGIN', 'END')

precedence = (
    ('left', 'OR_SYM', 'OR'),
    ('left', 'AND_SYM', 'AND'),
    ('left', 'EQEQ', 'NE'),
    ('left', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES'),
    ('right', 'UMINUS', 'NOT'),
)


def generate_expr_asm(ast, target_reg: int) -> list:
    lines = []
    kind = ast[0]
    if kind == 'num':
        lines.append(f"ICARGA R{target_reg} {ast[1]}")
        return lines
    if kind == 'name':
        src_reg = ctx.reg_for(ast[1])
        if src_reg != target_reg:
            lines.append(f"COPIA R{target_reg}, R{src_reg}")
        return lines
    if kind == 'memref':
        addr = ast[1]
        lines.append(f"CARGA R{target_reg}, M[{addr}]")
        return lines
    if kind == 'memref_label':
        label = ast[1]
        offset = ast[2]
        lines.append(f"CARGA R{target_reg}, M[{label}+{offset}]")
        return lines
    if kind == 'memref_indirect':
        # ast = ('memref_indirect', name, offset_ast)
        name = ast[1]
        offset_ast = ast[2]
        # compute offset into a temp
        off_temp = ctx.new_temp()
        lines.extend(generate_expr_asm(offset_ast, off_temp))
        # load base address label into a temp
        base_temp = ctx.new_temp()
        lines.append(f"ICARGA R{base_temp} {name}")
        # add offset to base
        lines.append(f"SUMA R{base_temp}, R{off_temp}")
        # indirect load into target register
        lines.append(f"CARGAIND R{target_reg} R{base_temp}")
        return lines
    if kind == 'input':
        es_addr = __import__('constants').E_S_RANGE[0]
        lines.append(f"CARGA R{target_reg}, M[{es_addr}]")
        return lines
    if kind == 'uminus':
        inner = ast[1]
        lines.extend(generate_expr_asm(inner, target_reg))
        temp = ctx.new_temp()
        lines.append(f"ICARGA R{temp} -1")
        lines.append(f"MULT R{target_reg}, R{temp}")
        return lines
    if kind == 'binop':
        op = ast[1]
        left = ast[2]
        right = ast[3]
        lines.extend(generate_expr_asm(left, target_reg))
        temp = ctx.new_temp()
        lines.extend(generate_expr_asm(right, temp))
        if op == '+':
            lines.append(f"SUMA R{target_reg}, R{temp}")
        elif op == '-':
            lines.append(f"RESTA R{target_reg}, R{temp}")
        elif op == '*':
            lines.append(f"MULT R{target_reg}, R{temp}")
        else:
            raise SyntaxError(f"Unsupported binary op in expression: {op}")
        return lines
    raise SyntaxError(f"Unknown expr AST node: {ast}")


def p_program(p):
    'program : stmts'
    p[0] = '\n'.join(p[1])


def p_stmts_multiple(p):
    'stmts : stmt stmts'
    p[0] = [p[1]] + p[2]


def p_stmts_empty(p):
    'stmts : '
    p[0] = []


def p_stmt_assignment_memload(p):
    'stmt : NAME EQUALS MEMREF'
    var = p[1]
    addr = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    p[0] = f"CARGA R{reg}, M[{addr}]"


def p_stmt_assignment_memstore(p):
    'stmt : MEMREF EQUALS NAME'
    addr = p[1]
    var = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    p[0] = f"GUARD R{reg}, M[{addr}]"


def p_stmt_assignment_number(p):
    'stmt : NAME EQUALS NUMBER'
    var = p[1]
    val = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg = ctx.reg_for(var)
    p[0] = f"ICARGA R{reg} {val}"


def p_stmt_assignment_name(p):
    'stmt : NAME EQUALS NAME'
    dst = p[1]
    src = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    reg_src = ctx.reg_for(src)
    p[0] = f"COPIA R{reg_dst}, R{reg_src}"



def p_stmt_assignment_expr(p):
    'stmt : NAME EQUALS expr'
    dst = p[1]
    ast = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    lines = generate_expr_asm(ast, reg_dst)
    p[0] = '\n'.join(lines)


def p_stmt_assignment_expr_assignop(p):
    'stmt : NAME ASSIGN_OP expr'
    dst = p[1]
    ast = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    reg_dst = ctx.reg_for(dst)
    lines = generate_expr_asm(ast, reg_dst)
    p[0] = '\n'.join(lines)


def p_stmt_register_assign(p):
    'stmt : REGISTER EQUALS expr'
    reg = p[1]
    ast = p[3]
    if reg == 0:
        raise SyntaxError('Assignment to R0 is not allowed')
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    lines = generate_expr_asm(ast, reg)
    p[0] = '\n'.join(lines)


def p_stmt_register_assign_op(p):
    'stmt : REGISTER ASSIGN_OP expr'
    reg = p[1]
    ast = p[3]
    if reg == 0:
        raise SyntaxError('Assignment to R0 is not allowed')
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    lines = generate_expr_asm(ast, reg)
    p[0] = '\n'.join(lines)


def p_expr_binop(p):
    'expr : expr PLUS expr'
    p[0] = ('binop', '+', p[1], p[3])


def p_expr_binop_sub(p):
    'expr : expr MINUS expr'
    p[0] = ('binop', '-', p[1], p[3])


def p_expr_binop_mul(p):
    'expr : expr TIMES expr'
    p[0] = ('binop', '*', p[1], p[3])


def p_expr_uminus(p):
    'expr : MINUS expr %prec UMINUS'
    p[0] = ('uminus', p[2])


def p_expr_group(p):
    'expr : LPAREN expr RPAREN'
    p[0] = p[2]


def p_expr_number(p):
    'expr : NUMBER'
    p[0] = ('num', p[1])


def p_expr_name(p):
    'expr : NAME'
    p[0] = ('name', p[1])


def p_expr_memref(p):
    'expr : MEMREF'
    p[0] = ('memref', p[1])


def p_expr_array_access_const(p):
    'expr : NAME LBRACKET NUMBER RBRACKET'
    name = p[1]
    idx = p[3]
    p[0] = ('memref_label', name, idx)


def p_expr_array_access_const_2d(p):
    'expr : NAME LBRACKET NUMBER RBRACKET LBRACKET NUMBER RBRACKET'
    name = p[1]
    i = int(p[3])
    j = int(p[6])
    # require declaration with dimensions
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    if j < 0 or j >= cols or i < 0 or i >= rows:
        # allow out-of-range but keep computed offset
        pass
    offset = i * cols + j
    p[0] = ('memref_label', name, offset)


def p_expr_array_access(p):
    'expr : NAME LBRACKET expr RBRACKET'
    name = p[1]
    offset_ast = p[3]
    # produce an indirect memref AST: base label + runtime offset
    p[0] = ('memref_indirect', name, offset_ast)


def p_expr_array_access_2d(p):
    'expr : NAME LBRACKET expr RBRACKET LBRACKET expr RBRACKET'
    name = p[1]
    i_ast = p[3]
    j_ast = p[6]
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    # offset = i * cols + j
    offset_ast = ('binop', '+', ('binop', '*', i_ast, ('num', cols)), j_ast)
    p[0] = ('memref_indirect', name, offset_ast)


def p_stmt_array_assign_const(p):
    'stmt : NAME LBRACKET NUMBER RBRACKET EQUALS expr'
    name = p[1]
    idx = p[3]
    ast = p[6]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    temp = ctx.new_temp()
    lines = generate_expr_asm(ast, temp)
    lines.append(f"GUARD R{temp}, M[{name}+{idx}]")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_const_2d(p):
    'stmt : NAME LBRACKET NUMBER RBRACKET LBRACKET NUMBER RBRACKET EQUALS expr'
    name = p[1]
    i = int(p[3])
    j = int(p[6])
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    offset = i * cols + j
    ast = p[9]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    temp = ctx.new_temp()
    lines = generate_expr_asm(ast, temp)
    lines.append(f"GUARD R{temp}, M[{name}+{offset}]")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_expr(p):
    'stmt : NAME LBRACKET expr RBRACKET EQUALS expr'
    name = p[1]
    offset_ast = p[3]
    ast = p[6]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    # compute value into a temp
    val_temp = ctx.new_temp()
    lines = generate_expr_asm(ast, val_temp)
    # compute offset into temp
    off_temp = ctx.new_temp()
    lines.extend(generate_expr_asm(offset_ast, off_temp))
    # load base address label into a temp and add offset
    base_temp = ctx.new_temp()
    lines.append(f"ICARGA R{base_temp} {name}")
    lines.append(f"SUMA R{base_temp}, R{off_temp}")
    # store value into memory at address in base_temp
    lines.append(f"GUARDIND R{val_temp} R{base_temp}")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_expr_2d(p):
    'stmt : NAME LBRACKET expr RBRACKET LBRACKET expr RBRACKET EQUALS expr'
    name = p[1]
    i_ast = p[3]
    j_ast = p[6]
    ast = p[9]
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    # value
    val_temp = ctx.new_temp()
    lines = generate_expr_asm(ast, val_temp)
    # offset = i * cols + j
    off_ast = ('binop', '+', ('binop', '*', i_ast, ('num', cols)), j_ast)
    off_temp = ctx.new_temp()
    lines.extend(generate_expr_asm(off_ast, off_temp))
    base_temp = ctx.new_temp()
    lines.append(f"ICARGA R{base_temp} {name}")
    lines.append(f"SUMA R{base_temp}, R{off_temp}")
    lines.append(f"GUARDIND R{val_temp} R{base_temp}")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_expr_assignop(p):
    'stmt : NAME LBRACKET expr RBRACKET ASSIGN_OP expr'
    name = p[1]
    offset_ast = p[3]
    ast = p[6]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    val_temp = ctx.new_temp()
    lines = generate_expr_asm(ast, val_temp)
    off_temp = ctx.new_temp()
    lines.extend(generate_expr_asm(offset_ast, off_temp))
    base_temp = ctx.new_temp()
    lines.append(f"ICARGA R{base_temp} {name}")
    lines.append(f"SUMA R{base_temp}, R{off_temp}")
    lines.append(f"GUARDIND R{val_temp} R{base_temp}")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_expr_assignop_2d(p):
    'stmt : NAME LBRACKET expr RBRACKET LBRACKET expr RBRACKET ASSIGN_OP expr'
    name = p[1]
    i_ast = p[3]
    j_ast = p[6]
    ast = p[9]
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    val_temp = ctx.new_temp()
    lines = generate_expr_asm(ast, val_temp)
    off_ast = ('binop', '+', ('binop', '*', i_ast, ('num', cols)), j_ast)
    off_temp = ctx.new_temp()
    lines.extend(generate_expr_asm(off_ast, off_temp))
    base_temp = ctx.new_temp()
    lines.append(f"ICARGA R{base_temp} {name}")
    lines.append(f"SUMA R{base_temp}, R{off_temp}")
    lines.append(f"GUARDIND R{val_temp} R{base_temp}")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_const_assignop(p):
    'stmt : NAME LBRACKET NUMBER RBRACKET ASSIGN_OP expr'
    name = p[1]
    idx = p[3]
    ast = p[6]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    temp = ctx.new_temp()
    lines = generate_expr_asm(ast, temp)
    lines.append(f"GUARD R{temp}, M[{name}+{idx}]")
    p[0] = '\n'.join(lines)


def p_stmt_array_assign_const_assignop_2d(p):
    'stmt : NAME LBRACKET NUMBER RBRACKET LBRACKET NUMBER RBRACKET ASSIGN_OP expr'
    name = p[1]
    i = int(p[3])
    j = int(p[6])
    dims = array_dims.get(name)
    if not dims or len(dims) < 2:
        raise SyntaxError(f"Array '{name}' used with two indices but not declared as 2-D")
    rows, cols = dims[0], dims[1]
    offset = i * cols + j
    ast = p[10]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    temp = ctx.new_temp()
    lines = generate_expr_asm(ast, temp)
    lines.append(f"GUARD R{temp}, M[{name}+{offset}]")
    p[0] = '\n'.join(lines)


def p_stmt_type_decl(p):
    'stmt : TYPE NAME LBRACE fields RBRACE'
    typename = p[2]
    fields = p[4]
    type_table[typename] = list(fields)
    p[0] = f"; TYPE {typename} with fields {fields}"


def p_fields_single(p):
    'fields : NAME'
    p[0] = [p[1]]


def p_fields_multiple(p):
    'fields : NAME COMMA fields'
    p[0] = [p[1]] + p[3]


def p_stmt_var_typed(p):
    'stmt : VAR NAME COLON NAME'
    varname = p[2]
    typename = p[4]
    if typename not in type_table:
        raise SyntaxError(f"Unknown type '{typename}' for variable {varname}")
    fields = type_table[typename]
    size = len(fields)
    data_vals = ' '.join(['0'] * size)
    _data_section.append(f"{varname}:")
    _data_section.append(f".data {data_vals}")
    p[0] = f"; VAR {varname} : {typename} -> {size} words"


def p_stmt_field_assign(p):
    'stmt : NAME DOT NAME EQUALS expr'
    var = p[1]
    field = p[3]
    ast = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    # Find field offset in declared types
    for tname, fields in type_table.items():
        if field in fields:
            offset = fields.index(field)
            temp = ctx.new_temp()
            lines = generate_expr_asm(ast, temp)
            lines.append(f"GUARD R{temp}, M[{var}+{offset}]")
            p[0] = '\n'.join(lines)
            return
    raise SyntaxError(f"Unknown field '{field}' for variable {var}")


def p_stmt_field_assign_assignop(p):
    'stmt : NAME DOT NAME ASSIGN_OP expr'
    var = p[1]
    field = p[3]
    ast = p[5]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    for tname, fields in type_table.items():
        if field in fields:
            offset = fields.index(field)
            temp = ctx.new_temp()
            lines = generate_expr_asm(ast, temp)
            lines.append(f"GUARD R{temp}, M[{var}+{offset}]")
            p[0] = '\n'.join(lines)
            return
    raise SyntaxError(f"Unknown field '{field}' for variable {var}")


def p_expr_field_access(p):
    'expr : NAME DOT NAME'
    var = p[1]
    field = p[3]
    # Find field in known types
    for tname, fields in type_table.items():
        if field in fields:
            offset = fields.index(field)
            p[0] = ('memref_label', var, offset)
            return
    raise SyntaxError(f"Unknown field '{field}' for variable {var}")


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


def p_stmt_print(p):
    'stmt : PRINT LPAREN print_args RPAREN'
    # print_args is a list of items (STRING or expr). We will emit
    # code that sends each item to E/S (strings as 8-byte chunks, exprs
    # evaluated into a register), and finally send a newline so the
    # whole print call ends in a single line.
    items = p[3]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    es_addr = __import__('constants').E_S_RANGE[0]
    lines = []

    def emit_string_no_nl(s: str):
        # emit string bytes as 8-byte little-endian chunks without adding newline
        bfull = s.encode('utf-8')
        for i in range(0, len(bfull), 8):
            chunk = bfull[i:i+8].ljust(8, b'\x00')
            val = int.from_bytes(chunk, 'little')
            lbl = ctx.new_label('str')
            _data_section.append(f"{lbl}:")
            _data_section.append(f".data {val}")
            r = ctx.new_temp()
            lines.append(f"CARGA R{r}, M[{lbl}]")
            lines.append(f"GUARD R{r}, M[{es_addr}]")

    for it in items:
        kind = it[0]
        if kind == 'string':
            s = it[1]
            if s:
                emit_string_no_nl(s)
        elif kind == 'expr':
            ast = it[1]
            r = ctx.new_temp()
            lines.extend(generate_expr_asm(ast, r))
            lines.append(f"GUARD R{r}, M[{es_addr}]")
        else:
            raise SyntaxError(f"Unknown print item kind: {kind}")

    # Finally, append a newline character
    nl_lbl = ctx.new_label('str')
    _data_section.append(f"{nl_lbl}:")
    _data_section.append(f".data {ord('\n')}")
    tmp = ctx.new_temp()
    lines.append(f"CARGA R{tmp}, M[{nl_lbl}]")
    lines.append(f"GUARD R{tmp}, M[{es_addr}]")
    p[0] = '\n'.join(lines)


def p_print_args_single(p):
    'print_args : print_arg'
    p[0] = [p[1]]


def p_print_args_multiple(p):
    'print_args : print_arg COMMA print_args'
    p[0] = [p[1]] + p[3]


def p_print_arg_string(p):
    'print_arg : STRING'
    p[0] = ('string', p[1])


def p_print_arg_expr(p):
    'print_arg : expr'
    p[0] = ('expr', p[1])


def p_expr_input(p):
    'expr : INPUT LPAREN RPAREN'
    # Represent input as a special AST node; when used in assignment it will
    # be compiled to a load from the ES address
    p[0] = ('input',)


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
    out.append(f"SICERO {end_label}")
    out.append(f"SIPOS {end_label}")
    out.extend(p[7])
    out.append(f"SALTA {loop_label}")
    out.append(f"{end_label}:")
    p[0] = '\n'.join(out)


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


def p_stmt_var_decl(p):
    'stmt : VAR NAME'
    p[0] = ''


def p_stmt_array_decl(p):
    'stmt : VAR NAME LBRACKET NUMBER RBRACKET'
    name = p[2]
    size = p[4]
    zeros = ' '.join(['0'] * int(size))
    # register as 1-D array
    array_dims[name] = [int(size)]
    p[0] = f"{name}:\n.data {zeros}"


def p_stmt_array_decl_2d(p):
    'stmt : VAR NAME LBRACKET NUMBER RBRACKET LBRACKET NUMBER RBRACKET'
    name = p[2]
    r = int(p[4])
    c = int(p[7])
    size = r * c
    zeros = ' '.join(['0'] * int(size))
    # register as 2-D array with dimensions [rows, cols]
    array_dims[name] = [r, c]
    p[0] = f"{name}:\n.data {zeros}"


def p_stmt_proc_def(p):
    'stmt : PROC NAME LPAREN params RPAREN COLON BEGIN stmts END'
    name = p[2]
    body = p[8]
    out = []
    out.append(f"{name}:")
    out.extend(body)
    if not out or not out[-1].strip().upper().startswith('VUELVE'):
        out.append('VUELVE')
    p[0] = '\n'.join(out)


def p_params(p):
    'params : '
    p[0] = []


def p_params_list(p):
    'params : NAME'
    p[0] = [p[1]]


def p_params_more(p):
    'params : NAME COMMA params'
    p[0] = [p[1]] + p[3]


def p_stmt_call(p):
    'stmt : CALL NAME LPAREN args RPAREN'
    name = p[2]
    args = p[4]
    if ctx is None:
        raise RuntimeError("Parser context not initialized")
    out = []
    for i, a in enumerate(args):
        targ = ctx.reg_start + i
        out.extend(generate_expr_asm(a, targ))
    out.append(f"LLAMA {name}")
    p[0] = '\n'.join(out)


def p_args(p):
    'args : '
    p[0] = []


def p_args_expr(p):
    'args : expr'
    p[0] = [p[1]]


def p_args_more(p):
    'args : expr COMMA args'
    p[0] = [p[1]] + p[3]


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


def p_stmt_asm(p):
    'stmt : NAME asm_args'
    parts = [p[1]] + p[2]
    p[0] = ' '.join(str(x) for x in parts if x is not None)


def p_asm_args_empty(p):
    'asm_args : '
    p[0] = []


def p_asm_args_more(p):
    'asm_args : asm_arg asm_args'
    p[0] = [p[1]] + p[2]


def p_asm_arg_register(p):
    'asm_arg : REGISTER'
    p[0] = f'R{p[1]}'


def p_asm_arg_number(p):
    'asm_arg : NUMBER'
    p[0] = str(p[1])


def p_asm_arg_memref(p):
    'asm_arg : MEMREF'
    p[0] = f'M[{p[1]}]'


def p_asm_arg_name(p):
    'asm_arg : NAME'
    p[0] = p[1]


def p_asm_arg_punct(p):
    'asm_arg : COMMA'
    p[0] = ','


def p_error(p):
    if p:
        raise SyntaxError(f"Syntax error at token {p.type} ({p.value}) line {p.lineno}")
    else:
        raise SyntaxError("Syntax error at EOF")


def compile_high_level(text: str) -> str:
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

    global ctx
    pre = _preprocess_indentation(text)
    # Reset type and data section state for this compilation
    type_table.clear()
    _data_section.clear()
    lexer = lex_spl.build_lexer()
    ctx = ParserContext()
    import sys
    module = sys.modules.get(__name__)
    if module is None:
        import inspect
        module = inspect.getmodule(inspect.currentframe())
    parser = yacc.yacc(module=module)
    try:
        result = parser.parse(pre, lexer=lexer)
        # If data section was populated, append it after the generated assembly
        if _data_section:
            data_text = '\n'.join(_data_section) + '\n'
            if result:
                # Ensure the program ends with an explicit PARA before data
                # so execution stops and doesn't fall through into data words.
                last_nonempty = None
                for ln in reversed(result.splitlines()):
                    if ln.strip():
                        last_nonempty = ln.strip()
                        break
                if last_nonempty is None or last_nonempty.upper() != 'PARA':
                    result = result + '\nPARA'
                return result + '\n' + data_text
            else:
                return data_text
        return result
    finally:
        ctx = None


if __name__ == '__main__':
    import sys
    data = sys.stdin.read()
    out = compile_high_level(data)
    if out is not None:
        sys.stdout.write(out)
    sys.stdout.write(out)
