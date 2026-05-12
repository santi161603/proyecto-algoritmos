from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ResultadoPatrones:
    ticker: str
    total_ventanas_alza: int
    frecuencia_alza_consecutiva: int
    proporcion_alza_consecutiva: float
    total_ventanas_reversion: int
    frecuencia_reversion_v: int
    proporcion_reversion_v: float


@dataclass
class ResultadoRiesgo:
    ticker: str
    n_precios: int
    n_retornos: int
    desviacion_estandar_diaria: float
    volatilidad_historica_anualizada: float
    categoria_riesgo: str = "SIN_CLASIFICAR"


class AnalizadorPatronesVolatilidad:
    """
    Req. 3: frecuencia de patrones con ventanas deslizantes + métricas de volatilidad.

    Patrones implementados:
      1) Alza consecutiva (ejemplo del enunciado)
         Dada una ventana de tamaño w sobre precios C:
           patrón_alza = 1 si C[t] < C[t+1] < ... < C[t+w-1]
         Complejidad por activo: O(n * w)

      2) Reversión en V (patrón adicional formalizado)
         Sobre ventana de tamaño 3 (C1, C2, C3):
           C2 < C1 y C2 < C3
           caída_rel = (C1 - C2) / C1 >= umbral
           rebote_rel = (C3 - C2) / C2 >= umbral
         Complejidad por activo: O(n)

    Volatilidad:
      - Retorno log diario: r_t = ln(C_t / C_{t-1})
      - Desviación estándar diaria: sigma_d = sqrt( (1/n) * sum((r_t - mean(r))^2) )
      - Volatilidad histórica anualizada: sigma_a = sigma_d * sqrt(252)
      Complejidad por activo: O(n)
    """

    def __init__(
        self,
        ventana_alza: int = 5,
        umbral_reversion: float = 0.01,
        dias_mercado: int = 252,
    ):
        if ventana_alza < 2:
            raise ValueError("ventana_alza debe ser >= 2")
        if umbral_reversion < 0:
            raise ValueError("umbral_reversion debe ser >= 0")

        self._ventana_alza = ventana_alza
        self._umbral_reversion = umbral_reversion
        self._dias_mercado = dias_mercado

    @staticmethod
    def _precios_validos(precios: List[float]) -> List[float]:
        return [p for p in precios if p is not None and p > 0]

    @staticmethod
    def retornos_log(precios: List[float]) -> List[float]:
        validos = [p for p in precios if p is not None and p > 0]
        if len(validos) < 2:
            return []

        retornos: List[float] = []
        for i in range(1, len(validos)):
            retornos.append(math.log(validos[i] / validos[i - 1]))
        return retornos

    def frecuencia_patron_alza_consecutiva(self, precios: List[float]) -> Tuple[int, int, float]:
        """
        Cuenta ventanas con incremento estricto en todos sus pasos.

        Ventana w cumple patrón si:
            p0 < p1 < ... < p(w-1)
        """
        serie = self._precios_validos(precios)
        w = self._ventana_alza
        if len(serie) < w:
            return 0, 0, 0.0

        total_ventanas = len(serie) - w + 1
        frecuencia = 0

        for i in range(total_ventanas):
            ventana = serie[i : i + w]
            es_alza = True
            for j in range(1, len(ventana)):
                if not (ventana[j - 1] < ventana[j]):
                    es_alza = False
                    break
            if es_alza:
                frecuencia += 1

        proporcion = frecuencia / total_ventanas if total_ventanas else 0.0
        return total_ventanas, frecuencia, proporcion

    def frecuencia_patron_reversion_v(self, precios: List[float]) -> Tuple[int, int, float]:
        """
        Patrón adicional formalizado: reversión en V en ventana de 3 días.

        Si (c1, c2, c3):
          - c2 es mínimo local: c2 < c1 y c2 < c3
          - caída relativa >= umbral
          - rebote relativo >= umbral
        """
        serie = self._precios_validos(precios)
        if len(serie) < 3:
            return 0, 0, 0.0

        total_ventanas = len(serie) - 2
        frecuencia = 0

        for i in range(total_ventanas):
            c1, c2, c3 = serie[i], serie[i + 1], serie[i + 2]
            if c1 <= 0 or c2 <= 0 or c3 <= 0:
                continue

            es_minimo_local = c2 < c1 and c2 < c3
            if not es_minimo_local:
                continue

            caida_rel = (c1 - c2) / c1
            rebote_rel = (c3 - c2) / c2

            if caida_rel >= self._umbral_reversion and rebote_rel >= self._umbral_reversion:
                frecuencia += 1

        proporcion = frecuencia / total_ventanas if total_ventanas else 0.0
        return total_ventanas, frecuencia, proporcion

    def metricas_volatilidad(self, precios: List[float]) -> Tuple[int, int, float, float]:
        retornos = self.retornos_log(precios)
        if not retornos:
            n_precios = len(self._precios_validos(precios))
            return n_precios, 0, 0.0, 0.0

        n = len(retornos)
        media = sum(retornos) / n
        varianza = sum((r - media) ** 2 for r in retornos) / n
        sigma_diaria = math.sqrt(varianza)
        sigma_anual = sigma_diaria * math.sqrt(self._dias_mercado)

        n_precios = len(self._precios_validos(precios))
        return n_precios, n, sigma_diaria, sigma_anual

    def analizar_activo(self, ticker: str, precios: List[float]) -> Tuple[ResultadoPatrones, ResultadoRiesgo]:
        tva, fa, pa = self.frecuencia_patron_alza_consecutiva(precios)
        tvr, fr, pr = self.frecuencia_patron_reversion_v(precios)
        np, nr, sigma_d, sigma_a = self.metricas_volatilidad(precios)

        patrones = ResultadoPatrones(
            ticker=ticker,
            total_ventanas_alza=tva,
            frecuencia_alza_consecutiva=fa,
            proporcion_alza_consecutiva=pa,
            total_ventanas_reversion=tvr,
            frecuencia_reversion_v=fr,
            proporcion_reversion_v=pr,
        )

        riesgo = ResultadoRiesgo(
            ticker=ticker,
            n_precios=np,
            n_retornos=nr,
            desviacion_estandar_diaria=sigma_d,
            volatilidad_historica_anualizada=sigma_a,
        )
        return patrones, riesgo

    @staticmethod
    def clasificar_riesgo_por_terciles(resultados: List[ResultadoRiesgo]) -> List[ResultadoRiesgo]:
        """
        Clasificación estrictamente algorítmica por terciles de volatilidad anualizada.

        - Tercil bajo   -> CONSERVADOR
        - Tercil medio  -> MODERADO
        - Tercil alto   -> AGRESIVO
        """
        if not resultados:
            return []

        ordenados = sorted(resultados, key=lambda r: r.volatilidad_historica_anualizada)
        n = len(ordenados)
        corte1 = n // 3
        corte2 = (2 * n) // 3

        clasificados: List[ResultadoRiesgo] = []
        for i, item in enumerate(ordenados):
            copia = ResultadoRiesgo(**item.__dict__)
            if i < corte1:
                copia.categoria_riesgo = "CONSERVADOR"
            elif i < corte2:
                copia.categoria_riesgo = "MODERADO"
            else:
                copia.categoria_riesgo = "AGRESIVO"
            clasificados.append(copia)

        return clasificados

    @staticmethod
    def ranking_riesgo_desc(resultados: List[ResultadoRiesgo]) -> List[ResultadoRiesgo]:
        return sorted(resultados, key=lambda r: r.volatilidad_historica_anualizada, reverse=True)

    def analizar_portafolio(self, series_por_ticker: Dict[str, List[float]]) -> Tuple[List[ResultadoPatrones], List[ResultadoRiesgo]]:
        patrones: List[ResultadoPatrones] = []
        riesgos: List[ResultadoRiesgo] = []

        for ticker, precios in sorted(series_por_ticker.items()):
            r_patrones, r_riesgo = self.analizar_activo(ticker, precios)
            patrones.append(r_patrones)
            riesgos.append(r_riesgo)

        riesgos_clasificados = self.clasificar_riesgo_por_terciles(riesgos)
        return patrones, riesgos_clasificados
