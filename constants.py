# ----------------------------------
# Memory
# ----------------------------------

WORDS_SIZE_BITS = 64
MEMORY_BITS = 24
MEMORY_SIZE = 2**MEMORY_BITS

CODE_RANGE = (0, 65535)
E_S_RANGE = (65536, 131071)
DATA_RANGE = (131072, 2031615)
STACK_RANGE = (2031616, MEMORY_SIZE-1)

# ----------------------------------
# Bus: CONTROL
# ----------------------------------

CONTROL_SIZE = 5

# ----------------------------------
# CPU
# ----------------------------------

REGISTERS_SIZE = 32

INS_TYPE_R = (1, 12)
INS_TYPE_I = (13, 26)
INS_TYPE_J = (27, 40)

# ----------------------------------
# Paths
# ----------------------------------

ISA_PATH = "ISA.json"
OPCODES_PATH = "opcodes.json"
MEMORY_SAVE_PATH = "memory.xlsx"
MEMORY_SAVE_PATH_CSV = "memory.csv"
REGISTERS_SAVE_PATH = "registers.xlsx"
