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
from urllib.parse import urlencode

from etl.interfaces import IExtractor, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import DELAY_ENTRE_REQUESTS, TIMEOUT_REQUEST, MAX_REINTENTOS


class ExtractorYahooFinance(IExtractor):
    """
    Implementación concreta del extractor para Yahoo Finance.
    Implementa IExtractor (Principio DIP / OCP).
    
    Yahoo Finance es más accesible y confiable que Investing.com para scraping.
    Usa el endpoint de descarga CSV que no requiere JavaScript.
    
    Usa cookies y crumb token para autenticación.
    
    Uso:
        logger    = ConsoleFileLogger()
        extractor = ExtractorYahooFinance(logger)
        serie     = extractor.extraer("ECOPETL.BO", "ECOPETROL", "2019-01-01", "2024-12-31")
    """
    
    URL_BASE = "https://query1.finance.yahoo.com/v7/finance/download/"
    URL_CRUMB = "https://query2.finance.yahoo.com/v1/test/getcrumb"
    URL_QUOTE = "https://finance.yahoo.com/quote/"
    
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
        self._crumb = None
        self._cookies_initialized = False
        
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
        
        # Inicializar cookies y obtener crumb si es necesario
        if not self._cookies_initialized:
            if not self._inicializar_sesion():
                self._logger.error(f"{simbolo}: no se pudo inicializar sesión con Yahoo Finance")
                return None
        
        # Convertir fechas a timestamps Unix
        period1 = self._fecha_a_timestamp(fecha_inicio)
        period2 = self._fecha_a_timestamp(fecha_fin)
        
        # Construir URL con crumb
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }
        
        # Agregar crumb si está disponible
        if self._crumb:
            params["crumb"] = self._crumb
        
        url = f"{self.URL_BASE}{simbolo_yahoo}?{urlencode(params)}"
        
        # Descargar datos con reintentos
        csv_text = self._descargar_con_reintentos(url)
        
        if csv_text is None:
            self._logger.error(f"{simbolo}: descarga fallida después de todos los reintentos")
            return None
        
        # Parsear CSV
        registros = self._parsear_csv(csv_text, simbolo)
        
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
    
    def _inicializar_sesion(self) -> bool:
        """
        Inicializa sesión con Yahoo Finance obteniendo cookies y crumb token.
        El crumb es un token CSRF necesario para la autenticación.
        """
        try:
            self._logger.info("Inicializando sesión con Yahoo Finance...")
            
            # Paso 1: Visitar página principal para obtener cookies
            response = self._session.get(
                self.URL_QUOTE + "SPY",  # Usar un símbolo conocido
                headers=self.HEADERS,
                timeout=TIMEOUT_REQUEST,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                self._logger.error(f"Error al obtener cookies: HTTP {response.status_code}")
                return False
            
            time.sleep(0.5)
            
            # Paso 2: Intentar obtener crumb
            try:
                crumb_response = self._session.get(
                    self.URL_CRUMB,
                    headers=self.HEADERS,
                    timeout=TIMEOUT_REQUEST
                )
                
                if crumb_response.status_code == 200:
                    self._crumb = crumb_response.text.strip()
                    self._logger.info(f"Crumb obtenido exitosamente")
                else:
                    # El crumb puede no ser necesario para todos los símbolos
                    self._logger.advertencia(
                        f"No se pudo obtener crumb (HTTP {crumb_response.status_code}), "
                        "continuando sin él..."
                    )
            except Exception as e:
                self._logger.advertencia(f"Error al obtener crumb: {e}, continuando sin él...")
            
            self._cookies_initialized = True
            self._logger.info("Sesión inicializada correctamente")
            return True
            
        except requests.RequestException as e:
            self._logger.error(f"Error al inicializar sesión: {e}")
            return False
    
    def _fecha_a_timestamp(self, fecha_iso: str) -> int:
        """Convierte fecha YYYY-MM-DD a timestamp Unix."""
        dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
        return int(dt.timestamp())
    
    def _descargar_con_reintentos(self, url: str, 
                                   reintentos: int = MAX_REINTENTOS) -> Optional[str]:
        """Descarga contenido con estrategia de reintentos."""
        for intento in range(1, reintentos + 1):
            try:
                time.sleep(0.5)  # Pausa cortés
                
                response = self._session.get(
                    url,
                    headers=self.HEADERS,
                    timeout=TIMEOUT_REQUEST,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    return response.text
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
            except requests.exceptions.RequestException as e:
                self._logger.error(f"Error inesperado: {e}")
                return None
            
            if intento < reintentos:
                espera = 2 ** intento
                self._logger.info(f"Esperando {espera}s antes del siguiente intento...")
                time.sleep(espera)
        
        return None
    
    def _parsear_csv(self, csv_text: str, simbolo: str) -> List[Dict]:
        """
        Parsea el CSV de Yahoo Finance.
        
        Formato esperado:
        Date,Open,High,Low,Close,Adj Close,Volume
        2019-01-02,2450.0,2500.0,2440.0,2480.0,2480.0,1234567
        """
        registros = []
        lineas = csv_text.strip().split('\n')
        
        if len(lineas) < 2:
            return []
        
        # Saltar header
        for linea in lineas[1:]:
            linea = linea.strip()
            if not linea:
                continue
            
            partes = linea.split(',')
            if len(partes) < 7:
                continue
            
            try:
                fecha = partes[0].strip()
                
                # Validar formato de fecha
                if not self._validar_fecha(fecha):
                    continue
                
                # Parsear valores numéricos (pueden ser 'null' o vacíos)
                open_val = self._parsear_float(partes[1])
                high_val = self._parsear_float(partes[2])
                low_val = self._parsear_float(partes[3])
                close_val = self._parsear_float(partes[4])
                adj_close_val = self._parsear_float(partes[5])
                volume_val = self._parsear_int(partes[6])
                
                # Si todos los precios son None, saltar registro
                if all(v is None for v in [open_val, high_val, low_val, close_val]):
                    continue
                
                registros.append({
                    "ticker": simbolo,
                    "fecha": fecha,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "close": close_val,
                    "adj_close": adj_close_val,
                    "volume": volume_val,
                })
                
            except (ValueError, IndexError) as e:
                self._logger.advertencia(f"Error parseando línea '{linea}': {e}")
                continue
        
        return registros
    
    def _validar_fecha(self, fecha: str) -> bool:
        """Valida que la fecha tenga formato YYYY-MM-DD."""
        patron = r"^\d{4}-\d{2}-\d{2}$"
        return bool(re.match(patron, fecha))
    
    def _parsear_float(self, texto: str) -> Optional[float]:
        """Convierte string a float, retorna None si no es válido."""
        texto = texto.strip().lower()
        if texto in ('', 'null', 'nan', '-'):
            return None
        try:
            return float(texto)
        except ValueError:
            return None
    
    def _parsear_int(self, texto: str) -> Optional[int]:
        """Convierte string a int, retorna None si no es válido."""
        texto = texto.strip().lower()
        if texto in ('', 'null', 'nan', '-'):
            return None
        try:
            return int(float(texto))  # float primero por si tiene decimales
        except ValueError:
            return None
