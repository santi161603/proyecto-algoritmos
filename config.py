# =============================================================================
# config.py — Configuración global del proyecto
# =============================================================================

from datetime import datetime

# ---------------------------------------------------------------------------
# Horizonte temporal
# ---------------------------------------------------------------------------
FECHA_INICIO = "2019-01-01"
FECHA_FIN    = datetime.today().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Portafolio de activos - Yahoo Finance
# Formato: (simbolo_yahoo, simbolo, nombre_legible, mercado)
#   Nota: varios tickers locales BVC no están disponibles directamente en Yahoo.
#   Se usan tickers válidos en Yahoo (incluyendo ADRs de la región) para asegurar
#   reproducibilidad del ETL.
# ---------------------------------------------------------------------------
ACTIVOS_YAHOO = [
    # --- Acciones/ADRs LatAm disponibles en Yahoo ---
    {"simbolo_yahoo": "EC",   "simbolo": "EC",   "nombre": "Ecopetrol ADR",            "mercado": "NYSE"},
    {"simbolo_yahoo": "CIB",  "simbolo": "CIB",  "nombre": "Bancolombia ADR",          "mercado": "NYSE"},
    {"simbolo_yahoo": "AVAL", "simbolo": "AVAL", "nombre": "Grupo Aval ADR",           "mercado": "NYSE"},
    {"simbolo_yahoo": "BAP",  "simbolo": "BAP",  "nombre": "Credicorp",                "mercado": "NYSE"},
    {"simbolo_yahoo": "ITUB", "simbolo": "ITUB", "nombre": "Itaú Unibanco",            "mercado": "NYSE"},
    {"simbolo_yahoo": "PBR",  "simbolo": "PBR",  "nombre": "Petrobras",                "mercado": "NYSE"},
    {"simbolo_yahoo": "VALE", "simbolo": "VALE", "nombre": "Vale S.A.",                "mercado": "NYSE"},
    {"simbolo_yahoo": "NU",   "simbolo": "NU",   "nombre": "Nu Holdings",              "mercado": "NYSE"},
    {"simbolo_yahoo": "GGAL", "simbolo": "GGAL", "nombre": "Grupo Financiero Galicia", "mercado": "NASDAQ"},
    {"simbolo_yahoo": "SPY",  "simbolo": "SPY",  "nombre": "SPDR S&P 500 ETF",         "mercado": "NYSE"},
    # --- ETFs Globales ---
    {"simbolo_yahoo": "VOO",          "simbolo": "VOO",       "nombre": "Vanguard S&P 500 ETF",  "mercado": "NYSE"},
    {"simbolo_yahoo": "CSPX.L",       "simbolo": "CSPX",      "nombre": "iShares Core S&P 500",  "mercado": "LSE"},
    {"simbolo_yahoo": "GXG",          "simbolo": "GXG",       "nombre": "Global X Colombia ETF", "mercado": "NYSE"},
    {"simbolo_yahoo": "ILF",          "simbolo": "ILF",       "nombre": "iShares Latin America", "mercado": "NYSE"},
    {"simbolo_yahoo": "EWW",          "simbolo": "EWW",       "nombre": "iShares MSCI Mexico",   "mercado": "NYSE"},
    {"simbolo_yahoo": "XLF",          "simbolo": "XLF",       "nombre": "Financial Select SPDR", "mercado": "NYSE"},
    {"simbolo_yahoo": "XLE",          "simbolo": "XLE",       "nombre": "Energy Select SPDR",    "mercado": "NYSE"},
    {"simbolo_yahoo": "EEM",          "simbolo": "EEM",       "nombre": "iShares MSCI EM",       "mercado": "NYSE"},
    {"simbolo_yahoo": "QQQ",          "simbolo": "QQQ",       "nombre": "Invesco QQQ Trust",     "mercado": "NYSE"},
    {"simbolo_yahoo": "XLK",          "simbolo": "XLK",       "nombre": "Technology Select SPDR", "mercado": "NYSE"},
]

