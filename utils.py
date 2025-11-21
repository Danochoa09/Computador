import csv
import json
import struct
import numpy as np
from bitarray import bitarray
from openpyxl import Workbook
from typing import Optional, Dict, Any

import constants


class NumberConversion:
    @staticmethod
    def safe_uint64(n: int) -> np.uint64:
        if not isinstance(n, int):
            raise TypeError("Se espera un entero.")
        if not (0 <= n <= (1 << 64) - 1):
            raise ValueError("El número no cabe en 64 bits sin signo.")
        return np.uint64(n)

    @staticmethod
    def bitarray2natural(bitarr: bitarray) -> int:
        """Bitarray a número natural"""
        return int(bitarr.to01(), 2)

    @staticmethod
    def natural2bitarray(natural: int, bits: int = None, truncate: bool = False) -> bitarray:
        """Número natural a bitarray"""
        if natural < 0:
            raise ValueError(f"El número ingresado {natural} no es un número natural")
        if bits is None:
            bits = natural.bit_length()

        if natural >= (1 << bits):
            if truncate:
                natural = natural % (1 << bits)  # Truncar: quedarse con los `bits` menos significativos
            else:
                raise ValueError(f"El número natural {natural} no cabe en {bits} bits.")

        natural_bin: bitarray = bitarray(format(natural, f'0{bits}b'))
        return natural_bin

    @staticmethod
    def bitarray2int(bitarr: bitarray) -> int:
        """Bitarray a entero"""
        if bitarr[0] == 0:
            return int(bitarr.to01(), 2)
        else:
            return int(bitarr[1:].to01(), 2) - (1 << len(bitarr) - 1)

    @staticmethod
    def int2bitarray(num_int: int, bits: int = None, truncate: bool = False) -> bitarray:
        """
        Entero a bit array (Complemento a 2)
        Convierte un entero con signo a bitarray en complemento a dos de `bits` bits.
        Si `truncate=True`, trunca el número a los `bits` menos significativos.
        """
        if bits is None:
            # Determinar automáticamente el mínimo de bits necesarios
            if num_int >= 0:
                bits = num_int.bit_length() + 1  # +1 para el bit de signo
            else:
                bits = (-num_int).bit_length() + 1  # también para negativo

        min_val = -(1 << (bits - 1))
        max_val = (1 << (bits - 1)) - 1

        if not (min_val <= num_int <= max_val):
            if truncate:
                # Truncamos bits menos significativos del C2
                unsigned = (1 << bits) + num_int if num_int < 0 else num_int
                unsigned %= (1 << bits)
            else:
                raise ValueError(f"{num_int} no cabe en {bits} bits (C2).")
        else:
            unsigned = (1 << bits) + num_int if num_int < 0 else num_int

        bitstr = format(unsigned, f'0{bits}b')
        return bitarray(bitstr)

    @staticmethod
    def binary_list2str(binary_list: bitarray) -> str:
        return "".join(str(bit) for bit in binary_list)

    @staticmethod
    def str2binary_list(binary_str: str) -> list[int]:
        if not all(c in ('0', '1') for c in binary_str):
            raise ValueError(
                "La cadena debe contener solo "
                "caracteres '0' o '1'."
            )
        return [int(bit) for bit in binary_str]

    @staticmethod
    def binary_list2entero(binary_list: list[int]) -> int:
        """
        Convierte una lista de bits (0 y 1) en su valor decimal
        usando complemento a dos.
        """
        if not binary_list:
            raise ValueError("La lista de bits no puede estar vacía.")

        if not all(isinstance(b, int) and b in (0, 1) for b in binary_list):
            raise ValueError("Todos los elementos deben ser enteros 0 o 1.")

        bit_string = ''.join(str(b) for b in binary_list)
        n_bits = len(binary_list)

        # Análisis del complemento a 2
        if binary_list[0] == 1:
            # Complemento a 2
            return int(bit_string, 2) - (1 << n_bits)  # 2^n_bits para obtener negativo
        else:
            return int(bit_string, 2)

    @staticmethod
    def entero2binary_list(
            n: int, fix_bits: Optional[int] = constants.WORDS_SIZE_BITS
    ) -> list[int]:
        """
        Convierte un número decimal (positivo o negativo) a una
        lista de bits en complemento a dos.
        """
        if not isinstance(n, int):
            raise ValueError("El número debe ser un entero.")

        # Si se especifican bits fijos, verificar si el número cabe en complemento a 2
        if fix_bits is not None:
            if not isinstance(fix_bits, int) or fix_bits <= 0:
                raise ValueError("fix_bits debe ser un entero positivo.")
            # Toma el menor valor decimal con 2^(fix_bits - 1) bits
            min_val = - (1 << (fix_bits - 1))
            # Toma el mayor valor decimal con 2^(fix_bits - 1) bits -1 por el cero
            max_val = (1 << (fix_bits - 1)) - 1
            if not (min_val <= n <= max_val):
                raise ValueError(f"El número {n} no se puede representar "
                                 f"con {fix_bits} bits en complemento a 2.")
            bits = fix_bits
        else:
            # Calcular bits mínimos necesarios para representar el número en complemento a 2
            if n >= 0:
                bits = n.bit_length() + 1  # +1 para el bit de signo
            else:
                bits = (-n).bit_length() + 1

        if n >= 0:
            bin_str = bin(n)[2:].zfill(bits)
        else:
            # complemento a dos de `n` negativo
            bin_str = bin((1 << bits) + n)[2:]

        return [int(bit) for bit in bin_str.zfill(bits)]

    @staticmethod
    def binary_list2natural(binary_list: list[int]) -> int:
        """
        Sin complemento a 2
        """
        binary_list = [0] + binary_list
        return NumberConversion.binary_list2entero(binary_list)

    @staticmethod
    def natural2binary_list(
            n: int, fix_bits: Optional[int] = constants.WORDS_SIZE_BITS
    ) -> list[int]:
        """
        Sin complemento a 2
        """
        if n < 0:
            raise ValueError("No se admiten valores negativos")

        if fix_bits:
            bin_list: list[int] = NumberConversion.entero2binary_list(
                n, fix_bits + 1)
        else:
            bin_list: list[int] = NumberConversion.entero2binary_list(n, None)
        # Le quito el signo
        if len(bin_list) > 1:
            bin_list = bin_list[1:]
        return bin_list

    @staticmethod
    def double2binary_list(value: float) -> list[int]:
        """
        Convierte un número de punto flotante (IEEE 754 doble precisión)
        a una lista de 64 bits (enteros 0 o 1).
        """
        if not isinstance(value, float):
            raise ValueError("El valor debe ser un "
                             "número de punto flotante (float).")

        # Empaquetar en formato IEEE 754 de doble precisión y convertir a bits
        # big-endian double, byte mas significativo primero
        packed = struct.pack('>d', value)
        bits = ''.join(f'{byte:08b}' for byte in packed)
        return [int(b) for b in bits]

    @staticmethod
    def binary_list2double(binary_list: list[int]) -> float:
        """
        Convierte una lista de 64 bits (enteros 0 o 1) en un número flotante
        usando el estándar IEEE 754 de doble precisión.
        """
        if len(binary_list) != 64:
            raise ValueError("La lista debe contener exactamente 64 bits.")

        if not all(b in (0, 1) for b in binary_list):
            raise ValueError("Todos los elementos deben ser 0 o 1.")

        bit_string = ''.join(str(b) for b in binary_list)
        byte_data = int(bit_string, 2).to_bytes(8, byteorder='big')
        return struct.unpack('>d', byte_data)[0]

    @staticmethod
    def truncate_bitarray_ls(bin_num: bitarray, bits: int) -> bitarray:
        """
        Truncate bin_num to the less significant given bits.
        Not In Place
        """
        if all(bit == 0 for bit in bin_num[:len(bin_num) - bits]):
            bin_num_truncated = bin_num[len(bin_num) - bits:].copy()
            return bin_num_truncated
        else:
            raise ValueError("Los 40 bits más significativos no son todos ceros")

    @staticmethod
    def extend_bitarray(num_bin: bitarray, bits_total: int) -> bitarray:
        """
        Extend bitarray with bits_total bits.
        Not In Place.
        """
        # Calcular cuántos ceros hay que agregar
        missing = bits_total - len(num_bin)

        # Agregar ceros a la izquierda
        num_bin_ext: bitarray = (bitarray('0' * missing) + num_bin).copy()
        return num_bin_ext


