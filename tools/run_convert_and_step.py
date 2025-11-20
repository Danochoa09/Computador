import sys, os
# ensure project root
root = os.path.dirname(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from model.compilador import flex_pipeline
from controller.computer import Action
from model.enlazador.enlazador import Enlazador

s = '''a = 7
b = 21

while a != b:
    if a > b:
        a = a - b
    else:
        b = b - a
M[131072] = a
'''

insts, img = flex_pipeline.pipeline_from_text(s, out_dir=None, basename='test_convert')
print('Generated', len(insts), 'instructions, image at', img)

# Load into enlazador and load at address 0
Enlazador.set_machine_code('\n'.join(insts))
Enlazador.link_load_machine_code(0)

# Start stepping
Action.start_stepping(0)
print('Stepping started at 0')
try:
    while True:
        formatted, opcode_len, did_para = Action.step()
        print('STEP:', formatted, 'TYPE=', opcode_len)
        if did_para:
            print('PARA encountered, stopping')
            break
except Exception as e:
    print('Error during stepping:', e)
    raise