# ---------------------------------------------------------------------------
# Portafolio de activos - Investing.com (DEPRECATED - bloqueado por anti-bot)
# Formato Investing.com: (curr_id, simbolo, nombre_legible, mercado)
#   curr_id → ID numérico interno de Investing.com
#   Para hallarlo: DevTools > Network > filtrar "HistoricalDataAjax" > payload curr_id
# ---------------------------------------------------------------------------
ACTIVOS_INVESTING = [
    # --- Acciones BVC (Colombia) ---
    {"curr_id": "23943",  "simbolo": "ECOPETROL", "nombre": "Ecopetrol S.A.",         "mercado": "BVC"},
    {"curr_id": "23944",  "simbolo": "ISA",        "nombre": "Interconexión Eléctrica","mercado": "BVC"},
    {"curr_id": "23950",  "simbolo": "GEB",        "nombre": "Grupo Energía Bogotá",   "mercado": "BVC"},
    {"curr_id": "23956",  "simbolo": "GRUPOSURA",  "nombre": "Grupo Sura",             "mercado": "BVC"},
    {"curr_id": "23958",  "simbolo": "NUTRESA",    "nombre": "Grupo Nutresa",          "mercado": "BVC"},
    {"curr_id": "23960",  "simbolo": "BANCOLOMBIA","nombre": "Bancolombia",            "mercado": "BVC"},
    {"curr_id": "23962",  "simbolo": "CEMARGOS",   "nombre": "Cementos Argos",         "mercado": "BVC"},
    {"curr_id": "23964",  "simbolo": "CORFICOLCF", "nombre": "Corficolombiana",        "mercado": "BVC"},
    {"curr_id": "23966",  "simbolo": "PFBCOLOM",   "nombre": "Bancolombia Pref.",      "mercado": "BVC"},
    {"curr_id": "23968",  "simbolo": "PFDAVVNDA",  "nombre": "Davivienda Pref.",       "mercado": "BVC"},
    # --- ETFs Globales ---
    {"curr_id": "166030", "simbolo": "VOO",        "nombre": "Vanguard S&P 500 ETF",   "mercado": "NYSE"},
    {"curr_id": "953624", "simbolo": "CSPX",       "nombre": "iShares Core S&P 500",   "mercado": "LSE"},
    {"curr_id": "179504", "simbolo": "GXG",        "nombre": "Global X Colombia ETF",  "mercado": "NYSE"},
    {"curr_id": "179506", "simbolo": "ILF",        "nombre": "iShares Latin America",  "mercado": "NYSE"},
    {"curr_id": "179510", "simbolo": "EWW",        "nombre": "iShares MSCI Mexico",    "mercado": "NYSE"},
    {"curr_id": "179512", "simbolo": "XLF",        "nombre": "Financial Select SPDR",  "mercado": "NYSE"},
    {"curr_id": "179514", "simbolo": "XLE",        "nombre": "Energy Select SPDR",     "mercado": "NYSE"},
    {"curr_id": "179516", "simbolo": "EEM",        "nombre": "iShares MSCI EM",        "mercado": "NYSE"},
    {"curr_id": "179518", "simbolo": "QQQ",        "nombre": "Invesco QQQ Trust",      "mercado": "NYSE"},
    {"curr_id": "179520", "simbolo": "SPY",        "nombre": "SPDR S&P 500 ETF",       "mercado": "NYSE"},
]

# ---------------------------------------------------------------------------
# Rutas del sistema de archivos
# ---------------------------------------------------------------------------
RUTA_RAW     = "data/raw"
RUTA_CLEAN   = "data/clean"
RUTA_MASTER  = "data/master_dataset.csv"
RUTA_LOG     = "logs/etl.log"
RUTA_REPORTE = "reportes/"

# ---------------------------------------------------------------------------
# Parámetros de limpieza
# ---------------------------------------------------------------------------
ZSCORE_UMBRAL_ANOMALIA = 4.0   # |Z| > 4 → anomalía
MAX_GAPS_INTERPOLACION = 5     # máximo días consecutivos a interpolar

# ---------------------------------------------------------------------------
# Parámetros de scraping
# ---------------------------------------------------------------------------
DELAY_ENTRE_REQUESTS = 3.0     # segundos entre requests (scraping ético)
TIMEOUT_REQUEST      = 30      # segundos de timeout por request
MAX_REINTENTOS       = 3       # reintentos ante fallo de red
