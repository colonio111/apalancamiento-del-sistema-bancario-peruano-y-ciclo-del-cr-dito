# Incidencias de las fuentes

Registro de las particularidades encontradas al extraer los datos y de cómo se resolvió cada una.

| N.º | Fuente | Incidencia | Solución |
|---|---|---|---|
| 1 | BCRP, API | Si se piden varias series en una sola consulta, la API las devuelve ordenadas por código y no en el orden solicitado. | Se pide una serie por consulta (`01_extraccion_api.py`). |
| 2 | SBS | Los reportes tienen extensión `.XLS`, pero algunos están en formato Excel antiguo (BIFF) y otros en formato moderno (xlsx). | Se leen con el motor `calamine` de pandas, que reconoce ambos formatos. Los archivos originales no se modifican. |
| 3 | SBS, B-2201 | La posición de las filas del balance cambia en una fila entre años. | Las filas se ubican por su etiqueta (p. ej. «TOTAL ACTIVO»), no por su número. |
| 4 | SBS | Cinco bancos cambiaron de nombre en el periodo y los nombres varían en mayúsculas, tildes, espacios y abreviaturas («B.» o «Banco»). | Armonización por fragmentos del nombre normalizado (lista `BANCOS` en `02_scraping_web.py`). Se conserva el nombre original. |
| 5 | SBS, B-2201 | El balance incluye columnas «con Sucursales en el Exterior» que repiten a un banco ya incluido (BCP, Interbank) y columnas de totales del sistema. | Se excluyen esas columnas y las de totales. |
| 6 | SBS, B-2401 y B-2402 | En estos reportes, el BCP (y en 2016 Scotiabank e Interbank) figura «con sucursales en el exterior», mientras que en el balance se toma solo la operación en el Perú. | Se mantiene, porque la morosidad y el ratio de capital global son porcentajes y la diferencia es mínima. Se declara como limitación. |
| 7 | SBS, B-2401 | El ratio de capital global de este reporte corresponde al mes anterior (p. ej. «al 30/11/2025» en el reporte de diciembre). | El ratio de capital global se toma del reporte B-2402, que corresponde al mismo mes. Del B-2401 solo se usa la morosidad. |
| 8 | SBS | Seis bancos no tienen los 120 meses porque entraron o salieron del sistema: Deutsche Bank (6 meses), Santander Consumer Bank (7), Compartamos Banco (12), Banco Cencosud (38), Banco BCI Perú (42) y Bank of China (66). | Se excluyen para obtener un panel balanceado de 15 bancos (1 800 observaciones). |
| 9 | SBS, Alfin Banco | Entre 2021-08 y 2022-09 su patrimonio cayó casi a cero (S/ 0,11 millones en noviembre de 2021), lo que lleva el apalancamiento a valores de hasta 5 380 veces. Es un episodio real, seguido de una recapitalización, y no un error de la fuente. | No se elimina. Se marca con `atipico_apalancamiento = 1` y se usa la versión acotada `apalancamiento_w`. |
| 10 | SBS | El servidor de archivos (`intranet2.sbs.gob.pe`) no publica `robots.txt` (HTTP 404). | Se trata como acceso permitido y se mantienen la pausa de 1,5 s y el User-Agent identificable. |
| 11 | BCRP, API | El filtro de Hamilton necesita 35 meses previos al primer mes con brecha. | Las series macro se descargan desde 2010-01 (pre-muestra); el panel de bancos sigue empezando en 2016-01. Nueva extracción del BCRP el 2026-11-12. |
| 12 | BCRP | El BCRP revisa ocasionalmente cifras pasadas (sobre todo del PBI), por lo que una descarga posterior puede cambiar algunos valores. | Se conserva la respuesta original de la API en `datos_crudos/` y el hash de los archivos procesados; cualquier diferencia futura se atribuye a revisiones de la fuente. |
| 13 | SBS, B-2402 | El ratio de capital global sube de forma discreta en enero de 2023 y el formato del reporte cambia (nuevas columnas de capital ordinario). | Coincide con las resoluciones de la SBS del 27/12/2022 (entre ellas la Res. SBS N.º 3952-2022) que adecuan el requerimiento de capital al estándar Basilea III, en el marco del D. L. N.º 1531. Se mantiene la serie y el cambio se discute en el artículo. |
