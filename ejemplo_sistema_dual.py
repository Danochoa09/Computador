"""
Ejemplo de uso del Sistema Dual: Compilador + Intérprete

Este script muestra cómo usar ambos modos desde código Python.
"""

print("="*70)
print("EJEMPLO: SISTEMA DUAL - COMPILADOR + INTÉRPRETE YACC")
print("="*70)

# ============================================================================
# EJEMPLO 1: Usando el COMPILADOR
# ============================================================================
print("\n" + "─"*70)
print("EJEMPLO 1: MODO COMPILADOR")
print("Flujo: SPL → Parser → Ensamblador → Binario → CPU")
print("─"*70)

from model.compilador.parser_spl import compile_high_level

codigo_spl = """
x = 10
y = 20
total = x + y
"""

print("\nCódigo SPL:")
print(codigo_spl)

asm = compile_high_level(codigo_spl)
print("\nCódigo Ensamblador Generado:")
print(asm[:200] + "..." if len(asm) > 200 else asm)

print("\n→ Este código ahora puede ser ensamblado y cargado en el CPU simulado")

# ============================================================================
# EJEMPLO 2: Usando el INTÉRPRETE
# ============================================================================
print("\n" + "─"*70)
print("EJEMPLO 2: MODO INTÉRPRETE")
print("Flujo: SPL → Parser + Acciones Semánticas → Resultado Directo")
print("─"*70)

from model.compilador.parser_spl import interpret_high_level

codigo_spl = """
x = 10
y = 20
total = x + y
print(total)
"""

print("\nCódigo SPL:")
print(codigo_spl)

ctx = interpret_high_level(codigo_spl)

print("\nResultados:")
print(f"  Variables: {ctx.variables}")
print(f"  Salida: {ctx.output}")

print("\n→ Ejecución instantánea, sin compilar!")

# ============================================================================
# EJEMPLO 3: TDA con Intérprete
# ============================================================================
print("\n" + "─"*70)
print("EJEMPLO 3: TDA EN MODO INTÉRPRETE")
print("─"*70)

tda_code = """
type Point {x, y}
var p : Point = {100, 200}
"""

print("\nCódigo SPL:")
print(tda_code)

ctx = interpret_high_level(tda_code)

print("\nResultados:")
print(f"  Variables: {ctx.variables}")
print(f"  Tipos declarados: {list(ctx.types.keys())}")
print(f"  Objetos creados: {list(ctx.objects.keys())}")
for obj_name, fields in ctx.objects.items():
    print(f"    {obj_name}: {fields}")

# ============================================================================
# COMPARACIÓN
# ============================================================================
print("\n" + "="*70)
print("COMPARACIÓN DE MODOS")
print("="*70)

print("""
┌───────────────────────┬─────────────────────┬──────────────────────┐
│ Característica        │ Compilador          │ Intérprete           │
├───────────────────────┼─────────────────────┼──────────────────────┤
│ Velocidad desarrollo  │ Lenta               │ Rápida               │
│ Pasos necesarios      │ 4                   │ 1                    │
│ Salida intermedia     │ Sí (ASM, BIN)       │ No                   │
│ Debugging             │ Difícil             │ Fácil                │
│ Simula CPU            │ Sí                  │ No                   │
│ Variables accesibles  │ En memoria CPU      │ En diccionario       │
│ Uso recomendado       │ Testing completo    │ Desarrollo rápido    │
└───────────────────────┴─────────────────────┴──────────────────────┘
""")

print("\n" + "="*70)
print("CONCLUSIÓN")
print("="*70)
print("""
✅ Ambos modos están COMPLETAMENTE FUNCIONALES
✅ Se pueden usar desde la interfaz gráfica o desde Python
✅ No hay interferencia entre modos

Para usar desde interfaz:
  - Click "Ventana de Compilación" → Flujo tradicional
  - Click "Ejecutar" → Flujo interpretado directo
""")
print("="*70)
