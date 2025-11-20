
import constants
import numpy as np

class Memory:
    """
    Clase que representa la memoria del procesador.
    Almacena un array de palabras de tamaño WORDS_SIZE_BITS.
    Cada palabra es una lista de bits (0 o 1).
    La memoria tiene un tamaño de MEMORY_SIZE palabras.
    """
    array: np.ndarray[np.uint64] = None
    # Direcciones de memoria que fueron escritas
    memory_changed = []

    @staticmethod
    def set_up():
        """
        Inicializa la memoria con un array de ceros.
        Cada palabra tiene WORDS_SIZE_BITS bits.
        La memoria tiene MEMORY_SIZE palabras.
        """
        Memory.array = np.zeros(
            constants.MEMORY_SIZE, dtype=np.uint64)

    @staticmethod
    def read(direction: int) -> np.uint64:
        """
        Devuelve la palabra almacenada en una dirección.
        :param direction: Dirección de memoria a leer.
        :return: Palabra almacenada en la dirección.
        """
        if not (0 <= direction < constants.MEMORY_SIZE):
            raise ValueError("Dirección de memoria fuera de rango.")

        # If reading from E/S range and GUI provided input, serve it first
        try:
            from controller import terminal as _term
            if constants.E_S_RANGE[0] <= direction <= constants.E_S_RANGE[1]:
                if _term.has_input():
                    v = _term.pop_input_uint64()
                    return np.uint64(v)
        except Exception:
            # ignore terminal bridge errors
            pass
        return Memory.array[direction]

    @staticmethod
    def write(direction: int, value: np.uint64):
        """
        Escribe una palabra en una dirección de memoria
        """
        if not (0 <= direction < constants.MEMORY_SIZE):
            raise ValueError("Dirección de memoria fuera de rango.")

        if not isinstance(value, np.uint64):
            raise TypeError("El valor debe ser de tipo np.uint64.")

        Memory.array[direction] = value
        if direction not in Memory.memory_changed:
            Memory.memory_changed.append(direction)
        # If writing to E/S range, notify terminal (GUI)
        try:
            from controller import terminal as _term
            if constants.E_S_RANGE[0] <= direction <= constants.E_S_RANGE[1]:
                # decode uint64 to int and notify
                _term.write_notify(direction, int(value))
        except Exception:
            pass
