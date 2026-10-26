# mex-ontologi-dashboards

Dashboards de Salud y Educación elaborados a partir de consultas de solo lectura
a **mex-ontologi**. La ontología aporta fuentes, significados y límites; los
valores numéricos proceden de archivos publicados por el portal de Sonora.

| Dashboard | Archivo principal |
|---|---|
| Salud | `dashboards/hermosillo-salud/app.py` |
| Educación | `dashboards/educacion-hermosillo/app.py` |

## Preparar o actualizar los artefactos

Requiere Python 3.12, uv y el repo MEX-Ontologi con su almacén persistente cargado.
Por defecto se busca como carpeta hermana. Para otra ubicación, definir
`MEX_ONTOLOGIA_DIR` antes de ejecutar los comandos.

```powershell
uv sync
uv run python scripts/configurar_mcp.py
uv run python scripts/extraer_significados.py --tema todos
uv run python scripts/descargar_salud.py
uv run python scripts/descargar_edu.py
uv run python scripts/preprocesar_hmo.py
uv run python scripts/preprocesar_edu.py
uv run python -m unittest discover -s tests -v
uv run python scripts/verificar.py --base origin/main
```

El extractor utiliza **MCP por defecto**. Si el transporte MCP no está disponible,
`--transporte cli` invoca exclusivamente `MEX-Ontologi/scripts/consultar_ontologia.py`.
No hay lectura directa de TTL ni sustitución silenciosa del transporte.

Codex y OpenCode pueden realizar esta preparación: ambos deben respetar AGENTS.md.
`opencode.json` registra el MCP local; el configurador adapta su ruta a la máquina.
En OpenCode se mantiene Muse 1.3 (`opencode-go/muse-spark-1.3-contributor`).

## Consultas simultáneas

El lanzador de MEX-Ontologi mantiene un único backend persistente, accesible por
MCP HTTP en localhost y protegido con token local. Cada agente utiliza un proxy
stdio y una sesión independiente. También la CLI canónica comparte ese backend.
Así, abrir varios clientes no intenta abrir varias veces el mismo almacén.
Tras migrar desde el lanzador antiguo hay que reconectar una sola vez los clientes
que retenían el bloqueo. No se borra LOCK ni se copian almacenes en uso.

## Evidencia publicada

- `config/recursos.json`: selección explícita de identificadores y nombres locales.
  Las URL y las IRI se recuperan por consulta, no se construyen como evidencia.
- `data/ontologia_*.json`: consulta, versión, filas recuperadas, conteos completos,
  columnas, estados de correspondencia y significados documentados.
- `data/significados_*.csv`: significado documental con sus IRI y diccionario.
  Un significado respaldado no valida por sí solo su enlace con una columna.
- `data/descargas_*.json`: URL, URL final, fecha de descarga y SHA-256. Los
  coordinadores usan únicamente el helper `descargar_ckan.py` de MEX-Ontologi.
- `config/artefactos.json`: hojas, filtros y transformaciones por Parquet.
- `data/procedencia_*.json`: vincula cada resultado con fuentes verificadas,
  columnas, diccionarios, huellas y metodología. Se muestra en ambos dashboards.
- `reports/verificacion.json`: comparación de todos los Parquet y significados
  contra una revisión Git, y pruebas de ejecución de las dos apps.

La fecha de extracción, la generación del manifiesto de ontología y la fecha de
carga son conceptos distintos. Si la carga no está documentada, se conserva null
y se señala el hueco. Lo no recuperado no se presenta como inexistente.

Las candidatas por nombre son hipótesis. No se realizan nuevos cruces. Para
estudiarlos, usar `MEX-Ontologi/scripts/consultar_cruces.py`; una correspondencia
revisada tampoco constituye autorización para un join.

## Publicación y uso local

```powershell
uv run streamlit run dashboards/hermosillo-salud/app.py
uv run streamlit run dashboards/educacion-hermosillo/app.py
```

Streamlit Community Cloud usa una app por archivo principal y las dependencias
de `requirements.txt`. Publicar juntos los Parquet, CSV y JSON de evidencia.
Los Excel originales permanecen fuera de Git. El sitio publicado usa los
artefactos preparados y no necesita el MCP ni acceso al repo de ontología.

## Límites de interpretación

Las series describen registros publicados, sin presumir cobertura municipal o
anual completa, causas de cambios, ni seguimiento de las mismas personas entre
series. Los códigos de periodo sin definición documental se muestran sin
traducir. La columna `acumulado` de vigilancia se identifica por su nombre y su
operación; su suma no se presenta como incidencia semanal.
