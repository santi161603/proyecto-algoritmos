import copy
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import MAX_GAPS_INTERPOLACION, ZSCORE_UMBRAL_ANOMALIA
from etl.interfaces import ILogger, ITransformador
from etl.models import RegistroPrecio, SerieHistorica


@dataclass
class ResultadoLimpieza:
    registros_entrada: int = 0
    registros_salida: int = 0
    registros_eliminados: int = 0
    duplicados_consolidados: int = 0
    faltantes_detectados: int = 0
    faltantes_interpolados: int = 0
    inconsistencias_detectadas: int = 0
    inconsistencias_corregidas: int = 0
    anomalias_detectadas: int = 0
    anomalias_marcadas: int = 0
    anomalias_eliminadas: int = 0


class DetectorValoresFaltantes:
    def detectar(self, registros: List[RegistroPrecio]) -> Tuple[List[int], List[int]]:
        completos: List[int] = []
        faltantes: List[int] = []

        for indice, registro in enumerate(registros):
            if registro.es_completo():
                completos.append(indice)
            else:
                faltantes.append(indice)

        return completos, faltantes


class InterpoladorLineal:
    CAMPOS = ["open", "high", "low", "close", "adj_close", "volume"]

    def __init__(self, max_gap: int = MAX_GAPS_INTERPOLACION):
        self._max_gap = max_gap

    def interpolar(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], int]:
        resultado = copy.deepcopy(registros)
        total_interpolados = 0

        for campo in self.CAMPOS:
            valores = [getattr(registro, campo) for registro in resultado]
            valores, interpolados = self._interpolar_campo(valores)
            total_interpolados += interpolados

            for indice, valor in enumerate(valores):
                if campo == "volume" and valor is not None:
                    setattr(resultado[indice], campo, int(round(valor)))
                else:
                    setattr(resultado[indice], campo, valor)

        return resultado, total_interpolados

    def _interpolar_campo(self, valores: List[Optional[float]]) -> Tuple[List[Optional[float]], int]:
        n = len(valores)
        if n == 0:
            return valores, 0

        rellenados = 0
        indice = 0

        while indice < n:
            if valores[indice] is not None:
                indice += 1
                continue

            izquierda = indice - 1
            valor_izq = valores[izquierda] if izquierda >= 0 else None

            derecha = indice + 1
            while derecha < n and valores[derecha] is None:
                derecha += 1

            longitud_gap = derecha - indice
            valor_der = valores[derecha] if derecha < n else None

            if longitud_gap > self._max_gap:
                if valor_izq is not None:
                    limite = min(derecha, n)
                    for relleno in range(indice, limite):
                        if valores[relleno] is None:
                            valores[relleno] = valor_izq
                            rellenados += 1
                indice = derecha
                continue

            if valor_izq is not None and valor_der is not None:
                pasos = derecha - izquierda
                for relleno in range(indice, derecha):
                    fraccion = (relleno - izquierda) / pasos
                    valores[relleno] = valor_izq + fraccion * (valor_der - valor_izq)
                    rellenados += 1
            elif valor_izq is not None:
                for relleno in range(indice, n):
                    if valores[relleno] is None:
                        valores[relleno] = valor_izq
                        rellenados += 1
            elif valor_der is not None:
                for relleno in range(indice, derecha):
                    valores[relleno] = valor_der
                    rellenados += 1

            indice = derecha

        return valores, rellenados


