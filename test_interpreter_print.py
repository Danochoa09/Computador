"""
Test del intérprete YACC con print
"""

from model.compilador.parser_spl import interpret_high_level

# Test 4: Print de variables
print("=" * 60)
print("TEST 4: Print de variables")
print("=" * 60)

code4 = """
x = 42
y = 100
print(x)
print(y)
print(x, y)
"""

try:
    ctx = interpret_high_level(code4)
    print(f"\n✓ Output generado:")
    for line in ctx.output:
        print(f"  {line}")
    print("✅ TEST 4 PASSED\n")
except Exception as e:
    print(f"❌ TEST 4 FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 5: Cálculos y print
print("=" * 60)
print("TEST 5: Cálculos con print")
print("=" * 60)

code5 = """
a = 10
b = 5
total = a + b
print("El resultado es:", total)
"""

try:
    ctx = interpret_high_level(code5)
    print(f"\n✓ Output generado:")
    for line in ctx.output:
        print(f"  {line}")
    print("✅ TEST 5 PASSED\n")
except Exception as e:
    print(f"❌ TEST 5 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
