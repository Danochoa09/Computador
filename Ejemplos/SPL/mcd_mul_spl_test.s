; Ejemplo: calcular MCD(a,b) usando basicmath.lib y multiplicarlo por un factor
; Incluye la librería relocalizable con #include (será expandida por el preprocesador)

; === BEGIN INCLUDE: libs/basicmath.lib ===
; basicmath.lib - Librería de operaciones matemáticas básicas
; Implementa MCD (Euclides) y Factorial con código relocalizable

; === DEFINICIONES DE CONSTANTES ===

; === RESERVA DE ESPACIO PARA VARIABLES TEMPORALES ===
; Área de trabajo para cálculos matemáticos (relocalizable)
math_temp_a:
.data 0
math_temp_b:
.data 0
math_temp_n:
.data 0
math_temp_result:
.data 0

; === SUBRUTINA: MCD (Algoritmo de Euclides) ===
; Entrada: R4 = a, R5 = b
; Salida: R4 = MCD(a, b)
; Modifica: R4, R5, R6
mcd_start:
    ; Guardar parámetros en variables temporales
    ICARGA R6, math_temp_a
    GUARDIND R4, R6
    ICARGA R6, math_temp_b
    GUARDIND R5, R6

mcd_loop:
    ; Comparar a y b
    COMP R4, R5
    SICERO mcd_end
    
    ; Si a > b
    SIPOS mcd_a_greater
    
    ; Else: b > a, entonces b = b - a
    RESTA R5, R4
    SALTA mcd_loop

mcd_a_greater:
    ; a = a - b
    RESTA R4, R5
    SALTA mcd_loop

mcd_end:
    ; R4 contiene el MCD
    ; Guardar resultado
    ICARGA R6, math_temp_result
    GUARDIND R4, R6
    ; Retornar (en un sistema real sería RET)
    ; Por ahora el resultado queda en R4

; === SUBRUTINA: FACTORIAL ===
; Entrada: R4 = n
; Salida: R4 = n!
; Modifica: R4, R5, R6
factorial_start:
    ; Guardar n
    ICARGA R6, math_temp_n
    GUARDIND R4, R6
    
    ; Inicializar acumulador (a = 1)
    ICARGA R5, 1
    
factorial_loop:
    ; Si n <= 1, terminar
    ICARGA R6, 1
    COMP R4, R6
    SIPOS factorial_continue
    SICERO factorial_end
    ; Si n < 1, también terminar
    SALTA factorial_end

factorial_continue:
    ; a = a * n
    MULT R5, R4
    
    ; n = n - 1
    ICARGA R6, 1
    RESTA R4, R6
    
    ; Continuar loop
    SALTA factorial_loop

factorial_end:
    ; Mover resultado a R4
    COPIA R4, R5
    ; Guardar resultado
    ICARGA R6, math_temp_result
    GUARDIND R4, R6
    ; Retornar (resultado en R4)
; === END INCLUDE: libs/basicmath.lib ===

; Valores de entrada
; Cargar constantes en registros R4 (a) y R5 (b)
ICARGA R4, 48
ICARGA R5, 18

; Llamar a la subrutina MCD definida en basicmath.lib
SALTA mcd_start

; Tras la subrutina, R4 contiene el MCD
; Multiplicar por un factor (5)
ICARGA R6, 5
MULT R4, R6

; Guardar el resultado en la dirección de salida (I/O)
; Usamos la dirección explícita para evitar limitaciones de expansión de macros dentro de M[...] 
GUARD R4, M[131072]

PARA