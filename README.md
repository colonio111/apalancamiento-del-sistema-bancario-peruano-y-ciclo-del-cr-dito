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
https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{código}/json/2016-1/2025-12/esp
```

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
| Periodo | 2016-01 a 2025-12 (120 meses) |
| Fecha de extracción | 2026-11-09 (BCRP) y 2026-11-11 (SBS) |

Las fechas de inicio y de corte son constantes en los scripts, por lo que una nueva ejecución pide exactamente el mismo periodo.

## 3. Estructura del repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `codigo/01_extraccion_api.py` | Vía 1: descarga las 4 series del BCRP |
| `codigo/02_scraping_web.py` | Vía 2: rastrea el portal de la SBS, descarga los 360 reportes y extrae las cifras por banco |
| `codigo/03_limpieza_datos.py` | Limpieza, validación, panel balanceado, variables del estudio, unión de las dos vías y hash |
| `codigo/04_analisis.py` | Estimaciones, tablas y figuras del artículo (Fase 4) |
| `datos_crudos/` | Respuestas originales de la API (JSON), reportes originales de la SBS (XLS), inventario de descargas y CSV crudos. **No se editan.** |
| `datos_procesados/` | `datos_procesados_2024200495A.csv` y su hash SHA-256 |
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
| beautifulsoup4 | 4.15.0 | lectura del HTML del portal de la SBS |
| python-calamine | 0.9.1 | lectura de los Excel de la SBS (formatos antiguo y moderno) |

## 5. Verificación de integridad

El archivo final se guarda con formato fijo (6 decimales y saltos de línea `\n`), de modo que su hash es el mismo en cualquier sistema operativo:

```
datos_procesados_2024200495A.csv
SHA-256: 2b30700e11c1107a3b40e28d52f759f2ae269025a380992460b5e4cbd3e5ab36
```

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

## 7. Uso de inteligencia artificial

El código se desarrolló con asistencia de Claude (Anthropic) como apoyo de programación y revisión metodológica. La autora ejecutó, verificó y es responsable de todo el contenido. La declaración completa figura en el artículo.
