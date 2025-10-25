import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

from controller.computer import Action, Data
from tools.flex_pipeline import pipeline_from_text


# Helper: detect GUARD opcode prefix from assembler tables
def _detect_guard_address_from_binary_lines(codigo_lines):
    """Given an iterable of 64-bit instruction strings, return the destination
    memory address used by a GUARD instruction if found, otherwise None.

    This uses the assembler mnemonic table to obtain the opcode bitpattern for
    GUARD and then scans the binary lines for that prefix. When found, the last
    24 bits of the instruction hold the memory address (per encoding).
    """
    try:
        from tools.assembler_from_as import MNEMONIC_TABLE
    except Exception:
        return None

    guard_entry = MNEMONIC_TABLE.get('GUARD')
    if not guard_entry:
        return None
    opcode_bits = guard_entry[2]

    for linea in codigo_lines:
        linea = linea.strip()
        if not linea:
            continue
        if linea.startswith(opcode_bits):
            try:
                addr = int(linea[-24:], 2)
                return addr
            except Exception:
                return None
    return None
import numpy as np
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

    def _crear_area_memoria(self):
        frame = ttk.LabelFrame(self.scroll_frame, text="Memoria", padding=10)
        frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Controls: start address and count and mode
        ctrl_frame = tk.Frame(frame)
        ctrl_frame.pack(anchor="w")

        ttk.Label(ctrl_frame, text="Inicio (dec):").pack(side="left")
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
        ttk.Button(ctrl_frame, text="Guardar cambios", command=self._guardar_memoria).pack(side="left", padx=4)

        # Text area to show/edit memory
        self.mem_text = scrolledtext.ScrolledText(frame, width=40, height=20)
        self.mem_text.pack(pady=6)

        ttk.Label(frame, text="Formato de cada línea: dirección:value (p. ej. 1028:0xFF)").pack(anchor="w")

        # --- Panel de Registros debajo de Memoria ---
        regs_frame = ttk.LabelFrame(self.scroll_frame, text="Registros", padding=10)
        regs_frame.grid(row=1, column=2, padx=10, pady=0, sticky="nsew")

        ctrl_regs = tk.Frame(regs_frame)
        ctrl_regs.pack(anchor="w")

        ttk.Label(ctrl_regs, text="Formato: ").pack(side="left")
        self.regs_mode = ttk.Combobox(ctrl_regs, values=["hex", "decimal", "bin"], width=8)
        self.regs_mode.set("hex")
        self.regs_mode.pack(side="left", padx=4)

        ttk.Button(ctrl_regs, text="Mostrar Registros", command=self._mostrar_registros).pack(side="left", padx=4)

        # Text area to show registers (read-only)
        self.regs_text = scrolledtext.ScrolledText(regs_frame, width=40, height=10)
        self.regs_text.pack(pady=6)
        # Make it read-only by default
        self.regs_text.configure(state='disabled')

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
                if not only_bits:
                    try:
                        insts, image_path = pipeline_from_text(codigo_raw)
                        bin_text = "\n".join(insts) + "\n"
                        # Replace editor with binary image
                        self.codigo_text.delete(1.0, tk.END)
                        self.codigo_text.insert(tk.END, bin_text)
                        # Load into memory at direccion_int
                        Action.load_machine_code(bin_text, direccion_int)
                    except Exception as e:
                        self.output_ejecucion.insert(tk.END, f"Error en pipeline: {e}\n")
                        return

                # Execute the program from the given start address
                Action.execute_progam(direccion_int)
                self.output_ejecucion.insert(
                    tk.END, f"Programa ejecutado desde dirección {direccion}.\n")

                # Detectar la dirección de resultado desde el código binario cargado
                codigo = self.codigo_text.get(1.0, tk.END).strip().splitlines()
                direccion_resultado = _detect_guard_address_from_binary_lines(codigo)
                if direccion_resultado is None:
                    direccion_resultado = 131072  # fallback

                resultado = Data.Memory_D.get_memory_content(direccion_resultado, "hex")
                self.output_ejecucion.insert(
                    tk.END, f"Resultado guardado en memoria[{direccion_resultado}]: {resultado}\n")

                # Refresh registers view after program execution
                try:
                    self._mostrar_registros()
                except Exception:
                    pass

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
                # Detectar la dirección de resultado desde el código binario cargado
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
