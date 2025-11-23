"""
Intérprete YACC para SPL - Ejecuta acciones semánticas directamente
Implementa el metalenguaje de programación siguiendo el paradigma YACC:
- Análisis sintáctico con gramática BNF
- Acciones semánticas que ejecutan el código durante el parsing
- Sin generación de código intermedio (ensamblador)
"""

from typing import Any, Dict, List, Optional
import sys


class InterpreterContext:
    """
    Contexto de ejecución del intérprete YACC.
    Mantiene el estado durante la ejecución de acciones semánticas.
    """
    
    def __init__(self):
        # Memoria de variables: nombre -> valor
        self.variables: Dict[str, Any] = {}
        
        # Tipos definidos: nombre_tipo -> lista de campos
        self.types: Dict[str, List[Dict[str, Any]]] = {}
        
        # Memoria de objetos TDA: variable -> {field: value, ...}
        self.objects: Dict[str, Dict[str, Any]] = {}
        
        # Stack de control para funciones/procedimientos
        self.call_stack: List[Dict[str, Any]] = []
        
        # Output buffer para print statements
        self.output: List[str] = []
        
        # Input buffer para input statements
        self.input_buffer: List[str] = []
        self.input_index: int = 0
        
        # Memoria simulada (arrays, matrices)
        self.memory: Dict[int, Any] = {}
        self.next_mem_addr: int = 0
        
        # Control flow flags
        self.break_flag: bool = False
        self.continue_flag: bool = False
        self.return_flag: bool = False
        self.return_value: Any = None
        
    def allocate_memory(self, size: int) -> int:
        """Asigna un bloque de memoria y retorna la dirección base"""
        base_addr = self.next_mem_addr
        for i in range(size):
            self.memory[base_addr + i] = 0
        self.next_mem_addr += size
        return base_addr
        
    def read_memory(self, addr: int) -> Any:
        """Lee un valor de memoria"""
        if addr not in self.memory:
            self.memory[addr] = 0
        return self.memory[addr]
        
    def write_memory(self, addr: int, value: Any):
        """Escribe un valor en memoria"""
        self.memory[addr] = value
        
    def set_variable(self, name: str, value: Any):
        """Asigna valor a una variable"""
        self.variables[name] = value
        
    def get_variable(self, name: str) -> Any:
        """Obtiene valor de una variable"""
        if name not in self.variables:
            raise NameError(f"Variable '{name}' no definida")
        return self.variables[name]
        
    def declare_type(self, typename: str, fields: List[Dict[str, Any]]):
        """Declara un nuevo tipo (struct/class)"""
        self.types[typename] = fields
        
    def create_object(self, varname: str, typename: str, init_values: Optional[List[Any]] = None):
        """Crea una instancia de un tipo"""
        if typename not in self.types:
            raise TypeError(f"Tipo '{typename}' no definido")
            
        fields = self.types[typename]
        obj = {}
        
        # Inicializar campos
        for i, field_info in enumerate(fields):
            field_name = field_info['name']
            if init_values and i < len(init_values):
                val = init_values[i]
                # Preservar tipo (int o float)
                if isinstance(val, (int, float)):
                    obj[field_name] = val
                else:
                    obj[field_name] = val
            else:
                obj[field_name] = 0  # Valor por defecto
                
        self.objects[varname] = obj
        self.variables[varname] = varname  # Referencia al objeto
        
    def get_field(self, varname: str, fieldname: str) -> Any:
        """Obtiene el valor de un campo de un objeto"""
        if varname not in self.objects:
            raise NameError(f"Objeto '{varname}' no existe")
        obj = self.objects[varname]
        if fieldname not in obj:
            raise AttributeError(f"Campo '{fieldname}' no existe en objeto '{varname}'")
        return obj[fieldname]
        
    def set_field(self, varname: str, fieldname: str, value: Any):
        """Asigna valor a un campo de un objeto"""
        if varname not in self.objects:
            raise NameError(f"Objeto '{varname}' no existe")
        obj = self.objects[varname]
        if fieldname not in obj:
            raise AttributeError(f"Campo '{fieldname}' no existe en objeto '{varname}'")
        obj[fieldname] = value
        
    def print_output(self, value: Any):
        """Agrega un valor al buffer de salida"""
        self.output.append(str(value))
        
    def read_input(self) -> str:
        """Lee una línea del buffer de entrada"""
        if self.input_index >= len(self.input_buffer):
            # Si no hay más input, leer de stdin
            return input()
        value = self.input_buffer[self.input_index]
        self.input_index += 1
        return value
        
    def evaluate_expression(self, expr_ast) -> Any:
        """
        Evalúa un AST de expresión y retorna su valor.
        Las expresiones vienen en formato tuple desde el parser.
        """
        if expr_ast is None:
            return 0
            
        # Número literal directo
        if isinstance(expr_ast, (int, float)):
            return expr_ast
            
        # String literal
        if isinstance(expr_ast, str):
            # Puede ser nombre de variable
            if expr_ast in self.variables:
                return self.variables[expr_ast]
            # O intentar convertir a número
            try:
                # Detectar si es float
                if '.' in expr_ast or 'e' in expr_ast.lower():
                    return float(expr_ast)
                return int(expr_ast)
            except ValueError:
                # Es un string literal
                return expr_ast
            
        # Tupla (AST node)
        if isinstance(expr_ast, tuple):
            if len(expr_ast) == 0:
                return 0
                
            node_type = expr_ast[0]
            
            # Número ('num', value)
            if node_type == 'num' or node_type == 'number':
                val = expr_ast[1]
                # Mantener el tipo original (int o float)
                if isinstance(val, (int, float)):
                    return val
                if isinstance(val, str):
                    # Intentar convertir, detectar si es float
                    if '.' in val or 'e' in val.lower():
                        return float(val)
                    return int(val)
                return 0
                
            # Variable ('name', varname)
            if node_type == 'name':
                varname = expr_ast[1]
                return self.get_variable(varname)
                
            # Operación unaria
            if node_type == 'uminus':
                operand = self.evaluate_expression(expr_ast[1])
                return -operand
                
            # Operación binaria
            if node_type == 'binop':
                op = expr_ast[1]
                left = self.evaluate_expression(expr_ast[2])
                right = self.evaluate_expression(expr_ast[3])
                
                if op == '+':
                    return left + right
                elif op == '-':
                    return left - right
                elif op == '*':
                    return left * right
                elif op == '/':
                    if right == 0:
                        raise ZeroDivisionError("División por cero")
                    return left // right  # División entera
                elif op == '%':
                    return left % right
                elif op == '<':
                    return 1 if left < right else 0
                elif op == '<=':
                    return 1 if left <= right else 0
                elif op == '>':
                    return 1 if left > right else 0
                elif op == '>=':
                    return 1 if left >= right else 0
                elif op == '==':
                    return 1 if left == right else 0
                elif op == '!=':
                    return 1 if left != right else 0
                elif op == 'and':
                    return 1 if (left and right) else 0
                elif op == 'or':
                    return 1 if (left or right) else 0
                else:
                    raise ValueError(f"Operador '{op}' no soportado")
                    
            # Acceso a campo (object.field)
            if node_type == 'field_access':
                varname = expr_ast[1]
                fieldname = expr_ast[2]
                return self.get_field(varname, fieldname)
                
            # Referencia a memoria (memref_label)
            if node_type == 'memref_label':
                varname = expr_ast[1]
                offset = expr_ast[2] if len(expr_ast) > 2 else 0
                return self.get_field(varname, f"field_{offset}") if varname in self.objects else self.get_variable(varname)
                
        return 0
        
    def reset(self):
        """Reinicia el contexto del intérprete"""
        self.variables.clear()
        self.types.clear()
        self.objects.clear()
        self.call_stack.clear()
        self.output.clear()
        self.memory.clear()
        self.next_mem_addr = 0
        self.input_index = 0
        self.break_flag = False
        self.continue_flag = False
        self.return_flag = False
        self.return_value = None


