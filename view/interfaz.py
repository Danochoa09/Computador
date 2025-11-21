import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

from controller.computer import Action, Data
from model.compilador.flex_pipeline import pipeline_from_text
from pathlib import Path
import json
from model.compilador.parser_spl import compile_high_level
from model.ensamblador.assembler_from_as import assemble_text
from model.enlazador.enlazador import Enlazador


# Helper: detect GUARD opcode prefix from assembler tables
def _detect_guard_address_from_binary_lines(codigo_lines):
    """Given an iterable of 64-bit instruction strings, return the destination
    memory address used by a GUARD instruction if found, otherwise None.

    This uses the assembler mnemonic table to obtain the opcode bitpattern for
    GUARD and then scans the binary lines for that prefix. When found, the last
    24 bits of the instruction hold the memory address (per encoding).
    
    Returns the LAST GUARD address in the DATA_RANGE (131072+) to avoid
    detecting I/O writes (65536-131071).
    """
    try:
        from model.ensamblador.assembler_from_as import MNEMONIC_TABLE
        from constants import DATA_RANGE
    except Exception:
        return None

    guard_entry = MNEMONIC_TABLE.get('GUARD')
    if not guard_entry:
        return None
    opcode_bits = guard_entry[2]

    last_data_addr = None
    for linea in codigo_lines:
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith(opcode_bits):
            try:
                addr = int(linea[-24:], 2)
                # Only consider addresses in DATA_RANGE (ignore E/S writes)
                if addr >= DATA_RANGE[0]:
                    last_data_addr = addr
            except Exception:
                continue
    return last_data_addr
import numpy as np
import threading
from model.procesador.memory import Memory


