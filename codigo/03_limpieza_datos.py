# Autora: Lucia Pamela Colonio Yaringaño
# Código de matrícula: 2024200495A
# Tema N.º 85 del temario (Unidad II): Apalancamiento del sistema bancario peruano y ciclo del crédito
# Fecha de extracción: 2026-11-11
"""
03_limpieza_datos.py · Limpieza, validación e integración de las dos vías.

Entradas (generadas por los scripts 01 y 02, no se modifican):
    datos_crudos/datos_crudos_bcrp_2024200495A.csv   series macro del BCRP (Vía 1, API)
    datos_crudos/datos_crudos_sbs_2024200495A.csv    cifras por banco de la SBS (Vía 2)

Qué hace:
    1. Convierte los valores a números y los periodos a fechas (AAAA-MM).
    2. Pasa la información de la SBS a una tabla ancha: una fila por banco y mes.
    3. Conserva solo los bancos con los 120 meses completos (panel balanceado).
    4. Valida la información: identidad contable (activo = pasivo + patrimonio)
       y cobertura de cada variable.
    5. Calcula las variables del estudio (apalancamiento, créditos directos,
       activo real) y marca los valores atípicos sin borrarlos.
    6. Une la información de los bancos con las series del BCRP por la llave
       de fecha. La llave del panel es Entidad + fecha.
    7. Guarda el archivo final y su huella digital SHA-256.

Salidas:
    datos_procesados/datos_procesados_2024200495A.csv   panel banco-mes final
    datos_procesados/sha256_datos_procesados.txt         hash SHA-256 del archivo final
    log_ejecucion.txt                                     resumen de cada paso

Ejecución (desde la carpeta raíz del repositorio):
    python codigo/03_limpieza_datos.py      (en Windows sin PATH: py codigo/03_limpieza_datos.py)
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. Parámetros
# ---------------------------------------------------------------------------
CODIGO_MATRICULA = "2024200495A"
FECHA_INICIO = "2016-01"
FECHA_CORTE = "2025-12"
MESES_ESPERADOS = len(pd.period_range(FECHA_INICIO, FECHA_CORTE, freq="M"))  # 120

# Meses abreviados que usa el BCRP en sus periodos ('Ene.2016', 'Set.2016'...)
MESES_BCRP = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
              "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}

# Variables de la SBS que debe tener cada banco en todos los meses
VARIABLES_CLAVE = ["activo_total", "patrimonio", "morosidad", "ratio_capital_global"]

# Tolerancia de la identidad contable, en miles de soles (diferencias de redondeo)
TOLERANCIA_IDENTIDAD = 1.0

# Percentiles para la versión acotada (winsorizada) del apalancamiento
PERCENTIL_INFERIOR = 0.01
PERCENTIL_SUPERIOR = 0.99

# ---------------------------------------------------------------------------
# 2. Rutas relativas a la carpeta del proyecto
# ---------------------------------------------------------------------------
if "__file__" in globals():
    RAIZ = Path(__file__).resolve().parent.parent
else:
    RAIZ = Path.cwd()
CARPETA_CRUDOS = RAIZ / "datos_crudos"
CARPETA_PROCESADOS = RAIZ / "datos_procesados"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
ENTRADA_BCRP = CARPETA_CRUDOS / f"datos_crudos_bcrp_{CODIGO_MATRICULA}.csv"
ENTRADA_SBS = CARPETA_CRUDOS / f"datos_crudos_sbs_{CODIGO_MATRICULA}.csv"
SALIDA = CARPETA_PROCESADOS / f"datos_procesados_{CODIGO_MATRICULA}.csv"
SALIDA_HASH = CARPETA_PROCESADOS / "sha256_datos_procesados.txt"


def anotar(mensaje: str) -> None:
    """Muestra el mensaje en consola y lo añade al log con fecha y hora."""
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [03_limpieza] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


# ---------------------------------------------------------------------------
# 3. Vía 1: series del BCRP
# ---------------------------------------------------------------------------
def preparar_bcrp() -> pd.DataFrame:
    """Tabla con una fila por mes y una columna por serie del BCRP."""
    crudo = pd.read_csv(ENTRADA_BCRP, dtype=str)

    # 'Ene.2016' -> 2016-01 ; los valores 'n.d.' se convierten en vacíos (NaN)
    partes = crudo["periodo_bcrp"].str.split(".", expand=True)
    crudo["anio"] = partes[1].astype(int)
    crudo["mes"] = partes[0].str.lower().str[:3].map(MESES_BCRP)
    if crudo["mes"].isna().any():
        raise ValueError(f"Mes no reconocido en el BCRP: {crudo.loc[crudo['mes'].isna(), 'periodo_bcrp'].unique()}")
    crudo["valor"] = pd.to_numeric(crudo["valor"], errors="coerce")

    macro = crudo.pivot_table(index=["anio", "mes"], columns="variable", values="valor", aggfunc="first")
    macro = macro.reset_index()
    macro.columns.name = None

    vacios = macro.drop(columns=["anio", "mes"]).isna().sum()
    anotar(f"BCRP: {len(macro)} meses · valores vacíos por serie: {vacios.to_dict()}")
    if len(macro) != MESES_ESPERADOS:
        raise ValueError(f"El BCRP tiene {len(macro)} meses; se esperaban {MESES_ESPERADOS}")
    return macro


# ---------------------------------------------------------------------------
# 4. Vía 2: cifras por banco de la SBS
# ---------------------------------------------------------------------------
def preparar_sbs() -> pd.DataFrame:
    """Tabla con una fila por banco y mes, y una columna por variable."""
    crudo = pd.read_csv(ENTRADA_SBS)
    crudo["valor"] = pd.to_numeric(crudo["valor"], errors="coerce")
    no_numericos = int(crudo["valor"].isna().sum())

    bancos = crudo.pivot_table(index=["entidad", "anio", "mes"], columns="variable",
                               values="valor", aggfunc="first").reset_index()
    bancos.columns.name = None
    anotar(f"SBS: {len(bancos)} filas banco-mes · {bancos['entidad'].nunique()} bancos · "
           f"valores no numéricos en el crudo: {no_numericos}")
    return bancos


def seleccionar_panel_balanceado(bancos: pd.DataFrame) -> pd.DataFrame:
    """
    Conserva los bancos que tienen las VARIABLES_CLAVE en los 120 meses.
    Los demás (entraron o salieron del sistema en el periodo) se excluyen y
    se anotan en el log con el número de meses que sí tienen.
    """
    completos = bancos.dropna(subset=VARIABLES_CLAVE)
    meses_por_banco = completos.groupby("entidad").size()
    incluidos = sorted(meses_por_banco[meses_por_banco == MESES_ESPERADOS].index)
    excluidos = meses_por_banco[meses_por_banco < MESES_ESPERADOS].to_dict()

    anotar(f"Bancos con los {MESES_ESPERADOS} meses completos: {len(incluidos)} · {incluidos}")
    anotar(f"Bancos excluidos (meses disponibles): {excluidos}")
    return bancos[bancos["entidad"].isin(incluidos)].copy()


def validar(panel: pd.DataFrame) -> None:
    """Controles de calidad: identidad contable y valores vacíos."""
    diferencia = (panel["activo_total"] - panel["pasivo_total"] - panel["patrimonio"]).abs()
    fallas = int((diferencia > TOLERANCIA_IDENTIDAD).sum())
    anotar(f"Identidad activo = pasivo + patrimonio: diferencia máxima {diferencia.max():.3f} "
           f"miles de S/ · filas fuera de tolerancia: {fallas}")

    vacios = panel.isna().sum()
    vacios = vacios[vacios > 0].to_dict()
    anotar(f"Valores vacíos en el panel: {vacios if vacios else 'ninguno'}")


# ---------------------------------------------------------------------------
# 5. Variables del estudio
# ---------------------------------------------------------------------------
def construir_variables(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Pasa los montos de miles a millones de soles (la unidad del BCRP) y
    calcula las variables que usa el análisis.
    """
    montos = ["activo_total", "pasivo_total", "patrimonio", "creditos_netos",
              "creditos_vigentes", "creditos_refinanciados", "creditos_atrasados", "provisiones"]
    for columna in montos:
        panel[columna] = panel[columna] / 1000  # miles de S/ -> millones de S/

    panel["creditos_directos"] = (panel["creditos_vigentes"] + panel["creditos_refinanciados"]
                                  + panel["creditos_atrasados"])
    # Apalancamiento = activo total / patrimonio (veces), como en Adrian y Shin (2010)
    panel["apalancamiento"] = panel["activo_total"] / panel["patrimonio"]
    # Activo en soles de diciembre de 2021 (deflactado con el IPC de Lima)
    panel["activo_real"] = panel["activo_total"] / (panel["ipc_lima"] / 100)
    return panel


