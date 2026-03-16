# =============================================================================
# main.py — Punto de entrada del proyecto
# =============================================================================
from config import ACTIVOS_YAHOO, FECHA_INICIO, FECHA_FIN

from etl.logger              import ConsoleFileLogger
from etl.extractor_yfinance  import ExtractorYahooFinance
from etl.transformador       import TransformadorSerie
from etl.cargador            import CargadorCSV
from etl.pipeline            import PipelineETL


def main():
    # ── Instanciar dependencias (Inyección de Dependencias) ──────────
    logger        = ConsoleFileLogger("logs/etl.log")
    
    # Usar Yahoo Finance (más confiable que Investing.com)
    extractor     = ExtractorYahooFinance(logger)
    activos       = ACTIVOS_YAHOO
    
    # Si deseas usar Investing.com (puede estar bloqueado):
    # from etl.extractor_investing import ExtractorInvesting
    # from config import ACTIVOS_INVESTING
    # extractor = ExtractorInvesting(logger)
    # activos = ACTIVOS_INVESTING
    
    transformador = TransformadorSerie(logger)
    cargador      = CargadorCSV(logger)

    # ── Crear y ejecutar pipeline ────────────────────────────────────
    pipeline  = PipelineETL(extractor, transformador, cargador, logger)
    resultado = pipeline.ejecutar(activos, FECHA_INICIO, FECHA_FIN)

    # ── Liberar recursos ─────────────────────────────────────────────
    extractor.cerrar()

    return resultado


if __name__ == "__main__":
    main()
