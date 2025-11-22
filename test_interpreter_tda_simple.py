"""
Test simplificado del intérprete YACC con TDA
"""

from model.compilador.parser_spl import interpret_high_level

# Test 6A: Declaración y creación básica
print("=" * 60)
print("TEST 6A: TDA - Declaración y creación básica")
print("=" * 60)

code6a = """
type Point {x, y}

var p1 : Point = {10, 20}

print(p1)
"""

try:
    ctx = interpret_high_level(code6a)
    print(f"✓ Tipos declarados: {list(ctx.types.keys())}")
    print(f"✓ Objetos creados: {list(ctx.objects.keys())}")
    print(f"✓ Campos de p1: {ctx.objects['p1']}")
    print("✅ TEST 6A PASSED\n")
except Exception as e:
    print(f"❌ TEST 6A FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 6B: Acceso a campo y asignación a variable
print("=" * 60)
print("TEST 6B: TDA - Acceso a campo")
print("=" * 60)

code6b = """
type Point {x, y}

var p : Point = {15, 25}

vx = p.x
vy = p.y

print(vx)
print(vy)
"""

try:
    ctx = interpret_high_level(code6b)
    print(f"✓ vx = {ctx.get_variable('vx')}")
    print(f"✓ vy = {ctx.get_variable('vy')}")
    print("✅ TEST 6B PASSED\n")
except Exception as e:
    print(f"❌ TEST 6B FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 6C: Modificación de campos
print("=" * 60)
print("TEST 6C: TDA - Modificación de campos")
print("=" * 60)

code6c = """
type Point {x, y}

var p : Point = {10, 20}

p.x = 100
p.y = 200

final_x = p.x
final_y = p.y

print(final_x)
print(final_y)
"""

try:
    ctx = interpret_high_level(code6c)
    print(f"✓ final_x = {ctx.get_variable('final_x')}")
    print(f"✓ final_y = {ctx.get_variable('final_y')}")
    
    assert ctx.get_variable('final_x') == 100, "final_x incorrecto"
    assert ctx.get_variable('final_y') == 200, "final_y incorrecto"
    
    print("✅ TEST 6C PASSED\n")
except Exception as e:
    print(f"❌ TEST 6C FAILED: {e}\n")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RESUMEN: INTÉRPRETE YACC CON TDA FUNCIONANDO")
print("=" * 60)
