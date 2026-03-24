# =============================================================================
# etl/extractor_googlefinance.py — Extractor de Google Finance (quote endpoint)
# Implementa IExtractor (Principio DIP / OCP)
# =============================================================================
import requests
import time
import re
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from etl.interfaces import IExtractor, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import TIMEOUT_REQUEST, MAX_REINTENTOS


class ExtractorGoogleFinance(IExtractor):
    """
        Implementación concreta del extractor para Google Finance.

        Usa endpoint de quote HTML:
            https://www.google.com/finance/quote/{TICKER}:{EXCHANGE}

        Nota importante:
        - El endpoint histórico legacy `getprices` actualmente devuelve 404.
        - Este extractor obtiene un snapshot diario desde los callbacks embebidos
            (precio de cierre del día), y construye un registro OHLCV para esa fecha.
            Se usa como fuente complementaria de Yahoo dentro del extractor combinado.

    Identificador esperado en `extraer`:
      - "TICKER:EXCHANGE"  (ej. "EC:NYSE", "GGAL:NASDAQ")
      - o solo "TICKER"    (usa exchange por defecto = "NYSE")
    """

    URL_QUOTE = "https://www.google.com/finance/quote/"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/plain,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }

    _MAPA_EXCHANGE = {
        "LSE": "LON",
    }

    def __init__(self, logger: ILogger):
        self._logger = logger
        self._session = requests.Session()
        self._deshabilitado = False

    def fuente(self) -> str:
        return "Google Finance"

    def extraer(self, identificador_google: str, simbolo: str,
                fecha_inicio: str, fecha_fin: str) -> Optional[SerieHistorica]:
        """
        Descarga datos diarios OHLCV desde Google Finance.
        """
        if self._deshabilitado:
            return None

        ticker_g, exchange_g = self._parsear_identificador(identificador_google)
        self._logger.info(
            f"Extrayendo {simbolo} ({ticker_g}:{exchange_g}) desde {self.fuente()}"
        )

        payload = self._descargar_quote_con_reintentos(
            ticker=ticker_g,
            exchange=exchange_g,
        )

        if payload is None:
            self._logger.error(f"{simbolo}: descarga fallida en Google Finance")
            return None

        dicts_raw = self._parsear_quote_callback(payload, simbolo, fecha_inicio, fecha_fin)
        if not dicts_raw:
            self._logger.advertencia(
                f"{simbolo}: respuesta recibida pero sin registros válidos en Google"
            )
            return None

        serie = SerieHistorica(ticker=simbolo)
        for d in dicts_raw:
            try:
                registro = RegistroPrecio(
                    ticker=d["ticker"],
                    fecha=d["fecha"],
                    open=d.get("open"),
                    high=d.get("high"),
                    low=d.get("low"),
                    close=d.get("close"),
                    adj_close=d.get("adj_close"),
                    volume=d.get("volume"),
                )
                serie.agregar(registro)
            except (KeyError, TypeError):
                continue

        serie.ordenar()
        self._logger.info(f"{simbolo}: {serie.longitud()} registros extraídos en Google")
        return serie

    def cerrar(self) -> None:
        self._session.close()

    def esta_disponible(self) -> bool:
        """Indica si Google Finance está habilitado para extracción."""
        return not self._deshabilitado

    # ------------------------------------------------------------------
    # Privados
    # ------------------------------------------------------------------

    def _parsear_identificador(self, identificador: str) -> Tuple[str, str]:
        texto = (identificador or "").strip()
        if not texto:
            return "", "NYSE"

        if ":" in texto:
            ticker, exchange = texto.split(":", 1)
            exchange = exchange.strip().upper() or "NYSE"
            exchange = self._MAPA_EXCHANGE.get(exchange, exchange)
            return ticker.strip(), exchange

        return texto, "NYSE"

    def _descargar_quote_con_reintentos(
        self,
        ticker: str,
        exchange: str,
        reintentos: int = MAX_REINTENTOS,
    ) -> Optional[str]:
        exchange_candidates = [
            exchange,
            self._MAPA_EXCHANGE.get(exchange, exchange),
            "NYSE",
            "NASDAQ",
            "NYSEARCA",
            "LON",
        ]
        # conservar orden y eliminar duplicados
        vistos = set()
        exchanges = []
        for ex in exchange_candidates:
            ex = (ex or "").strip().upper()
            if ex and ex not in vistos:
                vistos.add(ex)
                exchanges.append(ex)

        for intento in range(1, reintentos + 1):
            for ex in exchanges:
                try:
                    response = self._session.get(
                        f"{self.URL_QUOTE}{ticker}:{ex}",
                        headers=self.HEADERS,
                        timeout=TIMEOUT_REQUEST,
                        allow_redirects=True,
                    )

                    if response.status_code == 200 and "AF_initDataCallback" in response.text:
                        return response.text

                    if response.status_code == 404:
                        continue

                    response.raise_for_status()

                except requests.exceptions.Timeout:
                    self._logger.advertencia(f"Timeout Google intento {intento}/{reintentos}")
                except requests.exceptions.RequestException as e:
                    self._logger.advertencia(
                        f"Error de red Google intento {intento}/{reintentos}: {e}"
                    )

            if intento < reintentos:
                espera = 2 ** intento
                self._logger.info(f"Google: esperando {espera}s para reintento...")
                time.sleep(espera)

        return None

    def _parsear_quote_callback(self, html: str, simbolo: str,
                                fecha_inicio: str, fecha_fin: str) -> List[Dict]:
        """
        Parsea bloque AF_initDataCallback (ds:6) para construir snapshot diario.
        Dado que Google no expone histórico público estable en este endpoint,
        devuelve 1 registro del día de cotización disponible.
        """
        dt_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        dt_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

        m_ds6 = re.search(
            r"AF_initDataCallback\(\{key:\s*'ds:6'.*?\}\);</script>",
            html,
            re.DOTALL,
        )
        bloque = m_ds6.group(0) if m_ds6 else html

        # Precio de cierre/snapshot: primer vector [precio, variación, %variación,2,2,2]
        m_close = re.search(
            r"\[(-?\d+(?:\.\d+)?),-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,2,2,2\]",
            bloque,
        )
        if not m_close:
            return []
        close_v = self._parse_float(m_close.group(1))
        if close_v is None:
            return []

        # Timestamp del snapshot (epoch seconds)
        timestamps = re.findall(r"\[(1\d{9})\]", bloque)
        ts = int(timestamps[-1]) if timestamps else int(time.time())
        fecha = datetime.utcfromtimestamp(ts).date()

        if fecha < dt_ini or fecha > dt_fin:
            return []

        # Para consistencia OHLC cuando Google no entrega histórico diario detallado
        # en endpoint público, se construye vela plana con close.
        open_v = close_v
        high_v = close_v
        low_v = close_v

        return [{
            "ticker": simbolo,
            "fecha": fecha.strftime("%Y-%m-%d"),
            "open": open_v,
            "high": high_v,
            "low": low_v,
            "close": close_v,
            "adj_close": close_v,
            "volume": None,
        }]

    @staticmethod
    def _parse_float(valor: str) -> Optional[float]:
        texto = str(valor).strip().lower()
        if texto in ("", "nan", "null", "-"):
            return None
        try:
            return float(texto)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(valor: str) -> Optional[int]:
        texto = str(valor).strip().lower()
        if texto in ("", "nan", "null", "-"):
            return None
        try:
            return int(float(texto))
        except ValueError:
            return None
