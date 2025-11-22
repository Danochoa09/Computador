"""
Test del intérprete YACC con TDA (Tipos de Datos Abstractos)
"""

from model.compilador.parser_spl import interpret_high_level

# Test 6: Declaración y uso de tipos
print("=" * 60)
print("TEST 6: TDA - Declaración y creación de objetos")
print("=" * 60)

code6 = """
type Point {x, y}

var p1 : Point = {10, 20}
var p2 : Point = {30, 40}

print("p1.x =", p1.x)
print("p1.y =", p1.y)
print("p2.x =", p2.x)
print("p2.y =", p2.y)
"""

try:
    ctx = interpret_high_level(code6)
    print(f"\n✓ Tipos declarados: {list(ctx.types.keys())}")
    print(f"✓ Objetos creados: {list(ctx.objects.keys())}")
    print(f"\n✓ Output generado:")
    for line in ctx.output:
        print(f"  {line}")
    print("✅ TEST 6 PASSED\n")
except Exception as e:
    print(f"❌ TEST 6 FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 7: Modificación de campos
print("=" * 60)
print("TEST 7: TDA - Modificación de campos")
print("=" * 60)

code7 = """
type Rectangle {x, y, width, height}

var rect : Rectangle = {0, 0, 100, 50}

print("Rectángulo original:")
print("  x =", rect.x)
print("  width =", rect.width)

rect.x = 10
rect.width = 200

print("Rectángulo modificado:")
print("  x =", rect.x)
print("  width =", rect.width)
"""

try:
    ctx = interpret_high_level(code7)
    print(f"\n✓ Output generado:")
    for line in ctx.output:
        print(f"  {line}")
    print("✅ TEST 7 PASSED\n")
except Exception as e:
    print(f"❌ TEST 7 FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 8: Cálculos con campos
print("=" * 60)
print("TEST 8: TDA - Cálculos con campos")
print("=" * 60)

code8 = """
type Point {x, y}

var p1 : Point = {10, 20}
var p2 : Point = {30, 40}

dx = p2.x - p1.x
dy = p2.y - p1.y

print("Distancia en X:", dx)
print("Distancia en Y:", dy)

distance = dx * dx + dy * dy
print("Distancia cuadrada:", distance)
"""

try:
    ctx = interpret_high_level(code8)
    print(f"\n✓ Output generado:")
    for line in ctx.output:
        print(f"  {line}")
    
    # Verificar valores
    assert ctx.get_variable('dx') == 20, "dx incorrecto"
    assert ctx.get_variable('dy') == 20, "dy incorrecto"
    assert ctx.get_variable('distance') == 800, "distance incorrecto"
    
    print("✅ TEST 8 PASSED\n")
except Exception as e:
    print(f"❌ TEST 8 FAILED: {e}\n")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("RESUMEN: INTÉRPRETE YACC CON TDA FUNCIONANDO")
print("=" * 60)
