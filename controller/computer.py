import csv
import numpy as np
from bitarray import bitarray
from openpyxl import Workbook

import constants
from utils import NumberConversion as NC
from utils import FileManager

from model.procesador import CPU
from model.procesador import unidad_E_S
from model.procesador.memory import Memory
from model.enlazador.enlazador import Enlazador

from model.procesador import bus
from model.procesador.bus import DataBus, DirectionBus, ControlBus


# -----------------------
# Public Global Variables
# -----------------------

# -----------------------
# Funciones de acción
# -----------------------

class Action:

    @staticmethod
    def start_emulation() -> int:
        """
        Inicializar componentes y desplegar interfaz gráfica.
        Se llama desde el main para ejecutar tod0.

        return:
            0 éxito
            -1 fracaso
        """

        # Inicializar componentes
        bus.set_up()
        CPU.refresh()
        CPU.ALU.set_up()
        Memory.set_up()

        # Register terminal input callback to resume execution when input arrives
        try:
            from controller import terminal as _term
            _term.register_input_callback(Action._on_input_available)
        except Exception:
            pass

        # Desplegar interfaz grafica
        # TODO @sebastian desplegar

        # Retornar
        return 0
        # -1 fracaso
        pass

    # Stepping control flag
    _is_stepping: bool = False
    # Execution waiting for input
    _waiting_for_input: bool = False

    @staticmethod
    def start_stepping(address: int) -> None:
        """
        Prepare CPU to execute step-by-step from address. Sets internal stepping flag.
        """
        # Prepare CPU PC and set stepping mode
        Action._is_stepping = True
        CPU.preparate(address)
        CPU.EN_EJECUCION = True

    @staticmethod
    def _reg_name(reg_num: int) -> str:
        """Return human readable register name for a register number."""
        if reg_num == 0:
            return "PC"
        if reg_num == 1:
            return "SP"
        if reg_num == 2:
            return "IR"
        if reg_num == 3:
            return "ESTADO"
        return f"R{reg_num}"

    @staticmethod
    def _format_instruction(instr_asm: str, instr_args: list, opcode_len: str) -> str:
        """Build a readable instruction string with operands from CU.instruction_args."""
        if instr_asm is None:
            return None

        try:
            if opcode_len == "64":
                return instr_asm
            if opcode_len == "54":
                r = NC.bitarray2natural(instr_args[1])
                r_p = NC.bitarray2natural(instr_args[2])
                return f"{instr_asm} {Action._reg_name(r)}, {Action._reg_name(r_p)}"
            if opcode_len == "59":
                r = NC.bitarray2natural(instr_args[1])
                return f"{instr_asm} {Action._reg_name(r)}"
            if opcode_len == "35":
                r = NC.bitarray2natural(instr_args[1])
                m = NC.bitarray2natural(instr_args[2])
                # Some 35-bit-format instructions (e.g. GUARD) use the R field as unused (0)
                # and semantically operate over a memory operand only. Mostrar M[...] en ese caso
                if instr_asm is not None and instr_asm.upper() == 'GUARD' and r == 0:
                    return f"{instr_asm} M[{m}]"
                return f"{instr_asm} {Action._reg_name(r)}, {m}"
            if opcode_len == "27":
                r = NC.bitarray2natural(instr_args[1])
                v = NC.bitarray2int(instr_args[2])
                return f"{instr_asm} {Action._reg_name(r)}, {v}"
            if opcode_len == "40":
                m = NC.bitarray2natural(instr_args[1])
                return f"{instr_asm} {m}"
        except Exception:
            # Fallback to just the asm name
            return instr_asm


    @staticmethod
    def step() -> None:
        """
        Execute exactly one fetch-decode-execute cycle if stepping is active.
        If stepping wasn't started, raises RuntimeError.
        """
        if not Action._is_stepping:
            raise RuntimeError("Stepping not started. Call start_stepping(address) first.")
        # Execute one instruction
        CPU.fetch()
        CPU.decode()

        # Capture instruction metadata before execution
        try:
            instr_asm = CPU.CU.instruction_asm
            opcode_len = CPU.CU.opcode_length
            instr_args = CPU.CU.instruction_args
        except Exception:
            instr_asm = None
            opcode_len = None
            instr_args = None

        CPU.execute()

        did_para = bool(CPU.PARA_INSTRUCTION)

        # If instruction was PARA, stop stepping
        if did_para:
            Action._is_stepping = False
            CPU.refresh()

        # Build formatted instruction string
        formatted = Action._format_instruction(instr_asm, instr_args, opcode_len)

        return (formatted, opcode_len, did_para)

    @staticmethod
    def stop_stepping() -> None:
        """
        Stop stepping mode and refresh CPU state.
        """
        Action._is_stepping = False
        CPU.refresh()

    @staticmethod
    def is_stepping() -> bool:
        return bool(Action._is_stepping)

    @staticmethod
    def stop_emulation(
            save_memory: bool = False, save_registers: bool = False,
            mode: str = "bin"
    ) -> None:
        """
        Función que detiene toda la emulación.
        valid_modes = ["bin", "hex", "decimal", "decimalc2"]

        La idea es que un botón del front "Apagar",
        llama a esta función para que guarde tod0.

        Si en el front se seleccionó, "Guardar Memoria" o "Guardar Registros",
        entonces los parámetros deben ser True respectivamente.
        """
        valid_modes = ["bin", "hex", "decimal", "decimalc2"]
        if mode not in valid_modes:
            raise ValueError(
                f"Modo inválido: '{mode}'. "
                f"Opciones válidas: {valid_modes}")

        # Guardar memoria si requerido en .csv
        if save_memory:
            Data.Memory_D.save_memory_fast(constants.MEMORY_SAVE_PATH_CSV, mode)
            #Data.Memory_D.save_modified_memory(constants.MEMORY_SAVE_PATH, mode)

        # Guardar memoria si requerido en .csv
        if save_registers:
            registers_data: list[str] = (
                Data.CPU_D.get_registers_range_content(
                    0, constants.REGISTERS_SIZE - 1, mode
                )
            )
            FileManager.Excel.list_to_xlsx(
                registers_data, constants.REGISTERS_SAVE_PATH,
                "Registros"
            )

        # Cerrar interfaz gráfica
        # TODO @sebastian

        # Refrescar la CPU
        CPU.refresh()

        return

    @staticmethod
    def load_machine_code(machine_code_reloc: str, address: int):
        """
        Load machine code at the given address.

        El usuario puede escribir el código de máquina relocalizable en
        una ventana de exto fija en la APp.
        En la parte inferior debe haber un botón que diga enlazar
        y a la izquierda, un campo de texto donde se pueda poner la
        dirección, que es el área del código.

        Al darle click al botón,se llama a esta función con:
        :param machine_code_reloc un string, el código de máquina
            relocalizable que
            contiene '\n'para separar cada línea
        :param address número de 0 a 65535
        """
        # Verificar machine_code en una lista separada por '\n'
        Enlazador.set_machine_code(machine_code_reloc)

        # Cargar código
        Enlazador.link_load_machine_code(address)

    @staticmethod
    def execute_instruction(address: int):
        """
        Execute a specific instruction from a given address

        En el front debe haber un botón "Ejecutar Instrucción"
        Y una caja de texto donde se escribe la
        primera instrucción que se desea ejecutar.

        Al oprimir el botón, el PC se pone en dicha instrucción
        y se ejecuta solo una.
        """
        # Pone el contenido del PC de la ALU en la
        #   dirección address como bitarray
        CPU.preparate(address)

        # Poner CPU en ejecución
        CPU.EN_EJECUCION = True

        # Ciclo Fetch-Decode-Execute
        CPU.fetch()
        CPU.decode()
        CPU.execute()

        # Refrescar la CPU:
        #   Ejecución e instrucción de parada en Falso
        CPU.refresh()

    @staticmethod
    def execute_progam(address: int):
        """
        Start program execution with the instruction from a given address
        """
        # Pone el contenido del PC de la ALU en la
        #   dirección address como bitarray
        CPU.preparate(address)

        # Poner CPU en ejecución
        CPU.EN_EJECUCION = True

        # Ciclo Fetch-Decode-Execute
        try:
            while not CPU.PARA_INSTRUCTION:
                CPU.fetch()
                CPU.decode()
                CPU.execute()
        except Exception as e:
            # If execution requests input, wait here until input is available
            try:
                from controller import terminal as _term
                if isinstance(e, _term.InputNeeded):
                    # Block until input is available, then finish the instruction
                    import time
                    while not _term.has_input():
                        time.sleep(0.05)
                    # Now attempt to complete the instruction
                    CPU.execute()
                    # Continue execution loop
                    while not CPU.PARA_INSTRUCTION:
                        CPU.fetch()
                        CPU.decode()
                        try:
                            CPU.execute()
                        except Exception as e2:
                            if isinstance(e2, _term.InputNeeded):
                                # wait again
                                while not _term.has_input():
                                    time.sleep(0.05)
                                CPU.execute()
                                continue
                            else:
                                raise
                    # finished normally
                    pass
            except Exception:
                # If it's not InputNeeded or something else failed, re-raise
                raise

        # Refrescar la CPU:
        #   Ejecución e instrucción de parada en Falso
        CPU.refresh()

    @staticmethod
    def _on_input_available():
        """Called when terminal input is pushed. If execution was paused waiting
        for input, resume the interrupted instruction and continue execution."""
        try:
            from controller import terminal as _term
            if not Action._waiting_for_input:
                return
            # Attempt to finish the current instruction
            try:
                CPU.execute()
            except Exception as e:
                if isinstance(e, _term.InputNeeded):
                    # Still no input; remain waiting
                    Action._waiting_for_input = True
                    return
                else:
                    raise

            # Instruction finished; resume normal execution loop
            Action._waiting_for_input = False
            while not CPU.PARA_INSTRUCTION:
                CPU.fetch()
                CPU.decode()
                try:
                    CPU.execute()
                except Exception as e:
                    if isinstance(e, _term.InputNeeded):
                        Action._waiting_for_input = True
                        return
                    else:
                        raise
            CPU.refresh()
        except Exception:
            # Swallow to avoid crashing the GUI
            pass