def tratar_atipicos(panel: pd.DataFrame) -> pd.DataFrame:
    """
    No se borra ninguna observación. Se añaden dos columnas:
      atipico_apalancamiento  1 si el apalancamiento está fuera del rango
                              [Q1 - 3·RIC, Q3 + 3·RIC] de todo el panel
      apalancamiento_w        apalancamiento acotado a los percentiles 1 y 99
    El análisis usa apalancamiento_w y, como prueba de robustez, el original.
    """
    q1, q3 = panel["apalancamiento"].quantile([0.25, 0.75])
    ric = q3 - q1
    limite_inf, limite_sup = q1 - 3 * ric, q3 + 3 * ric
    panel["atipico_apalancamiento"] = (~panel["apalancamiento"].between(limite_inf, limite_sup)).astype(int)

    p_inf, p_sup = panel["apalancamiento"].quantile([PERCENTIL_INFERIOR, PERCENTIL_SUPERIOR])
    panel["apalancamiento_w"] = panel["apalancamiento"].clip(p_inf, p_sup)

    marcados = panel[panel["atipico_apalancamiento"] == 1]
    anotar(f"Atípicos del apalancamiento (fuera de [{limite_inf:.2f}; {limite_sup:.2f}]): "
           f"{len(marcados)} · por banco: {marcados.groupby('entidad').size().to_dict()}")
    anotar(f"Apalancamiento acotado a los percentiles 1 y 99: [{p_inf:.2f}; {p_sup:.2f}]")
    return panel


