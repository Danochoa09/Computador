from typing import Callable

import numpy as np
from bitarray import bitarray

import constants
from model.procesador.memory import Memory
from utils import NumberConversion as NC


def set_up():
    DataBus.set_up()
    DirectionBus.set_up()
    ControlBus.set_up()


def action():
    # Lee la instrucción de control y ejecuta su acción respectiva
    instruction: bitarray = ControlBus.read()
    call_instruccion(instruction[constants.CONTROL_SIZE-1])


def call_instruccion(instr: int):
    c_operations: dict[int, Callable[[], None]] = {
        ControlBus.READ_MEMORY: ControlBus.Instructions.read_memory,
        ControlBus.WRITE_MEMORY: ControlBus.Instructions.write_memory
    }

    try:
        c_operations[instr]()
    except KeyError:
        raise ValueError(f"Código {instr} no definido para "
                         f"instrucciones de control.")


class DataBus:
    """
    Bus de datos del procesador.
    Almacena la palabra de datos que se está procesando.
    Se usa para transferencia de datos entre memoria y registros.
    """
    array: bitarray = None

    @staticmethod
    def set_up():
        """
        Inicializa el bus de datos con una palabra de ceros.
        Un bit array de tamaño WORDS_SIZE_BITS de ceros.
        Se usa bitarray para optimizar el uso de memoria.
        Se usa endian='big' para que el primer bit sea el más significativo.
        """
        DataBus.array = bitarray(
            '0' * constants.WORDS_SIZE_BITS, endian='big')

    @staticmethod
    def read() -> bitarray:
        """
        Devuelve la palabra almacenada en el bus de datos
        """
        return DataBus.array

    @staticmethod
    def write(word: bitarray) -> None:
        "Escribe una palabra en el bus de datos"
        if len(word) != constants.WORDS_SIZE_BITS:
            raise ValueError(
                f"La palabra debe tener {constants.WORDS_SIZE_BITS} bits.")
        DataBus.array = word.copy()


class DirectionBus:
    """
    Bus de dirección del procesador.
    Almacena la dirección de memoria que se está accediendo.
    """
    array: bitarray = None

    @staticmethod
    def set_up():
        DirectionBus.array = bitarray(
            '0' * constants.MEMORY_BITS, endian='big')

    @staticmethod
    def read() -> bitarray:
        """
        Devuelve la dirección almacenada en el bus de dirección
        """
        return DirectionBus.array

    @staticmethod
    def write(word: bitarray) -> None:
        """
        Escribe una dirección en el bus de dirección
        24 bits
        """
        if len(word) != constants.MEMORY_BITS:
            raise ValueError(
                f"La dirección debe tener {constants.MEMORY_BITS} bits.")
        DirectionBus.array = word.copy()


class ControlBus:
    """
    Bus de control del procesador.
    Almacena la instrucción de control que se está ejecutando.
    """
    array: bitarray = None
    # Comandos en base 10, pasar a binario para hacer correspondencia con
    READ_MEMORY: int = 0
    WRITE_MEMORY: int = 1
    # Comandos en base 2
    READ_MEMORY_BIN: bitarray = NC.natural2bitarray(READ_MEMORY, bits=constants.CONTROL_SIZE)
    WRITE_MEMORY_BIN: bitarray = NC.natural2bitarray(WRITE_MEMORY, bits=constants.CONTROL_SIZE)

    @staticmethod
    def set_up():
        ControlBus.array = bitarray(
            '0' * constants.CONTROL_SIZE, endian='big')

    @staticmethod
    def read() -> bitarray:
        """
        Devuelve la instrucción de control almacenada en el bus de control
        """
        return ControlBus.array

    @staticmethod
    def write(word: bitarray) -> None:
        """
        Escribe una instrucción de control en el bus de control
        """
        if len(word) != constants.CONTROL_SIZE:
            raise ValueError(
                f"La instrucción de control debe tener {constants.CONTROL_SIZE} bits.")
        ControlBus.array = word.copy()

    class Instructions:
        """
        Instrucciones de control del bus.
        Contiene las operaciones que se pueden realizar con el bus de control.
        """
        @staticmethod
        def read_memory():
            """Get bitarray from memory and store it in Data bus"""
            addr = NC.bitarray2natural(DirectionBus.read())
            # If reading from E/S and no input available, signal that input is needed
            try:
                from controller import terminal as _term
                if constants.E_S_RANGE[0] <= addr <= constants.E_S_RANGE[1] and not _term.has_input():
                    raise _term.InputNeeded()
            except Exception as e:
                # If the exception is InputNeeded, re-raise to be handled upstream
                if type(e).__name__ == 'InputNeeded':
                    raise
                # otherwise ignore and continue to read memory normally
                pass
            word: np.uint64 = Memory.read(addr)
            word: bitarray = NC.natural2bitarray(int(word), bits=constants.WORDS_SIZE_BITS)
            DataBus.write(word)

        @staticmethod
        def write_memory():
            """Get bitaray at DataBus and store it in Memory"""
            word: bitarray = DataBus.read().copy()
            address: int = NC.bitarray2natural(DirectionBus.read())

            word: np.uint64 = NC.safe_uint64(NC.bitarray2natural(word))

            Memory.write(address, word)
