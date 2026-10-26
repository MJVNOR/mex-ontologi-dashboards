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
| Salud en Hermosillo | `dashboards/hermosillo-salud/app.py` | 7 conjuntos grupo Salud, 230 significados |

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
