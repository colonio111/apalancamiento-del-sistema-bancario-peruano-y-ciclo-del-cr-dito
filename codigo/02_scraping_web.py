# Autora: Lucia Pamela Colonio Yaringaño
# Código de matrícula: 2024200495A
# Tema N.º 85 del temario (Unidad II): Apalancamiento del sistema bancario peruano y ciclo del crédito
# Fecha de extracción: 2026-11-11
"""
02_scraping_web.py · Vía 2 de extracción: rastreo del portal estadístico de la SBS
y descarga programática de los reportes mensuales por empresa bancaria.

Reportes (Superintendencia de Banca, Seguros y AFP, Banca Múltiple):
    B-2201  Balance general y estado de ganancias y pérdidas por empresa bancaria
    B-2401  Indicadores financieros por empresa bancaria (morosidad)
    B-2402  Requerimiento de patrimonio efectivo y ratio de capital global

Cómo funciona:
    1. Comprueba que el robots.txt de la SBS permite las rutas que se van a usar.
    2. Abre la página de cada reporte en el portal y, con BeautifulSoup, busca los
       enlaces a archivos Excel (selector CSS: a[href]; se conservan los que
       terminan en .xls/.XLS/.xlsx). Así se obtiene la lista de archivos por mes,
       que es la "paginación" del portal: una página por reporte con un enlace
       por mes y por año.
    3. Conserva solo los meses entre FECHA_INICIO y FECHA_CORTE.
    4. Descarga cada archivo tal como lo publica la SBS, con pausa entre
       solicitudes y un User-Agent identificable.
    5. Lee los archivos descargados y extrae, por banco y por mes, las cifras
       que usa el estudio (activo, pasivo, patrimonio, créditos, morosidad y
       ratio de capital global). Las filas se ubican por su ETIQUETA (por
       ejemplo "TOTAL ACTIVO") y no por su número, porque la posición cambia
       entre años. Los nombres de los bancos se armonizan (p. ej. Banco
       Continental -> BBVA Perú) y se conserva también el nombre original.

Salidas:
    datos_crudos/sbs/{reporte}/*.XLS                      archivos originales, sin editar
    datos_crudos/sbs_inventario_descargas_2024200495A.csv una fila por archivo: URL,
                                                          código HTTP, tamaño, fecha y hash
    datos_crudos/datos_crudos_sbs_2024200495A.csv         cifras extraídas, formato largo:
                                                          una fila por banco, mes y variable
    log_ejecucion.txt                                     registro de cada solicitud

Ejecución (desde la carpeta raíz del repositorio):
    python codigo/02_scraping_web.py           descarga completa (360 archivos, ~12 min)
    python codigo/02_scraping_web.py --demo    demostración en vivo: últimos 3 meses (~30 s)
    (en Windows sin PATH, usar  py  en lugar de  python)

Si un archivo ya fue descargado, no se vuelve a pedir (salvo en modo --demo),
para no cargar el servidor de la SBS con solicitudes repetidas.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 1. Parámetros congelados de la extracción
# ---------------------------------------------------------------------------
CODIGO_MATRICULA = "2024200495A"
FECHA_INICIO = "2016-01"
FECHA_CORTE = "2025-12"

# Código del reporte en la SBS -> nombre corto usado en este proyecto
REPORTES_SBS = {
    "B-2201": "balance_general",
    "B-2401": "indicadores_financieros",
    "B-2402": "ratio_capital_global",
}

URL_PORTAL = "https://www.sbs.gob.pe/app/stats_net/stats/EstadisticaSistemaFinancieroResultados.aspx?c={reporte}"
USER_AGENT = "UNCP-FinanzasI-Tema85/1.0 (trabajo academico; L. P. Colonio Yaringano)"
PAUSA_ENTRE_SOLICITUDES = 1.5  # segundos; la consigna exige al menos 1 s
INTENTOS_MAXIMOS = 3
TIEMPO_LIMITE = 60
MESES_DEMO = 3                 # meses que se descargan en modo --demo

# Nombres de los meses tal como aparecen en las rutas de la SBS
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Patrón de las rutas de los archivos, por ejemplo:
#   .../estadistica/financiera/2016/Enero/B-2201-en2016.XLS
PATRON_ARCHIVO = re.compile(
    r"/financiera/(?P<anio>\d{4})/(?P<mes>[A-Za-z]+)/(?P<archivo>(?P<reporte>B-\d+)-[a-z]{2}\d{4}\.(?:xls|xlsx))$",
    re.IGNORECASE,
)

# Abreviatura del mes en el nombre del archivo (B-2201-en2016.XLS -> enero)
MES_EN_ARCHIVO = {"en": 1, "fe": 2, "ma": 3, "ab": 4, "my": 5, "jn": 6,
                  "jl": 7, "ag": 8, "se": 9, "oc": 10, "no": 11, "di": 12}

# Armonización de nombres de bancos: si el nombre (en minúsculas y sin tildes)
# contiene el fragmento, se le asigna el nombre armonizado. El orden importa:
# "santander consumer" debe revisarse antes que "santander".
BANCOS = [
    ("continental", "BBVA Perú"), ("bbva", "BBVA Perú"),
    ("comercio", "BANCOM"), ("bancom", "BANCOM"),
    ("credito del peru", "BCP"), ("credito con sucursales", "BCP"),
    ("financiero", "Banco Pichincha"), ("pichincha", "Banco Pichincha"),
    ("interamericano", "BanBif"),
    ("scotiabank", "Scotiabank Perú"),
    ("citibank", "Citibank Perú"),
    ("interbank", "Interbank"),
    ("mibanco", "Mibanco"),
    ("gnb", "Banco GNB"),
    ("falabella", "Banco Falabella"),
    ("santander consumer", "Santander Consumer Bank"), ("santander", "Banco Santander Perú"),
    ("ripley", "Banco Ripley"),
    ("azteca", "Alfin Banco"), ("alfin", "Alfin Banco"),
    ("icbc", "Banco ICBC"),
    ("deutsche", "Deutsche Bank Perú"),
    ("cencosud", "Banco Cencosud"),
    ("china", "Bank of China"),
    ("bci", "Banco BCI Perú"),
    ("compartamos", "Compartamos Banco"),
]

# Filas que se extraen del balance (B-2201), buscadas por su etiqueta.
# Patrón sobre la etiqueta en minúsculas y sin tildes. "dentro_de_creditos"
# indica que la fila se busca después de "CRÉDITOS NETOS..." (hay otras filas
# llamadas "Vigentes" o "Provisiones" en otras partes del balance).
FILAS_BALANCE = [
    ("activo_total", r"^total activo$", False),
    ("pasivo_total", r"^total pasivo$", False),
    ("patrimonio", r"^patrimonio$", False),
    ("creditos_netos", r"^creditos netos", False),
    ("creditos_vigentes", r"^vigentes", True),
    ("creditos_refinanciados", r"^refinanciados", True),
    ("creditos_atrasados", r"^atrasados", True),
    ("provisiones", r"^provisiones", True),
]

# ---------------------------------------------------------------------------
# 2. Rutas relativas a la carpeta del proyecto
# ---------------------------------------------------------------------------
if "__file__" in globals():
    RAIZ = Path(__file__).resolve().parent.parent
else:
    RAIZ = Path.cwd()
CARPETA_CRUDOS = RAIZ / "datos_crudos"
ARCHIVO_LOG = RAIZ / "log_ejecucion.txt"


def anotar(mensaje: str) -> None:
    """Muestra el mensaje en consola y lo añade al log con fecha y hora."""
    linea = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [02_sbs] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as log:
        log.write(linea + "\n")


def crear_sesion() -> requests.Session:
    """Sesión HTTP que envía siempre el mismo User-Agent identificable."""
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": USER_AGENT})
    return sesion


def pedir(sesion: requests.Session, url: str) -> requests.Response:
    """
    GET con reintentos. Devuelve la respuesta si el código HTTP es 200;
    si falla INTENTOS_MAXIMOS veces, lanza un error con el último motivo.
    """
    ultimo_motivo = ""
    for intento in range(1, INTENTOS_MAXIMOS + 1):
        try:
            respuesta = sesion.get(url, timeout=TIEMPO_LIMITE)
            if respuesta.status_code == 200:
                return respuesta
            ultimo_motivo = f"HTTP {respuesta.status_code}"
        except requests.RequestException as error:
            ultimo_motivo = f"error de conexión ({error.__class__.__name__})"
        anotar(f"Intento {intento} fallido para {url}: {ultimo_motivo}")
        time.sleep(PAUSA_ENTRE_SOLICITUDES * (intento + 1))
    raise RuntimeError(f"{url} · {ultimo_motivo}")


def robots_permite(sesion: requests.Session, url: str) -> bool:
    """
    Lee el robots.txt del dominio de la URL y comprueba si nuestro User-Agent
    puede acceder a ella. Si el dominio no publica robots.txt, se permite.
    """
    partes = urlparse(url)
    url_robots = f"{partes.scheme}://{partes.netloc}/robots.txt"
    lector = robotparser.RobotFileParser()
    try:
        respuesta = sesion.get(url_robots, timeout=TIEMPO_LIMITE)
        if respuesta.status_code >= 400:
            anotar(f"robots.txt de {partes.netloc}: no publicado (HTTP {respuesta.status_code}), acceso permitido")
            return True
        lector.parse(respuesta.text.splitlines())
    except requests.RequestException:
        anotar(f"robots.txt de {partes.netloc}: no se pudo leer; se continúa con cautela")
        return True
    permitido = lector.can_fetch(USER_AGENT, url)
    anotar(f"robots.txt de {partes.netloc}: {'permite' if permitido else 'PROHÍBE'} {partes.path}")
    return permitido


def listar_archivos(sesion: requests.Session, reporte: str) -> list[dict]:
    """
    Rastrea la página del reporte en el portal y devuelve un registro por
    archivo mensual: reporte, año, mes, URL y nombre del archivo.
    Selector usado: todos los <a href> de la página cuyo destino coincide con
    PATRON_ARCHIVO (archivo Excel dentro de /estadistica/financiera/).
    """
    url_pagina = URL_PORTAL.format(reporte=reporte)
    respuesta = pedir(sesion, url_pagina)
    sopa = BeautifulSoup(respuesta.text, "html.parser")

    encontrados = {}
    for enlace in sopa.select("a[href]"):
        destino = enlace["href"].strip()
        coincidencia = PATRON_ARCHIVO.search(destino)
        if not coincidencia or coincidencia["reporte"].upper() != reporte:
            continue
        mes = MESES.get(coincidencia["mes"].lower())
        if mes is None:
            continue
        clave = (int(coincidencia["anio"]), mes)
        encontrados[clave] = {
            "reporte": reporte,
            "anio": clave[0],
            "mes": mes,
            "url": requests.compat.urljoin(url_pagina, destino),
            "archivo": coincidencia["archivo"],
        }
    anotar(f"{reporte}: página rastreada (HTTP {respuesta.status_code}) · {len(encontrados)} archivos mensuales enlazados")
    return [encontrados[clave] for clave in sorted(encontrados)]


def dentro_de_ventana(registro: dict, desde: str, hasta: str) -> bool:
    """True si el mes del archivo está entre 'desde' y 'hasta' (formato AAAA-MM)."""
    periodo = f"{registro['anio']:04d}-{registro['mes']:02d}"
    return desde <= periodo <= hasta


def meses_esperados(desde: str, hasta: str) -> list[tuple[int, int]]:
    """Lista de (año, mes) que debería existir en la ventana."""
    periodos = pd.period_range(desde, hasta, freq="M")
    return [(p.year, p.month) for p in periodos]


# ---------------------------------------------------------------------------
# 3. Lectura de los archivos descargados
#    Los archivos de la SBS mezclan dos formatos (Excel antiguo .xls y Excel
#    moderno guardado con extensión .XLS). El motor "calamine" lee ambos.
# ---------------------------------------------------------------------------
def normalizar(texto) -> str:
    """Minúsculas, sin tildes y con un solo espacio: 'Créditos  Netos' -> 'creditos netos'."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.lower()).strip()


