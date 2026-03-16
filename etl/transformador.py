# =============================================================================
# etl/transformador.py — Limpieza y normalización de series temporales
# Implementa ITransformador (Principio DIP / SRP)
# =============================================================================
import math
import copy
from typing import List, Optional, Tuple

from etl.interfaces import ITransformador, ILogger
from etl.models import SerieHistorica, RegistroPrecio
from config import ZSCORE_UMBRAL_ANOMALIA, MAX_GAPS_INTERPOLACION


class DetectorValoresFaltantes:
    """
    Detecta gaps en una serie temporal.
    Principio SRP: única responsabilidad de detección.
    """

    def detectar(self, registros: List[RegistroPrecio]) -> Tuple[List[int], List[int]]:
        """
        Retorna dos listas de índices:
          - completos:   índices con todos los campos OHLC presentes
          - faltantes:   índices con al menos un campo OHLC nulo

        Complejidad: O(n)
        """
        completos  = []
        faltantes  = []

        for i, r in enumerate(registros):
            if r.es_completo():
                completos.append(i)
            else:
                faltantes.append(i)

        return completos, faltantes


class InterpoladorLineal:
    """
    Rellena valores faltantes mediante interpolación lineal.
    Principio SRP: única responsabilidad de interpolación.

    Justificación matemática:
      Para dos puntos conocidos (x0, y0) y (x1, y1), el valor
      interpolado en xi es:
          y(xi) = y0 + (y1 - y0) * (xi - x0) / (x1 - x0)

      Apropiado para series de precios donde los gaps suelen corresponder
      a días festivos o interrupciones de mercado (los precios no hacen
      saltos abruptos en esos periodos).

    Limitación: no se interpola si el gap supera MAX_GAPS_INTERPOLACION
    para evitar fabricar datos durante períodos de suspensión prolongada.

    Complejidad: O(n) por campo, O(n * c) total donde c = número de campos.
    """

    CAMPOS = ["open", "high", "low", "close", "adj_close"]

    def __init__(self, max_gap: int = MAX_GAPS_INTERPOLACION):
        self._max_gap = max_gap

    def interpolar(self, registros: List[RegistroPrecio]) -> List[RegistroPrecio]:
        """
        Aplica interpolación lineal en los campos OHLC y adj_close.
        Modifica una copia de los registros para respetar inmutabilidad.
        """
        resultado = copy.deepcopy(registros)
        n = len(resultado)

        for campo in self.CAMPOS:
            valores = [getattr(r, campo) for r in resultado]
            valores = self._interpolar_campo(valores, n)
            for i in range(n):
                setattr(resultado[i], campo, valores[i])

        return resultado

    def _interpolar_campo(self, valores: List[Optional[float]], n: int) -> List[Optional[float]]:
        """
        Interpola una lista de valores con Nones.
        Itera una sola vez de izquierda a derecha: O(n).
        """
        i = 0
        while i < n:
            if valores[i] is None:
                # Buscar el último valor válido antes del gap
                izq = i - 1
                v_izq = valores[izq] if izq >= 0 else None

                # Buscar el siguiente valor válido después del gap
                j = i + 1
                while j < n and valores[j] is None:
                    j += 1

                tamano_gap = j - i

                if tamano_gap > self._max_gap:
                    # Gap demasiado grande: forward fill si hay valor izquierdo
                    # Decisión: preservar último conocido es menos erróneo
                    # que interpolar durante suspensiones largas.
                    if v_izq is not None:
                        for k in range(i, min(j, n)):
                            valores[k] = v_izq
                    i = j
                    continue

                v_der = valores[j] if j < n else None

                if v_izq is not None and v_der is not None:
                    pasos = j - izq
                    for k in range(i, j):
                        fraccion  = (k - izq) / pasos
                        valores[k] = v_izq + fraccion * (v_der - v_izq)
                elif v_izq is not None:
                    for k in range(i, n):
                        if valores[k] is None:
                            valores[k] = v_izq
                elif v_der is not None:
                    for k in range(i, j):
                        valores[k] = v_der

            i += 1

        return valores


