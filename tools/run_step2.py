import sys, os, importlib
root = os.path.dirname(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

# load assembler_by path
import importlib.util
spec = importlib.util.spec_from_file_location('assembler_from_as', os.path.join(root, 'tools', 'assembler_from_as.py'))
assembler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembler)

# import Enlazador and controller Action via normal imports
from model.enlazador.enlazador import Enlazador
from controller.computer import Action
from model.procesador import bus
from model.procesador.CPU import ALU
from model.procesador.memory import Memory

asm = '''ICARGA R4 7
ICARGA R5 21
loop_4:
COMP R4, R5
SICERO end_5
SIPOS a_gt_6
SINEG b_gt_7
a_gt_6:
RESTA R4, R5
SALTA loop_4
b_gt_7:
RESTA R5, R4
SALTA loop_4
end_5:
GUARD R4, M[131072]
'''

print('Assembling...')
insts = assembler.assemble_text(asm)
print('Got', len(insts), 'instructions')

# Load into memory via Enlazador
Enlazador.set_machine_code('\n'.join(insts))
# Ensure processor and memory are initialized before loading
bus.set_up()
ALU.set_up()
Memory.set_up()
Enlazador.link_load_machine_code(0)

# start stepping
Action.start_stepping(0)
print('Stepping...')
try:
    while True:
        formatted, opcode_len, did_para = Action.step()
        print('STEP:', formatted, 'TYPE=', opcode_len)
        if did_para:
            print('PARA')
            break
except Exception as e:
    print('Exception during stepping:', e)
    import traceback; traceback.print_exc()
    sys.exit(1)

print('Done')