def armonizar_banco(nombre) -> str | None:
    """
    Nombre armonizado del banco, o None si la celda no es un banco
    (vacía, 'Activo' o una fila de totales del sistema).
    """
    texto = normalizar(nombre)
    if texto in ("", "nan", "activo") or texto.startswith("total"):
        return None
    for fragmento, nombre_armonizado in BANCOS:
        if fragmento in texto:
            return nombre_armonizado
    return f"NO IDENTIFICADO: {str(nombre).strip()}"


def leer_hoja(ruta: Path) -> pd.DataFrame:
    """Primera hoja del archivo, sin encabezados (se ubican a mano)."""
    return pd.read_excel(ruta, engine="calamine", sheet_name=0, header=None)


def fila_de_bancos(hoja: pd.DataFrame) -> int:
    """Número de la fila que tiene los nombres de los bancos (al menos 5)."""
    for i in range(min(15, len(hoja))):
        nombres = [armonizar_banco(celda) for celda in hoja.iloc[i]]
        if sum(1 for n in nombres if n and not n.startswith("NO IDENTIFICADO")) >= 5:
            return i
    raise ValueError("no se encontró la fila con los nombres de los bancos")


def buscar_fila(etiquetas: list[str], patron: str, desde: int = 0) -> int | None:
    """Primera fila (desde 'desde') cuya etiqueta coincide con el patrón."""
    for i in range(desde, len(etiquetas)):
        if re.match(patron, etiquetas[i]):
            return i
    return None


