import importlib.util, os
root = os.getcwd()
spec = importlib.util.spec_from_file_location('assembler_from_as', os.path.join(root,'tools','assembler_from_as.py'))
assembler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembler)
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
insts = assembler.assemble_text(asm)
for i, inst in enumerate(insts):
    print(i, inst)
