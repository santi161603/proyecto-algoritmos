from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import RUTA_MASTER

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Rectangle
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Matplotlib no está disponible. Instala con: pip install matplotlib"
    ) from exc


SALIDA_DIR = Path("reportes/seguimiento4")
HEATMAP_PNG = SALIDA_DIR / "matriz_correlacion_heatmap.png"
PDF_REPORTE = SALIDA_DIR / "reporte_tecnico_dashboard.pdf"


@dataclass
class OHLC:
    fecha: str
    ticker: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]


def to_float(v: Optional[str]) -> Optional[float]:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def cargar_ohlc_desde_master(ruta_master: str) -> Dict[str, List[OHLC]]:
    if not Path(ruta_master).exists():
        raise FileNotFoundError(f"No existe archivo maestro: {ruta_master}")

    por_ticker: Dict[str, List[OHLC]] = {}

    with open(ruta_master, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get("ticker") or "").strip().upper()
            fecha = (row.get("fecha") or "").strip()
            if not ticker or not fecha:
                continue

            o = OHLC(
                fecha=fecha,
                ticker=ticker,
                open=to_float(row.get("open")),
                high=to_float(row.get("high")),
                low=to_float(row.get("low")),
                close=to_float(row.get("close")),
            )
            por_ticker.setdefault(ticker, []).append(o)

    for ticker, registros in por_ticker.items():
        registros.sort(key=lambda r: r.fecha)
        por_ticker[ticker] = registros

    return por_ticker


def retornos_log_por_fecha(registros: List[OHLC]) -> Dict[str, float]:
    retornos: Dict[str, float] = {}
    prev_close: Optional[float] = None

    for r in registros:
        c = r.close
        if c is None or c <= 0:
            prev_close = None
            continue
        if prev_close is not None and prev_close > 0:
            retornos[r.fecha] = math.log(c / prev_close)
        prev_close = c

    return retornos


def pearson(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / n
    vx = sum((a - mx) ** 2 for a in x) / n
    vy = sum((b - my) ** 2 for b in y) / n
    sx = math.sqrt(vx)
    sy = math.sqrt(vy)
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return cov / (sx * sy)


def matriz_correlacion(por_ticker: Dict[str, List[OHLC]]) -> Tuple[List[str], List[List[float]]]:
    tickers = sorted(por_ticker.keys())
    retornos_ticker: Dict[str, Dict[str, float]] = {
        t: retornos_log_por_fecha(por_ticker[t]) for t in tickers
    }

    n = len(tickers)
    matriz: List[List[float]] = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                matriz[i][j] = 1.0
                continue
            t1 = tickers[i]
            t2 = tickers[j]
            fechas_comunes = sorted(set(retornos_ticker[t1].keys()) & set(retornos_ticker[t2].keys()))
            if len(fechas_comunes) < 2:
                matriz[i][j] = 0.0
                continue
            x = [retornos_ticker[t1][f] for f in fechas_comunes]
            y = [retornos_ticker[t2][f] for f in fechas_comunes]
            matriz[i][j] = pearson(x, y)

    return tickers, matriz


def sma(values: List[Optional[float]], window: int) -> List[Optional[float]]:
    if window <= 0:
        raise ValueError("window debe ser > 0")

    out: List[Optional[float]] = [None] * len(values)
    suma = 0.0
    cola: List[float] = []

    for i, v in enumerate(values):
        if v is None:
            cola.clear()
            suma = 0.0
            continue

        cola.append(v)
        suma += v

        if len(cola) > window:
            suma -= cola.pop(0)

        if len(cola) == window:
            out[i] = suma / window

    return out


def crear_heatmap(tickers: List[str], corr: List[List[float]], out_png: Path):
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)

    ax.set_xticks(range(len(tickers)))
    ax.set_yticks(range(len(tickers)))
    ax.set_xticklabels(tickers, rotation=90)
    ax.set_yticklabels(tickers)
    ax.set_title("Matriz de Correlación de Retornos (Pearson)")

    for i in range(len(tickers)):
        for j in range(len(tickers)):
            ax.text(j, i, f"{corr[i][j]:.2f}", ha="center", va="center", fontsize=6, color="black")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    return fig


