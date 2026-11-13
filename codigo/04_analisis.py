# Autora: Lucia Pamela Colonio Yaringaño
# Código de matrícula: 2024200495A
# Tema N.º 85 del temario (Unidad II): Apalancamiento del sistema bancario peruano y ciclo del crédito
# Fecha de extracción: 2026-11-12
"""
04_analisis.py · Análisis descriptivo y econométrico del artículo.

Entradas (generadas por 03_limpieza_datos.py):
    datos_procesados/datos_procesados_2024200495A.csv   panel de 15 bancos × 120 meses
    datos_procesados/macro_mensual_2024200495A.csv      series del BCRP 2010-01 a 2025-12

Bloques (cada uno genera sus tablas y figuras en /salidas):
    1. Fuentes y ciclo económico
         tabla_fuentes.csv        Tabla 1: fuentes, códigos y variables
         brechas_ciclo.csv        brechas del crédito y del PBI (filtro de Hamilton)
         fig_ciclos.svg           Figura 2: ciclo del crédito y del producto
    2. Análisis descriptivo del panel de bancos
         tabla_descriptivos.csv   Tabla 2: estadística descriptiva
         fig_apalancamiento.svg   Figura 3: apalancamiento y capital 2016-2025
         fig_mapa_calor.svg       Figura 4: apalancamiento por banco y año
    3. Estacionariedad y prueba de prociclicidad (H1)
         tabla_raiz_unitaria.csv  Tabla 3: pruebas de raíz unitaria (panel y series)
         tabla_adrian_shin.csv    Tabla 4: prueba de prociclicidad de Adrian y Shin (2010)
         fig_adrian_shin.svg      Figura 5: crecimiento del activo frente al del apalancamiento
    4. Modelo dinámico del apalancamiento frente al ciclo (H2)
         tabla_modelo_dinamico.csv  Tabla 5: modelo dinámico y crecimiento a 12 meses
    5. Heterogeneidad (H3) y robustez
         tabla_heterogeneidad.csv   Tabla A1 (anexo): β por periodo y por colchón de capital
         fig_heterogeneidad.svg     Figura 6: prociclicidad por periodo y por colchón de capital
         tabla_robustez.csv         Tabla 6, panel A: resultados principales con otras especificaciones
         tabla_robustez_gmm.csv     Tabla 6, panel B: modelo dinámico con System GMM

Método econométrico (implementado con numpy y scipy, sin cajas negras):
    - Efectos fijos por banco (transformación within) y, si se pide, por mes.
    - Errores estándar de Driscoll y Kraay (1998): robustos a heterocedasticidad,
      autocorrelación y dependencia entre bancos (choques comunes del sistema).
    - System GMM (Arellano y Bover, 1995; Blundell y Bond, 1998) en una etapa, con
      instrumentos colapsados (Roodman, 2009), errores robustos por banco, prueba
      de Hansen y pruebas de autocorrelación AR(1) y AR(2) de Arellano y Bond (1991).
    - Raíz unitaria: Dickey-Fuller aumentada por banco, combinada con las pruebas
      de Maddala-Wu y Choi; valores p del estadístico de Dickey-Fuller obtenidos por
      simulación de Monte Carlo con la semilla SEMILLA.

Las tablas se guardan en CSV (el artículo en Typst las lee directamente) y las
figuras en SVG (formato vectorial, nítido a cualquier tamaño).

Ejecución (desde la carpeta raíz del repositorio):
    python codigo/04_analisis.py      (en Windows sin PATH: py codigo/04_analisis.py)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # dibuja sin abrir ventanas (funciona en cualquier computadora)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# 1. Parámetros
# ---------------------------------------------------------------------------
CODIGO_MATRICULA = "2024200495A"
SEMILLA = 495                 # últimos 4 dígitos del código (0495), para cualquier paso aleatorio
FECHA_INICIO = "2016-01"      # inicio del panel de bancos
FECHA_CORTE = "2025-12"

# Filtro de Hamilton (2018) para datos mensuales: horizonte de 2 años y 12 rezagos
HAMILTON_H = 24
HAMILTON_P = 12

# Periodo de la pandemia (se sombrea en las figuras)
PANDEMIA = ("2020-03", "2021-12")

# Pruebas de raíz unitaria
REZAGOS_MAX_ADF = 12          # rezagos máximos de la ADF (se eligen por criterio de Akaike)
REPLICAS_DF = 20000           # réplicas de Monte Carlo para los valores p de Dickey-Fuller
NIVEL_SIGNIFICANCIA = 0.05

# Estilo común de las figuras
AZUL = "#1f3a5f"
DORADO = "#c49a2c"
GRIS = "#8a8f98"
GRIS_CLARO = "#e6e8eb"
ANCHO_UNA_COLUMNA = 3.4       # pulgadas (una columna del artículo)
ANCHO_DOS_COLUMNAS = 7.0      # pulgadas (ancho completo)

# ---------------------------------------------------------------------------
# 2. Rutas relativas a la carpeta del proyecto
# ---------------------------------------------------------------------------
if "__file__" in globals():
    RAIZ = Path(__file__).resolve().parent.parent
else:
    RAIZ = Path.cwd()
CARPETA_PROCESADOS = RAIZ / "datos_procesados"
CARPETA_SALIDAS = RAIZ / "salidas"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
ENTRADA_PANEL = CARPETA_PROCESADOS / f"datos_procesados_{CODIGO_MATRICULA}.csv"
ENTRADA_MACRO = CARPETA_PROCESADOS / f"macro_mensual_{CODIGO_MATRICULA}.csv"


def anotar(mensaje: str) -> None:
    """Muestra el mensaje en consola y lo añade al log con fecha y hora."""
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [04_analisis] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


def guardar_tabla(tabla: pd.DataFrame, nombre: str) -> None:
    """Guarda una tabla en /salidas con formato fijo (igual en cualquier sistema)."""
    ruta = CARPETA_SALIDAS / nombre
    tabla.to_csv(ruta, index=False, encoding="utf-8", lineterminator="\n")
    anotar(f"Tabla guardada: salidas/{nombre} · {len(tabla)} filas")


def configurar_graficos() -> None:
    """Estilo sobrio y uniforme para todas las figuras del artículo."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",   # viene con matplotlib: igual en todas las computadoras
        "font.size": 8,
        "axes.titlesize": 8.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 8,
        "axes.edgecolor": GRIS,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRIS_CLARO,
        "grid.linewidth": 0.5,
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "legend.frameon": False,
        "lines.linewidth": 1.3,
        "svg.fonttype": "path",         # el texto se guarda como trazos: se ve igual en Typst
        "svg.hashsalt": CODIGO_MATRICULA,  # SVG idéntico en cada ejecución
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
    })


def guardar_figura(figura: plt.Figure, nombre: str) -> None:
    """Guarda la figura en SVG dentro de /salidas, sin fecha interna (archivo reproducible)."""
    figura.savefig(CARPETA_SALIDAS / nombre, format="svg", metadata={"Date": None})
    plt.close(figura)
    anotar(f"Figura guardada: salidas/{nombre}")


def sombrear_pandemia(eje: plt.Axes) -> None:
    """Franja gris en el periodo de la pandemia."""
    eje.axvspan(pd.Timestamp(PANDEMIA[0]), pd.Timestamp(PANDEMIA[1]) + pd.offsets.MonthEnd(0),
                color=GRIS_CLARO, alpha=0.8, lw=0, zorder=0)


# ---------------------------------------------------------------------------
# 3. Bloque 1 · Fuentes y ciclo económico
# ---------------------------------------------------------------------------
def tabla_fuentes() -> pd.DataFrame:
    """Tabla 1 del artículo: qué se obtuvo de cada vía y para qué se usa."""
    filas = [
        ("Vía 1 · API REST", "BCRP (BCRPData)", "PN00505MM", "Crédito al sector privado (TC constante)", "Millones de S/", "Brecha del crédito"),
        ("Vía 1 · API REST", "BCRP (BCRPData)", "PN01773AM", "PBI desestacionalizado", "Índice 2007 = 100", "Brecha del producto"),
        ("Vía 1 · API REST", "BCRP (BCRPData)", "PD04722MM", "Tasa de referencia", "%", "Control de política monetaria"),
        ("Vía 1 · API REST", "BCRP (BCRPData)", "PN38705PM", "IPC de Lima Metropolitana", "Índice dic. 2021 = 100", "Deflactor"),
        ("Vía 2 · Descarga programática", "SBS", "B-2201", "Activo, pasivo, patrimonio y créditos por banco", "Millones de S/", "Apalancamiento y tamaño"),
        ("Vía 2 · Descarga programática", "SBS", "B-2401", "Morosidad por banco", "%", "Calidad de cartera"),
        ("Vía 2 · Descarga programática", "SBS", "B-2402", "Ratio de capital global por banco", "%", "Colchón de capital"),
    ]
    return pd.DataFrame(filas, columns=["Vía", "Fuente", "Código", "Variable", "Unidad", "Uso en el estudio"])


