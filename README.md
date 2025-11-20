Proyecto SPL — Preprocesador, Ensamblador y Enlazador-Cargador
===============================================================

Objetivo
--------
Proveer el análisis, diseño e implementación del sistema SPL (Preprocesador, Ensamblador y Enlazador-Cargador) que produzca código binario compatible con el simulador de computador en este repositorio.

Entregables
-----------
- Documentación (vocabulario, categorías léxicas y patrones regex).
- Plantillas (esqueletos) FLEX (.l) para el preprocesador y el ensamblador.
- Esqueleto de enlazador-cargador en Python (`tools/linker.py`) que combina objetos y genera un archivo de carga que el simulador puede leer.
- Instrucciones para compilar/usar las herramientas con `lex.py` en Python.

Resumen del flujo
-----------------
1. El programador escribe un archivo fuente SPL (.spl), que contiene instrucciones de alto nivel (estructuras imperativas), macros y declaraciones de datos.
2. El PREPROCESADOR (FLEX) realiza: inclusión de archivos, sustitución de macros, eliminación de comentarios y producción de un archivo `.s` (ensamblador) intermedio.
3. El ENSAMBLADOR (FLEX) transforma el `.s` en código objeto: secuencia de instrucciones codificadas en el formato binario de la ISA y tablas de relocación/símbolos. Produce un archivo `.o` (formato textual simple de objeto, ver `tools/linker.py`).
4. El ENLAZADOR-CARGADOR (script Python) combina múltiples `.o`, aplica relocaciones, resuelve símbolos externos y genera un archivo de carga (texto binario listo para ser cargado por el simulador o un `memory.dump`).

Formato de objeto sencillo propuesto
-----------------------------------
Usaremos un formato textual legible que el enlazador pueda procesar. Ejemplo:

-- header
ENTRY: main
SEGMENT: CODE,SIZE=128,BASE=0
SEGMENT: DATA, SIZE=64, BASE=0
-- symbols
SYM: main,5,local
SYM: foo,25,external
-- code
INST: 000000... (64 bits)
INST: 000111... (64 bits)
-- reloc
RELOC: 3, TYPE=ABS, SYMBOL=foo

Este formato permite almacenar: tabla de símbolos, segmento de código, relocaciones y datos inicializados.

Vocabulario y categorías léxicas
--------------------------------
Ver `doc/SPL_vocabulary.md` (archivo generado en `doc/`) para el vocabulario completo, categorías léxicas y patrones regex propuestos.

Plantillas FLEX
---------------
En `tools/` encontrarás dos ficheros de ejemplo:
- `spl_preprocessor.l` - plantilla FLEX para preprocesador (manejo de includes y macros).
- `assembler.l` - plantilla FLEX para el ensamblador (tokenización del lenguaje de ensamblador intermedio y acciones que imprimen el código objeto en formato textual simple).

Enlazador-Cargador (esqueleto)
-----------------------------
`tools/linker.py` implementa: lectura de archivos `.o`, construcción de tabla de símbolos global, aplicación de relocaciones y escritura de un fichero de carga (binario textual que el simulador puede cargar con `Action.load_machine_code`).

Cómo usar (resumen)
-------------------
- Para usar el preprocesador y ensamblador con flex:
  1. `flex spl_preprocessor.l` → `lex.yy.c`  
  2. `gcc lex.yy.c -lfl -o preproc`  
  3. `./preproc < input.spl > out.s`  

- Para ensamblar:
  1. `flex assembler.l` → `lex.yy.c`  
  2. `gcc lex.yy.c -lfl -o assembler`  
  3. `./assembler < out.s > file.o`  

- Para enlazar y cargar:
  1. `python tools/linker.py file1.o file2.o -o image.bin`  
  2. Abrir el simulador y usar la opción "Cargar a Memoria" con la dirección deseada (o extender `Action` para leer `image.bin` directamente).

Instalación y uso rápido (Python/Ply)
------------------------------------

1. Instala dependencias del proyecto (incluye `ply`):

```powershell
python -m pip install -r requirements.txt
```

2. Convertir un archivo SPL de alto nivel a imagen binaria (desde Python):

```python
from tools.flex_pipeline import pipeline_from_text
txt = open('Ejemplos/SPL/euclides_high.spl').read()
insts, image_path = pipeline_from_text(txt)
print('Imagen escrita en', image_path)
```

3. Usar la GUI: ejecutar `view/interfaz.py` (lanzará Tkinter). En el panel "Código Binario" pega el contenido `.s` o el SPL de alto nivel y pulsa "Convertir"; luego rellena "Dirección de carga (hex)" y pulsa "Cargar a Memoria".

4. Prueba rápida E2E (sin pytest):

```powershell
cd "c:\Users\danoc\OneDrive\Escritorio\FLOW UNAL\Lenguajes\Computador"
python -c "import sys; sys.path.insert(0, r'c:\\Users\\danoc\\OneDrive\\Escritorio\\FLOW UNAL\\Lenguajes\\Computador'); from tools.tests.test_euclides_pipeline import test_euclides_pipeline_creates_guard; test_euclides_pipeline_creates_guard(); print('OK')"
```

