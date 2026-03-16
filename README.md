# Análisis de Algoritmos — BVC Project
## Requerimiento 1: ETL de datos financieros

---

## Estructura del proyecto

```
proyecto_bvc/
│
├── config.py                      # Configuración global (activos, fechas, rutas)
├── main.py                        # Punto de entrada
├── requirements.txt
│
├── etl/
│   ├── __init__.py
│   ├── interfaces.py              # Contratos abstractos (IExtractor, ITransformador, ICargador, ILogger)
│   ├── models.py                  # Entidades del dominio (RegistroPrecio, SerieHistorica, Activo)
│   ├── logger.py                  # ConsoleFileLogger
│   ├── extractor_investing.py     # Scraper de Investing.com
│   ├── transformador.py           # Limpieza: interpolación + detección de anomalías
│   ├── cargador.py                # Persistencia CSV (individual + maestro)
│   └── pipeline.py                # Orquestador ETL
│
├── data/
│   ├── raw/                       # CSVs crudos por activo (generados automáticamente)
│   ├── clean/                     # CSVs limpios por activo
│   └── master_dataset.csv         # Dataset unificado long-format
│
├── logs/
│   └── etl.log                    # Log de ejecución
│
└── reportes/                      # Salida del dashboard (Req. 4)
```

---

## Cómo ejecutar

```bash
pip install -r requirements.txt
python main.py
```


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
