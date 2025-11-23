# Índice de Ejemplos YACC - Intérprete SPL

## ✅ Estado: 16/16 ejemplos funcionando

---

## 📂 Categorías

### 🔤 Básicos (Variables y Expresiones)

#### **01_variables_basicas.spl**
- **Descripción**: Declaración y asignación simple de variables
- **Conceptos**: Variables, asignación
- **Resultado**: `x = 10`, `y = 20`, `z = 5`

#### **02_expresiones_aritmeticas.spl**
- **Descripción**: Operaciones aritméticas básicas
- **Conceptos**: +, -, *
- **Resultado**: `s = 8`, `r = 2`, `p = 15`

#### **03_precedencia_operadores.spl**
- **Descripción**: Verificar precedencia de operadores
- **Conceptos**: Orden de evaluación (* antes que +)
- **Resultado**: `resultado1 = 25` (10 + 5 * 3 = 10 + 15)

#### **16_aritmetica_flotante.spl** ✨ NUEVO
- **Descripción**: Soporte completo para números decimales (float)
- **Conceptos**: Literales float (3.14), notación científica (1.5e2), mezcla int/float
- **Operaciones**: Cálculo de área (π), descuentos, conversiones de temperatura
- **Salida**: `78.53975`, `85.0`, `450000000000000.0`, `298.65`

---

### 🖨️ Entrada/Salida

#### **04_print_simple.spl**
- **Descripción**: Uso básico de print con variables
- **Conceptos**: print(), múltiples argumentos
- **Salida**: `10 20 30`

#### **05_print_con_strings.spl**
- **Descripción**: Print combinando strings y variables
- **Conceptos**: print() con texto
- **Salida**: `El resultado es: 42`

---

### 🏗️ TDA (Tipos de Datos Abstractos)

#### **06_tda_punto.spl**
- **Descripción**: Declarar tipo Point y crear instancias
- **Conceptos**: type, instanciación con valores
- **Objetos**: `p1: {x: 10, y: 20}`, `p2: {x: 30, y: 40}`

#### **07_tda_rectangulo.spl**
- **Descripción**: TDA con más campos
- **Conceptos**: TDA con 4 campos
- **Objetos**: `rect: {x: 0, y: 0, ancho: 100, alto: 50}`

#### **08_tda_modificacion_campos.spl**
- **Descripción**: Modificar campos de objetos
- **Conceptos**: Acceso y asignación de campos (p.x = 100)
- **Resultado**: Objeto `p` modificado a `{x: 100, y: 200}`

#### **15_tda_complejo.spl**
- **Descripción**: TDA con múltiples instancias
- **Conceptos**: Múltiples objetos del mismo tipo
- **Objetos**: `juan: {edad: 25, ...}`, `maria: {edad: 30, ...}`

---

### 🧮 Aplicaciones Prácticas

#### **09_calculadora.spl**
- **Descripción**: Calculadora con 3 operaciones
- **Conceptos**: Operaciones sobre variables
- **Salida**: Suma, Resta, Multiplicación

#### **10_contador.spl**
- **Descripción**: Simular un contador incrementando
- **Conceptos**: Auto-referencia (contador = contador + 1)
- **Salida**: Contador: 0, 1, 2, 3

#### **11_fibonacci_manual.spl**
- **Descripción**: Primeros números de Fibonacci manualmente
- **Conceptos**: Secuencia, intercambio de variables
- **Salida**: 0 1 1 2 3 5 8 13 21 34

#### **12_conversion_temperatura.spl**
- **Descripción**: Conversión aproximada de temperatura
- **Conceptos**: Cálculos con constantes
- **Salida**: Celsius: 25, Aprox Fahrenheit: 82

#### **13_area_rectangulo.spl**
- **Descripción**: Calcular área de rectángulo
- **Conceptos**: Fórmula matemática (área = base * altura)
- **Salida**: Area: 50

#### **14_promedio.spl**
- **Descripción**: Sumar varias notas
- **Conceptos**: Suma acumulativa
- **Salida**: Total: 253

---

## 📊 Resumen por Funcionalidad

