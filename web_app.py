from __future__ import annotations

import csv
import io
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import RUTA_MASTER
from main import main as run_etl_main
from etl.similitud import CalculadorSimilitud, ANALISIS_COMPLEJIDAD
from etl.analisis_frecuencia_volatilidad import AnalizadorPatronesVolatilidad
from seguimiento4.dashboard_bursatil import (
    HEATMAP_PNG,
    PDF_REPORTE,
    SALIDA_DIR as SALIDA_REQ4,
    cargar_ohlc_desde_master,
    crear_candlestick,
    crear_heatmap,
    exportar_pdf,
    matriz_correlacion,
)


def cargar_master_rows() -> List[Dict[str, str]]:
    if not Path(RUTA_MASTER).exists():
        return []
    rows: List[Dict[str, str]] = []
    with open(RUTA_MASTER, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def get_tickers(rows: List[Dict[str, str]]) -> List[str]:
    return sorted({(r.get("ticker") or "").strip().upper() for r in rows if r.get("ticker")})


def to_float(v: Optional[str]) -> Optional[float]:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def precios_close_por_ticker(rows: List[Dict[str, str]], ticker: str) -> List[float]:
    filtrados = [r for r in rows if (r.get("ticker") or "").strip().upper() == ticker]
    filtrados.sort(key=lambda r: (r.get("fecha") or ""))
    return [to_float(r.get("close")) for r in filtrados]


def fechas_y_close(rows: List[Dict[str, str]], ticker: str):
    filtrados = [r for r in rows if (r.get("ticker") or "").strip().upper() == ticker]
    filtrados.sort(key=lambda r: (r.get("fecha") or ""))
    fechas = [r.get("fecha") for r in filtrados]
    closes = [to_float(r.get("close")) for r in filtrados]
    return fechas, closes


def series_por_ticker(rows: List[Dict[str, str]]) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for r in sorted(rows, key=lambda x: ((x.get("ticker") or ""), (x.get("fecha") or ""))):
        t = (r.get("ticker") or "").strip().upper()
        if not t:
            continue
        out.setdefault(t, []).append(to_float(r.get("close")))
    return out


def csv_bytes_from_rows(headers: List[str], rows: List[Dict[str, object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def app_header():
    st.set_page_config(page_title="Dashboard Algorítmico Bursátil", layout="wide")
    st.title("📊 Dashboard Algorítmico Bursátil")
    st.caption("Universidad del Quindío · Análisis de Algoritmos · ETL + Similitud + Riesgo + Visualización")

    rows = cargar_master_rows()
    tickers = get_tickers(rows)

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros en master", f"{len(rows):,}".replace(",", "."))
    c2.metric("Activos detectados", len(tickers))
    c3.metric("Estado dataset", "Disponible" if rows else "No disponible")

    return rows, tickers


def tab_requerimiento_1(rows: List[Dict[str, str]]):
    st.subheader("Requerimiento 1 · ETL, limpieza y unificación")
    st.write("Automatiza extracción, transformación y carga con política de anomalías configurable.")

    estrategia = st.selectbox("Estrategia de anomalías", ["marcar", "eliminar", "winsorizar"], index=0)

    if st.button("▶ Ejecutar ETL completo", use_container_width=True):
        try:
            os.environ["ESTRATEGIA_ANOMALIAS"] = estrategia
            with st.spinner("Ejecutando ETL..."):
                resultado = run_etl_main()
            st.success("ETL ejecutado correctamente")
            st.code(resultado.resumen())
        except Exception as exc:
            st.error(f"Error al ejecutar ETL: {exc}")

    st.markdown("Resumen actual del dataset maestro")
    if not rows:
        st.warning("No existe `master_dataset`. Ejecuta ETL para generarlo.")
        return

    tickers = get_tickers(rows)
    st.write({
        "activos": len(tickers),
        "registros": len(rows),
        "primer_activo": tickers[0] if tickers else "N/A",
        "ultimo_activo": tickers[-1] if tickers else "N/A",
    })


def tab_requerimiento_2(rows: List[Dict[str, str]], tickers: List[str]):
    st.subheader("Requerimiento 2 · Similitud entre series de tiempo")

    if len(tickers) < 2:
        st.warning("Se requieren al menos 2 activos en `master_dataset`.")
        return

    c1, c2, c3 = st.columns([1, 1, 1])
    t1 = c1.selectbox("Activo A", tickers, index=0)
    t2 = c2.selectbox("Activo B", tickers, index=1 if len(tickers) > 1 else 0)
    usar_retornos = c3.checkbox("Comparar con retornos", value=True)

    if t1 == t2:
        st.info("Selecciona dos activos distintos para comparar.")
        return

    if st.button("📐 Calcular similitud", use_container_width=True):
        try:
            p1 = precios_close_por_ticker(rows, t1)
            p2 = precios_close_por_ticker(rows, t2)

            r = CalculadorSimilitud.comparar_series(
                p1,
                p2,
                usar_retornos=usar_retornos,
                activo_x=t1,
                activo_y=t2,
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Euclidiana", f"{r.euclidiana:.6f}")
            m2.metric("Pearson", f"{r.pearson:.6f}")
            m3.metric("DTW", f"{r.dtw:.6f}")
            m4.metric("Coseno", f"{r.coseno:.6f}")

            f1, s1 = fechas_y_close(rows, t1)
            f2, s2 = fechas_y_close(rows, t2)
            st.line_chart({t1: [v for v in s1 if v is not None], t2: [v for v in s2 if v is not None]})

            st.text_area("Análisis de complejidad", ANALISIS_COMPLEJIDAD.strip(), height=260)

        except Exception as exc:
            st.error(f"Error al calcular similitud: {exc}")


def tab_requerimiento_3(rows: List[Dict[str, str]]):
    st.subheader("Requerimiento 3 · Frecuencia de patrones y volatilidad")

    c1, c2 = st.columns(2)
    ventana = c1.slider("Ventana alza consecutiva", min_value=3, max_value=10, value=5)
    umbral = c2.slider("Umbral reversión en V", min_value=0.0, max_value=0.05, value=0.01, step=0.005)

    if st.button("📈 Ejecutar análisis de patrones y riesgo", use_container_width=True):
        try:
            series = series_por_ticker(rows)
            if not series:
                st.warning("No hay series en master_dataset")
                return

            analizador = AnalizadorPatronesVolatilidad(ventana_alza=ventana, umbral_reversion=umbral)
            patrones, riesgo = analizador.analizar_portafolio(series)
            ranking = analizador.ranking_riesgo_desc(riesgo)

            st.success(f"Análisis ejecutado para {len(series)} activos")

            st.markdown("Top 10 activos más riesgosos")
            top10 = ranking[:10]
            st.write([
                {
                    "ticker": r.ticker,
                    "volatilidad_anualizada": round(r.volatilidad_historica_anualizada, 6),
                    "categoria": r.categoria_riesgo,
                }
                for r in top10
            ])

            st.markdown("Frecuencia de patrones (primeros 10)")
            st.write([
                {
                    "ticker": p.ticker,
                    "alza_consecutiva": p.frecuencia_alza_consecutiva,
                    "prop_alza": round(p.proporcion_alza_consecutiva, 6),
                    "reversion_v": p.frecuencia_reversion_v,
                    "prop_reversion_v": round(p.proporcion_reversion_v, 6),
                }
                for p in patrones[:10]
            ])

            export_rows = [
                {
                    "ticker": r.ticker,
                    "volatilidad_historica_anualizada": f"{r.volatilidad_historica_anualizada:.8f}",
                    "categoria_riesgo": r.categoria_riesgo,
                }
                for r in ranking
            ]
            st.download_button(
                "⬇ Descargar ranking de riesgo (CSV)",
                data=csv_bytes_from_rows(
                    ["ticker", "volatilidad_historica_anualizada", "categoria_riesgo"],
                    export_rows,
                ),
                file_name="ranking_riesgo_req3.csv",
                mime="text/csv",
            )

        except Exception as exc:
            st.error(f"Error en Req.3: {exc}")


def tab_requerimiento_4(tickers: List[str]):
    st.subheader("Requerimiento 4 · Dashboard visual + reporte PDF")

    if not Path(RUTA_MASTER).exists():
        st.warning("No existe `master_dataset`. Ejecuta ETL primero.")
        return

    seleccion_default = [t for t in ["SPY", "QQQ", "GGAL"] if t in tickers]
    seleccion = st.multiselect(
        "Activos para candlestick",
        options=tickers,
        default=seleccion_default if seleccion_default else tickers[:3],
    )
    if not seleccion:
        st.info("Selecciona al menos un activo.")
        return

    if st.button("🖼 Generar visualizaciones y PDF", use_container_width=True):
        try:
            por_ticker = cargar_ohlc_desde_master(RUTA_MASTER)
            tks, corr = matriz_correlacion(por_ticker)

            fig_heat = crear_heatmap(tks, corr, HEATMAP_PNG)
            st.pyplot(fig_heat, clear_figure=True)

            for t in seleccion:
                fig = crear_candlestick(por_ticker.get(t, []), t)
                out = SALIDA_REQ4 / f"candlestick_{t}.png"
                out.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(out, dpi=180)
                st.pyplot(fig, clear_figure=True)

            exportar_pdf(
                tickers=tks,
                corr=corr,
                por_ticker=por_ticker,
                tickers_candles=seleccion,
                ruta_pdf=PDF_REPORTE,
            )

            st.success("Dashboard visual generado correctamente")

            if HEATMAP_PNG.exists():
                st.image(str(HEATMAP_PNG), caption="Heatmap de correlación")

            if PDF_REPORTE.exists():
                with open(PDF_REPORTE, "rb") as f:
                    st.download_button(
                        "⬇ Descargar reporte técnico PDF",
                        data=f.read(),
                        file_name=PDF_REPORTE.name,
                        mime="application/pdf",
                    )
        except Exception as exc:
            st.error(f"Error en Req.4: {exc}")


def main():
    rows, tickers = app_header()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Req. 1 · ETL",
        "Req. 2 · Similitud",
        "Req. 3 · Patrones/Riesgo",
        "Req. 4 · Dashboard/PDF",
    ])

    with tab1:
        tab_requerimiento_1(rows)
    with tab2:
        tab_requerimiento_2(rows, tickers)
    with tab3:
        tab_requerimiento_3(rows)
    with tab4:
        tab_requerimiento_4(tickers)


if __name__ == "__main__":
    main()
