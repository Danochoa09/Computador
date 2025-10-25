import numpy as np
from bitarray import bitarray

import utils
from utils import NumberConversion as NC
from model.procesador.memory import Memory

codigo_modulo = "ES"


def leer_dispositivo(direccion: int) -> bitarray:
    if utils.check_address_operation(codigo_modulo, direccion):
        word_uint: np.uint64 = Memory.read(direccion)
        word: bitarray = NC.natural2bitarray(int(word_uint), bits=64)
        return word
    else:
        raise Exception("La dirección para E/S no esta en el rango válido")


def escribir_dispositivo(direccion: int, word: bitarray):
    if utils.check_address_operation(codigo_modulo, direccion):
        word_uint: np.uint64 = np.uint64(NC.bitarray2natural(word))
        Memory.write(direccion, word_uint)
    else:
        raise Exception("La dirección para E/S no esta en el rango válido")
