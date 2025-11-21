"""
Preprocesador para SPL y ensamblador
Soporta directivas:
- #define NOMBRE valor  : Define una macro de sustitución
- #include "archivo"   : Incluye el contenido de otro archivo
"""

import re
from pathlib import Path
from typing import Dict, Set


class PreprocessorError(Exception):
    """Error durante el preprocesamiento"""
    pass


def preprocess(source_text: str, source_file: Path = None) -> str:
    """
    Procesa el texto fuente expandiendo macros y procesando includes.
    
    Args:
        source_text: El código fuente a preprocesar
        source_file: Path del archivo fuente (necesario para resolver includes relativos)
        
    Returns:
        El texto preprocesado con todas las macros expandidas e includes insertados
    """
    defines: Dict[str, str] = {}
    included_files: Set[Path] = set()
    
    if source_file:
        source_dir = source_file.parent
    else:
        # Fallback: buscar directorio de librerías relativo al módulo
        source_dir = Path(__file__).resolve().parent.parent.parent / 'Ejemplos' / 'libs'
    
    def process_text(text: str, current_file: Path = None) -> str:
        """Procesa recursivamente el texto, manejando defines e includes"""
        lines = text.splitlines()
        result_lines = []
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Procesar #define
            if stripped.startswith('#define'):
                match = re.match(r'#define\s+(\w+)\s+(.*)', stripped)
                if match:
                    macro_name = match.group(1)
                    macro_value = match.group(2).strip()
                    defines[macro_name] = macro_value
                    # Agregar línea comentada para traceabilidad
                    result_lines.append(f'# #define {macro_name} {macro_value}')
                else:
                    raise PreprocessorError(
                        f"Sintaxis inválida en #define en línea {line_num}: {line}"
                    )
                continue
            
            # Procesar #include
            if stripped.startswith('#include'):
                match = re.match(r'#include\s+"([^"]+)"', stripped)
                if not match:
                    match = re.match(r'#include\s+<([^>]+)>', stripped)
                
                if match:
                    include_filename = match.group(1)
                    
                    # Resolver la ruta del archivo a incluir
                    if current_file:
                        include_path = current_file.parent / include_filename
                    else:
                        include_path = source_dir / include_filename
                    
                    # Buscar también en directorio de librerías si no se encuentra
                    if not include_path.exists():
                        libs_dir = Path(__file__).resolve().parent.parent.parent / 'Ejemplos' / 'libs'
                        include_path = libs_dir / include_filename
                    
                    # Normalizar path para evitar includes circulares
                    include_path = include_path.resolve()
                    
                    if not include_path.exists():
                        raise PreprocessorError(
                            f"No se encontró el archivo incluido '{include_filename}' "
                            f"(buscado en: {include_path})"
                        )
                    
                    # Evitar includes circulares
                    if include_path in included_files:
                        result_lines.append(f'# #include "{include_filename}" (ya incluido)')
                        continue
                    
                    included_files.add(include_path)
                    
                    # Leer y procesar el archivo incluido
                    try:
                        included_text = include_path.read_text(encoding='utf-8')
                        result_lines.append(f'# BEGIN #include "{include_filename}"')
                        processed_include = process_text(included_text, include_path)
                        result_lines.extend(processed_include.splitlines())
                        result_lines.append(f'# END #include "{include_filename}"')
                    except Exception as e:
                        raise PreprocessorError(
                            f"Error al procesar archivo incluido '{include_filename}': {e}"
                        )
                else:
                    raise PreprocessorError(
                        f"Sintaxis inválida en #include en línea {line_num}: {line}\n"
                        f"Use: #include \"archivo.spl\" o #include <archivo.spl>"
                    )
                continue
            
            # Expandir macros en la línea actual
            expanded_line = line
            for macro_name, macro_value in defines.items():
                # Usar word boundaries para evitar reemplazos parciales
                # Por ejemplo, NUM1 no debe reemplazarse en NUM10
                pattern = r'\b' + re.escape(macro_name) + r'\b'
                expanded_line = re.sub(pattern, macro_value, expanded_line)
            
            result_lines.append(expanded_line)
        
        return '\n'.join(result_lines)
    
    return process_text(source_text, source_file)


def preprocess_file(file_path: Path) -> str:
    """
    Lee y preprocesa un archivo completo.
    
    Args:
        file_path: Ruta al archivo a preprocesar
        
    Returns:
        El contenido preprocesado
    """
    source_text = file_path.read_text(encoding='utf-8')
    return preprocess(source_text, file_path)


if __name__ == '__main__':
    # Prueba simple del preprocesador
    test_code = """
#define MAX 100
#define MIN 10

var x
x = MAX
if x > MIN:
    print("x es mayor que MIN")
end
"""
    result = preprocess(test_code)
    print("=== CÓDIGO PREPROCESADO ===")
    print(result)
