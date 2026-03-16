# =============================================================================
# etl/logger.py — Implementación concreta de ILogger
# =============================================================================
import os
import sys
from datetime import datetime
from etl.interfaces import ILogger


class ConsoleFileLogger(ILogger):
    """
    Logger que escribe simultáneamente en consola y en archivo de log.
    Principio SRP: única responsabilidad de registro de eventos.
    """

    NIVELES = {"INFO": "✅", "WARN": "⚠️ ", "ERROR": "❌"}

    def __init__(self, ruta_log: str = "logs/etl.log"):
        os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
        self._ruta = ruta_log

    def _escribir(self, nivel: str, mensaje: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        icono     = self.NIVELES.get(nivel, "  ")
        linea     = f"[{timestamp}] {icono} [{nivel}] {mensaje}"

        # Consola (con manejo de encoding para Windows)
        stream = sys.stderr if nivel == "ERROR" else sys.stdout
        try:
            print(linea, file=stream, flush=True)
        except UnicodeEncodeError:
            # Si falla, reemplazar caracteres problemáticos
            linea_ascii = linea.encode('ascii', 'replace').decode('ascii')
            print(linea_ascii, file=stream, flush=True)

        # Archivo
        with open(self._ruta, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def info(self, mensaje: str)       -> None: self._escribir("INFO",  mensaje)
    def error(self, mensaje: str)      -> None: self._escribir("ERROR", mensaje)
    def advertencia(self, mensaje: str)-> None: self._escribir("WARN",  mensaje)
