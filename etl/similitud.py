"""
Módulo de similitud entre series de tiempo.

Implementa 4 algoritmos de similitud:
1. Distancia euclidiana: √Σ(x_i - y_i)²
   - Complejidad O(n)
   - Sensible a escala y magnitud

2. Correlación de Pearson: Σ((x_i - x̄)(y_i - ȳ)) / (σ_x * σ_y)
   - Complejidad O(n)
   - Mide relación lineal (-1 a 1)

3. Dynamic Time Warping (DTW): distancia mínima con alineación flexible
   - Complejidad O(n²) con programación dinámica
   - Permite series de longitud diferente

4. Similitud por coseno: Σ(x_i * y_i) / (||x|| * ||y||)
   - Complejidad O(n)
   - Rango 0 a 1 (angular)
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ResultadoSimilitud:
    """Contenedor de resultados de similitud entre dos series."""
    euclidiana: float
    pearson: float
    dtw: float
    coseno: float
    activo_1: str
    activo_2: str


class CalculadorSimilitud:
    """Calcula similitud entre dos series de precios/retornos."""

    @staticmethod
    def distancia_euclidiana(serie_x: List[float], serie_y: List[float]) -> float:
        """
        Distancia euclidiana entre dos series.
        
        Fórmula: √Σ(x_i - y_i)²
        
        Args:
            serie_x: Lista de valores serie 1
            serie_y: Lista de valores serie 2
        
        Returns:
            Distancia euclidiana (0 = idénticas)
        
        Complejidad: O(n) - una pasada, suma de cuadrados
        """
        if len(serie_x) != len(serie_y):
            raise ValueError("Las series deben tener la misma longitud")
        
        if len(serie_x) == 0:
            return 0.0
        
        suma_cuadrados = sum((x - y) ** 2 for x, y in zip(serie_x, serie_y))
        return math.sqrt(suma_cuadrados)

    @staticmethod
    def correlacion_pearson(serie_x: List[float], serie_y: List[float]) -> float:
        """
        Correlación de Pearson entre dos series.
        
        Fórmula: Σ((x_i - x̄)(y_i - ȳ)) / (σ_x * σ_y)
        
        Args:
            serie_x: Lista de valores serie 1
            serie_y: Lista de valores serie 2
        
        Returns:
            Correlación de Pearson (-1 a 1)
            - 1: correlación positiva perfecta
            - 0: sin correlación
            - -1: correlación negativa perfecta
        
        Complejidad: O(n) - tres pasadas (media, varianza, covarianza)
        """
        if len(serie_x) != len(serie_y):
            raise ValueError("Las series deben tener la misma longitud")
        
        n = len(serie_x)
        if n < 2:
            return 0.0
        
        # Calcular medias
        media_x = sum(serie_x) / n
        media_y = sum(serie_y) / n
        
        # Calcular covarianza y desviaciones estándar
        covarianza = sum((x - media_x) * (y - media_y) for x, y in zip(serie_x, serie_y)) / n
        varianza_x = sum((x - media_x) ** 2 for x in serie_x) / n
        varianza_y = sum((y - media_y) ** 2 for y in serie_y) / n
        
        desv_x = math.sqrt(varianza_x)
        desv_y = math.sqrt(varianza_y)
        
        if desv_x < 1e-12 or desv_y < 1e-12:
            return 0.0
        
        return covarianza / (desv_x * desv_y)

    @staticmethod
    def similitud_coseno(serie_x: List[float], serie_y: List[float]) -> float:
        """
        Similitud por coseno entre dos series.
        
        Fórmula: Σ(x_i * y_i) / (||x|| * ||y||)
        
        Args:
            serie_x: Lista de valores serie 1
            serie_y: Lista de valores serie 2
        
        Returns:
            Similitud coseno (0 a 1)
            - 1: series paralelas (misma dirección angular)
            - 0: series ortogonales
        
        Complejidad: O(n) - producto escalar y normas
        """
        if len(serie_x) != len(serie_y):
            raise ValueError("Las series deben tener la misma longitud")
        
        if len(serie_x) == 0:
            return 0.0
        
        # Producto escalar
        producto_punto = sum(x * y for x, y in zip(serie_x, serie_y))
        
        # Normas (magnitudes)
        norma_x = math.sqrt(sum(x ** 2 for x in serie_x))
        norma_y = math.sqrt(sum(y ** 2 for y in serie_y))
        
        if norma_x < 1e-12 or norma_y < 1e-12:
            return 0.0
        
        return producto_punto / (norma_x * norma_y)

    @staticmethod
    def dynamic_time_warping(serie_x: List[float], serie_y: List[float]) -> float:
        """
        Dynamic Time Warping (DTW) - distancia con alineación flexible.
        
        Permite comparar series de longitud diferente encontrando la ruta
        óptima de alineación que minimiza la distancia acumulada.
        
        Fórmula (recursiva):
            DTW(i, j) = |x_i - y_j| + min(
                DTW(i-1, j),      # inserción en y
                DTW(i, j-1),      # inserción en x
                DTW(i-1, j-1)     # coincidencia
            )
        
        Args:
            serie_x: Lista de valores serie 1
            serie_y: Lista de valores serie 2
        
        Returns:
            Distancia DTW (mínima distancia de alineación)
        
        Complejidad: O(n*m) donde n=len(x), m=len(y)
        - Espacio: O(n*m) para la matriz de DP
        - Tiempo: n*m iteraciones, cada una O(1)
        
        Ventajas:
        - Tolera series de diferente longitud
        - Captura alineaciones no lineales
        
        Desventajas:
        - Más lento que distancia euclidiana
        - Requiere espacio O(n*m)
        """
        if not serie_x or not serie_y:
            return float('inf')
        
        n = len(serie_x)
        m = len(serie_y)
        
        # Inicializar matriz de distancias acumuladas
        dtw_matrix = [[float('inf')] * (m + 1) for _ in range(n + 1)]
        dtw_matrix[0][0] = 0
        
        # Llenar matriz con programación dinámica
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                costo = abs(serie_x[i - 1] - serie_y[j - 1])
                dtw_matrix[i][j] = costo + min(
                    dtw_matrix[i - 1][j],      # inserción
                    dtw_matrix[i][j - 1],      # eliminación
                    dtw_matrix[i - 1][j - 1]   # coincidencia
                )
        
        return dtw_matrix[n][m]

    @staticmethod
    def calcular_retornos(precios: List[float]) -> List[float]:
        """
        Calcula retornos logarítmicos de una serie de precios.
        
        Fórmula: r_i = ln(P_i / P_{i-1})
        
        Args:
            precios: Lista de precios de cierre
        
        Returns:
            Lista de retornos (longitud = len(precios) - 1)
        """
        if len(precios) < 2:
            return []
        
        retornos = []
        for i in range(1, len(precios)):
            if precios[i - 1] is None or precios[i] is None or precios[i - 1] <= 0 or precios[i] <= 0:
                continue
            retorno = math.log(precios[i] / precios[i - 1])
            retornos.append(retorno)
        
        return retornos

    @classmethod
    def comparar_series(
        cls,
        precios_x: List[float],
        precios_y: List[float],
        usar_retornos: bool = True,
        activo_x: str = "Activo1",
        activo_y: str = "Activo2"
    ) -> ResultadoSimilitud:
        """
        Compara dos series de precios usando los 4 algoritmos.
        
        Args:
            precios_x: Lista de precios activo 1
            precios_y: Lista de precios activo 2
            usar_retornos: Si True, calcula sobre retornos; si False, sobre precios normalizados
            activo_x: Nombre del activo 1
            activo_y: Nombre del activo 2
        
        Returns:
            ResultadoSimilitud con las 4 métricas
        """
        # Limpiar None
        precios_x = [p for p in precios_x if p is not None]
        precios_y = [p for p in precios_y if p is not None]
        
        if len(precios_x) < 2 or len(precios_y) < 2:
            raise ValueError("Series requieren al menos 2 precios válidos")
        
        if usar_retornos:
            serie_x = cls.calcular_retornos(precios_x)
            serie_y = cls.calcular_retornos(precios_y)
        else:
            # Normalizar precios por el primero
            serie_x = [p / precios_x[0] for p in precios_x]
            serie_y = [p / precios_y[0] for p in precios_y]
        
        if len(serie_x) < 2 or len(serie_y) < 2:
            raise ValueError("Series no tienen suficientes retornos válidos")
        
        # Calcular similitud euclidiana (normalizar por longitud promedio)
        min_len = min(len(serie_x), len(serie_y))
        if min_len > 0:
            serie_x_corta = serie_x[:min_len]
            serie_y_corta = serie_y[:min_len]
            euclidiana = cls.distancia_euclidiana(serie_x_corta, serie_y_corta) / math.sqrt(min_len)
        else:
            euclidiana = float('inf')
        
        # Correlación Pearson (usa min_len)
        if min_len > 1:
            pearson = cls.correlacion_pearson(serie_x[:min_len], serie_y[:min_len])
        else:
            pearson = 0.0
        
        # DTW (permite longitudes diferentes)
        dtw = cls.dynamic_time_warping(serie_x, serie_y)
        
        # Similitud coseno (usa min_len)
        if min_len > 0:
            coseno = cls.similitud_coseno(serie_x[:min_len], serie_y[:min_len])
        else:
            coseno = 0.0
        
        return ResultadoSimilitud(
            euclidiana=euclidiana,
            pearson=pearson,
            dtw=dtw,
            coseno=coseno,
            activo_1=activo_x,
            activo_2=activo_y
        )


# Análisis de complejidad (documentación para referencia)
ANALISIS_COMPLEJIDAD = """
ANÁLISIS DE COMPLEJIDAD ALGORÍTMICA

