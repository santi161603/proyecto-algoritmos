from __future__ import annotations

import csv
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import RUTA_MASTER
from seguimiento1.ordenamientos import METODOS_ORDENAMIENTO, heap_sort


SALIDA_DIR = Path("reportes/seguimiento1")
MASTER_ORDENADO = SALIDA_DIR / "master_ordenado_fecha_close.csv"
TABLA_TIEMPOS = SALIDA_DIR / "tabla_tiempos_ordenamiento.csv"
TOP15_VOLUMEN = SALIDA_DIR / "top15_mayor_volumen_asc.csv"
GRAFICO_TIEMPOS = SALIDA_DIR / "tiempos_ordenamiento.png"


def cargar_master(ruta_master: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(ruta_master, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_float(valor: str | None) -> float:
    if valor in (None, "", "None"):
        return float("inf")
    try:
        return float(valor)
    except ValueError:
        return float("inf")


def to_int(valor: str | None) -> int | None:
    if valor in (None, "", "None"):
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def merge_sort_manual(items: List, key, reverse: bool = False) -> List:
    if len(items) <= 1:
        return items[:]

    mitad = len(items) // 2
    izquierda = merge_sort_manual(items[:mitad], key=key, reverse=reverse)
    derecha = merge_sort_manual(items[mitad:], key=key, reverse=reverse)

    resultado = []
    i = 0
    j = 0

    while i < len(izquierda) and j < len(derecha):
        ki = key(izquierda[i])
        kj = key(derecha[j])

        if not reverse:
            cond = ki <= kj
        else:
            cond = ki >= kj

        if cond:
            resultado.append(izquierda[i])
            i += 1
        else:
            resultado.append(derecha[j])
            j += 1

    while i < len(izquierda):
        resultado.append(izquierda[i])
        i += 1

    while j < len(derecha):
        resultado.append(derecha[j])
        j += 1

    return resultado


def ordenar_master_fecha_close(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # Fecha en formato YYYY-MM-DD (orden lexicográfico correcto),
    # desempate por close ascendente.
    return merge_sort_manual(
        rows,
        key=lambda r: (r.get("fecha", ""), to_float(r.get("close"))),
        reverse=False,
    )


def guardar_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def benchmark_ordenamientos_enteros(enteros: List[int], semilla: int = 42) -> List[Dict[str, str]]:
    random.seed(semilla)

    # Para algoritmos O(n^2), usar un tamaño razonable y reproducible.
    n = min(2000, len(enteros))
    if n < 100:
        raise ValueError("No hay suficientes enteros para benchmarking.")

    muestra = random.sample(enteros, n) if len(enteros) > n else enteros[:]
    esperado = heap_sort(muestra)

    resultados: List[Dict[str, str]] = []

    for metodo in METODOS_ORDENAMIENTO:
        datos = muestra[:]
        inicio = time.perf_counter()
        salida = metodo.funcion(datos)
        fin = time.perf_counter()

        if salida != esperado:
            raise RuntimeError(f"El algoritmo {metodo.nombre} no ordenó correctamente.")

        resultados.append(
            {
                "metodo": metodo.nombre,
                "tamano": str(n),
                "tiempo_segundos": f"{(fin - inicio):.6f}",
                "complejidad": metodo.complejidad,
            }
        )

    return merge_sort_manual(resultados, key=lambda r: float(r["tiempo_segundos"]))


def generar_grafico_tiempos(tabla: List[Dict[str, str]], salida: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return False

    metodos = [r["metodo"] for r in tabla]
    tiempos = [float(r["tiempo_segundos"]) for r in tabla]

    plt.figure(figsize=(12, 6))
    bars = plt.bar(metodos, tiempos)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Tiempo (segundos)")
    plt.title("Tiempos de 12 algoritmos de ordenamiento (ascendente)")

    for b, t in zip(bars, tiempos):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{t:.4f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    salida.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(salida, dpi=150)
    plt.close()
    return True


def top15_mayor_volumen_asc(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    con_volumen = []
    for r in rows:
        v = to_int(r.get("volume"))
        if v is not None:
            con_volumen.append((v, r))

    # Tomar 15 mayores por volumen y luego ordenar ascendente por volumen
    top = merge_sort_manual(con_volumen, key=lambda x: x[0], reverse=True)[:15]
    top_asc = merge_sort_manual(top, key=lambda x: x[0], reverse=False)
    return [r for _, r in top_asc]


def ejecutar() -> None:
    ruta_master = Path(RUTA_MASTER)
    if not ruta_master.exists():
        raise FileNotFoundError(f"No existe dataset maestro en: {ruta_master}")

    rows = cargar_master(str(ruta_master))
    if not rows:
        raise RuntimeError("El dataset maestro está vacío.")

    fieldnames = list(rows[0].keys())

    # 1) Ordenar registros por fecha y close
    ordenados = ordenar_master_fecha_close(rows)
    guardar_csv(MASTER_ORDENADO, ordenados, fieldnames)

    # 2) Benchmark de 12 algoritmos con enteros (volumen)
    enteros = [to_int(r.get("volume")) for r in rows]
    enteros = [v for v in enteros if v is not None]
    tabla = benchmark_ordenamientos_enteros(enteros)

    guardar_csv(
        TABLA_TIEMPOS,
        tabla,
        ["metodo", "tamano", "tiempo_segundos", "complejidad"],
    )

    # 3) Top 15 días de mayor volumen ordenados ascendentemente
    top15 = top15_mayor_volumen_asc(rows)
    guardar_csv(TOP15_VOLUMEN, top15, fieldnames)

    # 4) Diagrama de barras de tiempos
    grafico_ok = generar_grafico_tiempos(tabla, GRAFICO_TIEMPOS)

    print("=== Seguimiento 1 generado ===")
    print(f"Registros leídos: {len(rows)}")
    print(f"Master ordenado: {MASTER_ORDENADO}")
    print(f"Tabla tiempos: {TABLA_TIEMPOS}")
    print(f"Top 15 volumen: {TOP15_VOLUMEN}")
    if grafico_ok:
        print(f"Gráfico barras: {GRAFICO_TIEMPOS}")
    else:
        print("Gráfico barras: NO generado (instala matplotlib)")


if __name__ == "__main__":
    ejecutar()