# Instancia global del intérprete
interpreter: Optional[InterpreterContext] = None


def init_interpreter():
    """Inicializa el contexto global del intérprete"""
    global interpreter
    interpreter = InterpreterContext()
    return interpreter


def get_interpreter() -> InterpreterContext:
    """Obtiene la instancia del intérprete"""
    global interpreter
    if interpreter is None:
        interpreter = InterpreterContext()
    return interpreter


def execute_statement(stmt_ast):
    """
    Ejecuta una declaración (statement) del AST.
    Esta función será llamada desde las acciones semánticas del parser.
    """
    ctx = get_interpreter()
    
    if stmt_ast is None:
        return
        
    # String simple (comentarios del compilador original)
    if isinstance(stmt_ast, str):
        # Comentarios o directivas del compilador, ignorar
        return
        
    # Tupla (statement AST)
    if isinstance(stmt_ast, tuple):
        if len(stmt_ast) == 0:
            return
            
        stmt_type = stmt_ast[0]
        
        # Asignación simple: ('assign', varname, expr_ast)
        if stmt_type == 'assign':
            varname = stmt_ast[1]
            expr_ast = stmt_ast[2]
            value = ctx.evaluate_expression(expr_ast)
            ctx.set_variable(varname, value)
            
        # Asignación a campo: ('field_assign', varname, fieldname, expr_ast)
        elif stmt_type == 'field_assign':
            varname = stmt_ast[1]
            fieldname = stmt_ast[2]
            expr_ast = stmt_ast[3]
            value = ctx.evaluate_expression(expr_ast)
            ctx.set_field(varname, fieldname, value)
            
        # Declaración de tipo: ('type_decl', typename, fields)
        elif stmt_type == 'type_decl':
            typename = stmt_ast[1]
            fields = stmt_ast[2]
            ctx.declare_type(typename, fields)
            
        # Declaración de variable con tipo: ('var_decl', varname, typename, init_values)
        elif stmt_type == 'var_decl':
            varname = stmt_ast[1]
            typename = stmt_ast[2]
            init_values = stmt_ast[3] if len(stmt_ast) > 3 else None
            ctx.create_object(varname, typename, init_values)
            
        # If statement: ('if', condition_ast, then_stmts, else_stmts)
        elif stmt_type == 'if':
            condition = ctx.evaluate_expression(stmt_ast[1])
            if condition:
                execute_statements(stmt_ast[2])
            elif len(stmt_ast) > 3 and stmt_ast[3]:
                execute_statements(stmt_ast[3])
                
        # While loop: ('while', condition_ast, body_stmts)
        elif stmt_type == 'while':
            while True:
                condition = ctx.evaluate_expression(stmt_ast[1])
                if not condition:
                    break
                execute_statements(stmt_ast[2])
                if ctx.break_flag:
                    ctx.break_flag = False
                    break
                if ctx.continue_flag:
                    ctx.continue_flag = False
                    continue
                    
        # Print: ('print', expr_ast)
        elif stmt_type == 'print':
            value = ctx.evaluate_expression(stmt_ast[1])
            ctx.print_output(value)
            print(value)  # También imprimir a stdout
            
        # Input: ('input', varname)
        elif stmt_type == 'input':
            varname = stmt_ast[1]
            value = ctx.read_input()
            try:
                if '.' in value or 'e' in value.lower():
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                pass
            ctx.set_variable(varname, value)


def execute_statements(stmts_list):
    """Ejecuta una lista de statements"""
    if stmts_list is None:
        return
        
    if isinstance(stmts_list, list):
        for stmt in stmts_list:
            execute_statement(stmt)
    else:
        execute_statement(stmts_list)


def interpret_program(source_code: str, input_data: Optional[List[str]] = None):
    """
    Interpreta un programa SPL completo.
    
    Args:
        source_code: Código fuente SPL
        input_data: Lista de strings para simular input()
        
    Returns:
        InterpreterContext con el estado final
    """
    ctx = init_interpreter()
    
    if input_data:
        ctx.input_buffer = input_data
        
    # Aquí se integraría con el parser parser_spl.py
    # Por ahora, retornamos el contexto para testing
    return ctx