def leer_balance(ruta: Path) -> list[dict]:
    """
    B-2201: cada banco ocupa tres columnas (MN, ME, TOTAL); se toma TOTAL.
    Se omiten las columnas 'con Sucursales en el Exterior', que repiten a
    un banco ya incluido sumándole sus oficinas fuera del Perú.
    """
    hoja = leer_hoja(ruta)
    fb = fila_de_bancos(hoja)
    etiquetas = [normalizar(x) for x in hoja.iloc[:, 0]]

    inicio_creditos = buscar_fila(etiquetas, r"^creditos netos") or 0
    filas = {}
    for variable, patron, dentro_de_creditos in FILAS_BALANCE:
        filas[variable] = buscar_fila(etiquetas, patron, inicio_creditos if dentro_de_creditos else 0)
    no_halladas = [v for v, i in filas.items() if i is None]
    if no_halladas:
        raise ValueError(f"etiquetas no encontradas: {no_halladas}")

    registros = []
    for columna in range(1, hoja.shape[1]):
        nombre = hoja.iat[fb, columna]
        banco = armonizar_banco(nombre)
        if banco is None or "sucursales" in normalizar(nombre):
            continue
        col_total = next((k for k in range(columna, min(columna + 4, hoja.shape[1]))
                          if normalizar(hoja.iat[fb + 1, k]) == "total"), None)
        if col_total is None:
            raise ValueError(f"no se encontró la columna TOTAL de {nombre}")
        for variable, fila in filas.items():
            registros.append({"entidad_sbs": str(nombre).strip(), "entidad": banco,
                              "variable": variable, "valor": hoja.iat[fila, col_total],
                              "unidad": "miles de soles"})
    return registros


