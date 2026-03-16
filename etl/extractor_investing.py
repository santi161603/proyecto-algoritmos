# =============================================================================
# etl/extractor_investing.py — Scraper de Investing.com
# Implementa IExtractor (Principio DIP)
# =============================================================================
import requests
import time
import csv
import io
from datetime import datetime
from typing import Optional, List, Dict

from etl.interfaces import IExtractor, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import DELAY_ENTRE_REQUESTS, TIMEOUT_REQUEST, MAX_REINTENTOS


class ParserHTMLInvesting:
    """
    Parser manual de la tabla HTML que retorna Investing.com.
    Principio SRP: única responsabilidad de parsear HTML.

    No usa BeautifulSoup para cumplir la restricción del proyecto
    de implementar explícitamente los algoritmos.

    Estructura HTML objetivo:
        <table id="curr_table">
          <thead>...</thead>
          <tbody>
            <tr>
              <td>Feb 27, 2024</td>  ← fecha
              <td>45,230.5</td>      ← precio cierre
              <td>44,980.0</td>      ← precio apertura
              <td>45,400.0</td>      ← máximo
              <td>44,750.0</td>      ← mínimo
              <td>1.23M</td>         ← volumen
              <td>+0.55%</td>        ← variación (ignorar)
            </tr>
            ...
          </tbody>
        </table>
    """

    # Meses abreviados en inglés tal como los retorna Investing.com
    _MESES = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }

    def parsear(self, html: str, ticker: str) -> List[Dict]:
        """
        Extrae todas las filas de la tabla y las retorna como lista de dicts.
        Complejidad: O(n) donde n = longitud del HTML.
        """
        # Aislar el tbody para no parsear el thead
        inicio_tbody = html.find("<tbody>")
        fin_tbody    = html.find("</tbody>")
        if inicio_tbody == -1 or fin_tbody == -1:
            return []

        tbody = html[inicio_tbody + len("<tbody>") : fin_tbody]
        filas = self._extraer_filas(tbody)

        registros = []
        for celdas in filas:
            registro = self._construir_registro(celdas, ticker)
            if registro:
                registros.append(registro)

        return registros

    # ------------------------------------------------------------------
    # Métodos privados de parseo
    # ------------------------------------------------------------------

    def _extraer_filas(self, tbody: str) -> List[List[str]]:
        """Extrae lista de listas de texto de celdas por fila."""
        filas = []
        pos   = 0

        while True:
            ini_tr = tbody.find("<tr", pos)
            if ini_tr == -1:
                break
            fin_tr = tbody.find("</tr>", ini_tr)
            if fin_tr == -1:
                break

            fila_html = tbody[ini_tr : fin_tr + len("</tr>")]
            celdas    = self._extraer_celdas(fila_html)

            if celdas:
                filas.append(celdas)

            pos = fin_tr + 1

        return filas

    def _extraer_celdas(self, fila_html: str) -> List[str]:
        """Extrae el texto de cada <td> de una fila HTML."""
        celdas = []
        pos    = 0

        while True:
            ini_td = fila_html.find("<td", pos)
            if ini_td == -1:
                break

            # Avanzar hasta el cierre del tag de apertura '>'
            ini_contenido = fila_html.find(">", ini_td) + 1
            fin_td        = fila_html.find("</td>", ini_contenido)
            if fin_td == -1:
                break

            texto = fila_html[ini_contenido : fin_td]
            texto = self._limpiar_html(texto).strip()
            celdas.append(texto)

            pos = fin_td + 1

        return celdas

    def _limpiar_html(self, texto: str) -> str:
        """Elimina tags HTML internos de un fragmento de texto."""
        resultado = []
        dentro_tag = False

        for char in texto:
            if char == "<":
                dentro_tag = True
            elif char == ">":
                dentro_tag = False
            elif not dentro_tag:
                resultado.append(char)

        return "".join(resultado)

    def _parsear_fecha(self, texto: str) -> Optional[str]:
        """
        Convierte 'Feb 27, 2024' → '2024-02-27'.
        Retorna None si el formato no coincide.
        """
        texto = texto.strip()
        partes = texto.replace(",", "").split()
        if len(partes) != 3:
            return None

        mes_str, dia_str, anio_str = partes
        mes = self._MESES.get(mes_str)
        if not mes:
            return None

        try:
            return f"{anio_str}-{mes}-{int(dia_str):02d}"
        except ValueError:
            return None

    def _parsear_numero(self, texto: str) -> Optional[float]:
        """
        Limpia y convierte strings numéricos de Investing.com.
        Maneja formatos: '45,230.50', '45.230,50' (europeo), '45230.5'.
        """
        texto = texto.strip().replace("+", "").replace("%", "")

        # Detectar si usa coma como separador decimal (formato europeo)
        tiene_punto = "." in texto
        tiene_coma  = "," in texto

        if tiene_punto and tiene_coma:
            # Ejemplo: '1,234.56' → separador de miles es ','
            if texto.rindex(".") > texto.rindex(","):
                texto = texto.replace(",", "")
            else:
                # Ejemplo: '1.234,56' → separador de miles es '.'
                texto = texto.replace(".", "").replace(",", ".")
        elif tiene_coma and not tiene_punto:
            texto = texto.replace(",", ".")

        try:
            return float(texto)
        except ValueError:
            return None

    def _parsear_volumen(self, texto: str) -> Optional[int]:
        """
        Convierte strings de volumen con sufijos: '1.23M' → 1230000.
        Formatos soportados: K (miles), M (millones), B (billones), '-' (sin datos).
        """
        texto = texto.strip().upper()

        if texto in ("-", "N/A", ""):
            return None

        multiplicadores = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        sufijo = texto[-1] if texto[-1] in multiplicadores else None

        try:
            if sufijo:
                numero = float(texto[:-1].replace(",", ""))
                return int(numero * multiplicadores[sufijo])
            else:
                return int(float(texto.replace(",", "")))
        except ValueError:
            return None

    def _construir_registro(self, celdas: List[str], ticker: str) -> Optional[Dict]:
        """
        Ensambla un dict de registro a partir de las celdas de una fila.
        Investing.com retorna columnas en orden:
            [0] Fecha  [1] Precio  [2] Apertura  [3] Máximo  [4] Mínimo
            [5] Volumen  [6] Variación%
        """
        if len(celdas) < 6:
            return None

        fecha = self._parsear_fecha(celdas[0])
        if not fecha:
            return None

        return {
            "ticker":    ticker,
            "fecha":     fecha,
            "close":     self._parsear_numero(celdas[1]),
            "open":      self._parsear_numero(celdas[2]),
            "high":      self._parsear_numero(celdas[3]),
            "low":       self._parsear_numero(celdas[4]),
            "volume":    self._parsear_volumen(celdas[5]),
            "adj_close": self._parsear_numero(celdas[1]),  # Investing no separa adj_close
        }


