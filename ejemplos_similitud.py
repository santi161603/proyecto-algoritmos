#!/usr/bin/env python
"""
Script de ejemplos y análisis de complejidad de algoritmos de similitud.

Muestra:
1. Ejemplos de uso de cada algoritmo
2. Análisis de complejidad teórica vs práctica
3. Comparativa de tiempos de ejecución
4. Guía de cuándo usar cada algoritmo
"""

import math
import time
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.similitud import CalculadorSimilitud


def generar_serie_aleatoria(n: int, volatilidad: float = 0.02) -> list:
    """Genera serie de precios aleatoria con volatilidad controlada."""
    serie = [100.0]
    for _ in range(n - 1):
        cambio = random.gauss(0, volatilidad)
        nuevo_precio = serie[-1] * (1 + cambio)
        serie.append(max(nuevo_precio, 0.01))
    return serie


def generar_serie_correlacionada(serie_base: list, correlacion: float) -> list:
    """Genera serie correlacionada con serie_base."""
    if not 0 <= correlacion <= 1:
        raise ValueError("Correlación debe estar entre 0 y 1")
    
    serie_aleatoria = generar_serie_aleatoria(len(serie_base))
    
    # Combinar: (1-corr)*aleatorio + corr*base
    serie = []
    for i in range(len(serie_base)):
        valor = (1 - correlacion) * serie_aleatoria[i] + correlacion * serie_base[i]
        serie.append(valor)
    
    return serie


def ejemplo_basico():
    """Ejemplo básico de uso."""
    print("\n" + "="*80)
    print("  EJEMPLO 1: USO BÁSICO")
    print("="*80 + "\n")
    
    # Serie 1: comportamiento ascendente
    serie1 = [100, 102, 105, 108, 110, 115, 118, 120, 119, 121]
    
    # Serie 2: comportamiento similar
    serie2 = [50, 51, 53, 54, 55, 58, 59, 60, 59, 60]
    
    # Serie 3: comportamiento opuesto
    serie3 = [100, 98, 95, 92, 90, 85, 82, 80, 81, 79]
    
    print("Serie 1 (ascendente):", serie1)
    print("Serie 2 (ascendente, escala diferente):", serie2)
    print("Serie 3 (descendente):", serie3)
    
    # Comparar 1 vs 2 (similares)
    print("\n--- Comparación 1 vs 2 (ambas ascendentes, escalas diferentes) ---")
    resultado = CalculadorSimilitud.comparar_series(
        serie1, serie2, usar_retornos=True, activo_x="Serie1", activo_y="Serie2"
    )
    print(f"Euclidiana:  {resultado.euclidiana:.6f} (menor = similar)")
    print(f"Pearson:     {resultado.pearson:.6f} (1 = correlación perfecta)")
    print(f"Coseno:      {resultado.coseno:.6f} (1 = paralelas)")
    print(f"DTW:         {resultado.dtw:.6f} (menor = alineación mejor)")
    
    # Comparar 1 vs 3 (opuestas)
    print("\n--- Comparación 1 vs 3 (ascendente vs descendente) ---")
    resultado = CalculadorSimilitud.comparar_series(
        serie1, serie3, usar_retornos=True, activo_x="Serie1", activo_y="Serie3"
    )
    print(f"Euclidiana:  {resultado.euclidiana:.6f} (mayor = diferentes)")
    print(f"Pearson:     {resultado.pearson:.6f} (negativo = correlación inversa)")
    print(f"Coseno:      {resultado.coseno:.6f} (menor = ortogonales)")
    print(f"DTW:         {resultado.dtw:.6f}")


