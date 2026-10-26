# mex-ontologi-dashboards

Fábrica de dashboards construidos sobre la ontología **mex-ontologi**
(datos abiertos de Sonora, repo `MEX-Ontologi`, store portal con 322,495 triples
servido por el MCP `mex-ontologia`).

La ontología dice **qué conjuntos existen, qué significa cada variable, qué
archivos descargar y qué no está permitido afirmar** (sin cruces entre
conjuntos sin validación, sin inferir cobertura). Cada dashboard sigue ese
contrato: descubre por ontología, descarga la fuente, filtra, publica.

## Dashboards

| Dashboard | App | Fuente |
|---|---|---|
| Salud en Hermosillo | `dashboards/hermosillo-salud/app.py` — [ver en vivo](https://mjvnor-mex-ontologi-dashbo-dashboardshermosillo-saludapp-le2l94.streamlit.app/) | 7 conjuntos grupo Salud, 230 significados |
| Educación en Hermosillo | `dashboards/educacion-hermosillo/app.py` — [ver en vivo](https://mex-ontologi-dashboards-zqt8qvqfwwbacguuimtvwz.streamlit.app/) | Becas 2021-25 (filtro HMO) + UTH institucional, 124 significados |
| Seguridad en Sonora | `dashboards/seguridad-sonora/app.py` — [ver en vivo](https://mex-ontologi-dashboards-plduatjh2dn6pwcct3cwku.streamlit.app/) | Incidencia municipal 2015-25 + víctimas + 911 T1-T2 2026 + detenidas + desaparecidas + mapa 72 municipios, 107 significados |

## Crear un dashboard nuevo

1. Descubre conjuntos con el MCP o el TTL:
   `onto_query("SELECT ...")` / `scripts/extraer_significados.py`
   (`MEX_ONTOLOGIA_DIR` apunta al repo de la ontología).
2. Descarga los recursos que indique el inventario (`scripts/descargar_salud.py`
   como ejemplo; el portal exige `User-Agent`).
3. Filtra a tu población en `scripts/preprocesar_*.py` → `data/hmo_*.parquet`
   (los `*.xlsx` crudos están en `.gitignore`; se regeneran con el paso 2).
4. Crea `dashboards/<tema>/app.py` con Streamlit + Plotly.
5. Documenta conjuntos, filtros y totales en este README.

## Para qué sirven aquí la ontología y el MCP

El grafo de **mex-ontologi** guarda metadatos, estructuras y significados —
no las filas. Los números vienen de los archivos del portal; la ontología es
el mapa, el diccionario y el reglamento:

- **Descubrir:** de 89 conjuntos y 486 recursos, el grupo `Salud` (7 conjuntos)
  dice exactamente qué descargar, con IDs de dataset, recurso y nombre real
  de archivo.
- **Entender columnas:** `contenido-inspeccion.json` da hoja, columnas y
  método de encabezado por archivo, así se elige el filtro municipal
  (`Mun_Nombre`, `MUNICIPIORESIDENCIAD`, `des_munici`…) antes de abrir un Excel.
- **Significados:** 230 pares variable→significado documentado salen del
  `portal-completo.ttl` (la misma fuente que sirve el MCP) y alimentan la
  pestaña Ontología. Solo se usan significados respaldados, no candidatos.
- **Límites:** sin cruces entre conjuntos sin validación y sin inferir
  cobertura; por eso cada serie se reporta por separado como total declarado.

El **MCP `mex-ontologia`** (`opencode.json`, proceso local `serve` sobre el
store portal con 322,495 triples) expone ese grafo en vivo con `onto_query`,
`onto_stats`, `onto_status` y `onto_validate`: descubrir conjuntos y verificar
significados sin copiar archivos. Requiere el repo `MEX-Ontologi` en la ruta
de `cwd` y reiniciar la sesión tras cambiar la config.

## Desarrollo local

```powershell
uv sync
uv run python scripts/descargar_salud.py
uv run python scripts/extraer_significados.py
uv run python scripts/preprocesar_hmo.py
uv run streamlit run dashboards/hermosillo-salud/app.py
```

Requiere Python 3.12 y `uv`. El MCP `mex-ontologia` se registra en
`opencode.json` (apunta al repo `MEX-Ontologi`).

## Publicar en Streamlit Community Cloud

Una app por ruta de archivo principal dentro del mismo repo:

- **Main file path:** `dashboards/hermosillo-salud/app.py`
- Las dependencias salen de `requirements.txt`; los datos ya procesados
  (`data/*.parquet`, `*.csv`) viajan en el repo, sin descargar nada en la nube.
