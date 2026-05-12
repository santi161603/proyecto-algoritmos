# Proyecto: Análisis de Algoritmos — BVC

Conjunto de utilidades para ETL financiero, comparación de series temporales,
detección de patrones/volatilidad y generación de reportes visuales.

---

## Estructura relevante

```
proyecto-algoritmos/
├── config.py
├── main.py
├── requirements.txt
├── etl/
├── data/               # raw/, clean/, master_dataset.csv
├── reportes/           # Salida: PNG y PDF
├── seguimiento3/
└── web_app.py
```

---

## Quickstart (Windows — PowerShell)

1. Crear y activar entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

3. Ejecutar ETL (control de anomalías)

```powershell
# $env:ESTRATEGIA_ANOMALIAS = "marcar"  # opciones: marcar|eliminar|winsorizar
python main.py
```

4. Lanzar interfaz web (dentro del `venv`)

```powershell
python -m streamlit run web_app.py
```

5. Salidas importantes

- `data/master_dataset.csv` — dataset unificado (long-format)
- `data/clean/*.csv` — series limpias por activo
- `reportes/` — imágenes y `reporte_tecnico_dashboard.pdf`

---

## Archivos de interés

- `etl/transformador.py` — limpieza y tratamiento de anomalías
- `etl/similitud.py` — Euclidiana, Pearson, DTW, Coseno
- `seguimiento3/analisis_seguimiento3.py` — runner de patrones y riesgos
- `seguimiento4/dashboard_bursatil.py` — heatmap, candlesticks, PDF
- `web_app.py` — Streamlit UI integradora

---

## Troubleshooting rápido

- Ejecuta desde la raíz del repositorio.
- Si aparece `ModuleNotFoundError`, activa el `venv` o ejecuta con `python -m`.
- Para Streamlit, usa `python -m streamlit run web_app.py` dentro del `venv`.

---

## Documentación adicional

- `PROJECT_README.md` — instrucciones operativas detalladas
- `REQ2_MATEMATICA.md` — explicación matemática de similitud
- `GUIA_IMPLEMENTACION.md` — plantillas y checklist

```bash
pip install -r requirements.txt
python main.py
```


## Interfaz web (Dashboard)

Ejecuta la interfaz web interactiva con Streamlit:

```powershell
c:/Users/Santiago/Documents/GitHub/proyecto-algoritmos/.venv/Scripts/python.exe -m streamlit run web_app.py
```

La app contiene pestañas para los Requerimientos 1–4 y permite ejecutar el ETL, comparar series,
analizar patrones/volatilidad y generar el reporte técnico en PDF.

## Documentación adicional

- Explicación matemática y algoritmos de similitud: `REQ2_MATEMATICA.md`
- README operativo y arquitectura del proyecto: `PROJECT_README.md`


## Cómo encontrar los curr_id de Investing.com

1. Abre `https://www.investing.com` y busca el activo
2. Abre DevTools (F12) → pestaña **Network**
3. En la página del activo, ve a **Historical Data**
4. Filtra por `HistoricalDataAjax` en el panel Network
5. Haz clic en la request → pestaña **Payload**
6. Copia el valor de `curr_id`

---

## Decisiones algorítmicas documentadas

### Interpolación lineal (InterpoladorLineal)
- **Complejidad:** O(n × c) donde c = número de campos (constante = 5)
- **Justificación:** gaps en series de precios corresponden a festivos bursátiles;
  el precio no cambia abruptamente en esos días, por lo que la interpolación
  lineal es una aproximación razonable y computacionalmente eficiente.
- **Límite:** no se interpola si el gap supera `MAX_GAPS_INTERPOLACION` días
  para evitar fabricar datos durante suspensiones prolongadas.

### Detección de anomalías (DetectorAnomalias)
- **Complejidad:** O(n) — dos pasadas lineales
- **Métrica:** Z-score sobre retornos logarítmicos diarios
- **Decisión:** se MARCA pero NO se elimina la anomalía, ya que eventos
  como el crash de COVID-19 son retornos extremos reales relevantes para
  el análisis de volatilidad del Req. 3.

### Dataset maestro long-format
- **Ventaja sobre wide-format:** no genera columnas vacías por diferencias
  en calendarios bursátiles (BVC vs NYSE vs LSE tienen distintos festivos).
- **Complejidad de construcción:** O(A × N)
