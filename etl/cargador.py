# =============================================================================
# etl/cargador.py — Persistencia en CSV
# Implementa ICargador (Principio DIP / OCP)
# =============================================================================
import csv
import os
from typing import List

from etl.interfaces import ICargador, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import RUTA_RAW, RUTA_CLEAN, RUTA_MASTER


class CargadorCSV(ICargador):
    """
    Persiste series históricas en archivos CSV.
    Implementa ICargador (Principio OCP: se puede extender a DB sin
    modificar el pipeline, solo agregando otra implementación de ICargador).

    Responsabilidades:
      - Guardar CSV individual por activo (raw y clean)
      - Consolidar todas las series en un dataset maestro long-format
    """

    def __init__(self, logger: ILogger,
                 ruta_raw: str    = RUTA_RAW,
                 ruta_clean: str  = RUTA_CLEAN,
                 ruta_master: str = RUTA_MASTER):
        self._logger      = logger
        self._ruta_raw    = ruta_raw
        self._ruta_clean  = ruta_clean
        self._ruta_master = ruta_master

    # ------------------------------------------------------------------
    # Implementación de ICargador
    # ------------------------------------------------------------------

    def guardar_serie(self, serie: SerieHistorica, carpeta: str = None) -> bool:
        """
        Guarda una SerieHistorica en CSV individual.
        Nombre de archivo: {TICKER}.csv
        Complejidad: O(n) donde n = registros de la serie.
        """
        destino = carpeta or self._ruta_clean
        os.makedirs(destino, exist_ok=True)

        nombre   = serie.ticker.replace("/", "_").replace("-", "_") + ".csv"
        ruta     = os.path.join(destino, nombre)
        campos   = RegistroPrecio.campos_csv()
        registros = [r.to_dict() for r in serie.registros]

        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                writer.writerows(registros)
            self._logger.info(f"Serie guardada: {ruta} ({len(registros)} registros)")
            return True
        except OSError as e:
            self._logger.error(f"No se pudo escribir {ruta}: {e}")
            return False

    def guardar_maestro(self, series: List[SerieHistorica]) -> bool:
        """
        Consolida todas las series en un único dataset long-format.

        Formato long (una fila por fecha × activo):
            fecha | ticker | open | high | low | close | adj_close | volume | anomalia

        Decisión de diseño:
          Se elige formato long sobre wide porque:
          - Facilita filtros por activo o por fecha con O(1) de lectura
          - No genera columnas vacías cuando los calendarios no coinciden
          - Compatible con análisis futuros de similitud y clustering

        Complejidad: O(A × N) donde A = activos, N = días promedio.
        """
        os.makedirs(os.path.dirname(self._ruta_master), exist_ok=True)
        campos = RegistroPrecio.campos_csv()

        total_registros = 0
        try:
            with open(self._ruta_master, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()

                for serie in series:
                    for registro in serie.registros:
                        writer.writerow(registro.to_dict())
                        total_registros += 1

            self._logger.info(
                f"Dataset maestro generado: {self._ruta_master} "
                f"({total_registros} registros, {len(series)} activos)"
            )
            return True
        except OSError as e:
            self._logger.error(f"Error al escribir dataset maestro: {e}")
            return False

    # ------------------------------------------------------------------
    # Métodos adicionales de utilidad
    # ------------------------------------------------------------------

    def cargar_serie(self, simbolo: str, carpeta: str = None) -> SerieHistorica:
        """
        Carga una serie limpia desde su CSV individual.
        Útil para reanudar el pipeline sin re-extraer.
        """
        destino = carpeta or self._ruta_clean
        nombre  = simbolo.replace("/", "_").replace("-", "_") + ".csv"
        ruta    = os.path.join(destino, nombre)

        serie = SerieHistorica(ticker=simbolo)

        if not os.path.exists(ruta):
            self._logger.advertencia(f"Archivo no encontrado: {ruta}")
            return serie

        with open(ruta, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    registro = RegistroPrecio(
                        ticker    = row["ticker"],
                        fecha     = row["fecha"],
                        open      = self._parse_float(row.get("open")),
                        high      = self._parse_float(row.get("high")),
                        low       = self._parse_float(row.get("low")),
                        close     = self._parse_float(row.get("close")),
                        adj_close = self._parse_float(row.get("adj_close")),
                        volume    = self._parse_int(row.get("volume")),
                        anomalia  = row.get("anomalia", "False") == "True",
                    )
                    serie.agregar(registro)
                except (KeyError, ValueError):
                    continue

        return serie

    def existe_serie(self, simbolo: str, carpeta: str = None) -> bool:
        destino = carpeta or self._ruta_clean
        nombre  = simbolo.replace("/", "_").replace("-", "_") + ".csv"
        return os.path.exists(os.path.join(destino, nombre))

    # ------------------------------------------------------------------
    # Helpers de parseo
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_float(valor) -> float | None:
        if valor in (None, "", "None"):
            return None
        try:
            return float(valor)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(valor) -> int | None:
        if valor in (None, "", "None"):
            return None
        try:
            return int(float(valor))
        except ValueError:
            return None