class SimuladorComputador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Computador")
        self.geometry("1000x600")
        self._crear_scroll_general()

        # Inicializar el backend
        Action.start_emulation()

    def _crear_scroll_general(self):
        contenedor = tk.Frame(self)
        contenedor.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(contenedor, bg='gray90')
        scrollbar = ttk.Scrollbar(
            contenedor, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg='gray80')

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._crear_area_codigo()
        self._crear_area_memoria()
        self._crear_area_ejecucion()
        # Register a terminal write callback so Memory writes to E/S appear here
        try:
            from controller import terminal as _term
            def _term_cb(addr, text):
                try:
                    # Robust insertion: rebuild the widget content by finding the
                    # last prompt "> ", inserting the new program text just before
                    # it and preserving any user-typed text after the prompt.
                    self.terminal_output.configure(state='normal')
                    full = self.terminal_output.get("1.0", "end-1c")
                    # Find last occurrence of prompt marker
                    idx = full.rfind("> ")
                    if idx == -1:
                        before = full
                        user_text = ""
                    else:
                        before = full[:idx]
                        user_text = full[idx+2:]
                    # Rebuild content: if the program text already ends with a
                    # newline, don't add another one before the prompt. This
                    # preserves explicit '\n' from the program and avoids
                    # producing extra blank lines.
                    if text.endswith("\n"):
                        new = before + text + "> " + user_text
                    else:
                        new = before + text + "\n> " + user_text
                    # Replace whole widget content in a single operation
                    self.terminal_output.delete("1.0", tk.END)
                    self.terminal_output.insert(tk.END, new)
                    # Reposition the input mark at the end of the prompt
                    self.terminal_output.mark_set("input_start", "end-1c")
                    self.terminal_output.mark_gravity("input_start", tk.LEFT)
                    self.terminal_output.see(tk.END)
                except Exception:
                    pass
            _term.register_write_callback(_term_cb)
        except Exception:
            pass

    def _crear_area_memoria(self):
        frame = ttk.LabelFrame(self.scroll_frame, text="Memoria", padding=10)
        frame.grid(row=0, column=2, padx=0, pady=10, sticky="nsw")

        # Controls: start address and count and mode
        ctrl_frame = tk.Frame(frame)
        ctrl_frame.pack(anchor="w")

        ttk.Label(ctrl_frame, text="Inicio:").pack(side="left")
        self.mem_start = ttk.Entry(ctrl_frame, width=8)
        self.mem_start.pack(side="left", padx=4)

        ttk.Label(ctrl_frame, text="Cantidad:").pack(side="left")
        self.mem_count = ttk.Entry(ctrl_frame, width=6)
        self.mem_count.pack(side="left", padx=4)

        ttk.Label(ctrl_frame, text="Modo:").pack(side="left")
        self.mem_mode = ttk.Combobox(ctrl_frame, values=["hex", "decimal", "bin"], width=6)
        self.mem_mode.set("hex")
        self.mem_mode.pack(side="left", padx=4)

        ttk.Button(ctrl_frame, text="Mostrar", command=self._mostrar_memoria).pack(side="left", padx=4)

        # Text area to show/edit memory
        self.mem_text = scrolledtext.ScrolledText(frame, width=40, height=20)
        self.mem_text.pack(pady=6)

        # format label and move "Guardar cambios" button next to it
        format_frame = tk.Frame(frame)
        format_frame.pack(anchor="w", fill="x")
        ttk.Label(format_frame, text="Formato de cada línea: dirección:value (p. ej. 1028:0xFF)").pack(side="left")
        ttk.Button(format_frame, text="Guardar cambios", command=self._guardar_memoria).pack(side="left", padx=8)

        # --- Panel de Registros debajo de Memoria ---
        regs_frame = ttk.LabelFrame(self.scroll_frame, text="Registros", padding=10)
        regs_frame.grid(row=0, column=3, padx=10, pady=10, sticky="nsw")

        ctrl_regs = tk.Frame(regs_frame)
        ctrl_regs.pack(anchor="w")

        ttk.Label(ctrl_regs, text="Formato: ").pack(side="left")
        self.regs_mode = ttk.Combobox(ctrl_regs, values=["hex", "decimal", "bin"], width=8)
        self.regs_mode.set("hex")
        self.regs_mode.pack(side="left", padx=4)

        ttk.Button(ctrl_regs, text="Mostrar Registros", command=self._mostrar_registros).pack(side="left", padx=4)

        # Text area to show registers (read-only)
        self.regs_text = scrolledtext.ScrolledText(regs_frame, width=28, height=20)
        self.regs_text.pack(pady=6)
        # Make it read-only by default
        self.regs_text.configure(state='disabled')

        # --- Terminal I/O debajo de Memoria y Registros ---
        term_frame = ttk.LabelFrame(self.scroll_frame, text="Terminal I/O", padding=10)
        term_frame.grid(row=1, column=2, columnspan=2, padx=0, pady=10, sticky="nsew")

        # Terminal area (single widget for output and input)
        self.terminal_output = scrolledtext.ScrolledText(term_frame, width=80, height=8)
        self.terminal_output.pack(fill="both", expand=True, pady=(0, 6))
        # Allow the user to type directly. We'll manage the prompt and Enter handling.
        self.terminal_output.configure(state='normal')
        # Insert initial prompt
        self.terminal_output.insert(tk.END, "> ")
        # Remember a mark for where user input starts (after the prompt)
        self.terminal_output.mark_set("input_start", "end-1c")
        self.terminal_output.mark_gravity("input_start", tk.LEFT)

        # Bind Enter to capture the input typed on the last line
        self.terminal_output.bind('<Return>', self._terminal_send_from_text)
        # Bind Ctrl+L to clear (convenience)
        self.terminal_output.bind('<Control-l>', lambda e: (self._terminal_clear(), 'break'))

    def _mostrar_memoria(self):
        try:
            start_s = self.mem_start.get().strip()
            count_s = self.mem_count.get().strip()
            if start_s == "":
                start = 0
            else:
                start = int(start_s, 0)
            if count_s == "":
                count = 32
            else:
                count = int(count_s, 0)

            mode = self.mem_mode.get()
            if mode not in ("hex", "decimal", "bin"):
                mode = "hex"

            lines = []
            for addr in range(start, start + count):
                if addr < 0 or addr >= Memory.array.size:
                    break
                val = Data.Memory_D.get_memory_content(addr, "hex" if mode == "hex" else ("bin" if mode == "bin" else "decimal"))
                lines.append(f"{addr}:{val}")

            self.mem_text.delete(1.0, tk.END)
            self.mem_text.insert(tk.END, "\n".join(lines))
        except Exception as e:
            self.output_ejecucion.insert(tk.END, f"Error mostrando memoria: {e}\n")

    def _guardar_memoria(self):
        """Parse lines from mem_text and write to Memory. Lines must be 'addr:value'."""
        text = self.mem_text.get(1.0, tk.END).strip()
        if not text:
            return
        errors = []
        for i, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            if ':' not in line:
                errors.append((i, 'Formato inválido'))
                continue
            addr_s, val_s = line.split(':', 1)
            try:
                addr = int(addr_s.strip(), 0)
            except Exception:
                errors.append((i, 'Dirección inválida'))
                continue
            try:
                # Allow hex (0x...), bin (0b...), or decimal
                val_int = int(val_s.strip(), 0)
                if val_int < 0:
                    raise ValueError('Negativo')
                Memory.write(addr, np.uint64(val_int))
            except Exception as e:
                errors.append((i, f'Valor inválido: {e}'))

        if errors:
            msg = '; '.join([f"L{ln}:{err}" for ln, err in errors])
            self.output_ejecucion.insert(tk.END, f"Errores al guardar memoria: {msg}\n")
        else:
            self.output_ejecucion.insert(tk.END, "Memoria guardada correctamente.\n")

    def _terminal_send(self):
        """Send the content of the terminal entry to the terminal output.
        This is a simple local echo. Integration with the E/S model can be added
        later if needed.
        """
        # Backwards-compatible wrapper: if someone calls the old send method,
        # delegate to the new scrolledtext handler.
        try:
            self._terminal_send_from_text()
        except Exception:
            pass

    def _terminal_clear(self):
        """Clear the terminal output area."""
        try:
            self.terminal_output.configure(state='normal')
            self.terminal_output.delete(1.0, tk.END)
            # Insert fresh prompt after clearing
            self.terminal_output.insert(tk.END, "> ")
            self.terminal_output.mark_set("input_start", "end-1c")
            self.terminal_output.mark_gravity("input_start", tk.LEFT)
            # Keep it editable so user can type
            self.terminal_output.configure(state='normal')
        except Exception as e:
            try:
                self.output_ejecucion.insert(tk.END, f"Error clearing terminal: {e}\n")
            except Exception:
                pass

    def _terminal_send_from_text(self, event=None):
        """Handle Enter pressed inside the terminal scrolledtext.
        Capture the last line (user input after the prompt), process it,
        and append a new prompt. Returns the Tk binding break to stop the
        default newline insertion.
        """
        try:
            # Get the last line typed by the user
            content = self.terminal_output.get("1.0", "end-1c")
            lines = content.splitlines()
            last_line = lines[-1] if lines else ""
            if last_line.startswith("> "):
                input_text = last_line[2:]
            else:
                input_text = last_line

            # Simple processing: for now, echo to the execution output area
            # and leave the typed input as-is in the terminal area.
            if input_text.strip():
                try:
                    self.output_ejecucion.insert(tk.END, f"Terminal input: {input_text}\n")
                    # Send input to the emulator input queue so CPU reads can consume it
                    try:
                        from controller import terminal as _term
                        _term.push_input(input_text)
                    except Exception:
                        pass
                except Exception:
                    pass

            # Append a newline and a new prompt, move caret to end
            self.terminal_output.insert(tk.END, "\n> ")
            self.terminal_output.see(tk.END)
        except Exception as e:
            try:
                self.output_ejecucion.insert(tk.END, f"Error terminal send_from_text: {e}\n")
            except Exception:
                pass
        # Prevent Tk from inserting an extra newline
        return 'break'

    def _mostrar_registros(self):
        """Muestra los 32 registros (R0..R31) en el area de Registros usando el formato seleccionado."""
        try:
            mode = self.regs_mode.get()
            if mode not in ("hex", "decimal", "bin"):
                mode = "hex"

            lines = []
            for r in range(32):
                try:
                    val = Data.CPU_D.get_register_content(r, mode)
                except Exception:
                    val = "?"
                lines.append(f"R{r}: {val}")

            # write into the text widget by enabling temporarily
            self.regs_text.configure(state='normal')
            self.regs_text.delete(1.0, tk.END)
            self.regs_text.insert(tk.END, "\n".join(lines))
            self.regs_text.configure(state='disabled')
        except Exception as e:
            self.output_ejecucion.insert(tk.END, f"Error mostrando registros: {e}\n")

    # flags panel removed — flags will be created inside execution area

    def _update_flags(self):
        """Leer registro ESTADO y actualizar las etiquetas de banderas."""
        try:
            estado_bin = Data.CPU_D.get_register_content(3, "bin")
            # estado_bin is a 64-char string; flags set in ALU at positions: last bits
            # C at -1, P at -2, N at -3, D at -4 according to ALU.modify_state_int
            self.flag_C_var.set(estado_bin[-1])
            self.flag_P_var.set(estado_bin[-2])
            self.flag_N_var.set(estado_bin[-3])
            self.flag_D_var.set(estado_bin[-4])
        except Exception:
            # On error, set unknown
            self.flag_C_var.set("?")
            self.flag_P_var.set("?")
            self.flag_N_var.set("?")
            self.flag_D_var.set("?")

    def _crear_area_codigo(self):
        frame = ttk.LabelFrame(self.scroll_frame, text="Código Binario", padding=10)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ttk.Label(frame, text="Código:").pack(anchor="w")
        self.codigo_text = scrolledtext.ScrolledText(frame, width=80, height=20)
        self.codigo_text.pack()

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)

        self.btn_cargar_archivo = ttk.Button(
            btn_frame, text="Cargar desde Archivo", command=self._cargar_archivo)
        self.btn_cargar_archivo.pack(side="left", padx=5)

        ttk.Label(btn_frame, text="Dirección de carga (hex):").pack(side="left")
        self.direccion_carga = ttk.Entry(btn_frame, width=10)
        self.direccion_carga.pack(side="left", padx=5)

        self.btn_enlazar = ttk.Button(
            btn_frame, text="Cargar a Memoria", command=self._enlazar_codigo)
        self.btn_enlazar.pack(side="left", padx=5)

        # Button to run the FLEX-like pipeline: preproc -> assembler -> linker -> image
        self.btn_convertir = ttk.Button(
            btn_frame, text="Convertir", command=self._convertir_flex)
        self.btn_convertir.pack(side="left", padx=5)

        # Open separate compilation window
        ttk.Button(btn_frame, text="Abrir Ventana de Compilación", command=self._abrir_ventana_compilacion).pack(side="left", padx=5)

    def _abrir_ventana_compilacion(self):
        win = VentanaCompilacion(self)
        win.transient(self)
        win.grab_set()

    def _cargar_archivo(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo de código",
               filetypes=(("Archivos de texto", "*.txt"),("Archivos de configuración", "*.in"),("Todos los archivos", "*.*")
    )
        )
        if filepath:
            with open(filepath, "r", encoding="utf-8") as file:
                contenido = file.read()
                self.codigo_text.delete(1.0, tk.END)
                self.codigo_text.insert(tk.END, contenido)

    def _enlazar_codigo(self):
        codigo = self.codigo_text.get(1.0, tk.END).strip()
        direccion = self.direccion_carga.get()
        if codigo and direccion:
            try:
                direccion_int = int(direccion, 16)
                Action.load_machine_code(codigo, direccion_int)
                tk.messagebox.showinfo("Éxito", "Código cargado correctamente en la memoria.")
            except Exception as e:
                tk.messagebox.showerror("Error", f"No se pudo cargar: {e}")
        else:
            tk.messagebox.showwarning("Atención", "Falta código o dirección.")

    def _convertir_flex(self):
        """Toma el contenido actual del editor (source .spl), ejecuta el pipeline
        (preprocesador -> ensamblador -> enlazador) y reemplaza el contenido del
        editor por el binario resultante listo para "Cargar a Memoria".
        También escribe archivos intermedios en Ejemplos/SPL/.
        """
        codigo = self.codigo_text.get(1.0, tk.END).strip()
        if not codigo:
            tk.messagebox.showwarning("Atención", "No hay código cargado para convertir.")
            return

        try:
            insts, image_path = pipeline_from_text(codigo)

            # Replace editor content with final binary image (one 64-bit word per line)
            bin_text = "\n".join(insts) + "\n"
            self.codigo_text.delete(1.0, tk.END)
            self.codigo_text.insert(tk.END, bin_text)

            # Inform user and, if a load address is filled, optionally load it
            direccion = self.direccion_carga.get()
            if direccion:
                try:
                    direccion_int = int(direccion, 16)
                    Action.load_machine_code(bin_text, direccion_int)
                    tk.messagebox.showinfo("Éxito", f"Imagen generada y cargada en {direccion}.")
                except Exception as e:
                    tk.messagebox.showwarning("Aviso", f"Imagen generada en {image_path} pero no se pudo cargar: {e}")
            else:
                tk.messagebox.showinfo("Éxito", f"Imagen generada: {image_path}. Pegue la dirección y pulse 'Cargar a Memoria'.")

        except Exception as e:
            tk.messagebox.showerror("Error en conversión", f"Fallo al convertir: {e}")

    def _crear_area_ejecucion(self):
        frame = ttk.LabelFrame(self.scroll_frame, text="Ejecutar Programa", padding=10)
        frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        # Create a two-column content area: left = controls + output, right = flags
        content = tk.Frame(frame)
        content.pack(fill="both", expand=True)

        left = tk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew")

        right = tk.Frame(content)
        right.grid(row=0, column=1, sticky="n")

        # Left: controls
        ttk.Label(left, text="Dirección de inicio (hex):").pack(anchor="w")
        self.dir_inicio = ttk.Entry(left, width=15)
        self.dir_inicio.pack(anchor="w", pady=5)

        self.btn_ejecutar = ttk.Button(
            left, text="Ejecutar Programa", command=self._ejecutar_programa)
        self.btn_ejecutar.pack(pady=5)

        # Step controls
        step_frame = tk.Frame(left)
        step_frame.pack(fill="x", pady=5)

        self.btn_start_step = ttk.Button(step_frame, text="Iniciar Paso", command=self._start_paso)
        self.btn_start_step.pack(side="left", padx=5)

        self.btn_step = ttk.Button(step_frame, text="Paso", command=self._paso)
        self.btn_step.pack(side="left", padx=5)

        self.btn_stop_step = ttk.Button(step_frame, text="Detener Paso", command=self._stop_paso)
        self.btn_stop_step.pack(side="left", padx=5)

        self.output_ejecucion = scrolledtext.ScrolledText(left, width=80, height=10)
        self.output_ejecucion.pack()

        # Right: flags inside execution area
        flags_frame = ttk.LabelFrame(right, text="Banderas", padding=6)
        flags_frame.pack()

        # Variables for flags
        self.flag_C_var = tk.StringVar(value="0")
        self.flag_P_var = tk.StringVar(value="0")
        self.flag_N_var = tk.StringVar(value="0")
        self.flag_D_var = tk.StringVar(value="0")

        tk.Label(flags_frame, text="C (Zero):").grid(row=0, column=0, sticky="w")
        tk.Label(flags_frame, textvariable=self.flag_C_var).grid(row=0, column=1, sticky="w")

        tk.Label(flags_frame, text="P (Positive):").grid(row=1, column=0, sticky="w")
        tk.Label(flags_frame, textvariable=self.flag_P_var).grid(row=1, column=1, sticky="w")

        tk.Label(flags_frame, text="N (Negative):").grid(row=2, column=0, sticky="w")
        tk.Label(flags_frame, textvariable=self.flag_N_var).grid(row=2, column=1, sticky="w")

        tk.Label(flags_frame, text="D (Overflow):").grid(row=3, column=0, sticky="w")
        tk.Label(flags_frame, textvariable=self.flag_D_var).grid(row=3, column=1, sticky="w")

    def _ejecutar_programa(self):
        direccion = self.dir_inicio.get()
        if direccion:
            try:
                direccion_int = int(direccion, 16)
                # If the editor contains non-binary source (SPL/asm), run the pipeline first
                codigo_raw = self.codigo_text.get(1.0, tk.END)
                only_bits = all(c in '01\n\r\t ' for c in codigo_raw)
                image_path = None
                meta = {}
                insts = None
                if not only_bits:
                    try:
                        insts, image_path = pipeline_from_text(codigo_raw)
                        bin_text = "\n".join(insts) + "\n"
                        # Replace editor with binary image
                        self.codigo_text.delete(1.0, tk.END)
                        self.codigo_text.insert(tk.END, bin_text)
                        # Load into memory at direccion_int (base address)
                        Action.load_machine_code(bin_text, direccion_int)
                        # Read meta for entry_index/result_addr if present
                        try:
                            import json
                            from pathlib import Path as _P
                            meta_path = _P(image_path).with_suffix('.meta.json')
                            if meta_path.exists():
                                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                        except Exception:
                            meta = {}
                    except Exception as e:
                        self.output_ejecucion.insert(tk.END, f"Error en pipeline: {e}\n")
                        return
                else:
                    # Binary already; ensure it's loaded if user edited directly
                    try:
                        Action.load_machine_code(codigo_raw, direccion_int)
                        insts = [l.strip() for l in codigo_raw.strip().splitlines() if l.strip()]
                    except Exception:
                        pass

                # Determine execution start address using meta entry_index if available; fallback to first non-zero line
                start_exec_addr = direccion_int
                try:
                    if isinstance(meta, dict) and 'entry_index' in meta:
                        entry_index = int(meta['entry_index'])
                        start_exec_addr = direccion_int + entry_index
                    else:
                        if insts:
                            zero_word = '0' * 64
                            first_nonzero = next((i for i, l in enumerate(insts) if l != zero_word), 0)
                            start_exec_addr = direccion_int + first_nonzero
                except Exception:
                    start_exec_addr = direccion_int
                # Inform user if start adjusted
                if start_exec_addr != direccion_int:
                    self.output_ejecucion.insert(tk.END, f"Dirección base {hex(direccion_int)} ajustada a inicio de código {hex(start_exec_addr)}.\n")
                    try:
                        # Actualizar campo de inicio con nueva dirección efectiva (sin '0x')
                        self.dir_inicio.delete(0, tk.END)
                        self.dir_inicio.insert(0, format(start_exec_addr, 'x'))
                    except Exception:
                        pass

                # Run execution in a background thread so the GUI stays responsive
                def _run_and_report():
                    try:
                        Action.execute_progam(start_exec_addr)
                        # Prepare result detection and UI updates on main thread
                        def _finish():
                            self.output_ejecucion.insert(tk.END, f"Programa ejecutado desde dirección {hex(start_exec_addr)}.\n")

                            # Prefer metadata produced by the pipeline (.meta.json) to detect
                            # the result address; if not available, fall back to binary scan.
                            direccion_resultado = None
                            try:
                                if image_path:
                                    img_path = Path(image_path)
                                    meta_path = img_path.with_suffix('.meta.json')
                                    if meta_path.exists():
                                        meta2 = json.loads(meta_path.read_text(encoding='utf-8'))
                                        direccion_resultado = meta2.get('result_addr')
                            except Exception:
                                direccion_resultado = None

                            if direccion_resultado is None:
                                codigo = self.codigo_text.get(1.0, tk.END).strip().splitlines()
                                direccion_resultado = _detect_guard_address_from_binary_lines(codigo)
                                if direccion_resultado is None:
                                    direccion_resultado = 131072

                            try:
                                resultado = Data.Memory_D.get_memory_content(direccion_resultado, "decimal")
                            except Exception:
                                resultado = "<no disponible>"

                            self.output_ejecucion.insert(
                                tk.END, f"Resultado guardado en memoria[{direccion_resultado}]: {resultado}\n")

                            # Refresh registers view after program execution
                            try:
                                self._mostrar_registros()
                            except Exception:
                                pass

                        self.output_ejecucion.after(0, _finish)
                    except Exception as e:
                        error_msg = f"Error en ejecución: {e}\n"
                        self.output_ejecucion.after(0, lambda msg=error_msg: self.output_ejecucion.insert(tk.END, msg))

                t = threading.Thread(target=_run_and_report, daemon=True)
                t.start()
                self.output_ejecucion.insert(tk.END, "Ejecución iniciada en segundo plano...\n")

            except Exception as e:
                self.output_ejecucion.insert(tk.END, f"Error: {e}\n")
        else:
            self.output_ejecucion.insert(tk.END, "Dirección de inicio vacía.\n")

    def _start_paso(self):
        direccion = self.dir_inicio.get()
        if not direccion:
            self.output_ejecucion.insert(tk.END, "Dirección de inicio vacía.\n")
            return
        try:
            direccion_int = int(direccion, 16)
            Action.start_stepping(direccion_int)
            self.output_ejecucion.insert(tk.END, f"Modo paso a paso iniciado en dirección {direccion}.\n")
            # Refresh registers display when entering stepping mode
            try:
                self._mostrar_registros()
            except Exception:
                pass
        except Exception as e:
            self.output_ejecucion.insert(tk.END, f"Error al iniciar paso a paso: {e}\n")

    def _paso(self):
        try:
            ret = Action.step()

            instr_asm, opcode_len, did_para = (None, None, False)
            if ret is not None:
                instr_asm, opcode_len, did_para = ret

            # Map opcode length to instruction type
            instr_type = None
            if opcode_len == "64":
                instr_type = "C"
            elif opcode_len in ("54", "59"):
                instr_type = "R"
            elif opcode_len in ("35", "27"):
                instr_type = "I"
            elif opcode_len == "40":
                instr_type = "J"

            # Mostrar estado simple: tipo instrucción y PC en hexadecimal
            pc_hex = Data.CPU_D.get_register_content(0, "hex")
            if instr_type:
                self.output_ejecucion.insert(tk.END, f"Paso ejecutado. Tipo={instr_type} Instr={instr_asm} PC={pc_hex}\n")
            else:
                self.output_ejecucion.insert(tk.END, f"Paso ejecutado. PC={pc_hex}\n")

            # Actualizar banderas en la UI
            try:
                self._update_flags()
            except Exception:
                pass

            # Refresh registers display after each step
            try:
                self._mostrar_registros()
            except Exception:
                pass

            # Si la instrucción fue PARA, detectar dirección de resultado y mostrar valor
            if did_para or not Action.is_stepping():
                # Try to read pipeline metadata file next to the image if available
                direccion_resultado = None
                try:
                    # attempt to find the image path by reading the current editor
                    # (pipeline writes the .i file and the UI replaced editor with binary)
                    # We don't have image_path here, so fall back to scanning binaries
                    pass
                except Exception:
                    pass
                if direccion_resultado is None:
                    codigo = self.codigo_text.get(1.0, tk.END).strip().splitlines()
                    direccion_resultado = _detect_guard_address_from_binary_lines(codigo)
                    if direccion_resultado is None:
                        direccion_resultado = 131072  # fallback para compatibilidad

                resultado = Data.Memory_D.get_memory_content(direccion_resultado, "hex")
                self.output_ejecucion.insert(
                    tk.END, f"Resultado guardado en memoria[{direccion_resultado}]: {resultado}\n")
                # Update flags after program end as well
                try:
                    self._update_flags()
                except Exception:
                    pass
        except Exception as e:
            self.output_ejecucion.insert(tk.END, f"Error en paso: {e}\n")

    def _stop_paso(self):
        try:
            Action.stop_stepping()
            self.output_ejecucion.insert(tk.END, "Paso a paso detenido.\n")
        except Exception as e:
            self.output_ejecucion.insert(tk.END, f"Error al detener paso a paso: {e}\n")