def analisis_complejidad():
    """Análisis de complejidad teórica vs práctica."""
    print("\n" + "="*80)
    print("  EJEMPLO 2: ANÁLISIS DE COMPLEJIDAD (Tiempo de ejecución)")
    print("="*80 + "\n")
    
    tamaños = [100, 500, 1000, 2000, 5000]
    
    print("Tamaño | Euclidiana(ms) | Pearson(ms) | Coseno(ms) | DTW(ms)")
    print("-------|----------------|-------------|------------|----------")
    
    for n in tamaños:
        serie1 = generar_serie_aleatoria(n)
        serie2 = generar_serie_aleatoria(n)
        
        # Euclidiana
        start = time.time()
        for _ in range(100):
            CalculadorSimilitud.distancia_euclidiana(serie1, serie2)
        tiempo_eucl = (time.time() - start) * 10  # ms (100 iteraciones)
        
        # Pearson
        start = time.time()
        for _ in range(100):
            CalculadorSimilitud.correlacion_pearson(serie1, serie2)
        tiempo_pear = (time.time() - start) * 10
        
        # Coseno
        start = time.time()
        for _ in range(100):
            CalculadorSimilitud.similitud_coseno(serie1, serie2)
        tiempo_cos = (time.time() - start) * 10
        
        # DTW (menos iteraciones por ser O(n²))
        start = time.time()
        for _ in range(10):
            CalculadorSimilitud.dynamic_time_warping(serie1, serie2)
        tiempo_dtw = (time.time() - start) * 100  # ms (10 iteraciones)
        
        print(f"{n:6d} | {tiempo_eucl:14.3f} | {tiempo_pear:11.3f} | {tiempo_cos:10.3f} | {tiempo_dtw:8.3f}")
    
    print("\nObservaciones:")
    print("- Euclidiana, Pearson, Coseno: O(n) - lineales")
    print("- DTW: O(n²) - cuadrática, mucho más lenta para series grandes")
    print("- Para n=5000: DTW ~100x más lento que métodos lineales")


def analisis_correlacion():
    """Análisis de cómo varían métricas con correlación."""
    print("\n" + "="*80)
    print("  EJEMPLO 3: VARIACIÓN CON CORRELACIÓN")
    print("="*80 + "\n")
    
    serie_base = generar_serie_aleatoria(500)
    
    print("Correlación | Euclidiana | Pearson | Coseno")
    print("------------|------------|---------|--------")
    
    for corr in [0.0, 0.2, 0.5, 0.8, 1.0]:
        serie_corr = generar_serie_correlacionada(serie_base, corr)
        
        resultado = CalculadorSimilitud.comparar_series(
            serie_base, serie_corr, usar_retornos=True
        )
        
        print(f"{corr:10.1f} | {resultado.euclidiana:10.6f} | {resultado.pearson:7.4f} | {resultado.coseno:6.4f}")
    
    print("\nInterpretación:")
    print("- Correlación 0.0: Series completamente no correlacionadas")
    print("- Correlación 1.0: Series idénticas")
    print("- Pearson: Aumenta con correlación (-1 a 1)")
    print("- Coseno: Aumenta con correlación (0 a 1)")
    print("- Euclidiana: Disminuye con correlación (inverted)")


