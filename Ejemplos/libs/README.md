# Librerías SPL

Este directorio contiene librerías reutilizables para el lenguaje SPL que pueden ser incluidas usando la directiva `#include` del preprocesador.

## Uso del Preprocesador

El preprocesador de SPL soporta dos directivas principales:

### 1. `#define` - Definición de Macros

Define constantes que serán sustituidas en el código:

```spl
#define MAX_SIZE 100
#define OUTPUT_ADDR 131072

var x
x = MAX_SIZE
M[OUTPUT_ADDR] = x
```

### 2. `#include` - Inclusión de Archivos

Incluye el contenido de otro archivo SPL:

```spl
#include "basicmath.spl"
```

o con llaves angulares:

```spl
#include <basicmath.spl>
```

## Librerías Disponibles

### basicmath.spl

Funciones matemáticas básicas:

#### Función: Euclides (MCD)
Calcula el Máximo Común Divisor de dos números.

**Variables de entrada:**
- `mcd_a`: primer número
- `mcd_b`: segundo número

**Variable de salida:**
- `mcd_result`: el MCD calculado

**Ejemplo de uso:**
```spl
#define NUM1 48
#define NUM2 18

var mcd_a
var mcd_b
var mcd_result

mcd_a = NUM1
mcd_b = NUM2

#include "basicmath.spl"

print("MCD: ", mcd_result)
```

#### Función: Factorial
Calcula el factorial de un número.

**Variables de entrada:**
- `fact_n`: número del cual calcular el factorial

**Variable de salida:**
- `fact_result`: resultado del factorial

**Ejemplo de uso:**
```spl
var fact_n
var fact_result

fact_n = 5
#include "basicmath.spl"

print("5! = ", fact_result)  ; Imprime 120
```

#### Función: Potencia
Calcula base^exponente.

**Variables de entrada:**
- `pow_base`: base
- `pow_exp`: exponente
- `pow_counter`: contador (debe declararse)

**Variable de salida:**
- `pow_result`: resultado de la potencia

**Ejemplo de uso:**
```spl
var pow_base
var pow_exp
var pow_result
var pow_counter

pow_base = 2
pow_exp = 10
#include "basicmath.spl"

print("2^10 = ", pow_result)  ; Imprime 1024
```

### matrices.spl

Funciones para operaciones con matrices:

#### Función: Multiplicación de Matrices
Multiplica dos matrices A * B = C.

**Variables de entrada:**
- `mat_A[filas_A][cols_A]`: matriz A
- `mat_B[filas_B][cols_B]`: matriz B (filas_B debe ser igual a cols_A)
- `filas_A`: número de filas de A
- `cols_A`: número de columnas de A
- `cols_B`: número de columnas de B
- `mat_i`, `mat_j`, `mat_k`, `mat_sum`: variables auxiliares

**Variable de salida:**
- `mat_C[filas_A][cols_B]`: matriz resultado

**Ejemplo de uso:**
```spl
#define ROWS 2
#define COLS 2

var mat_A[2][2]
var mat_B[2][2]
var mat_C[2][2]
var filas_A
var cols_A
var cols_B
var mat_i
var mat_j
var mat_k
var mat_sum

; Inicializar matrices y dimensiones...
filas_A = ROWS
cols_A = COLS
cols_B = COLS

#include "matrices.spl"

; mat_C contiene el resultado
```

#### Función: Suma de Matrices
Suma dos matrices A + B = C.

**Variables requeridas:**
- `mat_A[filas][cols]`, `mat_B[filas][cols]`
- `mat_filas`, `mat_cols`
- `mat_i`, `mat_j`

**Salida:**
- `mat_C[filas][cols]`

#### Función: Transponer Matriz
Calcula la transpuesta de una matriz.

**Variables requeridas:**
- `mat_A[filas][cols]`
- `mat_filas`, `mat_cols`
- `mat_i`, `mat_j`

**Salida:**
- `mat_C[cols][filas]` (transpuesta)

#### Función: Inicializar a Cero
Inicializa una matriz con ceros.

**Variables requeridas:**
- `mat_filas`, `mat_cols`
- `mat_i`, `mat_j`

**Salida:**
- `mat_C[filas][cols]` con todos ceros

## Ejemplos Completos

Ver los archivos en el directorio `Ejemplos/`:

- `test_preprocessor_factorial.spl` - Uso básico con factorial
- `test_preprocessor_euclides.spl` - Cálculo de MCD
- `test_preprocessor_matrices.spl` - Multiplicación de matrices 2x2
- `test_preprocessor_completo.spl` - Uso combinado de múltiples funciones

## Notas Importantes

1. **Variables**: Todas las variables utilizadas por las funciones de las librerías deben ser declaradas en el programa principal antes de incluir la librería.

2. **Nombres de variables**: Las funciones de las librerías usan nombres de variables específicos. Asegúrate de usar exactamente esos nombres.

3. **Orden de ejecución**: El código de las librerías se ejecuta secuencialmente cuando es incluido. Las "funciones" no son llamables, sino que su código se inserta directamente.

4. **Includes múltiples**: Si incluyes la misma librería dos veces, el preprocesador detectará el include duplicado y lo ignorará para evitar código redundante.

5. **Directivas**: Las directivas `#define` e `#include` deben estar al inicio de la línea (pueden tener espacios antes).

## Flujo de Compilación

```
Archivo .spl
    ↓
[PREPROCESADOR] → Expande #define e #include → Archivo .pp
    ↓
[COMPILADOR] → Traduce SPL a ensamblador → Archivo .s
    ↓
[ENSAMBLADOR] → Convierte a código objeto → Archivo .o
    ↓
[ENLAZADOR] → Genera imagen ejecutable → Archivo .i
```

Todos los archivos intermedios se guardan para facilitar la depuración.