def check_address_operation(operator: str, direccion: int) -> bool:
    operators = {
        "C": constants.CODE_RANGE,
        "ES": constants.E_S_RANGE,
        "D": constants.DATA_RANGE,
        "S": constants.STACK_RANGE,
    }
    if operator in operators:
        range = operators[operator]
    else:
        raise ValueError("Operador invalido")

    return range[0] <= direccion <= range[1]


class Math:

    @staticmethod
    def build_huffman_with_lengths(lengths: list[int]) -> list[list[int]]:
        """
        List of binary numbers of size len(lengths) where
        the length of code at i is the specified at lengths[i]
        """
        codes = []
        current_code = 0
        current_length = lengths[0]
        for length in lengths:
            # Si el nuevo length es mayor que el anterior, se
            # le agregan ceros a la derecha
            # (<<= es desplazamiento a la izquierda).
            current_code <<= (length - current_length)
            code = format(current_code, f'0{length}b')
            codes.append(code)
            current_code += 1
            current_length = length

        codes_bin_list = []
        for code in codes:
            code_bin = [0 if l == '0' else 1 for l in code]
            codes_bin_list.append(code_bin)
        return codes_bin_list

    @staticmethod
    def huffman_set(lenghts_quan: list[tuple]) -> dict[int, list[list[int]]]:
        """
        lenghts_quan: [(length, quantity), ....]
        """
        lenghts_quan = sorted(lenghts_quan, key=lambda x: x[0])

        lengths_sep = []
        for length, quantity in lenghts_quan:
            for i in range(quantity):
                lengths_sep.append(length)

        codes_bin_list = Math.build_huffman_with_lengths(lengths_sep)

        codes_bin_grouped = {}
        for code_bin in codes_bin_list:
            index = len(code_bin)
            if index in codes_bin_grouped:
                codes_bin_grouped[index].append(code_bin)
            else:
                codes_bin_grouped[index] = [code_bin]

        return codes_bin_grouped


