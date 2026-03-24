# =============================================================================
# etl/extractor_yfinance.py — Scraper de Yahoo Finance
# Implementa IExtractor (Principio DIP)
# Alternativa más confiable que Investing.com
# =============================================================================
import requests
import time
import re
from datetime import datetime
from typing import Optional, List, Dict

from etl.interfaces import IExtractor, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import DELAY_ENTRE_REQUESTS, TIMEOUT_REQUEST, MAX_REINTENTOS


class ExtractorYahooFinance(IExtractor):
    """
    Implementación concreta del extractor para Yahoo Finance.
    Implementa IExtractor (Principio DIP / OCP).
    
    Yahoo Finance es más accesible y confiable que Investing.com para scraping.
    Esta implementación usa el endpoint JSON de `chart`,
    evitando el flujo de crumb/cookies del endpoint CSV.
    
    Uso:
        logger    = ConsoleFileLogger()
        extractor = ExtractorYahooFinance(logger)
        serie     = extractor.extraer("ECOPETL.BO", "ECOPETROL", "2019-01-01", "2024-12-31")
    """
    
    URL_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
    
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }
    
    def __init__(self, logger: ILogger):
        self._logger = logger
        self._session = requests.Session()
        
    def fuente(self) -> str:
        return "Yahoo Finance"
    
    def extraer(self, simbolo_yahoo: str, simbolo: str,
                fecha_inicio: str, fecha_fin: str) -> Optional[SerieHistorica]:
        """
        Descarga datos históricos desde Yahoo Finance.
        
        Args:
            simbolo_yahoo: Símbolo de Yahoo Finance (ej: "ECOPETL.BO" para BVC)
            simbolo: Símbolo simplificado para identificación interna
            fecha_inicio: Formato 'YYYY-MM-DD'
            fecha_fin: Formato 'YYYY-MM-DD'
            
        Returns:
            SerieHistorica con los datos o None si falla
        """
        self._logger.info(f"Extrayendo {simbolo} ({simbolo_yahoo}) desde {self.fuente()}")
        
        # Convertir fechas a timestamps Unix
        period1 = self._fecha_a_timestamp(fecha_inicio)
        period2 = self._fecha_a_timestamp(fecha_fin)

        # Descargar datos con reintentos desde endpoint JSON
        payload = self._descargar_chart_con_reintentos(simbolo_yahoo, period1, period2)

        if payload is None:
            self._logger.error(f"{simbolo}: descarga fallida después de todos los reintentos")
            return None

        # Parsear JSON
        registros = self._parsear_chart_json(payload, simbolo)
        
        if not registros:
            self._logger.advertencia(f"{simbolo}: CSV descargado pero sin registros válidos")
            return None
        
        # Construir serie
        serie = SerieHistorica(ticker=simbolo)
        for reg_dict in registros:
            try:
                registro = RegistroPrecio(
                    ticker=reg_dict["ticker"],
                    fecha=reg_dict["fecha"],
                    open=reg_dict.get("open"),
                    high=reg_dict.get("high"),
                    low=reg_dict.get("low"),
                    close=reg_dict.get("close"),
                    adj_close=reg_dict.get("adj_close"),
                    volume=reg_dict.get("volume"),
                )
                serie.agregar(registro)
            except (KeyError, TypeError) as e:
                self._logger.advertencia(f"Error al crear registro: {e}")
                continue
        
        serie.ordenar()
        self._logger.info(f"{simbolo}: {serie.longitud()} registros extraídos")
        
        return serie
    
    def cerrar(self) -> None:
        """Libera recursos de la sesión HTTP."""
        self._session.close()
    
    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------
    
    def _fecha_a_timestamp(self, fecha_iso: str) -> int:
        """Convierte fecha YYYY-MM-DD a timestamp Unix."""
        dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
        return int(dt.timestamp())

    def _descargar_chart_con_reintentos(
        self,
        simbolo_yahoo: str,
        period1: int,
        period2: int,
        reintentos: int = MAX_REINTENTOS,
    ) -> Optional[dict]:
        """Descarga JSON de chart con estrategia de reintentos."""
        for intento in range(1, reintentos + 1):
            try:
                time.sleep(0.5)

                params = {
                    "period1": period1,
                    "period2": period2,
                    "interval": "1d",
                    "events": "div,split",
                    "includeAdjustedClose": "true",
                }

                response = self._session.get(
                    f"{self.URL_CHART}{simbolo_yahoo}",
                    headers=self.HEADERS,
                    params=params,
                    timeout=TIMEOUT_REQUEST,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    self._logger.error(f"Símbolo no encontrado (404) en Yahoo Finance")
                    return None
                else:
                    response.raise_for_status()

            except requests.exceptions.HTTPError as e:
                self._logger.advertencia(
                    f"HTTP {response.status_code} en intento {intento}/{reintentos}: {e}"
                )
            except requests.exceptions.ConnectionError as e:
                self._logger.advertencia(f"Error de conexión en intento {intento}: {e}")
            except requests.exceptions.Timeout:
                self._logger.advertencia(f"Timeout en intento {intento}/{reintentos}")
            except ValueError as e:
                self._logger.advertencia(f"JSON inválido en intento {intento}/{reintentos}: {e}")
            except requests.exceptions.RequestException as e:
                self._logger.error(f"Error inesperado: {e}")
                return None

            if intento < reintentos:
                espera = 2 ** intento
                self._logger.info(f"Esperando {espera}s antes del siguiente intento...")
                time.sleep(espera)

        return None

    def _parsear_chart_json(self, payload: dict, simbolo: str) -> List[Dict]:
        """Parsea el JSON del endpoint chart de Yahoo Finance."""
        chart = payload.get("chart", {}) if isinstance(payload, dict) else {}
        resultados = chart.get("result") or []
        errores = chart.get("error")

        if errores:
            descripcion = errores.get("description", "error desconocido") if isinstance(errores, dict) else str(errores)
            self._logger.advertencia(f"Yahoo chart devolvió error para {simbolo}: {descripcion}")
            return []

        if not resultados:
            return []

        resultado = resultados[0]
        timestamps = resultado.get("timestamp") or []
        indicadores = resultado.get("indicators", {})
        quotes = (indicadores.get("quote") or [{}])[0]
        adjclose_arr = ((indicadores.get("adjclose") or [{}])[0]).get("adjclose") or []

        opens = quotes.get("open") or []
        highs = quotes.get("high") or []
        lows = quotes.get("low") or []
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []

        n = len(timestamps)
        registros: List[Dict] = []

        for i in range(n):
            ts = timestamps[i]
            fecha = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")

            open_val = self._valor_i(opens, i)
            high_val = self._valor_i(highs, i)
            low_val = self._valor_i(lows, i)
            close_val = self._valor_i(closes, i)
            adj_close_val = self._valor_i(adjclose_arr, i)
            volume_val = self._valor_i(volumes, i)

            if all(v is None for v in [open_val, high_val, low_val, close_val]):
                continue

            registros.append({
                "ticker": simbolo,
                "fecha": fecha,
                "open": self._parsear_float(open_val),
                "high": self._parsear_float(high_val),
                "low": self._parsear_float(low_val),
                "close": self._parsear_float(close_val),
                "adj_close": self._parsear_float(adj_close_val),
                "volume": self._parsear_int(volume_val),
            })

        return registros

    def _valor_i(self, arr: list, i: int):
        if i < len(arr):
            return arr[i]
        return None
    
    def _validar_fecha(self, fecha: str) -> bool:
        """Valida que la fecha tenga formato YYYY-MM-DD."""
        patron = r"^\d{4}-\d{2}-\d{2}$"
        return bool(re.match(patron, fecha))
    
    def _parsear_float(self, valor) -> Optional[float]:
        """Convierte valor a float, retorna None si no es válido."""
        if valor is None:
            return None
        texto = str(valor).strip().lower()
        if texto in ('', 'null', 'nan', '-'):
            return None
        try:
            return float(texto)
        except ValueError:
            return None

    def _parsear_int(self, valor) -> Optional[int]:
        """Convierte valor a int, retorna None si no es válido."""
        if valor is None:
            return None
        texto = str(valor).strip().lower()
        if texto in ('', 'null', 'nan', '-'):
            return None
        try:
            return int(float(texto))  # float primero por si tiene decimales
        except ValueError:
            return None