class LimpiadorCalidadDatos:
    def __init__(
        self,
        max_gap: int = MAX_GAPS_INTERPOLACION,
        umbral_anomalia: float = ZSCORE_UMBRAL_ANOMALIA,
        estrategia_anomalias: str = "marcar",
    ):
        self._detector = DetectorValoresFaltantes()
        self._interpolador = InterpoladorLineal(max_gap=max_gap)
        self._umbral_anomalia = umbral_anomalia
        self._estrategia_anomalias = estrategia_anomalias.lower().strip()

    def limpiar(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], ResultadoLimpieza]:
        resultado = ResultadoLimpieza(registros_entrada=len(registros))

        if not registros:
            return [], resultado

        ordenados = copy.deepcopy(sorted(registros, key=lambda registro: (registro.fecha, registro.ticker)))
        consolidados, duplicados = self._consolidar_duplicados(ordenados)
        resultado.duplicados_consolidados = duplicados

        _, faltantes = self._detector.detectar(consolidados)
        resultado.faltantes_detectados = len(faltantes)

        consolidados, detectadas, corregidas = self._corregir_inconsistencias(consolidados)
        resultado.inconsistencias_detectadas = detectadas
        resultado.inconsistencias_corregidas = corregidas

        consolidados, interpolados = self._interpolador.interpolar(consolidados)
        resultado.faltantes_interpolados = interpolados

        consolidados, eliminados_irrecuperables = self._depurar_incompletos(consolidados)
        resultado.registros_eliminados += eliminados_irrecuperables

        consolidados, anomalias_detectadas, anomalias_marcadas, anomalias_eliminadas = self._tratar_anomalias(consolidados)
        resultado.anomalias_detectadas = anomalias_detectadas
        resultado.anomalias_marcadas = anomalias_marcadas
        resultado.anomalias_eliminadas = anomalias_eliminadas

        resultado.registros_salida = len(consolidados)
        resultado.registros_eliminados = resultado.registros_entrada - resultado.registros_salida
        return consolidados, resultado

    def _consolidar_duplicados(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], int]:
        if not registros:
            return [], 0

        consolidados: List[RegistroPrecio] = []
        grupo_actual: List[RegistroPrecio] = [registros[0]]
        duplicados = 0

        for registro in registros[1:]:
            if registro.fecha == grupo_actual[-1].fecha:
                grupo_actual.append(registro)
                continue

            consolidados.append(self._fusionar_grupo(grupo_actual))
            if len(grupo_actual) > 1:
                duplicados += len(grupo_actual) - 1
            grupo_actual = [registro]

        consolidados.append(self._fusionar_grupo(grupo_actual))
        if len(grupo_actual) > 1:
            duplicados += len(grupo_actual) - 1

        return consolidados, duplicados

    def _fusionar_grupo(self, grupo: List[RegistroPrecio]) -> RegistroPrecio:
        mejor = max(grupo, key=self._puntaje_registro)
        fusionado = copy.deepcopy(mejor)

        for registro in grupo:
            for campo in ["open", "high", "low", "close", "adj_close", "volume"]:
                if getattr(fusionado, campo) is None and getattr(registro, campo) is not None:
                    setattr(fusionado, campo, getattr(registro, campo))

        fusionado.anomalia = any(registro.anomalia for registro in grupo)
        return fusionado

    @staticmethod
    def _puntaje_registro(registro: RegistroPrecio) -> int:
        score = 0
        for campo in ["open", "high", "low", "close", "adj_close"]:
            if getattr(registro, campo) is not None:
                score += 2
        if registro.volume is not None:
            score += 1
        return score

    def _corregir_inconsistencias(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], int, int]:
        corregidos: List[RegistroPrecio] = []
        detectadas = 0
        corregidas = 0

        for registro in registros:
            registro = copy.deepcopy(registro)
            detecto = False
            corrigiendo = False

            if any(valor is not None and valor < 0 for valor in [registro.open, registro.high, registro.low, registro.close, registro.adj_close]):
                detecto = True
                for campo in ["open", "high", "low", "adj_close"]:
                    valor = getattr(registro, campo)
                    if valor is not None and valor < 0:
                        setattr(registro, campo, None)
                        corrigiendo = True
                if registro.close is not None and registro.close <= 0:
                    continue

            if registro.high is not None and registro.low is not None and registro.high < registro.low:
                registro.high, registro.low = registro.low, registro.high
                detecto = True
                corrigiendo = True

            if registro.high is None and registro.open is not None and registro.close is not None:
                registro.high = max(registro.open, registro.close)
                detecto = True
                corrigiendo = True

            if registro.low is None and registro.open is not None and registro.close is not None:
                registro.low = min(registro.open, registro.close)
                detecto = True
                corrigiendo = True

            if registro.high is not None and registro.low is not None:
                for campo in ["open", "close", "adj_close"]:
                    valor = getattr(registro, campo)
                    if valor is not None:
                        valor_clamped = min(max(valor, registro.low), registro.high)
                        if valor_clamped != valor:
                            setattr(registro, campo, valor_clamped)
                            detecto = True
                            corrigiendo = True

            if registro.volume is not None and registro.volume < 0:
                registro.volume = None
                detecto = True
                corrigiendo = True

            if detecto:
                detectadas += 1
            if corrigiendo:
                corregidas += 1

            corregidos.append(registro)

        return corregidos, detectadas, corregidas

    def _depurar_incompletos(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], int]:
        depurados: List[RegistroPrecio] = []
        eliminados = 0

        for registro in registros:
            if registro.close is None:
                eliminados += 1
                continue

            if registro.open is None:
                registro.open = registro.close
            if registro.high is None:
                registro.high = max(v for v in [registro.open, registro.close, registro.low] if v is not None)
            if registro.low is None:
                registro.low = min(v for v in [registro.open, registro.close, registro.high] if v is not None)

            depurados.append(registro)

        return depurados, eliminados

    def _tratar_anomalias(self, registros: List[RegistroPrecio]) -> Tuple[List[RegistroPrecio], int, int, int]:
        if len(registros) < 3:
            return registros, 0, 0, 0

        indices_validos: List[int] = []
        retornos: List[float] = []

        for indice in range(1, len(registros)):
            previo = registros[indice - 1].close
            actual = registros[indice].close
            if previo is None or actual is None or previo <= 0 or actual <= 0:
                continue
            indices_validos.append(indice)
            retornos.append(math.log(actual / previo))

        if len(retornos) < 3:
            return registros, 0, 0, 0

        mediana = self._mediana(retornos)
        mad = self._mad(retornos, mediana)

        if mad < 1e-12:
            media = sum(retornos) / len(retornos)
            varianza = sum((r - media) ** 2 for r in retornos) / len(retornos)
            desviacion = math.sqrt(varianza)
            if desviacion < 1e-12:
                return registros, 0, 0, 0
            scores = {indice: abs((retorno - media) / desviacion) for indice, retorno in zip(indices_validos, retornos)}
        else:
            scores = {indice: abs(0.6745 * (retorno - mediana) / mad) for indice, retorno in zip(indices_validos, retornos)}

        candidatos = {indice: score for indice, score in scores.items() if score > self._umbral_anomalia}
        if not candidatos:
            return registros, 0, 0, 0

        if self._estrategia_anomalias == "eliminar":
            depurados = [registro for indice, registro in enumerate(registros) if indice not in candidatos]
            return depurados, len(candidatos), 0, len(candidatos)

        if self._estrategia_anomalias == "winsorizar":
            ajustados = copy.deepcopy(registros)
            limite = self._umbral_anomalia * (mad / 0.6745 if mad >= 1e-12 else 1.0)
            for indice, score in candidatos.items():
                previo = ajustados[indice - 1].close
                actual = ajustados[indice].close
                if previo is None or actual is None or previo <= 0 or actual <= 0:
                    continue
                retorno_actual = math.log(actual / previo)
                retorno_centrado = mediana if mad >= 1e-12 else 0.0
                retorno_capturado = max(min(retorno_actual, retorno_centrado + limite), retorno_centrado - limite)
                nuevo_close = previo * math.exp(retorno_capturado)
                factor = nuevo_close / actual
                ajustados[indice].close = nuevo_close
                if ajustados[indice].open is not None:
                    ajustados[indice].open *= factor
                if ajustados[indice].high is not None:
                    ajustados[indice].high *= factor
                if ajustados[indice].low is not None:
                    ajustados[indice].low *= factor
                if ajustados[indice].adj_close is not None:
                    ajustados[indice].adj_close *= factor
                ajustados[indice].anomalia = True
            return ajustados, len(candidatos), len(candidatos), 0

        marcados = copy.deepcopy(registros)
        for indice in candidatos:
            marcados[indice].anomalia = True
        return marcados, len(candidatos), len(candidatos), 0

    @staticmethod
    def _mediana(valores: List[float]) -> float:
        ordenados = sorted(valores)
        n = len(ordenados)
        centro = n // 2
        if n % 2 == 1:
            return ordenados[centro]
        return (ordenados[centro - 1] + ordenados[centro]) / 2

    def _mad(self, valores: List[float], mediana: float) -> float:
        desviaciones = [abs(valor - mediana) for valor in valores]
        return self._mediana(desviaciones)


