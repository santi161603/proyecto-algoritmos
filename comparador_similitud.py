#!/usr/bin/env python
"""
Comparador de similitud entre series de tiempo.

Permite seleccionar dos activos, visualizar sus series temporales
y calcular similitud usando 4 algoritmos diferentes.

Uso:
    python comparador_similitud.py [activo1] [activo2] [--retornos]

Ejemplos:
    python comparador_similitud.py SPY GGAL
    python comparador_similitud.py SPY GGAL --retornos
    python comparador_similitud.py               # modo interactivo
"""

import csv
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Agregar root al path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import RUTA_MASTER
from etl.similitud import CalculadorSimilitud, ResultadoSimilitud
from etl.models import RegistroPrecio, SerieHistorica


class CargadorDatos:
    """Carga datos desde archivos CSV."""
    
    @staticmethod
    def cargar_master() -> List[Dict[str, str]]:
        """Carga el dataset maestro."""
        rows: List[Dict[str, str]] = []
        if not Path(RUTA_MASTER).exists():
            raise FileNotFoundError(f"No se encontró {RUTA_MASTER}")
        
        with open(RUTA_MASTER, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows
    
    @staticmethod
    def obtener_activos_unicos(datos: List[Dict[str, str]]) -> List[str]:
        """Obtiene lista de activos únicos del dataset."""
        activos = sorted(set(row.get("ticker", "") for row in datos if row.get("ticker")))
        return activos
    
    @staticmethod
    def filtrar_por_ticker(datos: List[Dict[str, str]], ticker: str) -> List[Dict[str, str]]:
        """Filtra registros por ticker."""
        return [row for row in datos if row.get("ticker") == ticker]
    
    @staticmethod
    def convertir_a_serie_historica(datos_filtrados: List[Dict[str, str]], ticker: str) -> SerieHistorica:
        """Convierte datos CSV a SerieHistorica."""
        registros: List[RegistroPrecio] = []
        
        # Ordenar por fecha
        datos_ordenados = sorted(datos_filtrados, key=lambda r: r.get("fecha", ""))
        
        for row in datos_ordenados:
            try:
                fecha = row.get("fecha", "")
                ticker_row = row.get("ticker", "")
                
                # Convertir valores
                open_val = float(row.get("open")) if row.get("open") not in (None, "", "None") else None
                high_val = float(row.get("high")) if row.get("high") not in (None, "", "None") else None
                low_val = float(row.get("low")) if row.get("low") not in (None, "", "None") else None
                close_val = float(row.get("close")) if row.get("close") not in (None, "", "None") else None
                adj_close_val = float(row.get("adj_close")) if row.get("adj_close") not in (None, "", "None") else None
                volume_val = int(float(row.get("volume"))) if row.get("volume") not in (None, "", "None") else None
                
                registro = RegistroPrecio(
                    fecha=fecha,
                    ticker=ticker_row,
                    open=open_val,
                    high=high_val,
                    low=low_val,
                    close=close_val,
                    adj_close=adj_close_val,
                    volume=volume_val
                )
                registros.append(registro)
            except Exception as e:
                continue
        
        return SerieHistorica(ticker=ticker, registros=registros)


class VisualizadorComparacion:
    """Genera salida de resultados."""
    
    @staticmethod
    def mostrar_cabecera():
        """Muestra encabezado."""
        print("\n" + "="*80)
        print("  COMPARADOR DE SIMILITUD ENTRE SERIES DE TIEMPO")
        print("="*80 + "\n")
    
    @staticmethod
    def mostrar_activos(activos: List[str]):
        """Muestra lista de activos disponibles."""
        print("Activos disponibles:")
        for i, activo in enumerate(activos, 1):
            print(f"  {i:2d}. {activo}")
        print()
    
    @staticmethod
    def mostrar_info_serie(serie: SerieHistorica):
        """Muestra información de una serie."""
        precios = [r.close for r in serie.registros if r.close is not None]
        if precios:
            min_precio = min(precios)
            max_precio = max(precios)
            precio_promedio = sum(precios) / len(precios)
            print(f"  Registros: {len(serie.registros)}")
            print(f"  Precios válidos: {len(precios)}")
            print(f"  Rango: [{min_precio:.4f}, {max_precio:.4f}]")
            print(f"  Promedio: {precio_promedio:.4f}")
        else:
            print(f"  Registros: {len(serie.registros)} (sin precios válidos)")
    
    @staticmethod
    def mostrar_resultados(resultado: ResultadoSimilitud, usar_retornos: bool = True):
        """Muestra resultados de similitud."""
        print("\n" + "="*80)
        print(f"  RESULTADOS DE SIMILITUD: {resultado.activo_1} vs {resultado.activo_2}")
        print("="*80)
        
        modo = "RETORNOS" if usar_retornos else "PRECIOS NORMALIZADOS"
        print(f"\nModo: {modo}\n")
        
        print("┌─ DISTANCIA EUCLIDIANA ─────────────────────────────────────┐")
        print(f"│ Valor: {resultado.euclidiana:.6f}")
        print("│ Interpretación: Menor = más similares (escala sensible)")
        print("│ Complejidad: O(n)")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        print("┌─ CORRELACIÓN DE PEARSON ───────────────────────────────────┐")
        print(f"│ Valor: {resultado.pearson:.6f}")
        print("│ Rango: [-1, 1]")
        pearson_interp = ""
        if resultado.pearson > 0.7:
            pearson_interp = "Correlación positiva fuerte"
        elif resultado.pearson > 0.3:
            pearson_interp = "Correlación positiva moderada"
        elif resultado.pearson > -0.3:
            pearson_interp = "Sin correlación o débil"
        elif resultado.pearson > -0.7:
            pearson_interp = "Correlación negativa moderada"
        else:
            pearson_interp = "Correlación negativa fuerte"
        print(f"│ Interpretación: {pearson_interp}")
        print("│ Complejidad: O(n)")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        print("┌─ SIMILITUD POR COSENO ─────────────────────────────────────┐")
        print(f"│ Valor: {resultado.coseno:.6f}")
        print("│ Rango: [0, 1]")
        if resultado.coseno > 0.8:
            coseno_interp = "Series muy similares (paralelas)"
        elif resultado.coseno > 0.5:
            coseno_interp = "Series moderadamente similares"
        elif resultado.coseno > 0.2:
            coseno_interp = "Series débilmente similares"
        else:
            coseno_interp = "Series casi ortogonales"
        print(f"│ Interpretación: {coseno_interp}")
        print("│ Complejidad: O(n)")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        print("┌─ DYNAMIC TIME WARPING (DTW) ───────────────────────────────┐")
        print(f"│ Valor: {resultado.dtw:.6f}")
        print("│ Interpretación: Menor = mejor alineación temporal")
        print("│ Complejidad: O(n²)")
        print("│ Nota: Permite alineaciones no lineales entre series")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        print("="*80)
    
    @staticmethod
    def mostrar_resumen_complejidad():
        """Muestra resumen de complejidad."""
        print("\n" + "="*80)
        print("  RESUMEN DE COMPLEJIDAD ALGORÍTMICA")
        print("="*80 + "\n")
        
        print("┌─────────────────────┬────────┬────────┬──────────────────────────┐")
        print("│ Algoritmo           │ Tiempo │ Espacio│ Características          │")
        print("├─────────────────────┼────────┼────────┼──────────────────────────┤")
        print("│ Euclidiana          │ O(n)   │ O(1)   │ Rápida, sensible escala  │")
        print("│ Pearson             │ O(n)   │ O(1)   │ Correlación lineal       │")
        print("│ Coseno              │ O(n)   │ O(1)   │ Similitud angular        │")
        print("│ DTW                 │ O(n²)  │ O(n²)  │ Alineación flexible      │")
        print("└─────────────────────┴────────┴────────┴──────────────────────────┘\n")


def modo_interactivo():
    """Modo interactivo de selección."""
    cargador = CargadorDatos()
    
    print("\nCargando datos...")
    datos = cargador.cargar_master()
    activos = cargador.obtener_activos_unicos(datos)
    
    VisualizadorComparacion.mostrar_cabecera()
    VisualizadorComparacion.mostrar_activos(activos)
    
    # Seleccionar primer activo
    while True:
        try:
            idx1 = int(input("Selecciona índice del primer activo (o 0 para cancelar): ")) - 1
            if idx1 < 0:
                print("Cancelado.")
                return
            if 0 <= idx1 < len(activos):
                activo1 = activos[idx1]
                break
            print("Índice inválido.")
        except ValueError:
            print("Entrada inválida.")
    
    # Seleccionar segundo activo
    print()
    while True:
        try:
            idx2 = int(input("Selecciona índice del segundo activo (o 0 para cancelar): ")) - 1
            if idx2 < 0:
                print("Cancelado.")
                return
            if 0 <= idx2 < len(activos):
                activo2 = activos[idx2]
                break
            print("Índice inválido.")
        except ValueError:
            print("Entrada inválida.")
    
    usar_retornos = input("\n¿Usar retornos? (s/n, default=s): ").strip().lower() in ("s", "", "y", "yes")
    
    ejecutar_comparacion(datos, activo1, activo2, usar_retornos)


def ejecutar_comparacion(datos: List[Dict[str, str]], activo1: str, activo2: str, usar_retornos: bool = True):
    """Ejecuta la comparación entre dos activos."""
    cargador = CargadorDatos()
    
    try:
        # Cargar series
        datos_act1 = cargador.filtrar_por_ticker(datos, activo1)
        datos_act2 = cargador.filtrar_por_ticker(datos, activo2)
        
        if not datos_act1:
            print(f"Error: No se encontraron datos para {activo1}")
            return
        if not datos_act2:
            print(f"Error: No se encontraron datos para {activo2}")
            return
        
        serie1 = cargador.convertir_a_serie_historica(datos_act1, activo1)
        serie2 = cargador.convertir_a_serie_historica(datos_act2, activo2)
        
        # Mostrar información
        print(f"\n{activo1}:")
        VisualizadorComparacion.mostrar_info_serie(serie1)
        
        print(f"\n{activo2}:")
        VisualizadorComparacion.mostrar_info_serie(serie2)
        
        # Obtener precios
        precios1 = [r.close for r in serie1.registros]
        precios2 = [r.close for r in serie2.registros]
        
        # Calcular similitud
        print("\nCalculando similitud...")
        resultado = CalculadorSimilitud.comparar_series(
            precios1, precios2,
            usar_retornos=usar_retornos,
            activo_x=activo1,
            activo_y=activo2
        )
        
        # Mostrar resultados
        VisualizadorComparacion.mostrar_resultados(resultado, usar_retornos)
        VisualizadorComparacion.mostrar_resumen_complejidad()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Punto de entrada."""
    args = sys.argv[1:]
    
    if len(args) == 0:
        # Modo interactivo
        modo_interactivo()
    elif len(args) >= 2:
        # Modo línea de comandos
        activo1 = args[0].upper()
        activo2 = args[1].upper()
        usar_retornos = "--retornos" in args or "--sin-retornos" not in args
        
        cargador = CargadorDatos()
        datos = cargador.cargar_master()
        
        VisualizadorComparacion.mostrar_cabecera()
        ejecutar_comparacion(datos, activo1, activo2, usar_retornos)
    else:
        print("Uso:")
        print("  python comparador_similitud.py                  # Modo interactivo")
        print("  python comparador_similitud.py SPY GGAL         # Comparar activos")
        print("  python comparador_similitud.py SPY GGAL --retornos")
        sys.exit(1)


if __name__ == "__main__":
    main()
