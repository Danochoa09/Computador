"""Run the matmul_input_dynamic.spl example headless and feed inputs.
This script:
- Compiles the SPL example using the pipeline
- Loads the image at address 0
- Starts execution in a background thread
- Feeds a sequence of inputs with small delays
- Prints terminal and execution logs to stdout

Run from repository root: python tools/run_matmul_test.py
"""
import sys
import time
import threading
from pathlib import Path

# Ensure repo root is on sys.path so local packages can be imported when running
# this script directly.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model.compilador.flex_pipeline import pipeline_from_text
from controller import computer
from controller import terminal as _term

EXAMPLE = Path('Ejemplos') / 'SPL' / 'matmul_input_dynamic.spl'


def run_test():
    # Initialize emulator (register callbacks)
    computer.Action.start_emulation()

    src = EXAMPLE.read_text(encoding='utf-8')
    insts, image_path = pipeline_from_text(src, out_dir=EXAMPLE.parent, basename='matmul_test_run')
    print(f'Pipeline produced {len(insts)} instructions. First line (truncated): {insts[0][:64] if insts else "<none>"}')

    # Try to read the pipeline-generated metadata if any
    meta = {}
    try:
        import json
        meta_path = EXAMPLE.parent / 'matmul_test_run.meta.json'
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            print('Pipeline meta:', meta)
    except Exception as e:
        print('Could not read meta.json:', e)

    # Load image at address 0
    bin_text = "\n".join(insts) + "\n"
    try:
        computer.Action.load_machine_code(bin_text, 0)
    except Exception as e:
        print('load_machine_code raised:', e)
    try:
        from model.enlazador.enlazador import Enlazador
        lst = Enlazador.MACHINE_CODE_RELOC
        print('Enlazador.MACHINE_CODE_RELOC length:', 0 if lst is None else len(lst))
        if lst and len(lst) > 0:
            print('Sample line 0 length:', len(lst[0]))
            print('Sample line 0 prefix:', lst[0][:80])
    except Exception as e:
        print('Could not inspect Enlazador:', e)

    # Dump first few memory words for inspection
    try:
        from model.procesador.memory import Memory
        import numpy as _np
        print('Memory[0..7]:')
        for i in range(8):
            try:
                v = Memory.read(i)
                print(f'  {i}: 0x{int(v):016x}')
            except Exception as e:
                print('  read error', e)
    except Exception as e:
        print('Could not dump memory:', e)

    # Try a manual write via bus to test write path (write value 0xdeadbeef at address 0)
    try:
        from model.procesador import bus
        from utils import NumberConversion as NC
        from bitarray import bitarray
        w = NC.natural2bitarray(0xdeadbeef, 64)
        bus.DirectionBus.write(NC.natural2bitarray(0, 24))
        bus.DataBus.write(w)
        bus.ControlBus.write(bus.ControlBus.WRITE_MEMORY_BIN)
        bus.action()
        print('Wrote 0xdeadbeef to memory[0] via bus.action()')
        from model.procesador.memory import Memory
        print('Memory[0] now:', hex(int(Memory.read(0))))
    except Exception as e:
        print('Manual bus write failed:', e)

    # Determine start address: prefer metadata entry_index if available
    start_addr = 0
    try:
        if isinstance(meta, dict) and 'entry_index' in meta:
            start_addr = int(meta['entry_index'])
            print('Using entry_index from meta:', start_addr)
        else:
            for i, s in enumerate(insts):
                if s.strip('0') != '':
                    start_addr = i
                    break
            print('Detected code start index in image at', start_addr)
    except Exception as e:
        print('Could not determine start address, defaulting to 0:', e)

    # Run program in thread
    def runner():
        print(f'Starting program execution from {start_addr}...')
        try:
            computer.Action.execute_progam(start_addr)
            print('Program finished execution')
        except Exception as e:
            print('Execution error:', e)

    t = threading.Thread(target=runner, daemon=True)
    t.start()

    # Wait for a short while to allow program to print prompts
    time.sleep(0.5)

    # Prepare inputs for a small 2x2 example.
    # The SPL expects the interactive inputs in order:
    # f1, c1, f2, c2, then elements of A row-major, elements of B row-major
    inputs = [
        '2',  # f1
        '2',  # c1
        '2',  # f2
        '2',  # c2
        # A elements (2x2)
        '1', '2', '3', '4',
        # B elements (2x2)
        '5', '6', '7', '8'
    ]

    # Feed inputs with small delays to simulate user typing
    for i, s in enumerate(inputs):
        time.sleep(0.2)
        print(f'Pushing input: {s}')
        _term.push_input(s)

    # Wait for thread to finish
    t.join(timeout=10)
    if t.is_alive():
        print('Program still running after 10s; aborting test.')
    else:
        print('Test completed.')


if __name__ == '__main__':
    run_test()
