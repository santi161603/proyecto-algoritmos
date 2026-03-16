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
#   Para BVC (Colombia): agregar sufijo .BO
#   Para NYSE/NASDAQ: usar ticker directo
# ---------------------------------------------------------------------------
ACTIVOS_YAHOO = [
    # --- Acciones BVC (Colombia) ---
    {"simbolo_yahoo": "ECOPETROL.BO", "simbolo": "ECOPETROL", "nombre": "Ecopetrol S.A.",         "mercado": "BVC"},
    {"simbolo_yahoo": "ISA.BO",       "simbolo": "ISA",       "nombre": "Interconexión Eléctrica","mercado": "BVC"},
    {"simbolo_yahoo": "GEB.BO",       "simbolo": "GEB",       "nombre": "Grupo Energía Bogotá",   "mercado": "BVC"},
    {"simbolo_yahoo": "GRUPOSURA.BO", "simbolo": "GRUPOSURA", "nombre": "Grupo Sura",             "mercado": "BVC"},
    {"simbolo_yahoo": "NUTRESA.BO",   "simbolo": "NUTRESA",   "nombre": "Grupo Nutresa",          "mercado": "BVC"},
    {"simbolo_yahoo": "CIB.BO",       "simbolo": "BANCOLOMBIA","nombre": "Bancolombia",           "mercado": "BVC"},
    {"simbolo_yahoo": "CEMARGOS.BO",  "simbolo": "CEMARGOS",  "nombre": "Cementos Argos",        "mercado": "BVC"},
    {"simbolo_yahoo": "CORFICOLCF.BO","simbolo": "CORFICOLCF","nombre": "Corficolombiana",       "mercado": "BVC"},
    {"simbolo_yahoo": "PFBCOLOM.BO",  "simbolo": "PFBCOLOM",  "nombre": "Bancolombia Pref.",     "mercado": "BVC"},
    {"simbolo_yahoo": "PFDAVVNDA.BO", "simbolo": "PFDAVVNDA", "nombre": "Davivienda Pref.",      "mercado": "BVC"},
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
    {"simbolo_yahoo": "SPY",          "simbolo": "SPY",       "nombre": "SPDR S&P 500 ETF",      "mercado": "NYSE"},
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
