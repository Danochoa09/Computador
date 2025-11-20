import re

content = open('Ejemplos/SPL/matmul_input_dynamic.s', encoding='utf-8').read()
regs = set(int(m.group(1)) for m in re.finditer(r'R(\d+)', content))
print(f'Registers used: {sorted(regs)}')
print(f'Max register: R{max(regs)}')
invalid = [r for r in regs if r > 31]
print(f'Invalid registers (>31): {invalid if invalid else "None"}')