| Funcionalidad | Ejemplos | Total |
|---------------|----------|-------|
| Variables y asignaciones | 01, 02, 03 | 3 |
| Expresiones aritméticas | 02, 03, 09-14 | 8 |
| Print | 04, 05, 09-14 | 9 |
| TDA - Declaración | 06, 07, 08, 15 | 4 |
| TDA - Instanciación | 06, 07, 08, 15 | 4 |
| TDA - Modificación | 08 | 1 |
| Algoritmos | 10, 11 | 2 |
| Aplicaciones matemáticas | 12, 13, 14 | 3 |

---

## 🎓 Orden Recomendado de Aprendizaje

### Nivel 1: Introducción
1. `01_variables_basicas.spl` - Empezar aquí
2. `04_print_simple.spl` - Ver resultados
3. `05_print_con_strings.spl` - Output con texto

### Nivel 2: Operaciones
4. `02_expresiones_aritmeticas.spl` - Cálculos básicos
5. `03_precedencia_operadores.spl` - Orden de operaciones
6. `13_area_rectangulo.spl` - Aplicación simple

### Nivel 3: TDA
7. `06_tda_punto.spl` - Primer TDA
8. `07_tda_rectangulo.spl` - TDA con más campos
9. `08_tda_modificacion_campos.spl` - Modificar objetos
10. `15_tda_complejo.spl` - Múltiples instancias

### Nivel 4: Algoritmos
11. `10_contador.spl` - Incremento
12. `09_calculadora.spl` - Múltiples operaciones
13. `14_promedio.spl` - Suma acumulativa
14. `11_fibonacci_manual.spl` - Secuencia
15. `12_conversion_temperatura.spl` - Fórmulas

---

## 💡 Notas Importantes

### ✅ Operadores Soportados
- `+` (suma)
- `-` (resta)
- `*` (multiplicación)
- `<`, `>`, `<=`, `>=` (comparaciones)
- `==`, `!=` (igualdad)
- `and`, `or` (lógicos)

### ❌ Limitaciones Conocidas
- **División (`/`)**: No soportada por el lexer SPL
- **Arrays**: No implementados
- **if/while**: Parcialmente implementados
- **Funciones**: No soportadas

### 🔧 Convenciones
- Evitar nombres de variables que coincidan con mnemonics del ensamblador:
  - ❌ `suma`, `resta`, `copia`, `carga`, etc.
  - ✅ `s`, `r`, `total`, `resultado`, etc.

---

## 🚀 Ejecución Rápida

### Método 1: Interfaz Gráfica
```bash
python main.py
# Click "Ejecutar" → Cargar ejemplo → "Ejecutar →"
```

### Método 2: Python Directo
```python
from model.compilador.parser_spl import interpret_high_level
from pathlib import Path

codigo = Path("Ejemplos/yacc/01_variables_basicas.spl").read_text()
ctx = interpret_high_level(codigo)
print(ctx.variables)
```

### Método 3: Test Automático
```bash
python test_ejemplos_yacc.py
```

---

## 📈 Progresión de Complejidad

```
Simple ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Complejo

01 ──→ 04 ──→ 02 ──→ 06 ──→ 10 ──→ 11
      Variables   Aritmética   TDA    Algoritmos
```

---

## 🎯 Ejemplos Destacados

### 🌟 Mejor para Empezar
**01_variables_basicas.spl** - El más simple

### 🌟 Mejor para TDA
**08_tda_modificacion_campos.spl** - Muestra todo sobre TDA

### 🌟 Mejor Algoritmo
**11_fibonacci_manual.spl** - Secuencia completa

### 🌟 Más Práctico
**13_area_rectangulo.spl** - Aplicación real

---

## 📝 Plantilla para Nuevos Ejemplos

```spl
# Tu código aquí
x = 10
y = 20
resultado = x + y
print("Resultado:", resultado)
```

**Recordar**:
- No usar `;` para comentarios (causa errores)
- No usar nombres de instrucciones de ensamblador
- Evitar división `/`
- Cada statement en su propia línea