def leer_indicadores(ruta: Path) -> list[dict]:
    """B-2401: fila 'Créditos Atrasados (criterio SBS) / Créditos Directos' (morosidad, %)."""
    hoja = leer_hoja(ruta)
    fb = fila_de_bancos(hoja)
    etiquetas = [normalizar(x) for x in hoja.iloc[:, 0]]
    fila = buscar_fila(etiquetas, r"^creditos atrasados \(criterio (sbs|contable)\).*/ creditos directos")
    if fila is None:
        raise ValueError("no se encontró la fila de morosidad")
    registros = []
    for columna in range(1, hoja.shape[1]):
        nombre = hoja.iat[fb, columna]
        banco = armonizar_banco(nombre)
        if banco is None:
            continue
        registros.append({"entidad_sbs": str(nombre).strip(), "entidad": banco,
                          "variable": "morosidad", "valor": hoja.iat[fila, columna],
                          "unidad": "porcentaje"})
    return registros


def leer_capital(ruta: Path) -> list[dict]:
    """
    B-2402: los bancos están en filas (debajo de 'EMPRESAS'); el ratio de
    capital global está en la columna cuyo encabezado lo menciona (la última).
    """
    hoja = leer_hoja(ruta)
    etiquetas = [normalizar(x) for x in hoja.iloc[:, 0]]
    fila_empresas = buscar_fila(etiquetas, r"^empresas$")
    if fila_empresas is None:
        raise ValueError("no se encontró la fila 'EMPRESAS'")
    columna_rcg = None
    for columna in range(hoja.shape[1]):
        encabezado = " ".join(normalizar(x) for x in hoja.iloc[max(0, fila_empresas - 3):fila_empresas + 1, columna])
        if "ratio de capital global" in encabezado:
            columna_rcg = columna
    if columna_rcg is None:
        raise ValueError("no se encontró la columna del ratio de capital global")
    registros = []
    for fila in range(fila_empresas + 1, len(hoja)):
        if etiquetas[fila].startswith("total"):
            break
        banco = armonizar_banco(hoja.iat[fila, 0])
        if banco is None:
            continue
        registros.append({"entidad_sbs": str(hoja.iat[fila, 0]).strip(), "entidad": banco,
                          "variable": "ratio_capital_global", "valor": hoja.iat[fila, columna_rcg],
                          "unidad": "porcentaje"})
    return registros