def crear_candlestick(registros: List[OHLC], ticker: str, max_puntos: int = 120):
    data = [r for r in registros if r.open is not None and r.high is not None and r.low is not None and r.close is not None]
    if len(data) == 0:
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.set_title(f"{ticker} - Sin datos OHLC válidos")
        return fig

    data = data[-max_puntos:]

    closes = [r.close for r in data]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)

    x = list(range(len(data)))

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_title(f"{ticker} - Candlestick + SMA(20,50)")
    ax.set_xlabel("Índice temporal")
    ax.set_ylabel("Precio")

    ancho = 0.6
    for i, r in enumerate(data):
        color = "#2ca02c" if r.close >= r.open else "#d62728"

        # mecha (high-low)
        ax.vlines(i, r.low, r.high, color=color, linewidth=1)

        # cuerpo (open-close)
        bottom = min(r.open, r.close)
        height = abs(r.close - r.open)
        if height < 1e-8:
            height = 1e-8
        rect = Rectangle((i - ancho / 2, bottom), ancho, height, facecolor=color, edgecolor=color, alpha=0.8)
        ax.add_patch(rect)

    x20 = [i for i, v in enumerate(sma20) if v is not None]
    y20 = [v for v in sma20 if v is not None]
    x50 = [i for i, v in enumerate(sma50) if v is not None]
    y50 = [v for v in sma50 if v is not None]

    if x20:
        ax.plot(x20, y20, color="#1f77b4", linewidth=1.8, label="SMA 20")
    if x50:
        ax.plot(x50, y50, color="#ff7f0e", linewidth=1.8, label="SMA 50")

    if x20 or x50:
        ax.legend(loc="upper left")

    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def pares_extremos_correlacion(tickers: List[str], corr: List[List[float]]) -> Tuple[Tuple[str, str, float], Tuple[str, str, float]]:
    best = ("", "", -2.0)
    worst = ("", "", 2.0)

    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            c = corr[i][j]
            if c > best[2]:
                best = (tickers[i], tickers[j], c)
            if c < worst[2]:
                worst = (tickers[i], tickers[j], c)

    return best, worst


def exportar_pdf(
    tickers: List[str],
    corr: List[List[float]],
    por_ticker: Dict[str, List[OHLC]],
    tickers_candles: List[str],
    ruta_pdf: Path,
):
    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    best, worst = pares_extremos_correlacion(tickers, corr)

    with PdfPages(ruta_pdf) as pdf:
        # Portada técnica con resumen numérico
        fig_portada = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
        ax = fig_portada.add_subplot(111)
        ax.axis("off")

        texto = [
            "REPORTE TÉCNICO - DASHBOARD BURSÁTIL",
            f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Activos analizados: {len(tickers)}",
            "Métrica de correlación: Pearson sobre retornos log diarios",
            "",
            "Resumen numérico:",
            f"- Par más correlacionado: {best[0]} vs {best[1]}  (corr={best[2]:.4f})",
            f"- Par menos correlacionado: {worst[0]} vs {worst[1]}  (corr={worst[2]:.4f})",
            "",
            "Visualizaciones incluidas:",
            "1) Matriz de correlación (heatmap)",
            "2) Gráficos candlestick con SMA(20) y SMA(50)",
            "",
            "Notas algorítmicas:",
            "- SMA(k): promedio simple de k cierres consecutivos",
            "- Pearson: O(n) por par (sobre fechas comunes)",
            "- Matriz de correlación: O(m^2 * n) aprox., m=activos",
        ]

        ax.text(0.02, 0.98, "\n".join(texto), va="top", ha="left", fontsize=12)
        fig_portada.tight_layout()
        pdf.savefig(fig_portada)
        plt.close(fig_portada)

        # Heatmap
        fig_heat = crear_heatmap(tickers, corr, HEATMAP_PNG)
        pdf.savefig(fig_heat)
        plt.close(fig_heat)

        # Candlesticks por activo seleccionado
        for t in tickers_candles:
            if t not in por_ticker:
                continue
            fig_candle = crear_candlestick(por_ticker[t], t)
            png_path = SALIDA_DIR / f"candlestick_{t}.png"
            fig_candle.savefig(png_path, dpi=180)
            pdf.savefig(fig_candle)
            plt.close(fig_candle)


def seleccionar_tickers_por_defecto(tickers: List[str]) -> List[str]:
    preferidos = ["SPY", "QQQ", "GGAL"]
    seleccion = [t for t in preferidos if t in tickers]
    if len(seleccion) >= 3:
        return seleccion
    faltan = 3 - len(seleccion)
    for t in tickers:
        if t not in seleccion:
            seleccion.append(t)
            faltan -= 1
            if faltan == 0:
                break
    return seleccion


def main():
    por_ticker = cargar_ohlc_desde_master(RUTA_MASTER)
    if not por_ticker:
        raise RuntimeError("No se pudieron cargar series desde master_dataset")

    tickers, corr = matriz_correlacion(por_ticker)
    tickers_candles = seleccionar_tickers_por_defecto(tickers)

    exportar_pdf(
        tickers=tickers,
        corr=corr,
        por_ticker=por_ticker,
        tickers_candles=tickers_candles,
        ruta_pdf=PDF_REPORTE,
    )

    print("\nReq. 4 ejecutado correctamente.")
    print(f"- Heatmap: {HEATMAP_PNG}")
    print(f"- PDF técnico: {PDF_REPORTE}")
    for t in tickers_candles:
        print(f"- Candlestick: {SALIDA_DIR / f'candlestick_{t}.png'}")


if __name__ == "__main__":
    main()