class DetectorAnomalias:
    """
    Detecta retornos diarios estadísticamente anómalos usando Z-score.
    Principio SRP: única responsabilidad de detección de outliers.

    Algoritmo:
      1. Calcular retornos logarítmicos: r_t = ln(P_t / P_{t-1})
      2. Calcular media μ y desviación estándar σ de los retornos
      3. Marcar como anomalía si |z| = |(r_t - μ) / σ| > umbral

    Complejidad: O(n) — dos pasadas lineales (media, luego std)

    Nota: se MARCA la anomalía pero NO se elimina el registro.
    Eventos como el crash de COVID-19 (mar-2020) son retornos extremos
    reales y deben preservarse para análisis de volatilidad.
    """

    def __init__(self, umbral: float = ZSCORE_UMBRAL_ANOMALIA):
        self._umbral = umbral

    def detectar(self, registros: List[RegistroPrecio]) -> List[RegistroPrecio]:
        """
        Marca el campo `anomalia = True` en registros con retorno atípico.
        Retorna la misma lista con las marcas actualizadas.
        """
        closes = [r.close for r in registros if r.close is not None]
        if len(closes) < 2:
            return registros

        retornos = self._calcular_retornos_log(closes)
        media, std = self._estadisticas(retornos)

        if std < 1e-12:
            return registros

        idx_ret = 0
        for i, registro in enumerate(registros):
            if i == 0 or registro.close is None:
                registro.anomalia = False
                continue
            z = abs((retornos[idx_ret] - media) / std)
            registro.anomalia = z > self._umbral
            idx_ret += 1

        return registros

    def _calcular_retornos_log(self, closes: List[float]) -> List[float]:
        """
        Retornos logarítmicos: ln(P_t / P_{t-1}).
        Complejidad: O(n).
        """
        retornos = []
        for i in range(1, len(closes)):
            if closes[i] > 0 and closes[i - 1] > 0:
                retornos.append(math.log(closes[i] / closes[i - 1]))
            else:
                retornos.append(0.0)
        return retornos

    def _estadisticas(self, retornos: List[float]) -> Tuple[float, float]:
        """
        Calcula media y desviación estándar poblacional.
        Complejidad: O(n).
        """
        n    = len(retornos)
        media = sum(retornos) / n
        var   = sum((r - media) ** 2 for r in retornos) / n
        return media, math.sqrt(var)


class TransformadorSerie(ITransformador):
    """
    Pipeline de transformación/limpieza para una SerieHistorica.
    Implementa ITransformador (Principio DIP).
    Orquesta los tres componentes de limpieza (Principio SRP).

    Flujo:
      1. DetectorValoresFaltantes  → identifica registros incompletos
      2. InterpoladorLineal        → rellena valores faltantes
      3. DetectorAnomalias         → marca retornos atípicos
    """

    def __init__(self, logger: ILogger):
        self._logger       = logger
        self._detector     = DetectorValoresFaltantes()
        self._interpolador = InterpoladorLineal()
        self._anomalias    = DetectorAnomalias()

    def transformar(self, serie: SerieHistorica) -> SerieHistorica:
        """
        Ejecuta el pipeline completo sobre la serie.
        Retorna una nueva SerieHistorica con datos limpios.
        """
        self._logger.info(f"Transformando {serie.ticker} ({serie.longitud()} registros)")

        registros = serie.registros

        # Paso 1: detectar faltantes
        completos, faltantes = self._detector.detectar(registros)
        if faltantes:
            self._logger.advertencia(
                f"{serie.ticker}: {len(faltantes)} registros con valores faltantes"
            )

        # Paso 2: interpolar
        registros = self._interpolador.interpolar(registros)

        # Paso 3: detectar anomalías
        registros = self._anomalias.detectar(registros)
        n_anomalias = sum(1 for r in registros if r.anomalia)
        if n_anomalias:
            self._logger.advertencia(
                f"{serie.ticker}: {n_anomalias} registros marcados como anomalía"
            )

        # Construir nueva serie limpia
        serie_limpia = SerieHistorica(ticker=serie.ticker, registros=registros)
        self._logger.info(f"{serie.ticker}: transformación completada")

        return serie_limpia