# -----------------------
# Funciones de datos
# -----------------------

class Data:
    class Memory_D:

        @staticmethod
        def format_memory_value(val: np.uint64, mode: str) -> str:
            """
            Obtiene el string del valor uint64 y lo convierte
            :param val: uint64 que corresponde a un contenido de celda de memoria
            :param mode: ["bin", "hex", "decimal", "decimalc2"]
            :return:
            """
            if mode == "bin":
                return format(val, '064b')
            elif mode == "hex":
                return hex(val)
            elif mode == "decimal":
                return str(val)
            elif mode == "decimalc2":
                return str(NC.bitarray2int(NC.natural2bitarray(int(val))))
            else:
                raise ValueError("Modo no válido.")

        @staticmethod
        def save_memory_fast(path_csv: str, mode: str) -> None:
            """
            Guarda la memoria en un CSV fast
            :param path_csv
            :param mode: ('bin', 'hex', 'decimal', 'decimalc2').
            """
            mem_array: np.ndarray = Memory.array
            with open(path_csv, "w", encoding="utf-8") as f:
                for val in mem_array:
                    f.write(Data.Memory_D.format_memory_value(val, mode) + '\n')

        @staticmethod
        def save_modified_memory(path_xlsx: str, mode: str) -> None:
            """
            Guarda la memoria modificada en un Excel
            :param path_xlsx
            :param mode: ('bin', 'hex', 'decimal', 'decimalc2').
            """
            if not path_xlsx.endswith(".xlsx"):
                path_xlsx += ".xlsx"

            wb = Workbook()
            ws = wb.active
            ws.title = "Memoria Modificada"

            # Encabezados
            ws.append(["Dirección", "Contenido"])

            for address in Memory.memory_changed:
                content = Data.Memory_D.get_memory_content(address, mode)
                ws.append([address, content])

            wb.save(path_xlsx)

        @staticmethod
        def get_memory_content(address: int, mode: str) -> str:
            """
            Devuelve la palabra almacenada en una dirección de memoria en el formato solicitado.

            :param address: Dirección de memoria.
            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Cadena representando la palabra en el formato especificado.
            """
            valid_modes = ["bin", "hex", "decimal", "decimalc2"]
            if mode not in valid_modes:
                raise ValueError(f"Modo inválido: '{mode}'. Opciones válidas: {valid_modes}")

            word_64: np.uint64 = Memory.read(address)
            return Data.Memory_D.format_memory_value(word_64, mode)

        @staticmethod
        def get_memory_range_content(start: int, end: int, mode: str) -> list[str]:
            """
            Devuelve el contenido de un rango de direcciones de memoria en el formato especificado.

            :param start: Dirección inicial del rango (inclusive).
            :param end: Dirección final del rango (inclusive).
            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Lista de cadenas con el contenido de cada dirección en el formato solicitado.
            """
            if start > end:
                raise ValueError(
                    "La dirección inicial debe ser menor o "
                    "igual a la dirección final."
                )
            if start < 0:
                raise ValueError(f"Del rango {start} inválido. Debe ser mayor o igual a 0")
            if end > constants.STACK_RANGE[1]:
                raise ValueError(
                    f"Del rango {end} inválido. "
                    f"Debe ser menor o igual a {constants.STACK_RANGE[1]}")

            return [Data.Memory_D.get_memory_content(addr, mode) for addr in range(start, end + 1)]

        @staticmethod
        def get_code_segment_content(mode: str) -> list[str]:
            """
            Devuelve el contenido del segmento de código en el formato especificado.
            """
            return Data.Memory_D.get_memory_range_content(
                constants.CODE_RANGE[0], constants.CODE_RANGE[1],
                mode
            )

        @staticmethod
        def get_es_segment_content(mode: str) -> list[str]:
            """
            Devuelve el contenido del segmento de entrada/salida en el formato especificado.
            """
            return Data.Memory_D.get_memory_range_content(
                constants.E_S_RANGE[0], constants.E_S_RANGE[1],
                mode
            )

        @staticmethod
        def get_data_segment_content(mode: str) -> list[str]:
            """
            Devuelve el contenido del segmento de datos en el formato especificado.
            """
            return Data.Memory_D.get_memory_range_content(
                constants.DATA_RANGE[0], constants.DATA_RANGE[1],
                mode
            )

        @staticmethod
        def get_stack_segment_content(mode: str) -> list[str]:
            """
            Devuelve el contenido del segmento de pila (stack) en el formato especificado.
            """
            return Data.Memory_D.get_memory_range_content(
                constants.STACK_RANGE[0], constants.STACK_RANGE[1],
                mode
            )

    class CPU_D:
        @staticmethod
        def get_register_content(reg_num: int, mode: str) -> str:
            """
            Devuelve la palabra almacenada en una dirección de registros en el formato solicitado.

            PC, SP, IR, ESTADO, R4, ..., R31

            0,  1,   2,    3,   4,  ..., 31

            :param reg_num: Numero del registro
            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Cadena representando la palabra en el formato especificado.
            """
            valid_modes = ["bin", "hex", "decimal", "decimalc2"]
            if mode not in valid_modes:
                raise ValueError(f"Modo inválido: '{mode}'. Opciones válidas: {valid_modes}")

            word_bit: bitarray = CPU.ALU.read_register(reg_num)

            if mode == "bin":
                return word_bit.to01()
            elif mode == "hex":
                return hex(NC.bitarray2natural(word_bit))
            elif mode == "decimal":
                return str(NC.bitarray2natural(word_bit))
            elif mode == "decimalc2":
                return str(NC.bitarray2int(word_bit))

        @staticmethod
        def get_registers_range_content(start: int, end: int, mode: str) -> list[str]:
            """
            Devuelve el contenido de un rango de registros en el formato especificado.

            :param start: Dirección inicial del rango (inclusive).
            :param end: Dirección final del rango (inclusive).
            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Lista de cadenas con el contenido de cada dirección en el formato solicitado.
            """
            if start > end:
                raise ValueError(
                    "La dirección inicial debe ser menor o "
                    "igual a la dirección final."
                )
            if start < 0:
                raise ValueError(f"Del rango {start} inválido. Debe ser mayor o igual a 0")
            if end > 31:
                raise ValueError(f"Del rango {end} inválido. Debe ser menor o igual a 31")

            return [Data.CPU_D.get_register_content(num, mode) for num in range(start, end + 1)]

    class Bus_D:

        @staticmethod
        def get_databus(mode: str) -> str:
            """
            Devuelve el contenido del bus de datos en el formato solicitado.

            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Cadena representando la palabra en el formato especificado.
            """
            valid_modes = ["bin", "hex", "decimal", "decimalc2"]
            if mode not in valid_modes:
                raise ValueError(f"Modo inválido: '{mode}'. Opciones válidas: {valid_modes}")

            word_bit: bitarray = DataBus.read()

            if mode == "bin":
                return word_bit.to01()
            elif mode == "hex":
                return hex(NC.bitarray2natural(word_bit))
            elif mode == "decimal":
                return str(NC.bitarray2natural(word_bit))
            elif mode == "decimalc2":
                return str(NC.bitarray2int(word_bit))

        @staticmethod
        def get_directionbus(mode: str) -> str:
            """
            Devuelve el contenido del bus de dirección en el formato solicitado.

            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Cadena representando la palabra en el formato especificado.
            """
            valid_modes = ["bin", "hex", "decimal", "decimalc2"]
            if mode not in valid_modes:
                raise ValueError(f"Modo inválido: '{mode}'. Opciones válidas: {valid_modes}")

            word_bit: bitarray = DirectionBus.read()

            if mode == "bin":
                return word_bit.to01()
            elif mode == "hex":
                return hex(NC.bitarray2natural(word_bit))
            elif mode == "decimal":
                return str(NC.bitarray2natural(word_bit))
            elif mode == "decimalc2":
                return str(NC.bitarray2int(word_bit))

        @staticmethod
        def get_controlbus(mode: str) -> str:
            """
            Devuelve el contenido del bus de dirección en el formato solicitado.

            :param mode: Modo de representación ('bin', 'hex', 'decimal', 'decimalc2').
            :return: Cadena representando la palabra en el formato especificado.
            """
            valid_modes = ["bin", "hex", "decimal", "decimalc2"]
            if mode not in valid_modes:
                raise ValueError(f"Modo inválido: '{mode}'. Opciones válidas: {valid_modes}")

            word_bit: bitarray = ControlBus.read()

            if mode == "bin":
                return word_bit.to01()
            elif mode == "hex":
                return hex(NC.bitarray2natural(word_bit))
            elif mode == "decimal":
                return str(NC.bitarray2natural(word_bit))
            elif mode == "decimalc2":
                return str(NC.bitarray2int(word_bit))
