# main.py

from view.interfaz import SimuladorComputador  # ✅ Nombre de la clase corregido
from controller import computer  # Importa el backend para inicialización

if __name__ == '__main__':
    # Inicializa la emulación desde el backend
    computer.Action.start_emulation()

    # Lanza la interfaz gráfica
    app = SimuladorComputador()
    app.mainloop()
