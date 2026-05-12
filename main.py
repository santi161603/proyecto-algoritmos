# =============================================================================
# main.py — Punto de entrada del proyecto
# =============================================================================
import os

from config import ACTIVOS_YAHOO, FECHA_INICIO, FECHA_FIN

from etl.logger              import ConsoleFileLogger
from etl.extractor_yfinance  import ExtractorYahooFinance
from etl.extractor_googlefinance import ExtractorGoogleFinance
from etl.extractor_combinado import ExtractorCombinado
from etl.transformador       import TransformadorSerie
from etl.cargador            import CargadorCSV
from etl.pipeline            import PipelineETL


def main():
    # ── Instanciar dependencias (Inyección de Dependencias) ──────────
    logger        = ConsoleFileLogger("logs/etl.log")
    estrategia_anomalias = os.getenv("ESTRATEGIA_ANOMALIAS", "marcar")
    
    # Usar doble fuente: Yahoo + Google Finance
    extractor_yahoo  = ExtractorYahooFinance(logger)
    extractor_google = ExtractorGoogleFinance(logger)

    mapa_mercados = {a["simbolo"]: a.get("mercado", "NYSE") for a in ACTIVOS_YAHOO}
    mapa_tickers_google = {a["simbolo"]: a.get("simbolo", a["simbolo"]) for a in ACTIVOS_YAHOO}

    extractor = ExtractorCombinado(
        extractor_yahoo=extractor_yahoo,
        extractor_google=extractor_google,
        logger=logger,
        mapa_mercados=mapa_mercados,
        mapa_tickers_google=mapa_tickers_google,
    )

    activos       = ACTIVOS_YAHOO
    
    # Si deseas usar Investing.com (puede estar bloqueado):
    # from etl.extractor_investing import ExtractorInvesting
    # from config import ACTIVOS_INVESTING
    # extractor = ExtractorInvesting(logger)
    # activos = ACTIVOS_INVESTING
    
    transformador = TransformadorSerie(logger, estrategia_anomalias=estrategia_anomalias)
    cargador      = CargadorCSV(logger)

    # ── Crear y ejecutar pipeline ────────────────────────────────────
    pipeline  = PipelineETL(extractor, transformador, cargador, logger)
    resultado = pipeline.ejecutar(activos, FECHA_INICIO, FECHA_FIN)

    # ── Liberar recursos ─────────────────────────────────────────────
    extractor.cerrar()

    return resultado


if __name__ == "__main__":
    main()
