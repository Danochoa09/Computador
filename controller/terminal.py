"""Simple terminal bridge between Memory E/S and the GUI.
The module provides a write callback for Memory.write notifications and
an input queue for Memory.read to consume input provided by the GUI.
"""
from typing import Callable, Optional
import threading
import time

_write_callback: Optional[Callable[[int, str], None]] = None
_input_queue: list[int] = []
_input_callbacks: list[Callable[[], None]] = []

# Buffering for grouped writes: map address -> (accum_str, timer)
_write_buffers: dict[int, dict] = {}
# Lock to protect buffers
_buf_lock = threading.Lock()
_FLUSH_DELAY = 0.05  # seconds


class InputNeeded(Exception):
    """Raised by the bus/CPU when an E/S read requires user input."""
    pass


def register_write_callback(cb: Callable[[int, str], None]):
    """Register a function(cb(address:int, text:str)) to be called when
    a word is written into an E/S memory address.
    """
    global _write_callback
    _write_callback = cb


def write_notify(address: int, uint64_value: int):
    """Called by Memory when an E/S address is written. Decodes the 64-bit
    value into a small UTF-8 string and calls the registered callback."""
    global _write_callback
    # Heuristic: if the 64-bit word contains only printable ASCII bytes
    # (after stripping trailing zeros) then decode and show as text. Otherwise
    # display the numeric value (so programs that GUARD numbers print numbers).
    try:
        b = int(uint64_value).to_bytes(8, 'little')
        bstripped = b.rstrip(b"\x00")
        is_printable = True
        if not bstripped:
            # empty -> treat as empty string
            text = ''
            is_printable = True
        else:
            for ch in bstripped:
                # Allow common whitespace characters (tab, newline, carriage return)
                if ch in (9, 10, 13):
                    continue
                if ch < 32 or ch > 126:
                    is_printable = False
                    break
            if is_printable:
                try:
                    text = bstripped.decode('utf-8')
                except Exception:
                    is_printable = False
        if not is_printable:
            text = str(int(uint64_value))
    except Exception:
        text = str(uint64_value)

    # Buffer writes for a short time window so consecutive 8-byte chunks
    # produced by the compiler are concatenated into a single callback.
    with _buf_lock:
        entry = _write_buffers.get(address)
        if entry is None:
            # create new buffer entry
            entry = {'acc': text, 'timer': None}
            _write_buffers[address] = entry
        else:
            entry['acc'] += text

        # (re)start flush timer
        def _flush(a=address):
            try:
                with _buf_lock:
                    e = _write_buffers.pop(a, None)
                if e is None:
                    return
                acc_text = e.get('acc', '')
                if _write_callback:
                    try:
                        _write_callback(a, acc_text)
                    except Exception:
                        pass
            except Exception:
                pass

        # Cancel previous timer if any
        tprev = entry.get('timer')
        if tprev and isinstance(tprev, threading.Timer):
            try:
                tprev.cancel()
            except Exception:
                pass
        # Start a new timer to flush after short delay
        timer = threading.Timer(_FLUSH_DELAY, _flush)
        entry['timer'] = timer
        timer.daemon = True
        timer.start()


def push_input(text: str):
    """Push text into the input queue. Encodes to 64-bit integers (one per 8 bytes).
    For simplicity, we push only the first up-to-8-bytes chunk as one uint64.
    """
    if text is None:
        return
    val = encode_str_to_uint64(text)
    _input_queue.append(val)
    # Debug
    try:
        print(f"[terminal] push_input: queued='{text}' encoded=0x{val:x}")
    except Exception:
        pass
    # Notify any registered input callbacks (resume handlers)
    for cb in list(_input_callbacks):
        try:
            cb()
        except Exception:
            pass


def register_input_callback(cb: Callable[[], None]):
    """Register a callback called when input is pushed into the terminal queue."""
    _input_callbacks.append(cb)


def pop_input_uint64() -> int:
    if _input_queue:
        v = _input_queue.pop(0)
        try:
            print(f"[terminal] pop_input_uint64: returning 0x{v:x}")
        except Exception:
            pass
        return v
    try:
        print("[terminal] pop_input_uint64: queue empty, returning 0")
    except Exception:
        pass
    return 0


def has_input() -> bool:
    l = len(_input_queue) > 0
    try:
        print(f"[terminal] has_input? {l}")
    except Exception:
        pass
    return l


def encode_str_to_uint64(s: str) -> int:
    b = s.encode('utf-8')[:8]
    b = b.ljust(8, b"\x00")
    # little-endian
    return int.from_bytes(b, 'little')


def decode_uint64_to_str(v: int) -> str:
    b = int(v).to_bytes(8, 'little')
    # strip trailing zeros
    b = b.rstrip(b"\x00")
    try:
        return b.decode('utf-8')
    except Exception:
        # fallback to hex
        return hex(int(v))
