# Ejemplos YACC - Intérprete SPL

Esta carpeta contiene ejemplos para probar el **Intérprete YACC** del lenguaje SPL.

## 🚀 Cómo Usar

### Opción 1: Desde la Interfaz Gráfica
1. Ejecutar `python main.py`
2. Click en el botón **"Ejecutar"**
3. En la ventana que se abre, click en **"Cargar"**
4. Seleccionar uno de los archivos `.spl` de esta carpeta
5. Click en **"Ejecutar →"**
6. Ver los resultados a la derecha

### Opción 2: Desde Python
```python
from model.compilador.parser_spl import interpret_high_level
from pathlib import Path

# Cargar y ejecutar ejemplo
codigo = Path("Ejemplos/yacc/01_variables_basicas.spl").read_text()
ctx = interpret_high_level(codigo)

# Ver resultados
print("Variables:", ctx.variables)
print("Objetos:", ctx.objects)
print("Salida:", ctx.output)
```

## 📚 Lista de Ejemplos

### Básicos (1-5)
- **01_variables_basicas.spl** - Declaración simple de variables
- **02_expresiones_aritmeticas.spl** - Operaciones +, -, *, /
- **03_precedencia_operadores.spl** - Orden de operaciones
- **04_print_simple.spl** - Uso básico de print
- **05_print_con_strings.spl** - Print con texto y variables

### TDA - Tipos de Datos Abstractos (6-8, 15)
- **06_tda_punto.spl** - Tipo Point con coordenadas x, y
- **07_tda_rectangulo.spl** - Tipo Rectangle con 4 campos
- **08_tda_modificacion_campos.spl** - Modificar campos de objetos
- **15_tda_complejo.spl** - TDA Persona con múltiples instancias

### Aplicaciones (9-14)
- **09_calculadora.spl** - Calculadora con 4 operaciones
- **10_contador.spl** - Incrementar una variable
- **11_fibonacci_manual.spl** - Primeros números de Fibonacci
- **12_conversion_temperatura.spl** - Celsius a Fahrenheit
- **13_area_rectangulo.spl** - Calcular área
- **14_promedio.spl** - Promedio de 3 números

## ✅ Funcionalidades Demostradas

| Funcionalidad | Ejemplos |
|---------------|----------|
| Asignaciones | 01, 02, 03, 09-14 |
| Expresiones aritméticas | 02, 03, 09-14 |
| Precedencia de operadores | 03 |
| Print | 04, 05, 09-14 |
| TDA - Declaración | 06, 07, 15 |
| TDA - Instanciación | 06, 07, 08, 15 |
| TDA - Modificación | 08 |
| Cálculos complejos | 09-14 |

## 🎯 Resultados Esperados

Cada archivo `.spl` incluye en los comentarios:
- **Descripción**: Qué hace el ejemplo
- **Resultado esperado**: Variables que se crearán con sus valores
- **Salida esperada**: Lo que debería mostrar `print()`

## ⚠️ Limitaciones Conocidas

El intérprete YACC actualmente **NO soporta**:
- `if/else` (parcialmente implementado)
- `while` loops (parcialmente implementado)
- Arrays
- Funciones/procedimientos
- Input interactivo

## 🔧 Testing

Para ejecutar todos los ejemplos automáticamente:
```bash
python test_ejemplos_yacc.py
```

## 📖 Documentación

Para más información sobre el intérprete YACC, ver:
- `docs/METALENGUAJE_YACC_IMPLEMENTADO.txt`
- `docs/SISTEMA_DUAL_COMPILADOR_INTERPRETE.txt`

## 🆘 Solución de Problemas

**Problema**: Syntax error al ejecutar
- **Solución**: Verificar que el código no use `if/while` complejos o arrays

**Problema**: Variables no aparecen
- **Solución**: Verificar que las asignaciones estén en líneas separadas

**Problema**: Print no muestra nada
- **Solución**: Revisar la sección "Salida (print)" en la ventana de resultados
