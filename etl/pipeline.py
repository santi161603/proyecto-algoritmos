# =============================================================================
# etl/pipeline.py — Orquestador del proceso ETL
# Principio SRP: única responsabilidad de coordinar las tres fases
# Principio DIP: depende de interfaces, no de implementaciones concretas
# =============================================================================
import time
from typing import List

from etl.interfaces import IExtractor, ITransformador, ICargador, ILogger
from etl.models import Activo, SerieHistorica, ResultadoETL
from config import DELAY_ENTRE_REQUESTS


class PipelineETL:
    """
    Orquesta las fases Extracción → Transformación → Carga.

    Recibe sus dependencias por inyección (Principio DIP):
      - extractor:    cualquier IExtractor (Investing, Yahoo, etc.)
      - transformador: cualquier ITransformador
      - cargador:     cualquier ICargador (CSV, DB, etc.)
      - logger:       cualquier ILogger

    Esto permite intercambiar implementaciones sin modificar este orquestador
    (Principio OCP).
    """

    def __init__(self,
                 extractor:     IExtractor,
                 transformador: ITransformador,
                 cargador:      ICargador,
                 logger:        ILogger):
        self._extractor     = extractor
        self._transformador = transformador
        self._cargador      = cargador
        self._logger        = logger

    def ejecutar(self, activos: List[dict],
                 fecha_inicio: str, fecha_fin: str) -> ResultadoETL:
        """
        Ejecuta el pipeline completo para la lista de activos.

        Args:
            activos:      lista de dicts con {curr_id, simbolo, nombre, mercado}
            fecha_inicio: 'YYYY-MM-DD'
            fecha_fin:    'YYYY-MM-DD'

        Returns:
            ResultadoETL con métricas de la ejecución.
        """
        resultado = ResultadoETL(total_activos=len(activos))

        self._logger.info("=" * 60)
        self._logger.info("INICIO PIPELINE ETL")
        self._logger.info(f"Activos     : {len(activos)}")
        self._logger.info(f"Periodo     : {fecha_inicio} → {fecha_fin}")
        self._logger.info(f"Fuente      : {self._extractor.fuente()}")
        self._logger.info("=" * 60)

        series_exitosas: List[SerieHistorica] = []

        for i, datos_activo in enumerate(activos, start=1):
            # Extraer parámetros según la fuente de datos
            # Yahoo Finance usa 'simbolo_yahoo', Investing usa 'curr_id'
            if "simbolo_yahoo" in datos_activo:
                # Extractor Yahoo Finance
                identificador = datos_activo["simbolo_yahoo"]
            elif "curr_id" in datos_activo:
                # Extractor Investing.com
                identificador = datos_activo["curr_id"]
            else:
                self._logger.error(f"Activo sin identificador válido: {datos_activo}")
                continue
                
            simbolo = datos_activo["simbolo"]
            nombre  = datos_activo["nombre"]

            self._logger.info(f"\n[{i}/{len(activos)}] {simbolo} — {nombre}")

            # ── FASE 1: EXTRACCIÓN ─────────────────────────────────────
            serie_raw = self._extractor.extraer(identificador, simbolo, fecha_inicio, fecha_fin)

            if serie_raw is None or serie_raw.longitud() == 0:
                resultado.fallidos += 1
                resultado.errores.append(f"{simbolo}: extracción fallida o sin datos")
                self._logger.error(f"{simbolo}: omitido por falla en extracción")
                time.sleep(DELAY_ENTRE_REQUESTS)
                continue

            # ── FASE 2: TRANSFORMACIÓN ─────────────────────────────────
            serie_limpia = self._transformador.transformar(serie_raw)

            # ── FASE 3: CARGA INDIVIDUAL ───────────────────────────────
            guardado = self._cargador.guardar_serie(serie_limpia)
            if not guardado:
                resultado.errores.append(f"{simbolo}: fallo al guardar CSV individual")

            # Acumular métricas
            n_anomalias = sum(1 for r in serie_limpia.registros if r.anomalia)
            resultado.exitosos           += 1
            resultado.registros_totales  += serie_limpia.longitud()
            resultado.anomalias_totales  += n_anomalias
            series_exitosas.append(serie_limpia)

            # Pausa cortés entre requests (scraping ético)
            time.sleep(DELAY_ENTRE_REQUESTS)

        # ── FASE 3b: CONSOLIDACIÓN DEL DATASET MAESTRO ────────────────
        if series_exitosas:
            self._logger.info("\nConsolidando dataset maestro...")
            self._cargador.guardar_maestro(series_exitosas)
        else:
            self._logger.error("No hay series exitosas — dataset maestro no generado")

        # Resumen final
        self._logger.info("\n" + "=" * 60)
        self._logger.info("RESULTADO FINAL ETL")
        self._logger.info(resultado.resumen())
        self._logger.info("=" * 60)

        return resultado