# ---------------------------------------------------------------------------
# 6. Programa principal
# ---------------------------------------------------------------------------
def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    for entrada in (ENTRADA_BCRP, ENTRADA_SBS):
        if not entrada.exists():
            print(f"Falta {entrada.relative_to(RAIZ)}: ejecutar antes los scripts 01 y 02.")
            return 1

    CARPETA_PROCESADOS.mkdir(exist_ok=True)
    anotar("Inicio de la limpieza e integración de datos")

    macro = preparar_bcrp()
    bancos = seleccionar_panel_balanceado(preparar_sbs())
    validar(bancos)

    # Unión por la fecha: cada banco-mes recibe las series macro de ese mes
    panel = bancos.merge(macro, on=["anio", "mes"], how="left", validate="many_to_one")
    sin_macro = int(panel["credito_privado"].isna().sum())
    anotar(f"Unión SBS + BCRP por fecha: {len(panel)} filas · filas sin dato macro: {sin_macro}")

    panel = construir_variables(panel)
    panel = tratar_atipicos(panel)

    # Orden final: llave (entidad + fecha), variables bancarias, variables macro
    panel.insert(1, "fecha", pd.to_datetime(dict(year=panel["anio"], month=panel["mes"], day=1)).dt.strftime("%Y-%m"))
    columnas = ["entidad", "fecha", "anio", "mes",
                "activo_total", "pasivo_total", "patrimonio", "apalancamiento", "apalancamiento_w",
                "atipico_apalancamiento", "activo_real", "creditos_directos", "creditos_vigentes",
                "creditos_refinanciados", "creditos_atrasados", "creditos_netos", "provisiones",
                "morosidad", "ratio_capital_global",
                "credito_privado", "pbi_desestacionalizado", "tasa_referencia", "ipc_lima"]
    panel = panel[columnas].sort_values(["entidad", "fecha"]).reset_index(drop=True)

    if panel.duplicated(["entidad", "fecha"]).any():
        anotar("ERROR: hay filas repetidas para la llave entidad + fecha")
        return 1

    # Formato fijo (6 decimales y saltos de línea '\n') para que el archivo,
    # y por tanto su hash, sean idénticos en Windows, macOS y Linux.
    panel.to_csv(SALIDA, index=False, encoding="utf-8", float_format="%.6f", lineterminator="\n")
    huella = hashlib.sha256(SALIDA.read_bytes()).hexdigest()
    SALIDA_HASH.write_text(f"{huella}  {SALIDA.name}\n", encoding="utf-8")

    anotar(f"Archivo final: {SALIDA.relative_to(RAIZ).as_posix()} · {len(panel)} filas × {panel.shape[1]} columnas · "
           f"{panel['entidad'].nunique()} bancos · {panel['fecha'].nunique()} meses "
           f"({panel['fecha'].min()} a {panel['fecha'].max()})")
    anotar(f"SHA-256: {huella}")
    anotar("Limpieza terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