def casos_uso():
    """Recomendaciones de uso."""
    print("\n" + "="*80)
    print("  GUÍA DE CASOS DE USO")
    print("="*80 + "\n")
    
    print("""
DISTANCIA EUCLIDIANA
  ✓ Uso: Comparación rápida de precios normalizados
  ✓ Ventajas:
    - O(n) muy rápido
    - Fácil de interpretar (distancia real)
  ✗ Desventajas:
    - Sensible a escala
    - Sensible a magnitud
  → Casos: Búsqueda de pares similares en tiempo real

CORRELACIÓN DE PEARSON
  ✓ Uso: Medir relación lineal entre activos
  ✓ Ventajas:
    - O(n) rápido
    - Invariante a escala/traslación
    - Estadísticamente robusto
    - Rango [-1, 1] interpretable
  ✗ Desventajas:
    - Solo captura relaciones lineales
    - Puede ser engañoso con outliers
  → Casos: Análisis de correlación de cartera, hedge pairs

SIMILITUD POR COSENO
  ✓ Uso: Similitud de dirección (momentum)
  ✓ Ventajas:
    - O(n) rápido
    - Enfocado en ángulo/dirección, no magnitud
    - Rango [0, 1] simple
  ✗ Desventajas:
    - Ignora magnitud (puede ser ventaja o desventaja)
    - Similar a Pearson en muchos casos
  → Casos: Análisis de momentum relativo, clustering de volatilidad

DYNAMIC TIME WARPING (DTW)
  ✓ Uso: Alineación flexible de series
  ✓ Ventajas:
    - Tolera longitudes diferentes
    - Captura alineaciones no lineales (lags)
    - Excelente para detección de patrones desalineados
  ✗ Desventajas:
    - O(n²) costo computacional
    - Requiere O(n²) memoria
    - Más lento para series largas
  → Casos: Análisis de patrones históricos, detección de repeticiones
""")


def benchmark_completo():
    """Benchmark completo de todos los algoritmos."""
    print("\n" + "="*80)
    print("  EJEMPLO 4: BENCHMARK COMPLETO")
    print("="*80 + "\n")
    
    print("Comparando 5000 puntos de datos...")
    serie1 = generar_serie_aleatoria(5000)
    serie2 = generar_serie_aleatoria(5000)
    
    print("\nTiempos (ms para una ejecución):\n")
    
    # Euclidiana
    start = time.time()
    eucl = CalculadorSimilitud.distancia_euclidiana(serie1, serie2)
    tiempo_eucl = (time.time() - start) * 1000
    print(f"Euclidiana:    {tiempo_eucl:.3f}ms → {eucl:.6f}")
    
    # Pearson
    start = time.time()
    pear = CalculadorSimilitud.correlacion_pearson(serie1, serie2)
    tiempo_pear = (time.time() - start) * 1000
    print(f"Pearson:       {tiempo_pear:.3f}ms → {pear:.6f}")
    
    # Coseno
    start = time.time()
    cos = CalculadorSimilitud.similitud_coseno(serie1, serie2)
    tiempo_cos = (time.time() - start) * 1000
    print(f"Coseno:        {tiempo_cos:.3f}ms → {cos:.6f}")
    
    # DTW
    start = time.time()
    dtw = CalculadorSimilitud.dynamic_time_warping(serie1, serie2)
    tiempo_dtw = (time.time() - start) * 1000
    print(f"DTW:           {tiempo_dtw:.3f}ms → {dtw:.6f}")
    
    print(f"\nRatio DTW/Euclidiana: {tiempo_dtw/tiempo_eucl:.0f}x más lento")


def main():
    """Ejecuta todos los ejemplos."""
    ejemplo_basico()
    analisis_complejidad()
    analisis_correlacion()
    casos_uso()
    benchmark_completo()
    
    print("\n" + "="*80)
    print("  CONCLUSIÓN")
    print("="*80 + "\n")
    print("""
Para elegir el algoritmo de similitud:

1. Si necesitas VELOCIDAD → Euclidiana, Pearson o Coseno (O(n))
   - Correlación lineal → Pearson
   - Similitud angular → Coseno
   - Distancia real → Euclidiana

2. Si necesitas ALINEACIÓN FLEXIBLE → DTW (O(n²))
   - Vale la pena si: series de diferente longitud o patrones desalineados
   - No vale si: comparar cientos de pares diariamente

3. Para PORTAFOLIOS:
   - Correlación de Pearson para hedging
   - DTW para detección de patrones recurrentes
   - Coseno para análisis de momentum relativo

4. RECOMENDACIÓN GENERAL:
   - Usa Pearson como línea base (fácil de interpretar)
   - Compara con Coseno para validar (menos sensible a escala)
   - DTW solo si alineación temporal es crítica
""")


if __name__ == "__main__":
    main()
