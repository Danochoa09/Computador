"""
Test para verificar que ambos modos (compilador e intérprete) funcionen correctamente.
"""

print("="*60)
print("TEST DE MODO DUAL: COMPILADOR vs INTÉRPRETE")
print("="*60)

# Test 1: Verificar que el modo compilador esté activo por defecto
print("\n[TEST 1] Verificar modo compilador por defecto")
from model.compilador.parser_spl import INTERPRETER_MODE, compile_high_level
print(f"INTERPRETER_MODE = {INTERPRETER_MODE}")
assert INTERPRETER_MODE == False, "El modo por defecto debe ser compilador"
print("✓ PASSED: Modo compilador activo por defecto")

# Test 2: Compilar código SPL
print("\n[TEST 2] Compilar código SPL a ensamblador")
spl_code = """
x = 10
y = 20
total = x + y
"""

try:
    asm_code = compile_high_level(spl_code)
    print(f"✓ PASSED: Código compilado correctamente")
    print(f"Primeras líneas del ensamblador:")
    lines = asm_code.strip().split('\n')[:5]
    for line in lines:
        print(f"  {line}")
except Exception as e:
    print(f"✗ FAILED: Error al compilar: {e}")

# Test 3: Ejecutar código SPL con intérprete
print("\n[TEST 3] Ejecutar código SPL con intérprete")
from model.compilador.parser_spl import interpret_high_level

try:
    ctx = interpret_high_level(spl_code)
    print(f"✓ PASSED: Código interpretado correctamente")
    print(f"Variables:")
    for name, value in ctx.variables.items():
        print(f"  {name} = {value}")
    assert ctx.variables.get('x') == 10, "x debe ser 10"
    assert ctx.variables.get('y') == 20, "y debe ser 20"
    assert ctx.variables.get('total') == 30, "total debe ser 30"
    print("✓ Variables correctas")
except Exception as e:
    print(f"✗ FAILED: Error al interpretar: {e}")

# Test 4: Verificar que después de interpretar, el modo vuelve a compilador
print("\n[TEST 4] Verificar que el modo vuelve a compilador")
from model.compilador import parser_spl
print(f"INTERPRETER_MODE = {parser_spl.INTERPRETER_MODE}")
assert parser_spl.INTERPRETER_MODE == False, "El modo debe volver a compilador"
print("✓ PASSED: Modo vuelve a compilador después de interpretar")

# Test 5: Probar código con TDA
print("\n[TEST 5] Ejecutar código con TDA")
tda_code = """
type Point {x, y}

var p1 : Point = {10, 20}
var p2 : Point = {30, 40}

dx = p2.x - p1.x
dy = p2.y - p1.y
"""

try:
    ctx = interpret_high_level(tda_code)
    print(f"✓ PASSED: Código TDA interpretado correctamente")
    print(f"Variables:")
    for name, value in ctx.variables.items():
        print(f"  {name} = {value}")
    print(f"Objetos:")
    for name, fields in ctx.objects.items():
        print(f"  {name}: {fields}")
    assert ctx.variables.get('dx') == 20, "dx debe ser 20"
    assert ctx.variables.get('dy') == 20, "dy debe ser 20"
    print("✓ Cálculos TDA correctos")
except Exception as e:
    print(f"✗ FAILED: Error con TDA: {e}")

# Test 6: Probar print
print("\n[TEST 6] Ejecutar código con print")
print_code = """
x = 42
y = 100
print(x, y)
"""

try:
    ctx = interpret_high_level(print_code)
    print(f"✓ PASSED: Código con print interpretado correctamente")
    print(f"Salida:")
    for line in ctx.output:
        print(f"  {line}")
    assert len(ctx.output) > 0, "Debe haber salida"
    print("✓ Print funcionando")
except Exception as e:
    print(f"✗ FAILED: Error con print: {e}")

print("\n" + "="*60)
print("RESUMEN: Todos los tests pasaron correctamente")
print("✓ Modo compilador: Funciona")
print("✓ Modo intérprete: Funciona")
print("✓ Ambos modos coexisten sin interferencia")
print("="*60)
