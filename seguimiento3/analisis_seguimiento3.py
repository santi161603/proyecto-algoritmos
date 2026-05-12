from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import RUTA_MASTER
from etl.analisis_frecuencia_volatilidad import (
    AnalizadorPatronesVolatilidad,
    ResultadoPatrones,
    ResultadoRiesgo,
)


SALIDA_DIR = Path("reportes/seguimiento3")
SALIDA_PATRONES = SALIDA_DIR / "frecuencia_patrones.csv"
SALIDA_RIESGO = SALIDA_DIR / "clasificacion_riesgo.csv"
SALIDA_RANKING = SALIDA_DIR / "ranking_riesgo_desc.csv"


def cargar_series_por_ticker(ruta_master: str) -> Dict[str, List[float]]:
    series: Dict[str, List[float]] = {}

    with open(ruta_master, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = sorted(list(reader), key=lambda r: (r.get("ticker", ""), r.get("fecha", "")))

    for row in rows:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue

        raw_close = row.get("close")
        close = None
        if raw_close not in (None, "", "None"):
            try:
                close = float(raw_close)
            except ValueError:
                close = None

        series.setdefault(ticker, []).append(close)

    return series


def guardar_patrones(ruta: Path, resultados: List[ResultadoPatrones]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "ticker",
        "total_ventanas_alza",
        "frecuencia_alza_consecutiva",
        "proporcion_alza_consecutiva",
        "total_ventanas_reversion",
        "frecuencia_reversion_v",
        "proporcion_reversion_v",
    ]

    with open(ruta, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in resultados:
            writer.writerow(
                {
                    "ticker": r.ticker,
                    "total_ventanas_alza": r.total_ventanas_alza,
                    "frecuencia_alza_consecutiva": r.frecuencia_alza_consecutiva,
                    "proporcion_alza_consecutiva": f"{r.proporcion_alza_consecutiva:.6f}",
                    "total_ventanas_reversion": r.total_ventanas_reversion,
                    "frecuencia_reversion_v": r.frecuencia_reversion_v,
                    "proporcion_reversion_v": f"{r.proporcion_reversion_v:.6f}",
                }
            )


def guardar_riesgo(ruta: Path, resultados: List[ResultadoRiesgo]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "ticker",
        "n_precios",
        "n_retornos",
        "desviacion_estandar_diaria",
        "volatilidad_historica_anualizada",
        "categoria_riesgo",
    ]

    with open(ruta, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in resultados:
            writer.writerow(
                {
                    "ticker": r.ticker,
                    "n_precios": r.n_precios,
                    "n_retornos": r.n_retornos,
                    "desviacion_estandar_diaria": f"{r.desviacion_estandar_diaria:.8f}",
                    "volatilidad_historica_anualizada": f"{r.volatilidad_historica_anualizada:.8f}",
                    "categoria_riesgo": r.categoria_riesgo,
                }
            )


def imprimir_resumen(riesgo_ordenado_desc: List[ResultadoRiesgo]) -> None:
    print("\n=== Clasificación de Riesgo (top 10 más riesgosos) ===")
    print("Ticker | Vol. Anualizada | Categoría")
    print("--------------------------------------")
    for item in riesgo_ordenado_desc[:10]:
        print(f"{item.ticker:6s} | {item.volatilidad_historica_anualizada:15.6f} | {item.categoria_riesgo}")


def main() -> None:
    if not Path(RUTA_MASTER).exists():
        raise FileNotFoundError(f"No existe dataset maestro en: {RUTA_MASTER}")

    series_por_ticker = cargar_series_por_ticker(RUTA_MASTER)

    analizador = AnalizadorPatronesVolatilidad(
        ventana_alza=5,
        umbral_reversion=0.01,
        dias_mercado=252,
    )

    resultados_patrones, resultados_riesgo = analizador.analizar_portafolio(series_por_ticker)
    ranking_desc = analizador.ranking_riesgo_desc(resultados_riesgo)

    guardar_patrones(SALIDA_PATRONES, resultados_patrones)
    guardar_riesgo(SALIDA_RIESGO, resultados_riesgo)
    guardar_riesgo(SALIDA_RANKING, ranking_desc)

    print("\nReq. 3 ejecutado correctamente.")
    print(f"- Activos analizados: {len(series_por_ticker)}")
    print(f"- Frecuencia de patrones: {SALIDA_PATRONES}")
    print(f"- Clasificación de riesgo: {SALIDA_RIESGO}")
    print(f"- Ranking de riesgo (desc): {SALIDA_RANKING}")

    imprimir_resumen(ranking_desc)


if __name__ == "__main__":
    main()
