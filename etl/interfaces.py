# =============================================================================
# etl/interfaces.py — Contratos abstractos (Principios ISP y DIP de SOLID)
# =============================================================================
from abc import ABC, abstractmethod
from typing import List, Optional
from etl.models import SerieHistorica, RegistroPrecio


class IExtractor(ABC):
    """
    Contrato para cualquier fuente de datos financieros.
    Principio ISP: interfaz mínima y específica para extracción.
    Principio DIP: las capas superiores dependen de esta abstracción,
                   no de implementaciones concretas.
    """

    @abstractmethod
    def extraer(self, curr_id: str, simbolo: str,
                fecha_inicio: str, fecha_fin: str) -> Optional[SerieHistorica]:
        """
        Extrae datos históricos para un activo.
        Retorna SerieHistorica o None si falla.
        """

    @abstractmethod
    def fuente(self) -> str:
        """Nombre legible de la fuente (para logs y reportes)."""


class ITransformador(ABC):
    """
    Contrato para el proceso de limpieza y normalización.
    Principio SRP: responsabilidad única de transformación.
    """

    @abstractmethod
    def transformar(self, serie: SerieHistorica) -> SerieHistorica:
        """
        Recibe una serie cruda y retorna la serie limpia.
        No modifica el objeto original (inmutabilidad funcional).
        """


class ICargador(ABC):
    """
    Contrato para persistencia de datos.
    Principio OCP: agregar nuevos destinos (DB, S3, etc.)
                   sin modificar el pipeline.
    """

    @abstractmethod
    def guardar_serie(self, serie: SerieHistorica) -> bool:
        """Persiste una serie individual. Retorna True si exitoso."""

    @abstractmethod
    def guardar_maestro(self, series: List[SerieHistorica]) -> bool:
        """Consolida todas las series en el dataset maestro."""


class ILogger(ABC):
    """Contrato para logging desacoplado."""

    @abstractmethod
    def info(self, mensaje: str) -> None: ...

    @abstractmethod
    def error(self, mensaje: str) -> None: ...

    @abstractmethod
    def advertencia(self, mensaje: str) -> None: ...