class TransformadorSerie(ITransformador):
    def __init__(
        self,
        logger: ILogger,
        estrategia_anomalias: str = "marcar",
        max_gap_interpolacion: int = MAX_GAPS_INTERPOLACION,
    ):
        self._logger = logger
        self._limpiador = LimpiadorCalidadDatos(
            max_gap=max_gap_interpolacion,
            umbral_anomalia=ZSCORE_UMBRAL_ANOMALIA,
            estrategia_anomalias=estrategia_anomalias,
        )

    def transformar(self, serie: SerieHistorica) -> SerieHistorica:
        self._logger.info(f"Transformando {serie.ticker} ({serie.longitud()} registros)")

        registros_limpios, resultado = self._limpiador.limpiar(serie.registros)

        if resultado.faltantes_detectados:
            self._logger.advertencia(f"{serie.ticker}: {resultado.faltantes_detectados} registros con valores faltantes")
        if resultado.inconsistencias_detectadas:
            self._logger.advertencia(
                f"{serie.ticker}: {resultado.inconsistencias_detectadas} inconsistencias detectadas, {resultado.inconsistencias_corregidas} corregidas"
            )
        if resultado.duplicados_consolidados:
            self._logger.advertencia(f"{serie.ticker}: {resultado.duplicados_consolidados} duplicados consolidados")
        if resultado.anomalias_detectadas:
            if self._limpiador._estrategia_anomalias == "eliminar":
                self._logger.advertencia(f"{serie.ticker}: {resultado.anomalias_eliminadas} anomalías eliminadas")
            elif self._limpiador._estrategia_anomalias == "winsorizar":
                self._logger.advertencia(f"{serie.ticker}: {resultado.anomalias_marcadas} anomalías corregidas")
            else:
                self._logger.advertencia(f"{serie.ticker}: {resultado.anomalias_marcadas} registros marcados como anomalía")

        serie_limpia = SerieHistorica(ticker=serie.ticker, registros=registros_limpios)
        self._logger.info(
            f"{serie.ticker}: limpieza completada | entrada={resultado.registros_entrada}, salida={resultado.registros_salida}, eliminados={resultado.registros_eliminados}"
        )
        return serie_limpia
