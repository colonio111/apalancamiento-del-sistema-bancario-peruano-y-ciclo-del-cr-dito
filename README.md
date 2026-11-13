# Tema 85 · Apalancamiento del sistema bancario peruano y ciclo del crédito

- **Autora:** Lucia Pamela Colonio Yaringaño
- **Código de matrícula:** 2024200495A
- **Curso:** Finanzas I (055D) · Facultad de Economía · Universidad Nacional del Centro del Perú · Unidad II · 2026-II
- **Repositorio:** https://github.com/colonio111/apalancamiento-del-sistema-bancario-peruano-y-ciclo-del-cr-dito

Este repositorio contiene el código y los datos del artículo *Prociclicidad del apalancamiento de la banca múltiple peruana frente al ciclo del crédito y del producto, 2016–2025*. El resultado es un panel balanceado de **15 bancos × 120 meses = 1 800 observaciones banco-mes**, construido con dos vías de extracción.

## 1. Fuentes de datos

### Vía 1 · API REST del BCRP (BCRPData)

Endpoint (formato documentado por el BCRP), una solicitud por serie:

```
https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{código}/json/2010-1/2025-12/esp
```

Las series se descargan desde 2010-01. Los meses 2010-2015 son una **pre-muestra** que solo se usa para calcular las brechas del ciclo con el filtro de Hamilton (2018), que pierde los primeros 35 meses de cada serie (horizonte de 24 meses y 12 rezagos). El panel de bancos empieza en 2016-01.

| Código | Serie | Unidad |
|---|---|---|
| PN00505MM | Crédito de las sociedades creadoras de depósito al sector privado, tipo de cambio constante | millones de S/ |
| PN01773AM | PBI desestacionalizado | índice 2007 = 100 |
| PD04722MM | Tasa de referencia de la política monetaria | % |
| PN38705PM | Índice de precios al consumidor de Lima Metropolitana | índice dic. 2021 = 100 |

No requiere clave de acceso (API key).

### Vía 2 · Descarga programática del portal estadístico de la SBS

Páginas rastreadas con BeautifulSoup (selector CSS `a[href]`), una por reporte:

```
https://www.sbs.gob.pe/app/stats_net/stats/EstadisticaSistemaFinancieroResultados.aspx?c={reporte}
```

Archivos descargados (uno por mes):

```
https://intranet2.sbs.gob.pe/estadistica/financiera/{año}/{Mes}/{reporte}-{mm}{año}.XLS
```

| Reporte | Contenido | Variables extraídas |
|---|---|---|
| B-2201 | Balance general por empresa bancaria | activo, pasivo, patrimonio, créditos (vigentes, refinanciados, atrasados), provisiones |
| B-2401 | Indicadores financieros por empresa bancaria | morosidad |
| B-2402 | Requerimiento de patrimonio efectivo y ratio de capital global | ratio de capital global |

Buenas prácticas aplicadas: revisión previa de `robots.txt` (el portal permite `/app/stats_net/`; el servidor de archivos no publica `robots.txt`), User-Agent identificable, pausa de 1,5 s entre solicitudes, hasta 3 reintentos y no se vuelve a descargar un archivo que ya existe.

### Llave de integración

**Entidad + fecha (AAAA-MM).** Cada observación banco-mes de la SBS recibe las series del BCRP del mismo mes.

## 2. Ventana congelada

| Parámetro | Valor |
|---|---|
| Panel de bancos | 2016-01 a 2025-12 (120 meses) |
| Series macro del BCRP | 2010-01 a 2025-12 (192 meses, con la pre-muestra) |
| Fecha de extracción | 2026-11-12 (BCRP) y 2026-11-11 (SBS) |

Las fechas de inicio y de corte son constantes en los scripts, por lo que una nueva ejecución pide exactamente el mismo periodo.

## 3. Estructura del repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `codigo/01_extraccion_api.py` | Vía 1: descarga las 4 series del BCRP |
| `codigo/02_scraping_web.py` | Vía 2: rastrea el portal de la SBS, descarga los 360 reportes y extrae las cifras por banco |
| `codigo/03_limpieza_datos.py` | Limpieza, validación, panel balanceado, variables del estudio, unión de las dos vías y hash |
| `codigo/04_analisis.py` | Brechas del ciclo, estadística descriptiva, pruebas de raíz unitaria, prueba de prociclicidad, modelo dinámico, heterogeneidad y robustez |
| `datos_crudos/` | Respuestas originales de la API (JSON), reportes originales de la SBS (XLS), inventario de descargas y CSV crudos. **No se editan.** |
| `datos_procesados/` | Panel final (`datos_procesados_2024200495A.csv`), series macro (`macro_mensual_2024200495A.csv`) y sus hashes SHA-256 |
| `salidas/` | Tablas (CSV) y figuras (SVG) que usa el artículo |
| `diccionario_variables.md` | Definición, unidad y fuente de cada variable |
| `incidencias_fuente.md` | Particularidades de las fuentes y cómo se resolvieron |
| `log_ejecucion.txt` | Registro con fecha, hora y código HTTP de cada paso |

## 4. Cómo reproducir los resultados

**Requisitos:** Python 3.11 o superior (probado con Python 3.14 en Windows 11) y conexión a internet.

Desde la carpeta raíz del repositorio:

```bash
python -m pip install -r requirements.txt
python codigo/01_extraccion_api.py      # ~10 s
python codigo/02_scraping_web.py        # ~12 min la primera vez; luego solo lee los archivos
python codigo/03_limpieza_datos.py      # ~2 s
python codigo/04_analisis.py            # ~5 s: genera todas las tablas y figuras en salidas/
```

En Windows, si `python` no se reconoce, usar `py` (por ejemplo, `py codigo/01_extraccion_api.py`).

Demostración en vivo de la Vía 2 (descarga solo los últimos 3 meses en una carpeta aparte, ~30 s):

```bash
python codigo/02_scraping_web.py --demo
```

### Versiones de las librerías

| Librería | Versión | Uso |
|---|---|---|
| requests | 2.34.2 | solicitudes HTTP |
| pandas | 3.0.6 | tablas de datos |
| numpy | 2.5.3 | cálculo numérico |
| beautifulsoup4 | 4.15.0 | lectura del HTML del portal de la SBS |
| python-calamine | 0.9.1 | lectura de los Excel de la SBS (formatos antiguo y moderno) |
| scipy | 1.18.1 | distribuciones estadísticas (valores p) |
| matplotlib | 3.11.2 | figuras del artículo |

`04_analisis.py` anota en el log las versiones con las que se ejecutó.

## 5. Verificación de integridad

Los archivos procesados se guardan con formato fijo (6 decimales y saltos de línea `\n`), de modo que su hash es el mismo en cualquier sistema operativo:

```
datos_procesados_2024200495A.csv   2b30700e11c1107a3b40e28d52f759f2ae269025a380992460b5e4cbd3e5ab36
macro_mensual_2024200495A.csv      f37533722ac53198c77b7a9dde75c6b2131b1f87b5cd25747672e1a569b21ac0
```

El BCRP revisa ocasionalmente cifras pasadas (sobre todo del PBI). Si una nueva descarga cambia el hash de las series macro, la diferencia se debe a esas revisiones y no al código.

Para comprobarlo:

```bash
# Windows (PowerShell)
Get-FileHash datos_procesados/datos_procesados_2024200495A.csv -Algorithm SHA256
# macOS / Linux
shasum -a 256 datos_procesados/datos_procesados_2024200495A.csv
```

## 6. Resumen del panel

| Concepto | Valor |
|---|---|
| Bancos incluidos (120 meses completos) | 15: Alfin Banco, BANCOM, BanBif, Banco Falabella, Banco GNB, Banco ICBC, Banco Pichincha, Banco Ripley, Banco Santander Perú, BBVA Perú, BCP, Citibank Perú, Interbank, Mibanco, Scotiabank Perú |
| Bancos excluidos (entraron o salieron en el periodo) | Banco BCI Perú, Banco Cencosud, Bank of China, Compartamos Banco, Deutsche Bank Perú, Santander Consumer Bank |
| Observaciones | 1 800 banco-mes × 23 columnas |
| Valores vacíos | ninguno |
| Identidad activo = pasivo + patrimonio | se cumple en todas las filas (diferencia máxima: S/ 39) |

## 7. Salidas del análisis (`salidas/`)

| Archivo | En el artículo | Contenido |
|---|---|---|
| `tabla_fuentes.csv` | Tabla 1 | Fuentes, códigos y variables de las dos vías |
| `fig_ciclos.svg` | Figura 2 | Brechas del crédito real y del PBI (filtro de Hamilton) y tasa de referencia |
| `brechas_ciclo.csv` | — | Datos de las brechas |
| `tabla_descriptivos.csv` | Tabla 2 | Estadística descriptiva (con desviación entre bancos y dentro de cada banco) |
| `fig_apalancamiento.svg` | Figura 3 | Apalancamiento y ratio de capital global, 2016-2025 |
| `fig_mapa_calor.svg` | Figura 4 | Apalancamiento promedio anual por banco |
| `tabla_raiz_unitaria.csv` | Tabla 3 | Pruebas de raíz unitaria (Choi, Maddala-Wu y ADF) |
| `tabla_adrian_shin.csv` | Tabla 4 | Prueba de prociclicidad de Adrian y Shin (H1) |
| `fig_adrian_shin.svg` | Figura 5 | Crecimiento del activo frente al del apalancamiento |
| `tabla_modelo_dinamico.csv` | Tabla 5 | Apalancamiento frente a las brechas del ciclo (H2) |
| `fig_heterogeneidad.svg` | Figura 6 | Prociclicidad por periodo y por colchón de capital (H3) |
| `tabla_heterogeneidad.csv` | Tabla A1 | Pendientes por grupo y pruebas de diferencia |
| `tabla_robustez.csv` | Tabla 6, panel A | Resultados con especificaciones alternativas |
| `tabla_robustez_gmm.csv` | Tabla 6, panel B | Modelo dinámico con System GMM y sus diagnósticos |

Métodos implementados en `04_analisis.py` con numpy y scipy: filtros de Hamilton y Hodrick-Prescott, efectos fijos con errores de Driscoll y Kraay, pruebas de raíz unitaria con valores p simulados (semilla 495, últimos dígitos del código de matrícula) y System GMM con instrumentos colapsados. El System GMM se validó con datos simulados antes de aplicarlo.

## 8. Uso de inteligencia artificial

El código se desarrolló con asistencia de Claude (Anthropic) como apoyo de programación y revisión metodológica. La autora ejecutó, verificó y es responsable de todo el contenido. La declaración completa figura en el artículo.
