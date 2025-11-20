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

# Flag to track if next value should be treated as number
_next_is_number = False


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
    global _write_callback, _next_is_number
    # Heuristic: if the 64-bit word contains only printable ASCII bytes
    # (after stripping trailing zeros) then decode and show as text. Otherwise
    # display the numeric value (so programs that GUARD numbers print numbers).
    try:
        b = int(uint64_value).to_bytes(8, 'little')
        bstripped = b.rstrip(b"\x00")
        
        # Check for numeric marker: 0xFF 0x4E 0x00 ... 0x02
        if len(b) == 8 and b[0] == 0xFF and b[1] == 0x4E and b[7] == 2:
            # Numeric marker detected - next value is a number
            _next_is_number = True
            return  # Don't display the marker itself
        
        # Check if previous value was a numeric marker
        if _next_is_number:
            # Force treat as number
            text = str(int(uint64_value))
            _next_is_number = False
        # Special case: newline marker from print statements
        # Pattern: \n\x00\x00\x00\x00\x00\x00\x01
        elif len(b) == 8 and b[0] == 10 and b[7] == 1 and b[1:7] == b'\x00' * 6:
            text = '\n'
        # Special case 2: empty value
        elif not bstripped:
            text = ''
        # Multi-byte values: likely text strings
        elif len(bstripped) > 1:
            # Check if all bytes are printable
            is_printable = True
            for ch in bstripped:
                # Allow whitespace
                if ch in (9, 10, 13):
                    continue
                if ch < 32 or ch > 126:
                    is_printable = False
                    break
            
            if is_printable:
                try:
                    text = bstripped.decode('utf-8')
                except Exception:
                    text = str(int(uint64_value))
            else:
                text = str(int(uint64_value))
        # Single byte value
        else:
            byte_val = bstripped[0]
            # If it's a printable ASCII character (space to ~)
            if 32 <= byte_val <= 126:
                # Treat as character (this includes ':', letters, punctuation)
                text = chr(byte_val)
            else:
                # Non-printable single byte (0-31, 127-255): treat as number
                # This catches the case of print(10) where 10 is the byte value
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
        return v
    return 0


def has_input() -> bool:
    l = len(_input_queue) > 0
    return l


def encode_str_to_uint64(s: str) -> int:
    # Try to parse as integer first (for numeric input)
    try:
        s_stripped = s.strip()
        if s_stripped:
            # Try decimal
            num = int(s_stripped, 10)
            return num
    except ValueError:
        pass
    
    # Fallback: encode as UTF-8 string (for text input)
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