class FileManager:
    class JSON:
        @staticmethod
        def dict2JSON(path_JSON: str, data: Dict):
            if ".json" not in path_JSON:
                path_JSON += ".json"
            with open(path_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

        @staticmethod
        def JSON2dict(path_JSON: str) -> Dict[str, Any]:
            if not path_JSON.endswith(".json"):
                path_JSON += ".json"

            with open(path_JSON, "r", encoding="utf-8") as f:
                return json.load(f)

    class CSV:

        @staticmethod
        def list_to_csv(data: list[str], filename: str):
            """
            Guarda una lista de strings en un archivo .csv, una cadena por fila.

            :param data: Lista de cadenas.
            :param filename: Nombre del archivo (puede incluir .csv o no).
            """
            if not filename.endswith(".csv"):
                filename += ".csv"

            with open(filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                for line in data:
                    writer.writerow([line])

    class Excel:

        @staticmethod
        def list_to_xlsx(data: list[str], filename: str, title: str = "Datos"):
            """
            Guarda una lista de strings en un archivo .xlsx,
            una cadena por fila (una por celda en la columna A).

            :param data: Lista de cadenas.
            :param filename: Nombre del archivo (puede incluir .xlsx o no).
            """
            if not filename.endswith(".xlsx"):
                filename += ".xlsx"

            wb = Workbook()
            ws = wb.active
            ws.title = title

            for i, line in enumerate(data, start=1):
                ws.cell(row=i, column=1, value=line)

            wb.save(filename)


    class TXT:
        @staticmethod
        def read_file_as_str(path: str) -> str:
            """
            Lee el contenido completo de un archivo como una única cadena de texto.

            :param path: Ruta del archivo, como ( .in)
            :return: Contenido del archivo como string
            """
            with open(path, "r", encoding="utf-8") as f:
                contenido = f.read()
            return contenido