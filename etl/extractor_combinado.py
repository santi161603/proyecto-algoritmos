# =============================================================================
# etl/extractor_combinado.py — Extractor multi-fuente (Yahoo + Google)
# =============================================================================
from typing import Optional, Dict

from etl.interfaces import IExtractor, ILogger
from etl.models import SerieHistorica, RegistroPrecio


class ExtractorCombinado(IExtractor):
    """
    Ejecuta extracción en dos fuentes y fusiona los resultados:
      1) Yahoo Finance (fuente primaria)
      2) Google Finance (complementaria)

    Regla de fusión por fecha:
      - Se priorizan valores de Yahoo
      - Si un campo viene nulo en Yahoo, se rellena con Google
      - Si una fecha solo existe en Google, se agrega
    """

    _MAPA_EXCHANGE = {
        "LSE": "LON",  # alias más común en Google
    }

    def __init__(
        self,
        extractor_yahoo: IExtractor,
        extractor_google: IExtractor,
        logger: ILogger,
        mapa_mercados: Dict[str, str] | None = None,
        mapa_tickers_google: Dict[str, str] | None = None,
    ):
        self._yahoo = extractor_yahoo
        self._google = extractor_google
        self._logger = logger
        self._mapa_mercados = mapa_mercados or {}
        self._mapa_tickers_google = mapa_tickers_google or {}

    def fuente(self) -> str:
        return "Yahoo Finance + Google Finance"

    def extraer(self, identificador_yahoo: str, simbolo: str,
                fecha_inicio: str, fecha_fin: str) -> Optional[SerieHistorica]:
        serie_yahoo = self._yahoo.extraer(identificador_yahoo, simbolo, fecha_inicio, fecha_fin)

        ticker_google = self._mapa_tickers_google.get(simbolo, simbolo)
        exchange = self._normalizar_exchange(self._mapa_mercados.get(simbolo, "NYSE"))
        identificador_google = f"{ticker_google}:{exchange}"

        google_disponible = True
        if hasattr(self._google, "esta_disponible"):
            try:
                google_disponible = bool(self._google.esta_disponible())
            except Exception:
                google_disponible = True

        serie_google = None
        if google_disponible:
            serie_google = self._google.extraer(identificador_google, simbolo, fecha_inicio, fecha_fin)

        if serie_yahoo is None and serie_google is None:
            self._logger.error(f"{simbolo}: sin datos en ambas fuentes")
            return None
        if serie_yahoo is None:
            self._logger.advertencia(f"{simbolo}: Yahoo falló, se usa solo Google")
            return serie_google
        if serie_google is None:
            if google_disponible:
                self._logger.advertencia(f"{simbolo}: Google falló, se usa solo Yahoo")
            return serie_yahoo

        serie_fusionada = self._fusionar_series(serie_yahoo, serie_google, simbolo)
        self._logger.info(
            f"{simbolo}: fusión completada "
            f"(Yahoo={serie_yahoo.longitud()}, Google={serie_google.longitud()}, "
            f"Final={serie_fusionada.longitud()})"
        )
        return serie_fusionada

    def cerrar(self) -> None:
        # Cierre defensivo por si la implementación concreta expone `cerrar()`
        if hasattr(self._yahoo, "cerrar"):
            self._yahoo.cerrar()
        if hasattr(self._google, "cerrar"):
            self._google.cerrar()

    def _normalizar_exchange(self, exchange: str) -> str:
        ex = (exchange or "NYSE").strip().upper()
        return self._MAPA_EXCHANGE.get(ex, ex)

    def _fusionar_series(self, s1: SerieHistorica, s2: SerieHistorica, simbolo: str) -> SerieHistorica:
        por_fecha: Dict[str, RegistroPrecio] = {}

        for r in s1.registros:
            por_fecha[r.fecha] = r

        for r2 in s2.registros:
            r1 = por_fecha.get(r2.fecha)
            if r1 is None:
                por_fecha[r2.fecha] = r2
                continue

            por_fecha[r2.fecha] = RegistroPrecio(
                ticker=simbolo,
                fecha=r1.fecha,
                open=r1.open if r1.open is not None else r2.open,
                high=r1.high if r1.high is not None else r2.high,
                low=r1.low if r1.low is not None else r2.low,
                close=r1.close if r1.close is not None else r2.close,
                adj_close=r1.adj_close if r1.adj_close is not None else r2.adj_close,
                volume=r1.volume if r1.volume is not None else r2.volume,
                anomalia=False,
            )

        serie = SerieHistorica(ticker=simbolo, registros=list(por_fecha.values()))
        serie.ordenar()
        return serie
