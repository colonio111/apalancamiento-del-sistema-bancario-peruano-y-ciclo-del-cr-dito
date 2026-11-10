# Autora: Lucia Pamela Colonio Yaringaño
# Código de matrícula: 2024200495A
# Tema N.º 85 del temario (Unidad II): Apalancamiento del sistema bancario peruano y ciclo del crédito
# Fecha de extracción: 2026-11-09
"""
01_extraccion_api.py · Vía 1 de extracción: API REST de BCRPData (BCRP).

Descarga cuatro series mensuales del Banco Central de Reserva del Perú para el
periodo congelado FECHA_INICIO a FECHA_CORTE:

    PN00505MM  Crédito al sector privado, tipo de cambio constante (millones S/)
    PN01773AM  PBI desestacionalizado (índice 2007 = 100)
    PD04722MM  Tasa de referencia de la política monetaria (%)
    PN38705PM  IPC de Lima Metropolitana (índice dic. 2021 = 100)

Endpoint (formato documentado por el BCRP):
    https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{código}/json/{inicio}/{fin}/esp

Salidas:
    datos_crudos/bcrp_{código_serie}_2024200495A.json   respuesta original de la API, sin tocar
    datos_crudos/datos_crudos_bcrp_2024200495A.csv      las cuatro series juntas, en formato largo
    log_ejecucion.txt                                    fecha, hora, código HTTP y filas por serie

Ejecución (desde la carpeta raíz del repositorio):
    python codigo/01_extraccion_api.py      (o, en Windows sin PATH: py codigo/01_extraccion_api.py)

Requisitos: Python 3.11 o superior (lo exige pandas 3), con las librerías de requirements.txt.
"""

# Permite usar anotaciones de tipo modernas en cualquier versión de Python 3
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# 1. Parámetros congelados de la consulta
#    Son constantes a propósito: si el script se vuelve a ejecutar otro día,
#    pide exactamente el mismo periodo y las mismas series (numeral 2.4.5).
# ---------------------------------------------------------------------------
CODIGO_MATRICULA = "2024200495A"
FECHA_INICIO = "2016-01"   # primer mes del panel
FECHA_CORTE = "2025-12"    # último mes del panel (120 meses en total)

# Código de serie del BCRP -> nombre corto de la variable en este proyecto
SERIES_BCRP = {
    "PN00505MM": "credito_privado",
    "PN01773AM": "pbi_desestacionalizado",
    "PD04722MM": "tasa_referencia",
    "PN38705PM": "ipc_lima",
}

URL_API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
USER_AGENT = "UNCP-FinanzasI-Tema85/1.0 (trabajo academico; L. P. Colonio Yaringano)"
PAUSA_ENTRE_SOLICITUDES = 1.5  # segundos; la consigna exige al menos 1 s
INTENTOS_MAXIMOS = 3
TIEMPO_LIMITE = 30             # segundos de espera por respuesta

# ---------------------------------------------------------------------------
# 2. Rutas relativas a la carpeta del proyecto (nunca rutas como C:\Users\...)
#    __file__ es este script; .parent.parent sube de /codigo a la raíz.
# ---------------------------------------------------------------------------
#    Si el código se ejecuta dentro de un cuaderno (Jupyter o Colab), donde
#    __file__ no existe, se toma como raíz la carpeta de trabajo actual.
if "__file__" in globals():
    RAIZ = Path(__file__).resolve().parent.parent
else:
    RAIZ = Path.cwd()
CARPETA_CRUDOS = RAIZ / "datos_crudos"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"
ARCHIVO_CSV_CRUDO = CARPETA_CRUDOS / f"datos_crudos_bcrp_{CODIGO_MATRICULA}.csv"


def anotar(mensaje: str) -> None:
    """Muestra el mensaje en consola y lo añade al log con fecha y hora."""
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [01_api] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


def periodo_bcrp(fecha_aaaa_mm: str) -> str:
    """Convierte '2016-01' al formato que pide la API del BCRP: '2016-1'."""
    anio, mes = fecha_aaaa_mm.split("-")
    return f"{anio}-{int(mes)}"