class SesionInvesting:
    """
    Gestiona la sesión HTTP con Investing.com.
    Principio SRP: responsabilidad única de manejar conexión y headers.
    Encapsula el manejo de cookies y reintentos.
    """

    URL_BASE    = "https://www.investing.com"
    URL_DATOS   = "https://www.investing.com/instruments/HistoricalDataAjax"

    HEADERS_NAVEGADOR = {
        "User-Agent":       (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept":           "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language":  "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding":  "gzip, deflate, br, zstd",
        "Connection":       "keep-alive",
        "Sec-Ch-Ua":        '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest":   "document",
        "Sec-Fetch-Mode":   "navigate",
        "Sec-Fetch-Site":   "none",
        "Sec-Fetch-User":   "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control":    "max-age=0",
        "DNT":              "1",
    }

    HEADERS_AJAX = {
        "User-Agent":       (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept":           "*/*",
        "Accept-Language":  "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding":  "gzip, deflate, br, zstd",
        "Content-Type":     "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Origin":           "https://www.investing.com",
        "Referer":          "https://www.investing.com/",
        "Sec-Ch-Ua":        '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest":   "empty",
        "Sec-Fetch-Mode":   "cors",
        "Sec-Fetch-Site":   "same-origin",
        "Connection":       "keep-alive",
        "DNT":              "1",
    }

    def __init__(self, logger: ILogger, timeout: int = TIMEOUT_REQUEST):
        self._session = requests.Session()
        self._logger  = logger
        self._timeout = timeout
        self._inicializada = False

    def inicializar(self) -> bool:
        """
        Visita la página principal para obtener cookies de sesión.
        Investing.com requiere cookies válidas para aceptar requests AJAX.
        """
        try:
            # Primera visita para obtener cookies iniciales
            response = self._session.get(
                self.URL_BASE,
                headers=self.HEADERS_NAVEGADOR,
                timeout=self._timeout,
                allow_redirects=True
            )
            
            # Pequeña pausa para simular comportamiento humano
            time.sleep(0.5)
            
            # Visitar una segunda página para establecer más cookies
            self._session.get(
                self.URL_BASE + "/equities/ecopetrol",
                headers=self.HEADERS_NAVEGADOR,
                timeout=self._timeout,
                allow_redirects=True
            )
            
            self._inicializada = True
            self._logger.info("Sesión con Investing.com inicializada correctamente")
            return True
        except requests.RequestException as e:
            self._logger.error(f"No se pudo inicializar sesión: {e}")
            return False

    def post_datos(self, payload: dict, reintentos: int = MAX_REINTENTOS) -> Optional[str]:
        """
        Realiza POST al endpoint de datos históricos con reintentos automáticos.
        Retorna el HTML de respuesta o None si todos los reintentos fallan.

        Estrategia de reintentos: espera exponencial (2s, 4s, 8s).
        """
        if not self._inicializada:
            if not self.inicializar():
                return None

        for intento in range(1, reintentos + 1):
            try:
                # Pequeña pausa antes del request para simular comportamiento humano
                time.sleep(0.8)
                
                response = self._session.post(
                    self.URL_DATOS,
                    data=payload,
                    headers=self.HEADERS_AJAX,
                    timeout=self._timeout,
                    allow_redirects=True
                )
                
                # Verificar status code antes de raise_for_status para mejor logging
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    self._logger.advertencia(
                        f"HTTP 403 (Acceso denegado) en intento {intento}/{reintentos}. "
                        "El sitio puede estar bloqueando el scraping."
                    )
                    # Re-inicializar sesión en caso de 403
                    if intento < reintentos:
                        self._logger.info("Re-inicializando sesión...")
                        self._inicializada = False
                        time.sleep(3)
                        self.inicializar()
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
                self._logger.error(f"Error inesperado en request: {e}")
                return None

            if intento < reintentos:
                espera = 2 ** intento  # 2, 4, 8 segundos
                self._logger.info(f"Esperando {espera}s antes del siguiente intento...")
                time.sleep(espera)

        return None

    def cerrar(self) -> None:
        self._session.close()


class ExtractorInvesting(IExtractor):
    """
    Implementación concreta del extractor para Investing.com.
    Implementa IExtractor (Principio DIP / OCP).

    Orquesta SesionInvesting (conexión) y ParserHTMLInvesting (parseo)
    manteniendo cada responsabilidad separada (Principio SRP).

    Uso:
        logger    = ConsoleFileLogger()
        extractor = ExtractorInvesting(logger)
        serie     = extractor.extraer("23943", "ECOPETROL", "2019-01-01", "2024-12-31")
    """

    def __init__(self, logger: ILogger):
        self._logger  = logger
        self._sesion  = SesionInvesting(logger)
        self._parser  = ParserHTMLInvesting()

    # ------------------------------------------------------------------
    # Implementación de IExtractor
    # ------------------------------------------------------------------

    def fuente(self) -> str:
        return "Investing.com"

    def extraer(self, curr_id: str, simbolo: str,
                fecha_inicio: str, fecha_fin: str) -> Optional[SerieHistorica]:
        """
        Descarga y parsea datos históricos desde Investing.com.

        Algoritmo:
        1. Construir payload con fechas formateadas y curr_id
        2. POST al endpoint AJAX (con reintentos)
        3. Parsear HTML de respuesta extrayendo tabla OHLCV
        4. Construir SerieHistorica con los RegistroPrecio obtenidos

        Complejidad: O(n) donde n = número de registros en el HTML.
        """
        self._logger.info(f"Extrayendo {simbolo} (curr_id={curr_id}) desde {self.fuente()}")

        payload = self._construir_payload(curr_id, fecha_inicio, fecha_fin)
        html    = self._sesion.post_datos(payload)

        if html is None:
            self._logger.error(f"{simbolo}: todos los reintentos fallaron")
            return None

        if not self._es_respuesta_valida(html):
            self._logger.error(f"{simbolo}: respuesta HTML no contiene tabla de datos")
            return None

        dicts_raw = self._parser.parsear(html, simbolo)

        if not dicts_raw:
            self._logger.advertencia(f"{simbolo}: HTML parseado pero sin registros extraídos")
            return None

        serie = self._construir_serie(dicts_raw, simbolo)
        self._logger.info(f"{simbolo}: {serie.longitud()} registros extraídos")

        return serie

    # ------------------------------------------------------------------
    # Métodos privados de soporte
    # ------------------------------------------------------------------

    def _construir_payload(self, curr_id: str, fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Construye el payload POST que espera el endpoint de Investing.com.
        Las fechas deben ir en formato MM/DD/YYYY.
        """
        def fmt(fecha_iso: str) -> str:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
            return dt.strftime("%m/%d/%Y")

        return {
            "curr_id":  curr_id,
            "st_date":  fmt(fecha_inicio),
            "end_date": fmt(fecha_fin),
            "action":   "historical_data",
        }

    def _es_respuesta_valida(self, html: str) -> bool:
        """
        Verifica que el HTML contenga la tabla de datos esperada.
        Investing.com puede retornar páginas de error o CAPTCHA.
        """
        return "<tbody>" in html and "<td" in html

    def _construir_serie(self, dicts_raw: List[dict], simbolo: str) -> SerieHistorica:
        """
        Convierte lista de dicts parseados en SerieHistorica con RegistroPrecio.
        Complejidad: O(n).
        """
        serie = SerieHistorica(ticker=simbolo)

        for d in dicts_raw:
            try:
                registro = RegistroPrecio(
                    ticker    = d["ticker"],
                    fecha     = d["fecha"],
                    open      = d.get("open"),
                    high      = d.get("high"),
                    low       = d.get("low"),
                    close     = d.get("close"),
                    adj_close = d.get("adj_close"),
                    volume    = d.get("volume"),
                )
                serie.agregar(registro)
            except (KeyError, TypeError):
                continue

        serie.ordenar()
        return serie

    def cerrar(self) -> None:
        """Libera recursos de la sesión HTTP."""
        self._sesion.cerrar()
