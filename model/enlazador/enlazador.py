import numpy as np
from bitarray import bitarray

import constants
from utils import NumberConversion as NC
from model.procesador import bus

class Enlazador:
    # Código de máquina donde cada línea está separada por un \n
    MACHINE_CODE_RELOC: list[str] = None

    @staticmethod
    def set_machine_code(machine_code_reloc: str):
        """
        Guarda el machine code, como código de máquina relocalizable.
        Las instrucciones deben estar separadas por saltos de línea (\n).

        :param machine_code_reloc: Cadena con instrucciones en código máquina separadas por \n.
        """

        if not isinstance(machine_code_reloc, str):
            raise TypeError("El código de máquina debe ser una cadena (str).")

        machine_code_reloc_lines: list[str] = machine_code_reloc.strip().split('\n')
        if (len(machine_code_reloc_lines) < 1 or
                any(not line.strip()
                    for line in machine_code_reloc_lines)):
            raise ValueError(
                "La cadena debe contener líneas "
                "separadas por '\\n', sin líneas vacías."
            )

        Enlazador.MACHINE_CODE_RELOC = machine_code_reloc_lines

    @staticmethod
    def link_load_machine_code(address: int):
        """
        Carga el código de máquina relocalizable
        en la posición:
        :param address: número natural de 0 a 65535
        """
        if not (0 <= address <= constants.CODE_RANGE[1]):
            raise ValueError(
                f"Dirección {address} inválida para "
                f"el área del código"
            )

        lines = Enlazador.MACHINE_CODE_RELOC

        # Quick bounds check: ensure the whole image fits in the code area
        image_len = len(lines)
        if address + image_len - 1 > constants.CODE_RANGE[1]:
            raise ValueError(
                f"El código no cabe en el área de código: "
                f"direcciones {address}..{address+image_len-1} exceden {constants.CODE_RANGE[1]}"
            )

        # Detect leading zero-words in the image to warn about .data placed before code
        zero_word = '0' * constants.WORDS_SIZE_BITS
        leading_zeros = 0
        for ln in lines:
            if ln == zero_word:
                leading_zeros += 1
            else:
                break
        if leading_zeros > 0:
            # leading zeros detected; no debug printing in production
            pass

        for idx, code_line in enumerate(lines):
            # Crear conteo de bits para verificar que sea de tamaño WORD
            bits_count = 0
            # Contar 0 y 1
            bits_count += code_line.count('0') + code_line.count('1')

            # Reemplazar {natural} si existe
            if '{' in code_line and '}' in code_line:
                # Obtener el número en llaves
                start = code_line.find('{') + 1
                end = code_line.find('}')
                natural_str = code_line[start:end]

                # Verificar que es natural
                try:
                    natural_val = int(natural_str)
                    if natural_val < 0:
                        raise ValueError()
                except ValueError:
                    raise ValueError(f"Línea {idx}: "
                                     f"valor no "
                                     f"numérico natural en {{...}}: '{natural_str}'")

                direccion_relocalizada = natural_val + address
                # 24 bits con ceros a la izquierda
                direccion_bin: str = (
                    format(direccion_relocalizada, '024b'))

                # Reemplazar la subcadena completa "{...}" por el binario
                code_line: str = code_line.replace(
                    f'{{{natural_str}}}', direccion_bin)

                # Contar bits del nuevo binario insertado
                bits_count += len(direccion_bin)

                # Verificar que la instrucción sea del tamaño de WORD
                if bits_count != constants.WORDS_SIZE_BITS:
                    raise ValueError(f"Instrucción {idx} no tiene 64 bits")

            instruction_bin: bitarray = bitarray(code_line)

            # Cargar la instrucción en memoria
            target_addr = address + idx
            bus.DirectionBus.write(NC.natural2bitarray(target_addr, 24))
            bus.ControlBus.write(bus.ControlBus.WRITE_MEMORY_BIN)
            bus.DataBus.write(instruction_bin)
            bus.action()

        # Summary print for debugging large images
        first_nonzero = next((i for i, l in enumerate(lines) if l != zero_word), None)
          # load summary (suppressed debug print)