LECTORES = {"B-2201": leer_balance, "B-2401": leer_indicadores, "B-2402": leer_capital}


def extraer_cifras(carpeta_destino: Path, archivo_salida: Path) -> int:
    """
    Recorre los archivos descargados, extrae las cifras de cada uno y las
    guarda en un CSV largo. Devuelve el número de archivos con error.
    """
    filas, errores = [], 0
    for reporte, lector in LECTORES.items():
        for ruta in sorted((carpeta_destino / reporte).glob("*.[xX][lL][sS]*")):
            clave = re.search(r"-([a-z]{2})(\d{4})\.", ruta.name.lower())
            try:
                for registro in lector(ruta):
                    filas.append({"reporte": reporte, "archivo": ruta.name,
                                  "anio": int(clave.group(2)), "mes": MES_EN_ARCHIVO[clave.group(1)],
                                  **registro})
            except (ValueError, KeyError, AttributeError) as error:
                errores += 1
                anotar(f"{ruta.name}: no se pudo leer · {error}")

    tabla = pd.DataFrame(filas)
    tabla.to_csv(archivo_salida, index=False, encoding="utf-8")
    anotar(f"Cifras extraídas: {archivo_salida.relative_to(RAIZ).as_posix()} · {len(tabla)} filas")
    if tabla.empty:
        return errores + 1

    sin_identificar = sorted(tabla.loc[tabla["entidad"].str.startswith("NO IDENTIFICADO"), "entidad"].unique())
    if sin_identificar:
        anotar(f"Bancos sin armonizar (revisar la lista BANCOS): {sin_identificar}")

    # Cobertura: observaciones banco-mes con activo y patrimonio disponibles
    balance = tabla[tabla["variable"].isin(["activo_total", "patrimonio"])]
    obs = balance.groupby(["entidad", "anio", "mes"]).size()
    anotar(f"Observaciones banco-mes en el balance: {len(obs)} · bancos distintos: {tabla['entidad'].nunique()}")
    return errores


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    argumentos = argparse.ArgumentParser(description="Descarga de reportes mensuales de la SBS")
    argumentos.add_argument("--demo", action="store_true",
                            help=f"descarga solo los últimos {MESES_DEMO} meses (demostración en vivo)")
    modo_demo = argumentos.parse_args().demo

    # En modo demostración se descargan siempre de nuevo los últimos meses,
    # en una carpeta aparte para no mezclar con la extracción completa.
    if modo_demo:
        desde = str(pd.Period(FECHA_CORTE, freq="M") - (MESES_DEMO - 1))
        carpeta_destino = CARPETA_CRUDOS / "sbs_demo"
        archivo_inventario = CARPETA_CRUDOS / f"sbs_demo_inventario_{CODIGO_MATRICULA}.csv"
    else:
        desde = FECHA_INICIO
        carpeta_destino = CARPETA_CRUDOS / "sbs"
        archivo_inventario = CARPETA_CRUDOS / f"sbs_inventario_descargas_{CODIGO_MATRICULA}.csv"

    anotar(f"Inicio de la extracción SBS · {'DEMOSTRACIÓN' if modo_demo else 'completa'} · periodo {desde} a {FECHA_CORTE}")
    sesion = crear_sesion()

    # 1. robots.txt: portal (páginas) y servidor de archivos
    ejemplo_archivo = "https://intranet2.sbs.gob.pe/estadistica/financiera/2016/Enero/B-2201-en2016.XLS"
    if not (robots_permite(sesion, URL_PORTAL.format(reporte="B-2201"))
            and robots_permite(sesion, ejemplo_archivo)):
        anotar("El robots.txt prohíbe la ruta: se detiene la extracción (ver numeral 2.4.3 de la consigna)")
        return 1

    # Si ya existe un inventario de una ejecución anterior, se conserva la fecha
    # y el código HTTP de la descarga original de cada archivo.
    previo = {}
    if archivo_inventario.exists() and not modo_demo:
        tabla_previa = pd.read_csv(archivo_inventario, dtype=str).fillna("")
        previo = {fila["archivo"]: fila for fila in tabla_previa.to_dict("records")}

    inventario = []
    faltantes = []
    errores = 0

    for reporte, nombre_corto in REPORTES_SBS.items():
        time.sleep(PAUSA_ENTRE_SOLICITUDES)
        registros = [r for r in listar_archivos(sesion, reporte)
                     if dentro_de_ventana(r, desde, FECHA_CORTE)]

        # Control de cobertura: ¿falta algún mes en el portal?
        disponibles = {(r["anio"], r["mes"]) for r in registros}
        for anio, mes in meses_esperados(desde, FECHA_CORTE):
            if (anio, mes) not in disponibles:
                faltantes.append(f"{reporte} {anio}-{mes:02d}")

        carpeta_reporte = carpeta_destino / reporte
        carpeta_reporte.mkdir(parents=True, exist_ok=True)

        for registro in registros:
            ruta_local = carpeta_reporte / registro["archivo"]
            fila = {**registro, "nombre_reporte": nombre_corto,
                    "ruta_local": ruta_local.relative_to(RAIZ).as_posix()}

            if ruta_local.exists() and not modo_demo:
                contenido = ruta_local.read_bytes()
                anterior = previo.get(registro["archivo"], {})
                fila.update(http=anterior.get("http") or "ya descargado", bytes=len(contenido),
                            sha256=hashlib.sha256(contenido).hexdigest(),
                            descargado_en=anterior.get("descargado_en", ""))
                inventario.append(fila)
                continue

            time.sleep(PAUSA_ENTRE_SOLICITUDES)
            try:
                respuesta = pedir(sesion, registro["url"])
                ruta_local.write_bytes(respuesta.content)   # archivo original, sin cambios
                fila.update(http=respuesta.status_code, bytes=len(respuesta.content),
                            sha256=hashlib.sha256(respuesta.content).hexdigest(),
                            descargado_en=f"{datetime.now():%Y-%m-%d %H:%M:%S}")
                anotar(f"{registro['archivo']}: HTTP {respuesta.status_code} · {len(respuesta.content):,} bytes")
            except RuntimeError as error:
                errores += 1
                fila.update(http="error", bytes=0, sha256="", descargado_en="")
                anotar(f"{registro['archivo']}: ERROR · {error}")
            inventario.append(fila)

    # Inventario de descargas: evidencia de qué se descargó, cuándo y con qué hash
    tabla = pd.DataFrame(inventario)
    tabla.to_csv(archivo_inventario, index=False, encoding="utf-8")
    anotar(f"Inventario guardado: {archivo_inventario.relative_to(RAIZ).as_posix()} · {len(tabla)} archivos")

    if not tabla.empty:
        anotar(f"Archivos por reporte: {tabla.groupby('reporte').size().to_dict()}")
    if faltantes:
        anotar(f"Meses no publicados en el portal: {faltantes}")

    # 5. Lectura de los archivos descargados -> CSV crudo en formato largo
    if modo_demo:
        archivo_cifras = CARPETA_CRUDOS / f"sbs_demo_cifras_{CODIGO_MATRICULA}.csv"
    else:
        archivo_cifras = CARPETA_CRUDOS / f"datos_crudos_sbs_{CODIGO_MATRICULA}.csv"
    errores += extraer_cifras(carpeta_destino, archivo_cifras)

    if errores:
        anotar(f"Extracción INCOMPLETA: {errores} archivos con error. Volver a ejecutar para reintentar solo esos.")
        return 1
    anotar("Extracción SBS terminada sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