def filtro_hamilton(serie: pd.Series, h: int = HAMILTON_H, p: int = HAMILTON_P) -> pd.DataFrame:
    """
    Filtro de Hamilton (2018). Para cada mes t se estima por MCO

        y(t+h) = b0 + b1·y(t) + b2·y(t-1) + ... + bp·y(t-p+1) + v(t+h)

    La tendencia es el valor ajustado y la brecha (ciclo) es el residuo v(t+h):
    la parte de y que no se podía anticipar con la información de h meses antes.
    Con y = 100·ln(x), la brecha se lee como desviación porcentual.
    """
    y = serie.to_numpy(dtype=float)
    n = len(y)
    filas = range(h + p - 1, n)                       # meses con brecha calculable
    X = np.column_stack([np.ones(len(filas))] +
                        [y[[t - h - j for t in filas]] for j in range(p)])
    Y = y[list(filas)]
    coeficientes, *_ = np.linalg.lstsq(X, Y, rcond=None)
    tendencia = X @ coeficientes

    resultado = pd.DataFrame(index=serie.index, columns=["tendencia", "brecha"], dtype=float)
    resultado.iloc[list(filas), 0] = tendencia
    resultado.iloc[list(filas), 1] = Y - tendencia
    return resultado


def calcular_brechas(macro: pd.DataFrame) -> pd.DataFrame:
    """Brechas del crédito real y del PBI con el filtro de Hamilton."""
    macro = macro.set_index(pd.PeriodIndex(macro["fecha"], freq="M"))
    credito_real = macro["credito_privado"] / (macro["ipc_lima"] / 100)  # soles de dic. 2021
    log_credito = 100 * np.log(credito_real)
    log_pbi = 100 * np.log(macro["pbi_desestacionalizado"])

    hc = filtro_hamilton(log_credito)
    hy = filtro_hamilton(log_pbi)
    brechas = pd.DataFrame({
        "fecha": macro.index.astype(str),
        "log_credito_real": log_credito.to_numpy(),
        "tendencia_credito": hc["tendencia"].to_numpy(),
        "brecha_credito": hc["brecha"].to_numpy(),
        "log_pbi": log_pbi.to_numpy(),
        "tendencia_pbi": hy["tendencia"].to_numpy(),
        "brecha_pbi": hy["brecha"].to_numpy(),
        "tasa_referencia": macro["tasa_referencia"].to_numpy(),
    })
    brechas = brechas[(brechas["fecha"] >= FECHA_INICIO) & (brechas["fecha"] <= FECHA_CORTE)].reset_index(drop=True)
    if brechas[["brecha_credito", "brecha_pbi"]].isna().any().any():
        raise ValueError("Faltan meses previos para el filtro de Hamilton: revisar la pre-muestra del BCRP")
    return brechas


def figura_ciclos(brechas: pd.DataFrame) -> plt.Figure:
    """
    Figura 2: (a) brecha del crédito real y del PBI; (b) tasa de referencia.
    Las dos brechas comparten eje para comparar su amplitud y su sincronía.
    """
    fechas = pd.to_datetime(brechas["fecha"])
    figura, (eje_a, eje_b) = plt.subplots(2, 1, figsize=(ANCHO_DOS_COLUMNAS, 3.9), sharex=True,
                                          gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.28})
    for eje in (eje_a, eje_b):
        sombrear_pandemia(eje)

    eje_a.axhline(0, color=GRIS, lw=0.7)
    eje_a.plot(fechas, brechas["brecha_credito"], color=AZUL, label="Brecha del crédito real")
    eje_a.plot(fechas, brechas["brecha_pbi"], color=DORADO, label="Brecha del PBI")
    eje_a.set_ylabel("Desviación respecto\nde la tendencia (%)")
    eje_a.set_title("(a) Ciclo del crédito y del producto (filtro de Hamilton, h = 24, p = 12)")
    eje_a.legend(loc="lower left", ncol=2)
    eje_a.text(pd.Timestamp("2020-04"), eje_a.get_ylim()[1] * 0.92, "Pandemia", fontsize=7, color=GRIS, va="top")

    eje_b.step(fechas, brechas["tasa_referencia"], where="post", color=AZUL)
    eje_b.set_ylabel("%")
    eje_b.set_title("(b) Tasa de referencia del BCRP")
    eje_b.set_ylim(bottom=0)
    return figura


def bloque_1_ciclo() -> pd.DataFrame:
    anotar("Bloque 1 · Fuentes y ciclo económico")
    guardar_tabla(tabla_fuentes(), "tabla_fuentes.csv")

    macro = pd.read_csv(ENTRADA_MACRO)
    brechas = calcular_brechas(macro)
    guardar_tabla(brechas.round(6), "brechas_ciclo.csv")

    # Resumen en el log: cuánto se movió cada ciclo y cuándo tocó fondo
    for variable in ("brecha_credito", "brecha_pbi"):
        minimo = brechas.loc[brechas[variable].idxmin()]
        maximo = brechas.loc[brechas[variable].idxmax()]
        anotar(f"{variable}: mínimo {minimo[variable]:.2f} % ({minimo['fecha']}) · "
               f"máximo {maximo[variable]:.2f} % ({maximo['fecha']}) · desv. est. {brechas[variable].std():.2f}")
    correlacion = brechas["brecha_credito"].corr(brechas["brecha_pbi"])
    anotar(f"Correlación entre la brecha del crédito y la del PBI: {correlacion:.3f}")

    guardar_figura(figura_ciclos(brechas), "fig_ciclos.svg")
    return brechas


# ---------------------------------------------------------------------------
# 4. Bloque 2 · Análisis descriptivo del panel de bancos
# ---------------------------------------------------------------------------
# Variables de la Tabla 2: columna del panel -> (nombre en la tabla, unidad)
VARIABLES_DESCRIPTIVAS = {
    "apalancamiento_w": ("Apalancamiento (acotado P1-P99)", "veces"),
    "apalancamiento": ("Apalancamiento (original)", "veces"),
    "ratio_capital_global": ("Ratio de capital global", "%"),
    "morosidad": ("Morosidad", "%"),
    "activo_real_mm": ("Activo real", "miles de millones de S/ de 2021"),
    "brecha_credito": ("Brecha del crédito real", "%"),
    "brecha_pbi": ("Brecha del PBI", "%"),
    "tasa_referencia": ("Tasa de referencia", "%"),
}


def cargar_panel(brechas: pd.DataFrame) -> pd.DataFrame:
    """Panel de bancos con las brechas del ciclo añadidas por la fecha."""
    panel = pd.read_csv(ENTRADA_PANEL)
    panel = panel.merge(brechas[["fecha", "brecha_credito", "brecha_pbi"]], on="fecha",
                        how="left", validate="many_to_one")
    panel["activo_real_mm"] = panel["activo_real"] / 1000   # millones -> miles de millones
    panel["fecha_dt"] = pd.to_datetime(panel["fecha"])
    return panel


