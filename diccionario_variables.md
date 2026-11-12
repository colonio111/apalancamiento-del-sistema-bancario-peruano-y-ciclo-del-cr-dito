# Diccionario de variables

Archivo: `datos_procesados/datos_procesados_2024200495A.csv` · 1 800 filas (15 bancos × 120 meses) · 23 columnas.
Llave: **entidad + fecha**. Los montos están en **millones de soles corrientes**, salvo que se indique otra unidad.

| Variable | Descripción | Unidad | Fuente | Rango |
|---|---|---|---|---|
| `entidad` | Banco, con nombre armonizado (ver nota 1) | texto | SBS | 15 bancos |
| `fecha` | Mes de la observación | AAAA-MM | — | 2016-01 a 2025-12 |
| `anio` | Año | número | — | 2016–2025 |
| `mes` | Mes | 1 a 12 | — | 1–12 |
| `activo_total` | Total activo | millones de S/ | SBS, B-2201 | 353,87 – 202 161,92 |
| `pasivo_total` | Total pasivo | millones de S/ | SBS, B-2201 | 256,49 – 174 844,78 |
| `patrimonio` | Patrimonio contable | millones de S/ | SBS, B-2201 | 0,11 – 27 317,14 |
| `apalancamiento` | Activo total / patrimonio | veces | calculada | 2,93 – 5 379,99 |
| `apalancamiento_w` | Apalancamiento acotado a los percentiles 1 y 99 del panel (ver nota 2) | veces | calculada | 3,66 – 15,59 |
| `atipico_apalancamiento` | 1 si el apalancamiento está fuera de [Q1 − 3·RIC; Q3 + 3·RIC] | 0 / 1 | calculada | 14 casos |
| `activo_real` | Activo total / (IPC de Lima / 100) | millones de S/ de dic. 2021 | calculada | 413,71 – 199 435,32 |
| `creditos_directos` | Vigentes + refinanciados y reestructurados + atrasados | millones de S/ | calculada (SBS, B-2201) | 118,73 – 125 118,21 |
| `creditos_vigentes` | Créditos vigentes | millones de S/ | SBS, B-2201 | 114,22 – 118 636,11 |
| `creditos_refinanciados` | Créditos refinanciados y reestructurados | millones de S/ | SBS, B-2201 | 0 – 2 446,97 |
| `creditos_atrasados` | Créditos atrasados (vencidos y en cobranza judicial) | millones de S/ | SBS, B-2201 | 0 – 5 329,04 |
| `creditos_netos` | Créditos netos de provisiones y de ingresos no devengados | millones de S/ | SBS, B-2201 | 113,42 – 118 052,94 |
| `provisiones` | Provisiones para créditos (con signo negativo, como en el balance) | millones de S/ | SBS, B-2201 | −7 243,96 – −1,26 |
| `morosidad` | Créditos atrasados (criterio SBS) / créditos directos | % | SBS, B-2401 | 0 – 22,70 |
| `ratio_capital_global` | Patrimonio efectivo / activos ponderados por riesgo | % | SBS, B-2402 | 2,89 – 68,33 |
| `credito_privado` | Crédito de las sociedades creadoras de depósito al sector privado, tipo de cambio constante (PN00505MM) | millones de S/ | BCRP, API | 255 669,94 – 434 915,71 |
| `pbi_desestacionalizado` | PBI desestacionalizado (PN01773AM) | índice 2007 = 100 | BCRP, API | 104,36 – 194,00 |
| `tasa_referencia` | Tasa de referencia de la política monetaria (PD04722MM) | % | BCRP, API | 0,25 – 7,75 |
| `ipc_lima` | IPC de Lima Metropolitana (PN38705PM) | índice dic. 2021 = 100 | BCRP, API | 84,87 – 115,92 |

## Notas

1. **Armonización de nombres.** Los bancos que cambiaron de nombre en el periodo se tratan como una sola entidad: Banco Continental → BBVA Perú; Banco de Comercio → BANCOM; Banco Financiero → Banco Pichincha; Banco Azteca → Alfin Banco; Banco Interamericano de Finanzas → BanBif. El nombre original de cada archivo se conserva en `datos_crudos/datos_crudos_sbs_2024200495A.csv` (columna `entidad_sbs`).
2. **Valores atípicos.** Los 14 casos marcados corresponden a Alfin Banco entre 2021-08 y 2022-09, cuando su patrimonio cayó casi a cero antes de su recapitalización (ver `incidencias_fuente.md`). No se elimina ninguna observación: el análisis usa `apalancamiento_w` y, como prueba de robustez, `apalancamiento`.
3. Las brechas del crédito y del PBI (filtro de Hamilton) y las transformaciones logarítmicas se calculan en `04_analisis.py`, no en este archivo.
