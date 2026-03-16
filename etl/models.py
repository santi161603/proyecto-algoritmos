# =============================================================================
# etl/models.py — Entidades del dominio (POO)
# =============================================================================
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RegistroPrecio:
    """
    Representa un punto de datos OHLCV para un activo en una fecha.
    Entidad inmutable del dominio financiero.
    """
    ticker:    str
    fecha:     str           # ISO 8601: YYYY-MM-DD
    open:      Optional[float]
    high:      Optional[float]
    low:       Optional[float]
    close:     Optional[float]
    adj_close: Optional[float]
    volume:    Optional[int]
    anomalia:  bool = False

    def es_completo(self) -> bool:
        """Retorna True si todos los campos OHLC tienen valor."""
        return all(v is not None for v in [self.open, self.high, self.low, self.close])

    def to_dict(self) -> dict:
        return {
            "ticker":    self.ticker,
            "fecha":     self.fecha,
            "open":      self.open,
            "high":      self.high,
            "low":       self.low,
            "close":     self.close,
            "adj_close": self.adj_close,
            "volume":    self.volume,
            "anomalia":  self.anomalia,
        }

    @staticmethod
    def campos_csv() -> List[str]:
        return ["ticker", "fecha", "open", "high", "low", "close", "adj_close", "volume", "anomalia"]


@dataclass
class SerieHistorica:
    """
    Colección ordenada de RegistroPrecio para un activo.
    Encapsula la lógica de acceso a la serie temporal.
    """
    ticker:    str
    registros: List[RegistroPrecio] = field(default_factory=list)

    def agregar(self, registro: RegistroPrecio) -> None:
        self.registros.append(registro)

    def ordenar(self) -> None:
        """Ordena cronológicamente in-place. O(n log n)."""
        self.registros.sort(key=lambda r: r.fecha)

    def get_closes(self) -> List[float]:
        return [r.close for r in self.registros if r.close is not None]

    def get_fechas(self) -> List[str]:
        return [r.fecha for r in self.registros]

    def longitud(self) -> int:
        return len(self.registros)

    def __repr__(self) -> str:
        return f"SerieHistorica(ticker={self.ticker!r}, n={self.longitud()})"


@dataclass
class Activo:
    """
    Representa un instrumento financiero con sus metadatos.
    """
    curr_id:  str
    simbolo:  str
    nombre:   str
    mercado:  str
    serie:    Optional[SerieHistorica] = None

    def tiene_datos(self) -> bool:
        return self.serie is not None and self.serie.longitud() > 0

    def __repr__(self) -> str:
        return f"Activo({self.simbolo!r}, mercado={self.mercado!r})"


@dataclass
class ResultadoETL:
    """
    Resultado de la ejecución del pipeline ETL.
    Facilita el reporte de métricas sin acoplar capas.
    """
    total_activos:      int = 0
    exitosos:           int = 0
    fallidos:           int = 0
    registros_totales:  int = 0
    anomalias_totales:  int = 0
    errores:            List[str] = field(default_factory=list)

    def tasa_exito(self) -> float:
        if self.total_activos == 0:
            return 0.0
        return self.exitosos / self.total_activos * 100

    def resumen(self) -> str:
        return (
            f"Activos procesados : {self.exitosos}/{self.total_activos}\n"
            f"Registros totales  : {self.registros_totales}\n"
            f"Anomalías marcadas : {self.anomalias_totales}\n"
            f"Tasa de éxito      : {self.tasa_exito():.1f}%\n"
            f"Errores            : {len(self.errores)}"
        )