if __name__ == "__main__":
    app = SimuladorComputador()
    app.mainloop()

# --- Nueva ventana de compilación/ensamblado ---
class VentanaCompilacion(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Pipeline de Compilación SPL")
        self.geometry("1600x700")
        self._build_ui()

    def _build_ui(self):
        # Layout: four columns showing the compilation pipeline
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Column 0: Código Alto Nivel (SPL)
        col0 = ttk.LabelFrame(container, text="1. CÓDIGO SPL", padding=8)
        col0.grid(row=0, column=0, padx=4, pady=6, sticky="nsew")
        
        top_row0 = tk.Frame(col0)
        top_row0.pack(fill="x")
        ttk.Button(top_row0, text="Cargar", command=self._cargar_archivo_high).pack(side="left", padx=2)
        ttk.Button(top_row0, text="Preprocesar →", command=self._preprocesar).pack(side="left", padx=2)
        
        self.txt_high = scrolledtext.ScrolledText(col0, width=35, height=25, wrap=tk.NONE)
        self.txt_high.pack(fill="both", expand=True)
        
        # Column 1: Código Preprocesado
        col1 = ttk.LabelFrame(container, text="2. PREPROCESADO", padding=8)
        col1.grid(row=0, column=1, padx=4, pady=6, sticky="nsew")
        
        top_row1 = tk.Frame(col1)
        top_row1.pack(fill="x")
        ttk.Button(top_row1, text="Compilar →", command=self._compilar).pack(side="left", padx=2)
        
        self.txt_preproc = scrolledtext.ScrolledText(col1, width=35, height=25, wrap=tk.NONE)
        self.txt_preproc.pack(fill="both", expand=True)

        # Column 2: Código Assembler
        col2 = ttk.LabelFrame(container, text="3. ENSAMBLADOR", padding=8)
        col2.grid(row=0, column=2, padx=4, pady=6, sticky="nsew")
        
        btn_mid = tk.Frame(col2)
        btn_mid.pack(fill="x")
        ttk.Button(btn_mid, text="Ensamblar →", command=self._ensamblar).pack(side="left", padx=2)
        ttk.Button(btn_mid, text="Tokens", command=self._mostrar_tokens).pack(side="left", padx=2)
        
        self.txt_asm = scrolledtext.ScrolledText(col2, width=35, height=25, wrap=tk.NONE)
        self.txt_asm.pack(fill="both", expand=True)

        # Column 3: Código Binario
        col3 = ttk.LabelFrame(container, text="4. BINARIO", padding=8)
        col3.grid(row=0, column=3, padx=4, pady=6, sticky="nsew")
        
        addr_row = tk.Frame(col3)
        addr_row.pack(fill="x")
        ttk.Label(addr_row, text="Dir. carga (hex):").pack(side="left")
        self.addr_entry = ttk.Entry(addr_row, width=10)
        self.addr_entry.insert(0, "0")
        self.addr_entry.pack(side="left", padx=4)
        ttk.Button(addr_row, text="Cargar", command=self._enlazar_cargar).pack(side="left", padx=2)

        self.txt_reloc = scrolledtext.ScrolledText(col3, width=35, height=25, wrap=tk.NONE)
        self.txt_reloc.pack(fill="both", expand=True)
        
        # Configure grid weights
        for i in range(4):
            container.grid_columnconfigure(i, weight=1)
        container.grid_rowconfigure(0, weight=1)

    # Actions
    def _cargar_archivo_high(self):
        path = filedialog.askopenfilename(
            title="Seleccionar código SPL",
            filetypes=(("SPL files", "*.spl"), ("Todos", "*.*")),
        )
        if not path:
            return
        try:
            txt = Path(path).read_text(encoding="utf-8")
            self.txt_high.delete("1.0", tk.END)
            self.txt_high.insert(tk.END, txt)
            # Clear downstream stages
            self.txt_preproc.delete("1.0", tk.END)
            self.txt_asm.delete("1.0", tk.END)
            self.txt_reloc.delete("1.0", tk.END)
        except Exception as e:
            tk.messagebox.showerror("Error", f"No se pudo cargar: {e}")
    
    def _preprocesar(self):
        """Paso 1: Preprocesar el código SPL (expandir #define e #include)"""
        src = self.txt_high.get("1.0", tk.END).strip()
        if not src:
            tk.messagebox.showwarning("Atención", "No hay código para preprocesar.")
            return
        try:
            from model.preprocesador.preprocessor import preprocess
            preprocessed = preprocess(src, source_file=None)
            self.txt_preproc.delete("1.0", tk.END)
            self.txt_preproc.insert(tk.END, preprocessed)
            # Clear downstream stages
            self.txt_asm.delete("1.0", tk.END)
            self.txt_reloc.delete("1.0", tk.END)
        except Exception as e:
            tk.messagebox.showerror("Error al preprocesar", f"{e}")

    def _compilar(self):
        """Paso 2: Compilar código preprocesado a ensamblador"""
        src = self.txt_preproc.get("1.0", tk.END).strip()
        if not src:
            # Si no hay código preprocesado, intentar preprocesar primero
            self._preprocesar()
            src = self.txt_preproc.get("1.0", tk.END).strip()
            if not src:
                return
        
        try:
            asm = compile_high_level(src)
            self.txt_asm.delete("1.0", tk.END)
            self.txt_asm.insert(tk.END, asm)
            # Clear downstream stages
            self.txt_reloc.delete("1.0", tk.END)
        except Exception as e:
            tk.messagebox.showerror("Error al compilar", f"{e}")

    def _ensamblar(self):
        """Paso 3: Ensamblar código a binario"""
        asm = self.txt_asm.get("1.0", tk.END).strip()
        if not asm:
            tk.messagebox.showwarning("Atención", "No hay código assembler para ensamblar.")
            return
        try:
            maybe = assemble_text(asm)
            if isinstance(maybe, tuple) and len(maybe) == 2:
                insts, meta = maybe
            else:
                insts = maybe
                meta = {}
            self.txt_reloc.delete("1.0", tk.END)
            self.txt_reloc.insert(tk.END, "\n".join(insts) + "\n")
            if meta:
                self.txt_reloc.insert(tk.END, f"\n# META: {meta}\n")
        except Exception as e:
            tk.messagebox.showerror("Error al ensamblar", f"{e}")

    def _enlazar_cargar(self):
        """Paso 4: Cargar código binario en memoria"""
        bits = self.txt_reloc.get("1.0", tk.END).strip().splitlines()
        # Filtrar líneas de comentarios y vacías
        bits = [line for line in bits if line.strip() and not line.strip().startswith('#')]
        
        if not bits:
            tk.messagebox.showwarning("Atención", "No hay código binario para cargar.")
            return
        
        addr_s = self.addr_entry.get().strip()
        if not addr_s:
            addr_s = "0"
        try:
            addr = int(addr_s, 16)
        except Exception:
            tk.messagebox.showerror("Error", "Dirección inválida (use hex).")
            return

        try:
            # Cargar directamente en memoria usando Action
            binary_text = "\n".join(bits)
            Action.load_machine_code(binary_text, addr)
            tk.messagebox.showinfo("Éxito", 
                f"Código cargado en memoria desde dirección 0x{addr:X}\n"
                f"Total de instrucciones: {len(bits)}\n\n"
                f"Puede ejecutar desde la ventana principal.")
        except Exception as e:
            tk.messagebox.showerror("Error al cargar", f"{e}")

    def _mostrar_tokens(self):
        """Mostrar tokens del código ensamblador"""
        asm = self.txt_asm.get("1.0", tk.END).strip()
        if not asm:
            tk.messagebox.showwarning("Atención", "No hay código assembler para tokenizar.")
            return
        try:
            tokens = self._tokenize_asm(asm)
        except Exception as e:
            tk.messagebox.showerror("Error", f"No se pudo tokenizar: {e}")
            return

        win = tk.Toplevel(self)
        win.title("Tokens - Ensamblador")
        win.geometry("600x400")
        txt = scrolledtext.ScrolledText(win, width=70, height=25, font=("Courier", 10))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        
        txt.insert(tk.END, f"{'TIPO':<15} {'VALOR':<30}\n")
        txt.insert(tk.END, "="*50 + "\n")
        
        for kind, val in tokens:
            txt.insert(tk.END, f"{kind:<15} {val:<30}\n")
        
        txt.insert(tk.END, "\n" + "="*50 + "\n")
        txt.insert(tk.END, f"Total de tokens: {len(tokens)}\n")
        txt.configure(state='disabled')

    def _tokenize_asm(self, text):
        import re

        # ISA mnemonics should be marked as RESEV
        isa_mnemonics = {
            'procrastina', 'vuelve', 'suma', 'resta', 'mult', 'divi',
            'copia', 'comp', 'cargaind', 'guardind', 'limp', 'incre', 
            'decre', 'apila', 'desapila',
            'carga', 'guard', 'siregcero', 'siregncero', 'icarga', 
            'isuma', 'iresta', 'imult', 'idivi', 'iand', 'ior', 'ixor', 
            'icomp', 'salta', 'llama', 'sicero', 'sincero', 'sipos', 
            'sineg', 'sioverfl', 'simayor', 'simenor', 'interrup', 'para'
        }

        token_spec = [
            ('COMMENT', r';[^\n]*'),
            ('MEMREF', r'M\[(0x[0-9A-Fa-f]+|0b[01]+|\d+)\]'),
            ('REGISTER', r'R\d+'),
            ('HEX', r'0x[0-9A-Fa-f]+'),
            ('BIN', r'0b[01]+'),
            ('NUMBER', r'\d+'),
            ('IDENT', r'[A-Za-z_][A-Za-z0-9_]*'),
            ('COMMA', r','),
            ('COLON', r':'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('LBRACKET', r'\['),
            ('RBRACKET', r'\]'),
            ('PLUS', r'\+'),
            ('MINUS', r'-'),
            ('SKIP', r'[ \t]+'),
            ('NEWLINE', r'\n+'),
            ('MISMATCH', r'.'),
        ]

        tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_spec)
        get_token = re.compile(tok_regex).finditer
        tokens = []
        for mo in get_token(text):
            kind = mo.lastgroup
            value = mo.group()
            if kind in ('SKIP', 'NEWLINE'):
                continue
            if kind == 'COMMENT':
                tokens.append((kind, value.strip()))
                continue
            # Check if IDENT is actually an ISA mnemonic
            if kind == 'IDENT' and value.lower() in isa_mnemonics:
                tokens.append(('RESEV', value))
            else:
                tokens.append((kind, value))
        return tokens