1. DISTANCIA EUCLIDIANA
   ├─ Tiempo: O(n)
   │  └─ Una pasada sobre ambas series, suma de cuadrados
   ├─ Espacio: O(1) - solo acumulador
   └─ Observación: La más rápida; sensible a escala

2. CORRELACIÓN DE PEARSON
   ├─ Tiempo: O(n)
   │  └─ 3 pasadas: medias, varianzas, covarianza
   ├─ Espacio: O(1) - acumuladores
   └─ Observación: Invariante a escala/traslación; rango [-1, 1]

3. SIMILITUD POR COSENO
   ├─ Tiempo: O(n)
   │  └─ Producto punto + dos normas (una pasada cada una)
   ├─ Espacio: O(1)
   └─ Observación: Rango [0, 1]; sensible a dirección angular, no magnitud

4. DYNAMIC TIME WARPING (DTW)
   ├─ Tiempo: O(n × m)
   │  └─ Matriz n×m, cada celda O(1)
   ├─ Espacio: O(n × m)
   │  └─ Matriz completa de DP
   └─ Observación: La más cara; tolera longitudes diferentes y alineaciones no lineales

COMPARATIVA:
┌─────────────────┬────────┬────────┬──────────────────────┐
│ Algoritmo       │ Tiempo │ Espacio│ Casos de uso         │
├─────────────────┼────────┼────────┼──────────────────────┤
│ Euclidiana      │ O(n)   │ O(1)   │ Comparación rápida   │
│ Pearson         │ O(n)   │ O(1)   │ Correlación lineal   │
│ Coseno          │ O(n)   │ O(1)   │ Similitud angular    │
│ DTW             │ O(n²)  │ O(n²)  │ Alineación flexible  │
└─────────────────┴────────┴────────┴──────────────────────┘

DECISIÓN DE ELECCIÓN:
- Velocidad crítica → Pearson, Coseno o Euclidiana (O(n))
- Alineación flexible → DTW (O(n²))
- Relación lineal → Pearson
- Magnitud irrelevante → Coseno
- Series normalizadas → Euclidiana
"""