def tabla_descriptivos(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla 2. Además de las medidas habituales, separa la variabilidad en:
      D.E. entre bancos: diferencias entre los promedios de cada banco
      D.E. dentro:       variación de cada banco alrededor de su propio promedio
    Esta separación indica si la variable cambia sobre todo entre bancos o en el tiempo.
    """
    filas = []
    for columna, (nombre, unidad) in VARIABLES_DESCRIPTIVAS.items():
        x = panel[columna]
        promedio_banco = panel.groupby("entidad")[columna].transform("mean")
        filas.append({
            "Variable": nombre, "Unidad": unidad, "N": int(x.count()),
            "Media": x.mean(), "D.E.": x.std(),
            "D.E. entre bancos": panel.groupby("entidad")[columna].mean().std(),
            "D.E. dentro": (x - promedio_banco).std(),
            "Mín.": x.min(), "P25": x.quantile(0.25), "Mediana": x.median(),
            "P75": x.quantile(0.75), "Máx.": x.max(),
        })
    tabla = pd.DataFrame(filas)
    numericas = tabla.columns.drop(["Variable", "Unidad", "N"])
    tabla[numericas] = tabla[numericas].round(2)
    return tabla


def serie_sistema(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Por mes: mediana y cuartiles entre bancos del apalancamiento y del ratio de
    capital global, y el apalancamiento del sistema (suma de activos / suma de
    patrimonios), que pondera a cada banco por su tamaño.
    """
    por_mes = panel.groupby("fecha_dt")
    resumen = pd.DataFrame({
        "L_p25": por_mes["apalancamiento_w"].quantile(0.25),
        "L_mediana": por_mes["apalancamiento_w"].median(),
        "L_p75": por_mes["apalancamiento_w"].quantile(0.75),
        "L_sistema": por_mes["activo_total"].sum() / por_mes["patrimonio"].sum(),
        "RCG_p25": por_mes["ratio_capital_global"].quantile(0.25),
        "RCG_mediana": por_mes["ratio_capital_global"].median(),
        "RCG_p75": por_mes["ratio_capital_global"].quantile(0.75),
    })
    return resumen


def figura_apalancamiento(resumen: pd.DataFrame) -> plt.Figure:
    """Figura 3: (a) apalancamiento y (b) ratio de capital global, 2016-2025."""
    fechas = resumen.index
    figura, (eje_a, eje_b) = plt.subplots(2, 1, figsize=(ANCHO_DOS_COLUMNAS, 4.0), sharex=True,
                                          gridspec_kw={"hspace": 0.28})
    for eje in (eje_a, eje_b):
        sombrear_pandemia(eje)

    eje_a.fill_between(fechas, resumen["L_p25"], resumen["L_p75"], color=AZUL, alpha=0.15, lw=0,
                       label="Rango intercuartílico entre bancos")
    eje_a.plot(fechas, resumen["L_mediana"], color=AZUL, label="Mediana de los bancos")
    eje_a.plot(fechas, resumen["L_sistema"], color=DORADO, label="Sistema (activo total / patrimonio total)")
    eje_a.set_ylabel("Veces")
    eje_a.set_title("(a) Apalancamiento: activo total / patrimonio")
    eje_a.set_ylim(2.5, 13)
    eje_a.legend(loc="lower left", ncol=3)

    eje_b.fill_between(fechas, resumen["RCG_p25"], resumen["RCG_p75"], color=AZUL, alpha=0.15, lw=0)
    eje_b.plot(fechas, resumen["RCG_mediana"], color=AZUL)
    eje_b.set_ylabel("%")
    eje_b.set_title("(b) Ratio de capital global (mediana y rango intercuartílico)")
    return figura


def figura_mapa_calor(panel: pd.DataFrame) -> plt.Figure:
    """
    Figura 4: apalancamiento promedio de cada banco en cada año. Los bancos se
    ordenan de mayor a menor tamaño (activo promedio del periodo).
    """
    anual = panel.pivot_table(index="entidad", columns="anio", values="apalancamiento_w", aggfunc="mean")
    orden = panel.groupby("entidad")["activo_total"].mean().sort_values(ascending=False).index
    anual = anual.loc[orden]

    figura, eje = plt.subplots(figsize=(ANCHO_DOS_COLUMNAS, 4.2))
    imagen = eje.imshow(anual.to_numpy(), cmap="Blues", aspect="auto")
    eje.set_xticks(range(anual.shape[1]), anual.columns)
    eje.set_yticks(range(anual.shape[0]), anual.index)
    eje.tick_params(length=0)
    eje.grid(False)
    for lado in eje.spines.values():
        lado.set_visible(False)

    # Valor dentro de cada celda; texto blanco en las celdas oscuras
    umbral = np.nanmean(anual.to_numpy()) + 0.5 * np.nanstd(anual.to_numpy())
    for i in range(anual.shape[0]):
        for j in range(anual.shape[1]):
            valor = anual.iat[i, j]
            eje.text(j, i, f"{valor:.1f}".replace(".", ","), ha="center", va="center", fontsize=6.8,
                     color="white" if valor > umbral else "#1a1a1a")

    barra = figura.colorbar(imagen, ax=eje, fraction=0.025, pad=0.01)
    barra.set_label("Veces")
    barra.outline.set_visible(False)
    eje.set_title("Apalancamiento promedio anual por banco (ordenados por tamaño del activo)")
    return figura


def bloque_2_descriptivo(brechas: pd.DataFrame) -> pd.DataFrame:
    anotar("Bloque 2 · Análisis descriptivo del panel de bancos")
    panel = cargar_panel(brechas)
    guardar_tabla(tabla_descriptivos(panel), "tabla_descriptivos.csv")

    resumen = serie_sistema(panel)
    inicio, fin = resumen.iloc[0], resumen.iloc[-1]
    anotar(f"Apalancamiento del sistema: {inicio['L_sistema']:.2f} veces ({FECHA_INICIO}) -> "
           f"{fin['L_sistema']:.2f} veces ({FECHA_CORTE}) · máximo {resumen['L_sistema'].max():.2f} "
           f"({resumen['L_sistema'].idxmax():%Y-%m})")
    anotar(f"Ratio de capital global (mediana): {inicio['RCG_mediana']:.2f} % -> {fin['RCG_mediana']:.2f} %")

    # Concentración: participación de los 4 bancos más grandes en el activo del panel
    for anio in (int(FECHA_INICIO[:4]), int(FECHA_CORTE[:4])):
        diciembre = panel[(panel["anio"] == anio) & (panel["mes"] == 12)]
        cuota = diciembre["activo_total"].nlargest(4).sum() / diciembre["activo_total"].sum()
        anotar(f"Participación de los 4 bancos más grandes en el activo (dic. {anio}): {100 * cuota:.1f} %")
    correlacion = panel["apalancamiento_w"].corr(panel["ratio_capital_global"])
    anotar(f"Correlación entre apalancamiento acotado y ratio de capital global: {correlacion:.3f}")

    guardar_figura(figura_apalancamiento(resumen), "fig_apalancamiento.svg")
    guardar_figura(figura_mapa_calor(panel), "fig_mapa_calor.svg")
    return panel


# ---------------------------------------------------------------------------
# 5. Herramientas econométricas
# ---------------------------------------------------------------------------
def rezagos_driscoll_kraay(meses: int) -> int:
    """Ancho de banda habitual (Hoechle, 2007): parte entera de 4·(T/100)^(2/9)."""
    return int(np.floor(4 * (meses / 100) ** (2 / 9)))


def estimar_efectos_fijos(datos: pd.DataFrame, y: str, xs: list[str], efectos_tiempo: bool = False,
                          rezagos: int | None = None) -> dict:
    """
    Regresión con efectos fijos por banco (y opcionalmente por mes), estimada por
    MCO sobre los datos transformados (within), con errores estándar de
    Driscoll-Kraay. Devuelve coeficientes, errores, valores p y estadísticos.
    """
    d = datos.dropna(subset=[y] + xs).copy()
    columnas = [y] + xs
    # Transformación within: se resta el promedio de cada banco (y de cada mes)
    d[columnas] = d[columnas] - d.groupby("entidad")[columnas].transform("mean")
    if efectos_tiempo:
        d[columnas] = d[columnas] - d.groupby("fecha")[columnas].transform("mean")

    Y = d[y].to_numpy()
    X = d[xs].to_numpy()
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ Y
    residuos = Y - X @ beta

    # Driscoll-Kraay: se suman los productos x·e de todos los bancos en cada mes
    # (eso captura la correlación entre bancos) y se aplica Newey-West a esa serie.
    momentos = pd.DataFrame(X * residuos[:, None], index=d["fecha"].to_numpy()).groupby(level=0).sum()
    h = momentos.sort_index().to_numpy()
    T = h.shape[0]
    m = rezagos if rezagos is not None else rezagos_driscoll_kraay(T)
    S = h.T @ h
    for j in range(1, m + 1):
        peso = 1 - j / (m + 1)
        G = h[j:].T @ h[:-j]
        S += peso * (G + G.T)
    n_obs, k = X.shape
    bancos = d["entidad"].nunique()
    k_total = k + bancos + (T - 1 if efectos_tiempo else 0)   # parámetros, incluidos los efectos fijos
    ajuste = (n_obs - 1) / (n_obs - k_total) * T / (T - 1)
    V = ajuste * XtX_inv @ S @ XtX_inv
    errores = np.sqrt(np.diag(V))
    t = beta / errores
    p = 2 * stats.t.sf(np.abs(t), df=T - 1)                   # inferencia con T-1 grados de libertad

    r2_within = 1 - (residuos @ residuos) / ((Y - Y.mean()) @ (Y - Y.mean()))
    return {"coef": dict(zip(xs, beta)), "ee": dict(zip(xs, errores)), "p": dict(zip(xs, p)),
            "n": n_obs, "bancos": bancos, "meses": T, "r2_within": r2_within, "rezagos_dk": m,
            "efectos_tiempo": efectos_tiempo}


def estrellas(p: float) -> str:
    """*** p < 0,01; ** p < 0,05; * p < 0,10."""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def tabla_de_modelos(modelos: dict[str, dict], etiquetas: dict[str, str], filas_extra: dict[str, list[str]]) -> pd.DataFrame:
    """
    Tabla en el formato habitual de los artículos: un modelo por columna, el
    coeficiente con estrellas y debajo su error estándar entre paréntesis.
    """
    filas = []
    for variable, etiqueta in etiquetas.items():
        coeficientes, errores = [etiqueta], [""]
        for modelo in modelos.values():
            if variable in modelo["coef"]:
                coeficientes.append(f"{modelo['coef'][variable]:.3f}{estrellas(modelo['p'][variable])}")
                errores.append(f"({modelo['ee'][variable]:.3f})")
            else:
                coeficientes.append("")
                errores.append("")
        filas += [coeficientes, errores]
    filas.append(["Observaciones"] + [f"{m['n']:,}".replace(",", " ") for m in modelos.values()])
    filas.append(["Bancos"] + [str(m["bancos"]) for m in modelos.values()])
    filas.append(["Meses"] + [str(m["meses"]) for m in modelos.values()])
    filas.append(["R² within"] + [f"{m['r2_within']:.3f}" for m in modelos.values()])
    for nombre, valores in filas_extra.items():
        filas.append([nombre] + valores)
    return pd.DataFrame(filas, columns=["Variable"] + list(modelos))


# --- Raíz unitaria -----------------------------------------------------------
def regresion_adf(serie: np.ndarray, rezagos: int, tendencia: bool) -> tuple[float, float, int]:
    """
    Δy(t) = a [+ b·t] + ρ·y(t-1) + Σ γj·Δy(t-j) + e(t).
    Devuelve el estadístico t de ρ, el criterio de Akaike y las observaciones usadas.
    """
    dy = np.diff(serie)
    n = len(dy) - REZAGOS_MAX_ADF            # misma muestra para comparar rezagos
    Y = dy[REZAGOS_MAX_ADF:]
    columnas = [np.ones(n), serie[REZAGOS_MAX_ADF:-1]]
    if tendencia:
        columnas.append(np.arange(n, dtype=float))
    for j in range(1, rezagos + 1):
        columnas.append(dy[REZAGOS_MAX_ADF - j:-j])
    X = np.column_stack(columnas)
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ beta
    s2 = e @ e / (n - X.shape[1])
    ee_rho = np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
    aic = n * np.log(e @ e / n) + 2 * X.shape[1]
    return beta[1] / ee_rho, aic, n


def adf(serie: np.ndarray, tendencia: bool) -> tuple[float, int, int]:
    """ADF con el número de rezagos (0 a REZAGOS_MAX_ADF) que minimiza el criterio de Akaike."""
    resultados = [regresion_adf(serie, k, tendencia) for k in range(REZAGOS_MAX_ADF + 1)]
    mejor = int(np.argmin([r[1] for r in resultados]))
    return resultados[mejor][0], mejor, resultados[mejor][2]


_DISTRIBUCIONES_DF: dict[tuple[int, bool], np.ndarray] = {}


def valor_p_dickey_fuller(estadistico: float, n: int, tendencia: bool) -> float:
    """
    Valor p del estadístico de Dickey-Fuller. La distribución bajo la hipótesis
    nula (raíz unitaria) se obtiene simulando REPLICAS_DF caminatas aleatorias
    de largo n con la semilla del proyecto, y se guarda para no repetirla.
    """
    clave = (n, tendencia)
    if clave not in _DISTRIBUCIONES_DF:
        generador = np.random.default_rng(SEMILLA)
        e = generador.standard_normal((REPLICAS_DF, n + 1))
        y = np.cumsum(e, axis=1)
        dy, ylag = np.diff(y, axis=1), y[:, :-1]
        columnas = [np.ones(n), None] + ([np.arange(n, dtype=float)] if tendencia else [])
        valores_t = np.empty(REPLICAS_DF)
        for r in range(REPLICAS_DF):
            columnas[1] = ylag[r]
            X = np.column_stack(columnas)
            XtX_inv = np.linalg.inv(X.T @ X)
            beta = XtX_inv @ X.T @ dy[r]
            residuo = dy[r] - X @ beta
            s2 = residuo @ residuo / (n - X.shape[1])
            valores_t[r] = beta[1] / np.sqrt(s2 * XtX_inv[1, 1])
        _DISTRIBUCIONES_DF[clave] = np.sort(valores_t)
    distribucion = _DISTRIBUCIONES_DF[clave]
    # Proporción de réplicas con un estadístico igual o menor (prueba de cola izquierda)
    p = (np.searchsorted(distribucion, estadistico, side="right") + 1) / (REPLICAS_DF + 1)
    return float(min(p, 1.0))


def raiz_unitaria_panel(panel: pd.DataFrame, columna: str, tendencia: bool) -> dict:
    """
    ADF por banco sobre la serie sin el promedio de todos los bancos en cada mes
    (así se atenúan los choques comunes) y combinación de los valores p:
      Maddala-Wu: P = -2·Σ ln(p_i) ~ chi-cuadrado con 2N grados de libertad
      Choi:       Z = Σ Φ⁻¹(p_i) / √N ~ normal estándar
    Hipótesis nula: todos los bancos tienen raíz unitaria.
    """
    datos = panel.dropna(subset=[columna]).copy()
    datos[columna] = datos[columna] - datos.groupby("fecha")[columna].transform("mean")
    valores_p, rezagos = [], []
    for _, grupo in datos.sort_values("fecha").groupby("entidad"):
        estadistico, k, n = adf(grupo[columna].to_numpy(), tendencia)
        valores_p.append(valor_p_dickey_fuller(estadistico, n, tendencia))
        rezagos.append(k)
    valores_p = np.clip(valores_p, 1e-12, 1 - 1e-12)
    N = len(valores_p)
    p_mw = stats.chi2.sf(-2 * np.log(valores_p).sum(), 2 * N)
    z_choi = stats.norm.ppf(valores_p).sum() / np.sqrt(N)
    p_choi = stats.norm.cdf(z_choi)
    return {"rezagos": int(np.median(rezagos)), "estadistico": z_choi, "p": p_choi,
            "estadistico_2": -2 * np.log(valores_p).sum(), "p_2": p_mw}


# ---------------------------------------------------------------------------
# 6. Bloque 3 · Estacionariedad y prueba de prociclicidad (H1)
# ---------------------------------------------------------------------------
def preparar_variables_modelo(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Variables en logaritmos (×100, para leer las diferencias como %), sus
    variaciones mensuales y a 12 meses, y los controles rezagados un mes.
    """
    panel = panel.sort_values(["entidad", "fecha"]).reset_index(drop=True)
    panel["ln_L"] = 100 * np.log(panel["apalancamiento_w"])
    panel["ln_L_original"] = 100 * np.log(panel["apalancamiento"])
    panel["ln_A"] = 100 * np.log(panel["activo_total"])
    panel["ln_A_real"] = 100 * np.log(panel["activo_real"])
    for base in ("ln_L", "ln_L_original", "ln_A"):
        panel[f"d_{base}"] = panel.groupby("entidad")[base].diff()
        panel[f"d12_{base}"] = panel.groupby("entidad")[base].diff(12)
    for control in ("ratio_capital_global", "morosidad", "ln_A_real"):
        panel[f"{control}_l1"] = panel.groupby("entidad")[control].shift(1)
        panel[f"{control}_l12"] = panel.groupby("entidad")[control].shift(12)
    return panel


def tabla_raiz_unitaria(panel: pd.DataFrame, brechas: pd.DataFrame) -> pd.DataFrame:
    """Tabla 3: Panel A (bancos, Choi y Maddala-Wu) y Panel B (series macro, ADF)."""
    filas = []
    variables_panel = [
        ("ln_L", "ln apalancamiento", True),
        ("d_ln_L", "Δ ln apalancamiento", False),
        ("ln_A_real", "ln activo real", True),
        ("d_ln_A", "Δ ln activo", False),
        ("ratio_capital_global", "Ratio de capital global", False),
        ("morosidad", "Morosidad", False),
    ]
    for columna, nombre, tendencia in variables_panel:
        r = raiz_unitaria_panel(panel, columna, tendencia)
        filas.append({
            "Panel": "A. Bancos (15)", "Variable": nombre,
            "Determinísticos": "constante y tendencia" if tendencia else "constante",
            "Rezagos (mediana)": r["rezagos"],
            "Estadístico": f"Z = {r['estadistico']:.2f}", "Valor p": round(r["p"], 3),
            "Estadístico 2": f"P = {r['estadistico_2']:.1f}", "Valor p 2": round(r["p_2"], 3),
            "Conclusión": "Estacionaria" if max(r["p"], r["p_2"]) < NIVEL_SIGNIFICANCIA
            else "Mixta" if min(r["p"], r["p_2"]) < NIVEL_SIGNIFICANCIA else "Raíz unitaria",
        })
    for columna, nombre in [("brecha_credito", "Brecha del crédito"), ("brecha_pbi", "Brecha del PBI"),
                            ("tasa_referencia", "Tasa de referencia")]:
        estadistico, k, n = adf(brechas[columna].to_numpy(), tendencia=False)
        p = valor_p_dickey_fuller(estadistico, n, tendencia=False)
        filas.append({
            "Panel": "B. Series macro", "Variable": nombre, "Determinísticos": "constante",
            "Rezagos (mediana)": k, "Estadístico": f"τ = {estadistico:.2f}", "Valor p": round(p, 3),
            "Estadístico 2": "", "Valor p 2": "",
            "Conclusión": "Estacionaria" if p < NIVEL_SIGNIFICANCIA else "Raíz unitaria",
        })
    return pd.DataFrame(filas)


def modelos_adrian_shin(panel: pd.DataFrame) -> dict[str, dict]:
    """
    Prueba de prociclicidad de Adrian y Shin (2010):
        Δ ln L(it) = α(i) + β · Δ ln A(it) + δ'X(i,t-1) + ε(it)
    β > 0: el apalancamiento sube cuando los activos crecen (procíclico).
    β = 0: el banco mantiene un apalancamiento objetivo.
    """
    controles = ["ratio_capital_global_l1", "morosidad_l1", "ln_A_real_l1"]
    macro = ["brecha_credito", "brecha_pbi", "tasa_referencia"]
    controles_12 = ["ratio_capital_global_l12", "morosidad_l12", "ln_A_real_l12"]
    return {
        "(1)": estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A"]),
        "(2)": estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A"] + controles),
        "(3)": estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A"] + controles + macro),
        "(4)": estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A"] + controles, efectos_tiempo=True),
        "(5)": estimar_efectos_fijos(panel, "d12_ln_L", ["d12_ln_A"] + controles_12, rezagos=12),
    }


def tabla_adrian_shin(modelos: dict[str, dict]) -> pd.DataFrame:
    """Tabla 4. En el modelo (5) las variaciones son a 12 meses: se muestran en la fila de Δ ln A."""
    # Para presentar los dos horizontes en una sola fila, se renombran las variables del modelo (5)
    m5 = modelos["(5)"]
    for clave_12, clave in [("d12_ln_A", "d_ln_A"), ("ratio_capital_global_l12", "ratio_capital_global_l1"),
                            ("morosidad_l12", "morosidad_l1"), ("ln_A_real_l12", "ln_A_real_l1")]:
        for campo in ("coef", "ee", "p"):
            m5[campo][clave] = m5[campo].pop(clave_12)
    etiquetas = {
        "d_ln_A": "Δ ln activo (β)",
        "ratio_capital_global_l1": "Ratio de capital global (t-1)",
        "morosidad_l1": "Morosidad (t-1)",
        "ln_A_real_l1": "ln activo real (t-1)",
        "brecha_credito": "Brecha del crédito",
        "brecha_pbi": "Brecha del PBI",
        "tasa_referencia": "Tasa de referencia",
    }
    extra = {
        "Horizonte de la variación": ["1 mes", "1 mes", "1 mes", "1 mes", "12 meses"],
        "Efectos fijos de banco": ["Sí"] * 5,
        "Efectos fijos de mes": ["No", "No", "No", "Sí", "No"],
        "Rezagos Driscoll-Kraay": [str(m["rezagos_dk"]) for m in modelos.values()],
    }
    return tabla_de_modelos(modelos, etiquetas, extra)


def figura_adrian_shin(panel: pd.DataFrame, beta_12: float) -> plt.Figure:
    """
    Figura 5: crecimiento a 12 meses del activo (eje x) y del apalancamiento (eje y).
    Se resta el promedio de cada banco para ver la relación dentro de cada banco,
    que es la que estima el modelo con efectos fijos.
    """
    d = panel.dropna(subset=["d12_ln_A", "d12_ln_L"]).copy()
    for c in ("d12_ln_A", "d12_ln_L"):
        d[c] = d[c] - d.groupby("entidad")[c].transform("mean")
    en_pandemia = d["fecha"].between(PANDEMIA[0], PANDEMIA[1])

    figura, eje = plt.subplots(figsize=(ANCHO_UNA_COLUMNA, 3.0))
    eje.scatter(d.loc[~en_pandemia, "d12_ln_A"], d.loc[~en_pandemia, "d12_ln_L"], s=4, color=AZUL,
                alpha=0.35, lw=0, label="Otros meses")
    eje.scatter(d.loc[en_pandemia, "d12_ln_A"], d.loc[en_pandemia, "d12_ln_L"], s=4, color=DORADO,
                alpha=0.7, lw=0, label="Pandemia (2020-03 a 2021-12)")
    limite = np.nanpercentile(np.abs(d[["d12_ln_A", "d12_ln_L"]].to_numpy()), 99.5)
    x = np.array([-limite, limite])
    eje.plot(x, beta_12 * x, color="#b03a2e", lw=1.4, label=f"Pendiente estimada β = {beta_12:.2f}".replace(".", ","))
    eje.plot(x, x, color=GRIS, lw=0.8, ls="--", label="β = 1 (patrimonio constante)")
    eje.axhline(0, color=GRIS, lw=0.8, ls=":", label="β = 0 (apalancamiento objetivo)")
    eje.set_xlim(-limite, limite)
    eje.set_ylim(-limite, limite)
    eje.set_xlabel("Δ ln activo a 12 meses (%, desviación del promedio del banco)")
    eje.set_ylabel("Δ ln apalancamiento a 12 meses (%)")
    eje.legend(loc="lower right", fontsize=6.3, markerscale=2.5, handlelength=1.6)
    return figura


def bloque_3_prociclicidad(panel: pd.DataFrame, brechas: pd.DataFrame) -> pd.DataFrame:
    anotar("Bloque 3 · Estacionariedad y prueba de prociclicidad (H1)")
    panel = preparar_variables_modelo(panel)

    raiz = tabla_raiz_unitaria(panel, brechas)
    guardar_tabla(raiz, "tabla_raiz_unitaria.csv")
    for _, fila in raiz.iterrows():
        anotar(f"Raíz unitaria · {fila['Variable']}: {fila['Estadístico']} (p = {fila['Valor p']}) -> {fila['Conclusión']}")

    modelos = modelos_adrian_shin(panel)
    for nombre, m in modelos.items():
        clave = "d_ln_A" if "d_ln_A" in m["coef"] else "d12_ln_A"
        anotar(f"Adrian-Shin {nombre}: β = {m['coef'][clave]:.3f} (e.e. DK {m['ee'][clave]:.3f}, "
               f"p = {m['p'][clave]:.4f}) · N = {m['n']} · R² within = {m['r2_within']:.3f}")
    beta_12 = modelos["(5)"]["coef"]["d12_ln_A"]
    guardar_tabla(tabla_adrian_shin(modelos), "tabla_adrian_shin.csv")
    guardar_figura(figura_adrian_shin(panel, beta_12), "fig_adrian_shin.svg")
    return panel


# ---------------------------------------------------------------------------
# 7. Bloque 4 · Modelo dinámico del apalancamiento frente al ciclo (H2)
# ---------------------------------------------------------------------------
# Regresores del modelo dinámico (además del apalancamiento rezagado)
VARIABLES_CICLO = ["brecha_credito", "brecha_pbi", "tasa_referencia"]
CONTROLES_BANCO = ["ratio_capital_global_l1", "morosidad_l1", "ln_A_real_l1"]

ETIQUETAS_DINAMICO = {
    "ln_L_l1": "ln apalancamiento (t-1) (ρ)",
    "brecha_credito": "Brecha del crédito (γ1)",
    "brecha_pbi": "Brecha del PBI (γ2)",
    "tasa_referencia": "Tasa de referencia (θ)",
    "pandemia": "Pandemia (2020-03 a 2021-12)",
    "ratio_capital_global_l1": "Ratio de capital global (rezagado)",
    "morosidad_l1": "Morosidad (rezagada)",
    "ln_A_real_l1": "ln activo real (rezagado)",
}


def system_gmm(datos: pd.DataFrame, y: str, x_comunes: list[str], x_banco: list[str],
               rezagos_instrumento: tuple[int, int] = (2, 3)) -> dict:
    """
    System GMM para  y(it) = ρ·y(i,t-1) + x(it)'β + μ(i) + ε(it).

    Se apilan dos ecuaciones por banco:
      - en diferencias:  Δy(it) = ρ·Δy(i,t-1) + Δx(it)'β + Δε(it)
        instrumentos: y(i,t-2), y(i,t-3) (colapsados) y Δx_banco(it)
      - en niveles:      y(it) = c + ρ·y(i,t-1) + x(it)'β + μ(i) + ε(it)
        instrumentos: Δy(i,t-1), Δx_banco(it), x_comunes(t) y la constante
    x_comunes son las variables macro, iguales para todos los bancos y, por tanto,
    no correlacionadas con el efecto fijo μ(i): sirven como instrumento en niveles.
    x_banco (capital, morosidad, tamaño) sí pueden correlacionarse con μ(i): en
    niveles se instrumentan con sus diferencias (Blundell y Bond, 1998).
    Con solo 15 bancos, el número de instrumentos debe ser menor que 15
    (regla de Roodman, 2009); por eso se colapsan y se limitan los rezagos.
    Estimación en una etapa con matriz de pesos (Σ Z'Z)⁻¹ y errores robustos por banco.
    """
    desde, hasta = rezagos_instrumento
    n_rez = hasta - desde + 1
    xs = x_comunes + x_banco
    kb, kc = len(x_banco), len(x_comunes)
    bloques = []
    for _, g in datos.sort_values("fecha").groupby("entidad"):
        yy = g[y].to_numpy()
        X = g[xs].to_numpy()
        XB = g[x_banco].to_numpy()
        T = len(yy)
        filas_y, filas_x, filas_z = [], [], []
        # Ecuación en diferencias: t desde 2 (se necesita y(t-2) como instrumento)
        for t in range(2, T):
            if np.isnan(X[t]).any() or np.isnan(X[t - 1]).any():
                continue
            rezagos_y = [yy[t - j] if t - j >= 0 else 0.0 for j in range(desde, hasta + 1)]
            filas_y.append(yy[t] - yy[t - 1])
            filas_x.append([yy[t - 1] - yy[t - 2], *(X[t] - X[t - 1]), 0.0])
            filas_z.append(rezagos_y + list(XB[t] - XB[t - 1]) + [0.0] * (1 + kb + kc + 1))
        n_dif = len(filas_y)
        # Ecuación en niveles: t desde 2 (se necesita Δy(t-1))
        for t in range(2, T):
            if np.isnan(X[t]).any() or np.isnan(X[t - 1]).any():
                continue
            filas_y.append(yy[t])
            filas_x.append([yy[t - 1], *X[t], 1.0])
            filas_z.append([0.0] * (n_rez + kb) + [yy[t - 1] - yy[t - 2]] + list(XB[t] - XB[t - 1])
                           + list(X[t, :kc]) + [1.0])
        bloques.append((np.array(filas_y), np.array(filas_x), np.array(filas_z), n_dif))

    ZX = sum(Z.T @ X for _, X, Z, _ in bloques)
    ZY = sum(Z.T @ Y for Y, _, Z, _ in bloques)
    W = np.linalg.pinv(sum(Z.T @ Z for _, _, Z, _ in bloques))
    A = np.linalg.inv(ZX.T @ W @ ZX)
    beta = A @ ZX.T @ W @ ZY

    # Errores robustos por banco (sandwich) y prueba de Hansen
    momentos = [Z.T @ (Y - X @ beta) for Y, X, Z, _ in bloques]
    S = sum(np.outer(g, g) for g in momentos)
    V = A @ ZX.T @ W @ S @ W @ ZX @ A
    g_total = sum(momentos)
    hansen = float(g_total @ np.linalg.pinv(S) @ g_total)
    n_instrumentos = ZX.shape[0]
    gl = n_instrumentos - ZX.shape[1]
    p_hansen = float(stats.chi2.sf(hansen, gl)) if gl > 0 else float("nan")

    # Pruebas AR(1) y AR(2) sobre los residuos de la ecuación en diferencias
    def prueba_ar(orden: int) -> float:
        sumas = []
        for Y, X, _, n_dif in bloques:
            e = (Y - X @ beta)[:n_dif]
            sumas.append(e[orden:] @ e[:-orden])
        sumas = np.array(sumas)
        z = sumas.sum() / np.sqrt((sumas ** 2).sum())
        return float(2 * stats.norm.sf(abs(z)))

    nombres = ["y_l1"] + xs + ["constante"]
    errores = np.sqrt(np.diag(V))
    p = 2 * stats.norm.sf(np.abs(beta / errores))
    return {"coef": dict(zip(nombres, beta)), "ee": dict(zip(nombres, errores)), "p": dict(zip(nombres, p)),
            "V": pd.DataFrame(V, index=nombres, columns=nombres),
            "n": sum(len(Y) - n for Y, _, _, n in bloques), "bancos": len(bloques),
            "meses": datos["fecha"].nunique() - 2, "r2_within": float("nan"),
            "instrumentos": n_instrumentos, "hansen": hansen, "p_hansen": p_hansen,
            "p_ar1": prueba_ar(1), "p_ar2": prueba_ar(2)}


def efecto_largo_plazo(modelo: dict, variable: str, rho: str) -> tuple[float, float, float]:
    """
    Efecto de largo plazo: β / (1 - ρ). Su error estándar se obtiene por el
    método delta con la matriz de varianzas del modelo.
    """
    b, r = modelo["coef"][variable], modelo["coef"][rho]
    efecto = b / (1 - r)
    gradiente = np.array([1 / (1 - r), b / (1 - r) ** 2])
    V = modelo["V"].loc[[variable, rho], [variable, rho]].to_numpy()
    ee = float(np.sqrt(gradiente @ V @ gradiente))
    p = float(2 * stats.norm.sf(abs(efecto / ee)))
    return efecto, ee, p


def estimar_efectos_fijos_con_v(datos: pd.DataFrame, y: str, xs: list[str]) -> dict:
    """Igual que estimar_efectos_fijos, pero conserva la matriz de varianzas (para el método delta)."""
    modelo = estimar_efectos_fijos(datos, y, xs)
    # Se recalcula V a partir de los errores y de la estructura completa
    d = datos.dropna(subset=[y] + xs).copy()
    cols = [y] + xs
    d[cols] = d[cols] - d.groupby("entidad")[cols].transform("mean")
    X = d[xs].to_numpy()
    e = d[y].to_numpy() - X @ np.array([modelo["coef"][x] for x in xs])
    XtX_inv = np.linalg.inv(X.T @ X)
    h = pd.DataFrame(X * e[:, None], index=d["fecha"].to_numpy()).groupby(level=0).sum().sort_index().to_numpy()
    T, m = h.shape[0], modelo["rezagos_dk"]
    S = h.T @ h
    for j in range(1, m + 1):
        G = h[j:].T @ h[:-j]
        S += (1 - j / (m + 1)) * (G + G.T)
    n, k = X.shape
    ajuste = (n - 1) / (n - k - modelo["bancos"]) * T / (T - 1)
    modelo["V"] = pd.DataFrame(ajuste * XtX_inv @ S @ XtX_inv, index=xs, columns=xs)
    return modelo


def renombrar_rezagos_12(modelo: dict) -> dict:
    """
    En los modelos a 12 meses los controles van rezagados 12 meses. Para que
    compartan fila con los controles rezagados 1 mes en la tabla, se renombran.
    """
    for campo in ("coef", "ee", "p"):
        modelo[campo] = {clave.replace("_l12", "_l1"): valor for clave, valor in modelo[campo].items()}
    return modelo


def preparar_modelo_dinamico(panel: pd.DataFrame) -> pd.DataFrame:
    """Añade el apalancamiento rezagado y la variable de la pandemia."""
    panel = panel.copy()
    panel["ln_L_l1"] = panel.groupby("entidad")["ln_L"].shift(1)
    panel["ln_L_original_l1"] = panel.groupby("entidad")["ln_L_original"].shift(1)
    panel["pandemia"] = panel["fecha"].between(PANDEMIA[0], PANDEMIA[1]).astype(float)
    return panel


def bloque_4_modelo_dinamico(panel: pd.DataFrame) -> pd.DataFrame:
    anotar("Bloque 4 · Modelo dinámico del apalancamiento frente al ciclo (H2)")
    panel = preparar_modelo_dinamico(panel)

    # (1)-(2): modelo dinámico en niveles, como en el plan del estudio.
    # (3)-(4): crecimiento del apalancamiento a 12 meses. Es coherente con la
    # Tabla 3 (el nivel del apalancamiento está cerca de una raíz unitaria) y con
    # la frecuencia de las brechas, que se mueven lentamente.
    base = ["ln_L_l1"] + VARIABLES_CICLO + CONTROLES_BANCO
    base_12 = VARIABLES_CICLO + [c.replace("_l1", "_l12") for c in CONTROLES_BANCO]
    modelos = {
        "(1)": estimar_efectos_fijos_con_v(panel, "ln_L", base),
        "(2)": estimar_efectos_fijos_con_v(panel, "ln_L", base + ["pandemia"]),
        "(3)": renombrar_rezagos_12(estimar_efectos_fijos(panel, "d12_ln_L", base_12, rezagos=12)),
        "(4)": renombrar_rezagos_12(estimar_efectos_fijos(panel, "d12_ln_L", base_12 + ["pandemia"], rezagos=12)),
    }
    for nombre, m in modelos.items():
        rho = f"ρ = {m['coef']['ln_L_l1']:.3f} · " if "ln_L_l1" in m["coef"] else ""
        anotar(f"Modelo {nombre}: {rho}γ1 (crédito) = {m['coef']['brecha_credito']:.4f} "
               f"(p = {m['p']['brecha_credito']:.3f}) · γ2 (PBI) = {m['coef']['brecha_pbi']:.4f} "
               f"(p = {m['p']['brecha_pbi']:.3f}) · N = {m['n']}")
    sesgo = (1 + modelos["(2)"]["coef"]["ln_L_l1"]) / (modelos["(2)"]["meses"] - 1)
    anotar(f"Orden de magnitud del sesgo de Nickell en (1)-(2), (1 + ρ)/(T − 1): {sesgo:.3f}")

    # Efectos de largo plazo de las brechas en el modelo dinámico: γ / (1 - ρ)
    filas_largo = {}
    for variable, etiqueta in [("brecha_credito", "Largo plazo: brecha del crédito"),
                               ("brecha_pbi", "Largo plazo: brecha del PBI")]:
        coeficientes, errores = [], []
        for nombre, m in modelos.items():
            if "ln_L_l1" not in m["coef"]:
                coeficientes.append("")
                errores.append("")
                continue
            efecto, ee, p = efecto_largo_plazo(m, variable, "ln_L_l1")
            coeficientes.append(f"{efecto:.3f}{estrellas(p)}")
            errores.append(f"({ee:.3f})")
            anotar(f"Modelo {nombre} · {etiqueta}: {efecto:.3f} (e.e. {ee:.3f}, p = {p:.3f})")
        filas_largo[etiqueta] = coeficientes
        filas_largo[f" {etiqueta} (e.e.)"] = errores

    extra = {
        **filas_largo,
        "Variable dependiente": ["ln L", "ln L", "Δ12 ln L", "Δ12 ln L"],
        "Rezago de los controles": ["1 mes", "1 mes", "12 meses", "12 meses"],
        "Efectos fijos de banco": ["Sí"] * 4,
        "Rezagos Driscoll-Kraay": [str(m["rezagos_dk"]) for m in modelos.values()],
    }
    tabla = tabla_de_modelos(modelos, ETIQUETAS_DINAMICO, extra)
    # Las filas de error estándar del largo plazo se muestran sin nombre (como las demás)
    tabla["Variable"] = tabla["Variable"].where(~tabla["Variable"].str.endswith("(e.e.)"), "")
    guardar_tabla(tabla, "tabla_modelo_dinamico.csv")
    return panel


# ---------------------------------------------------------------------------
# 8. Bloque 5 · Heterogeneidad (H3) y robustez
# ---------------------------------------------------------------------------
PERIODOS = {
    "Prepandemia\n2016 a feb. 2020": ("2016-01", "2020-02"),
    "Pandemia\nmar. 2020 a 2021": PANDEMIA,
    "Pospandemia\n2022 a 2025": ("2022-01", "2025-12"),
}
LAMBDA_HP = 129600            # parámetro del filtro HP para datos mensuales (Ravn y Uhlig, 2002)


def betas_por_grupo(panel: pd.DataFrame, grupo: str, controles: list[str]) -> tuple[dict, pd.DataFrame, dict]:
    """
    Un solo modelo con una pendiente β distinta para cada grupo:
        Δ ln L = α(i) + Σ_g β_g · Δ ln A · 1[grupo = g] + δ'X + ε
    Devuelve el modelo, las pendientes con su intervalo de confianza al 95 %
    y la prueba de igualdad entre la primera y la última pendiente.
    """
    d = panel.copy()
    niveles = list(dict.fromkeys(d[grupo].dropna()))
    columnas = []
    for i, nivel in enumerate(niveles):
        columna = f"beta_g{i}"
        d[columna] = d["d_ln_A"] * (d[grupo] == nivel)
        columnas.append(columna)
    modelo = estimar_efectos_fijos_con_v(d, "d_ln_L", columnas + controles)
    critico = stats.t.ppf(0.975, df=modelo["meses"] - 1)
    filas = []
    for nivel, columna in zip(niveles, columnas):
        b, ee = modelo["coef"][columna], modelo["ee"][columna]
        filas.append({"grupo": nivel, "beta": b, "ee": ee, "inferior": b - critico * ee,
                      "superior": b + critico * ee, "p": modelo["p"][columna]})
    # Prueba de Wald de igualdad entre el primer y el último grupo
    c1, c2 = columnas[0], columnas[-1]
    V = modelo["V"]
    diferencia = modelo["coef"][c2] - modelo["coef"][c1]
    ee_dif = np.sqrt(V.loc[c1, c1] + V.loc[c2, c2] - 2 * V.loc[c1, c2])
    p_dif = float(2 * stats.t.sf(abs(diferencia / ee_dif), df=modelo["meses"] - 1))
    return modelo, pd.DataFrame(filas), {"diferencia": diferencia, "ee": ee_dif, "p": p_dif}


def figura_heterogeneidad(por_periodo: pd.DataFrame, por_colchon: pd.DataFrame, beta_total: float) -> plt.Figure:
    """Figura 6: β con su intervalo de confianza al 95 %, (a) por periodo y (b) por colchón de capital."""
    figura, (eje_a, eje_b) = plt.subplots(1, 2, figsize=(ANCHO_DOS_COLUMNAS, 2.7), sharey=True,
                                          gridspec_kw={"width_ratios": [3, 2], "wspace": 0.08})
    for eje, tabla, titulo, colores in [
        (eje_a, por_periodo, "(a) Por periodo", [AZUL, DORADO, AZUL]),
        (eje_b, por_colchon, "(b) Por colchón de capital", [AZUL, DORADO]),
    ]:
        x = np.arange(len(tabla))
        for i, fila in tabla.reset_index(drop=True).iterrows():
            eje.errorbar(x[i], fila["beta"], yerr=[[fila["beta"] - fila["inferior"]], [fila["superior"] - fila["beta"]]],
                         fmt="o", color=colores[i], ecolor=colores[i], elinewidth=1.3, capsize=4, markersize=5)
            eje.annotate(f"{fila['beta']:.2f}".replace(".", ","), (x[i], fila["superior"]),
                         textcoords="offset points", xytext=(0, 4), ha="center", fontsize=7.5, color=colores[i])
        eje.axhline(beta_total, color=GRIS, lw=0.8, ls="--")
        eje.set_xticks(x, tabla["grupo"])
        eje.set_xlim(-0.6, len(tabla) - 0.4)
        eje.set_title(titulo)
        eje.grid(axis="x", visible=False)
    eje_a.set_ylabel("β: respuesta del apalancamiento\nal crecimiento del activo")
    eje_a.text(-0.55, beta_total, f"β de todo el panel = {beta_total:.2f}".replace(".", ","),
               fontsize=7, color=GRIS, ha="left", va="bottom")
    return figura


def filtro_hp(y: np.ndarray, lam: float = LAMBDA_HP) -> np.ndarray:
    """Filtro de Hodrick-Prescott (dos colas): devuelve la brecha y - tendencia."""
    n = len(y)
    D = np.zeros((n - 2, n))
    for i in range(n - 2):
        D[i, i:i + 3] = [1.0, -2.0, 1.0]
    tendencia = np.linalg.solve(np.eye(n) + lam * D.T @ D, y)
    return y - tendencia


def brechas_hp() -> pd.DataFrame:
    """Brechas del crédito real y del PBI con el filtro HP (robustez frente a Hamilton)."""
    macro = pd.read_csv(ENTRADA_MACRO)
    credito_real = macro["credito_privado"] / (macro["ipc_lima"] / 100)
    return pd.DataFrame({
        "fecha": macro["fecha"],
        "brecha_credito": filtro_hp(100 * np.log(credito_real.to_numpy())),
        "brecha_pbi": filtro_hp(100 * np.log(macro["pbi_desestacionalizado"].to_numpy())),
    })


def fila_robustez(nombre: str, datos: pd.DataFrame, y_as: str = "d_ln_L", y_12: str = "d12_ln_L",
                  con_beta: bool = True, con_gammas: bool = True) -> dict:
    """
    Reestima con 'datos' el modelo (2) de la Tabla 4 (β de Adrian y Shin) y el
    modelo (4) de la Tabla 5 (brechas, crecimiento a 12 meses con pandemia).
    """
    controles = ["ratio_capital_global_l1", "morosidad_l1", "ln_A_real_l1"]
    controles_12 = [c.replace("_l1", "_l12") for c in controles]
    fila = {"Especificación": nombre}
    if con_beta:
        m = estimar_efectos_fijos(datos, y_as, ["d_ln_A"] + controles)
        fila["β (Adrian-Shin)"] = f"{m['coef']['d_ln_A']:.3f}{estrellas(m['p']['d_ln_A'])}"
        fila["e.e. β"] = f"({m['ee']['d_ln_A']:.3f})"
        fila["N (β)"] = f"{m['n']:,}".replace(",", " ")
    else:
        fila.update({"β (Adrian-Shin)": "", "e.e. β": "", "N (β)": ""})
    if con_gammas:
        extra = ["pandemia"] if datos["pandemia"].nunique() > 1 else []
        g = estimar_efectos_fijos(datos, y_12, VARIABLES_CICLO + controles_12 + extra, rezagos=12)
        for clave, nombre_col in [("brecha_credito", "γ1 (brecha del crédito)"), ("brecha_pbi", "γ2 (brecha del PBI)")]:
            fila[nombre_col] = f"{g['coef'][clave]:.3f}{estrellas(g['p'][clave])}"
            fila[f"e.e. {nombre_col[:2]}"] = f"({g['ee'][clave]:.3f})"
        fila["N (γ)"] = f"{g['n']:,}".replace(",", " ")
    else:
        fila.update({"γ1 (brecha del crédito)": "", "e.e. γ1": "", "γ2 (brecha del PBI)": "", "e.e. γ2": "", "N (γ)": ""})
    return fila


def tabla_robustez(panel: pd.DataFrame) -> pd.DataFrame:
    """Tabla 6, panel A: los resultados principales bajo especificaciones alternativas."""
    filas = [fila_robustez("Base: apalancamiento acotado (P1-P99), brechas de Hamilton", panel)]

    original = panel.copy()
    filas.append(fila_robustez("Apalancamiento original (sin acotar)", original,
                               y_as="d_ln_L_original", y_12="d12_ln_L_original"))

    filas.append(fila_robustez("Sin Alfin Banco", panel[panel["entidad"] != "Alfin Banco"]))

    hp = brechas_hp()
    con_hp = panel.drop(columns=["brecha_credito", "brecha_pbi"]).merge(hp, on="fecha", how="left")
    filas.append(fila_robustez("Brechas con el filtro HP (λ = 129 600)", con_hp, con_beta=False))

    sin_pandemia = panel[panel["pandemia"] == 0]
    filas.append(fila_robustez("Sin los meses de pandemia (2020-03 a 2021-12)", sin_pandemia))

    grandes = panel.groupby("entidad")["activo_total"].mean().nlargest(4).index
    filas.append(fila_robustez("Sin los 4 bancos más grandes", panel[~panel["entidad"].isin(grandes)]))

    m = estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A", "ratio_capital_global_l1", "morosidad_l1", "ln_A_real_l1"],
                              efectos_tiempo=True)
    filas.append({"Especificación": "Con efectos fijos de mes (absorben las brechas)",
                  "β (Adrian-Shin)": f"{m['coef']['d_ln_A']:.3f}{estrellas(m['p']['d_ln_A'])}",
                  "e.e. β": f"({m['ee']['d_ln_A']:.3f})", "N (β)": f"{m['n']:,}".replace(",", " "),
                  "γ1 (brecha del crédito)": "", "e.e. γ1": "", "γ2 (brecha del PBI)": "", "e.e. γ2": "", "N (γ)": ""})
    return pd.DataFrame(filas)


def tabla_gmm(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Tabla 6, panel B: el modelo dinámico (2) estimado por efectos fijos y por System GMM."""
    base = ["ln_L_l1"] + VARIABLES_CICLO + CONTROLES_BANCO + ["pandemia"]
    ef = estimar_efectos_fijos(panel, "ln_L", base)
    gmm = system_gmm(panel, "ln_L", VARIABLES_CICLO + ["pandemia"], CONTROLES_BANCO)
    gmm["coef"]["ln_L_l1"], gmm["ee"]["ln_L_l1"], gmm["p"]["ln_L_l1"] = (
        gmm["coef"].pop("y_l1"), gmm["ee"].pop("y_l1"), gmm["p"].pop("y_l1"))
    modelos = {"Efectos fijos (Driscoll-Kraay)": ef, "System GMM (una etapa)": gmm}
    etiquetas = {k: ETIQUETAS_DINAMICO[k] for k in ["ln_L_l1", "brecha_credito", "brecha_pbi", "tasa_referencia", "pandemia"]}
    extra = {
        "Instrumentos": ["", str(gmm["instrumentos"])],
        "Prueba de Hansen (valor p)": ["", f"{gmm['p_hansen']:.3f}"],
        "AR(1) en diferencias (valor p)": ["", f"{gmm['p_ar1']:.3f}"],
        "AR(2) en diferencias (valor p)": ["", f"{gmm['p_ar2']:.3f}"],
    }
    tabla = tabla_de_modelos(modelos, etiquetas, extra)
    tabla = tabla[~tabla["Variable"].isin(["R² within", "Meses"])]
    return tabla, gmm


def bloque_5_heterogeneidad_y_robustez(panel: pd.DataFrame) -> None:
    anotar("Bloque 5 · Heterogeneidad (H3) y robustez")
    panel = panel.copy()
    controles = ["ratio_capital_global_l1", "morosidad_l1", "ln_A_real_l1"]

    # Grupos: periodo del mes y colchón de capital del banco (RCG promedio sobre o
    # bajo la mediana de los 15 bancos; es fijo por banco para no depender del ciclo)
    panel["periodo"] = None
    for nombre, (desde, hasta) in PERIODOS.items():
        panel.loc[panel["fecha"].between(desde, hasta), "periodo"] = nombre
    rcg_medio = panel.groupby("entidad")["ratio_capital_global"].mean()
    alto = rcg_medio[rcg_medio > rcg_medio.median()].index
    panel["colchon"] = np.where(panel["entidad"].isin(alto), "Colchón alto\n(RCG > mediana)",
                                "Colchón bajo\n(RCG < mediana)")
    panel = panel.sort_values("colchon", ascending=False, kind="stable")   # primero el colchón bajo
    anotar(f"Bancos con colchón alto ({len(alto)}): {sorted(alto)}")

    _, por_periodo, prueba_periodo = betas_por_grupo(panel.sort_values(["fecha", "entidad"]), "periodo", controles)
    _, por_colchon, prueba_colchon = betas_por_grupo(panel, "colchon", controles)
    for tabla in (por_periodo, por_colchon):
        for _, f in tabla.iterrows():
            anotar(f"β · {f['grupo'].replace(chr(10), ' ')}: {f['beta']:.3f} (IC 95 %: {f['inferior']:.3f} a {f['superior']:.3f})")
    anotar(f"Diferencia pospandemia − prepandemia: {prueba_periodo['diferencia']:.3f} (p = {prueba_periodo['p']:.3f})")
    anotar(f"Diferencia colchón alto − colchón bajo: {prueba_colchon['diferencia']:.3f} (p = {prueba_colchon['p']:.3f})")

    beta_total = estimar_efectos_fijos(panel, "d_ln_L", ["d_ln_A"] + controles)["coef"]["d_ln_A"]
    heterogeneidad = pd.concat([por_periodo.assign(Dimensión="Periodo"), por_colchon.assign(Dimensión="Colchón de capital")])
    heterogeneidad["grupo"] = heterogeneidad["grupo"].str.replace("\n", " ")
    heterogeneidad = heterogeneidad[["Dimensión", "grupo", "beta", "ee", "inferior", "superior", "p"]].round(3)
    heterogeneidad.columns = ["Dimensión", "Grupo", "β", "e.e.", "IC 95 % inferior", "IC 95 % superior", "Valor p"]
    pruebas = pd.DataFrame([
        {"Dimensión": "Periodo", "Grupo": "Diferencia pospandemia − prepandemia",
         "β": round(prueba_periodo["diferencia"], 3), "e.e.": round(prueba_periodo["ee"], 3), "Valor p": round(prueba_periodo["p"], 3)},
        {"Dimensión": "Colchón de capital", "Grupo": "Diferencia colchón alto − colchón bajo",
         "β": round(prueba_colchon["diferencia"], 3), "e.e.": round(prueba_colchon["ee"], 3), "Valor p": round(prueba_colchon["p"], 3)},
    ])
    guardar_tabla(pd.concat([heterogeneidad, pruebas], ignore_index=True), "tabla_heterogeneidad.csv")
    guardar_figura(figura_heterogeneidad(por_periodo, por_colchon, beta_total), "fig_heterogeneidad.svg")

    robustez = tabla_robustez(panel.sort_values(["entidad", "fecha"]))
    guardar_tabla(robustez, "tabla_robustez.csv")
    for _, f in robustez.iterrows():
        anotar(f"Robustez · {f['Especificación']}: β = {f['β (Adrian-Shin)'] or '—'} · "
               f"γ2 = {f['γ2 (brecha del PBI)'] or '—'}")

    gmm_tabla, gmm = tabla_gmm(panel.sort_values(["entidad", "fecha"]))
    guardar_tabla(gmm_tabla, "tabla_robustez_gmm.csv")
    anotar(f"System GMM: ρ = {gmm['coef']['ln_L_l1']:.3f} · {gmm['instrumentos']} instrumentos · "
           f"Hansen p = {gmm['p_hansen']:.3f} · AR(1) p = {gmm['p_ar1']:.3f} · AR(2) p = {gmm['p_ar2']:.3f}")


# ---------------------------------------------------------------------------
# 9. Programa principal
# ---------------------------------------------------------------------------
def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    for entrada in (ENTRADA_PANEL, ENTRADA_MACRO):
        if not entrada.exists():
            print(f"Falta {entrada.relative_to(RAIZ)}: ejecutar antes los scripts 01, 02 y 03.")
            return 1

    np.random.seed(SEMILLA)
    CARPETA_SALIDAS.mkdir(exist_ok=True)
    configurar_graficos()
    anotar("Inicio del análisis")
    anotar(f"Versiones: Python {sys.version.split()[0]} · numpy {np.__version__} · pandas {pd.__version__} · "
           f"scipy {__import__('scipy').__version__} · matplotlib {matplotlib.__version__}")

    brechas = bloque_1_ciclo()
    panel = bloque_2_descriptivo(brechas)
    panel = bloque_3_prociclicidad(panel, brechas)
    panel = bloque_4_modelo_dinamico(panel)
    bloque_5_heterogeneidad_y_robustez(panel)

    anotar("Análisis terminado sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
