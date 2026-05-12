# REQUERIMIENTO 2 — Explicación matemática y análisis algorítmico

Este documento explica de forma matemática y algorítmica los cuatro métodos de similitud implementados en `etl/similitud.py`.

1) Distancia Euclidiana
----------------------
- Fórmula (dos vectores x,y de dimensión n):

  $$d_{E}(x,y)=\sqrt{\sum_{i=1}^{n}(x_i-y_i)^2}$$

- Interpretación: medida de discrepancia en la norma L2; sensible a la escala absoluta.
- Implementación práctica: se normaliza por \(\sqrt{n}\) en la comparación de series de retornos para permitir comparaciones de distinta duración.
- Complejidad temporal: O(n). Espacio: O(1) (acumuladores).

2) Correlación de Pearson
-------------------------
- Fórmula (muestras empíricas):

  $$\rho_{X,Y}=\frac{\mathrm{Cov}(X,Y)}{\sigma_X\sigma_Y} = \frac{\sum_{i=1}^n (x_i-\bar{x})(y_i-\bar{y})}{\sqrt{\sum_{i=1}^n (x_i-\bar{x})^2}\sqrt{\sum_{i=1}^n (y_i-\bar{y})^2}}$$

- Interpretación: mide la relación lineal entre dos series; rango \([-1,1]\).
- Estabilidad: invariante ante cambios lineales (es decir, escala y traslación). Sensible a outliers.
- Complejidad: O(n) — cálculo de medias, varianzas y covarianza (se pueden computar en una pasada usando Welford, pero la implementación actual usa dos pasadas para claridad).

3) Dynamic Time Warping (DTW)
-----------------------------
- Objetivo: permitir alineación no lineal entre dos secuencias (\(x_1..x_n\), \(y_1..y_m\)).
- Recurrencia (versión L1/L2 aplicada al coste por celda):

  \[\mathrm{DTW}(i,j) = d(x_i,y_j) + \min\{\mathrm{DTW}(i-1,j),\mathrm{DTW}(i,j-1),\mathrm{DTW}(i-1,j-1)\}\]

  donde \(d(x_i,y_j)=|x_i-y_j|\) (o \( (x_i-y_j)^2 \) si se prefiere L2).

- Matriz de programación dinámica: tamaño \((n+1)\times(m+1)\) con condición inicial \(\mathrm{DTW}(0,0)=0\) y resto \(+\infty\).
- Complejidad temporal: O(n·m). Espacio: O(n·m) (se puede optimizar a O(min(n,m)) si se recorren bandas o se usa streaming).
- Comentario: útil para series con desfases temporales o velocidades diferentes; coste elevado para series largas.

4) Similitud por Coseno
-----------------------
- Fórmula:

  $$\mathrm{cos}(x,y)=\frac{\sum_{i=1}^n x_i y_i}{\sqrt{\sum_{i=1}^n x_i^2}\sqrt{\sum_{i=1}^n y_i^2}}$$

- Interpretación: medida angular entre vectores; rango \([-1,1]\) si se permiten signos, o \([0,1]\) para vectores no negativos.
- Uso: compara dirección/movimiento relativo más que magnitud absoluta.
- Complejidad: O(n). Espacio: O(1).

Consideraciones prácticas
-------------------------
- Preprocesamiento: en `etl/similitud.py` se calcula por defecto sobre retornos logarítmicos para lograr invarianza frente a escalas de precio.
- Longitudes diferentes: DTW admite longitudes distintas; para métricas lineales (Euclidiana, Pearson, Coseno) se recorta al mínimo común de retornos (alineación por prefijo) o se normaliza.
- Robustez: para detectar anomalías o outliers previos se recomienda aplicar el tratamiento del `TransformadorSerie` (Req.1) antes de comparar series.

Pseudocódigo (DTW mínimo)
-------------------------
```
function DTW(x[1..n], y[1..m]):
    create matrix D[0..n,0..m] filled with +inf
    D[0][0] = 0
    for i in 1..n:
        for j in 1..m:
            cost = abs(x[i]-y[j])
            D[i][j] = cost + min(D[i-1][j], D[i][j-1], D[i-1][j-1])
    return D[n][m]
```

Complejidad y elección
----------------------
- Si la velocidad es crítica, usar Euclidiana/Pearson/Coseno (O(n)).
- Si la alineación es importante (desfase, aceleración), usar DTW pese a su coste O(n·m).

Referencias
-----------
- Keogh, E., & Ratanamahatana, C. A. (2005). Exact indexing of dynamic time warping.
- Pearson, K. (1895). Note on regression and inheritance in the case of two parents.
- Cosine similarity — documento técnico y usos en IR / NLP.

---

Cómo ejecutar los ejemplos
--------------------------

Desde la raíz del repositorio (con `venv` activado):

```powershell
python ejemplos_similitud.py
```

El script `ejemplos_similitud.py` ejecuta comparaciones de ejemplo y un benchmark
rápido para mostrar tiempos relativos entre Euclidiana/Pearson/Coseno y DTW.