def pedir_serie(codigo_serie: str) -> tuple[bytes, int]:
    """
    Solicita una serie a la API y devuelve (contenido en bytes, código HTTP).
    Se pide una serie por vez porque, al pedir varias juntas, la API las
    devuelve ordenadas por código y no en el orden solicitado.
    Si falla la conexión o el servidor responde con error, reintenta hasta
    INTENTOS_MAXIMOS veces, esperando un poco más en cada intento.
    """
    url = (f"{URL_API}/{codigo_serie}/json/"
           f"{periodo_bcrp(FECHA_INICIO)}/{periodo_bcrp(FECHA_CORTE)}/esp")
    cabeceras = {"User-Agent": USER_AGENT}

    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            respuesta = requests.get(url, headers=cabeceras, timeout=TIEMPO_LIMITE)
            if respuesta.status_code == 200:
                return respuesta.content, respuesta.status_code
            anotar(f"{codigo_serie}: HTTP {respuesta.status_code} en el intento {intento}")
        except requests.RequestException as error:
            anotar(f"{codigo_serie}: error de conexión en el intento {intento} ({error})")
        time.sleep(PAUSA_ENTRE_SOLICITUDES * intento)

    raise RuntimeError(f"No se pudo descargar la serie {codigo_serie} tras {INTENTOS_MAXIMOS} intentos")


def a_filas(contenido: bytes, codigo_serie: str) -> list[dict]:
    """
    Lee el JSON de la API y lo convierte en filas de una tabla larga:
    una fila por mes, con el código, el nombre oficial, el periodo y el valor.
    Los valores se guardan como texto, tal como vienen (incluido 'n.d.' si
    hubiera meses sin dato); la conversión a números se hace en 03_limpieza.
    """
    datos = json.loads(contenido.decode("utf-8"))
    nombre_oficial = datos["config"]["series"][0]["name"]
    filas = []
    for periodo in datos["periods"]:
        filas.append({
            "codigo_serie": codigo_serie,
            "variable": SERIES_BCRP[codigo_serie],
            "nombre_serie_bcrp": nombre_oficial,
            "periodo_bcrp": periodo["name"],   # p. ej. 'Ene.2016'
            "valor": periodo["values"][0],
        })
    return filas


def main() -> int:
    # Evita errores de impresión de tildes o del símbolo «·» en consolas que
    # no usan UTF-8 (algunas terminales antiguas de Windows)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    CARPETA_CRUDOS.mkdir(exist_ok=True)
    anotar(f"Inicio de la extracción BCRP · periodo {FECHA_INICIO} a {FECHA_CORTE}")

    todas_las_filas = []
    series_con_error = []

    for posicion, codigo in enumerate(SERIES_BCRP, start=1):
        try:
            contenido, estado_http = pedir_serie(codigo)

            # Respaldo de la respuesta original, byte por byte (evidencia primaria)
            (CARPETA_CRUDOS / f"bcrp_{codigo}_{CODIGO_MATRICULA}.json").write_bytes(contenido)

            filas = a_filas(contenido, codigo)
            todas_las_filas.extend(filas)
            anotar(f"{codigo} ({SERIES_BCRP[codigo]}): HTTP {estado_http} · {len(filas)} filas")
        except (RuntimeError, ValueError, KeyError) as error:
            series_con_error.append(codigo)
            anotar(f"{codigo}: ERROR · {error}")

        # Pausa de cortesía entre solicitudes (no después de la última)
        if posicion < len(SERIES_BCRP):
            time.sleep(PAUSA_ENTRE_SOLICITUDES)

    # Las cuatro series en un solo CSV crudo (formato largo, sin transformar)
    tabla = pd.DataFrame(todas_las_filas)
    tabla.to_csv(ARCHIVO_CSV_CRUDO, index=False, encoding="utf-8")
    anotar(f"Archivo crudo guardado: {ARCHIVO_CSV_CRUDO.relative_to(RAIZ)} · {len(tabla)} filas")

    # Control rápido: cada serie debe tener 120 meses
    if not tabla.empty:
        meses_por_serie = tabla.groupby("codigo_serie").size().to_dict()
        anotar(f"Meses por serie: {meses_por_serie}")

    if series_con_error:
        anotar(f"Extracción INCOMPLETA. Series con error: {series_con_error}")
        return 1
    anotar("Extracción BCRP terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
