# mex-ontologi-dashboards

## Fuente de los datos

**Los datos utilizados en estos dashboards provienen del [Portal de Datos Abiertos del Estado de Sonora](https://datos.sonora.gob.mx/).** Los valores se obtienen de los archivos publicados en ese portal por las dependencias y organizaciones responsables de cada conjunto.

La ontología **mex-ontologi** permite descubrir esas fuentes y consultar los significados y límites documentados de sus variables. Los filtros, agregaciones, visualizaciones y resultados de modelos elaborados en este repositorio son productos derivados de esas fuentes y deben conservar su procedencia y metodología.

## Propósito del proyecto

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
| Salud en Hermosillo | `dashboards/hermosillo-salud/app.py` — [ver en vivo](https://mjvnor-mex-ontologi-dashbo-dashboardshermosillo-saludapp-le2l94.streamlit.app/) | 7 conjuntos seleccionados, 212 significados documentados |
| Educación en Hermosillo | `dashboards/educacion-hermosillo/app.py` — [ver en vivo](https://mex-ontologi-dashboards-zqt8qvqfwwbacguuimtvwz.streamlit.app/) | Becas 2021-25 (filtro HMO) + UTH institucional + capacitación SEC, 115 significados documentados |
| Seguridad en Sonora | `dashboards/seguridad-sonora/app.py` — [ver en vivo](https://mex-ontologi-dashboards-plduatjh2dn6pwcct3cwku.streamlit.app/) | Incidencia municipal 2015-25 + víctimas + 911 T1-T2 2026 + detenidas + desaparecidas + mapa 72 municipios, 107 significados |

## Skills para análisis y dashboards

Codex y OpenCode cuentan con estas skills instaladas a nivel de usuario para
preparar y revisar los análisis de los dashboards:

| Skill | Uso | Fuente |
|---|---|---|
| `exploratory-data-analysis` | Explorar datos, faltantes y distribuciones antes del análisis. | [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/exploratory-data-analysis) |
| `validate-data` | Revisar cálculos, agregaciones, sesgos y respaldo de las conclusiones. | [Anthropic](https://github.com/anthropics/knowledge-work-plugins/tree/main/data/skills/validate-data) |
| `statistical-analysis` | Seleccionar métodos estadísticos e interpretar tendencias, correlaciones e incertidumbre. | [Anthropic](https://github.com/anthropics/knowledge-work-plugins/tree/main/data/skills/statistical-analysis) |
| `polars` | Preparar tablas y ejecutar filtros, transformaciones y agregaciones eficientes. | [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/polars) |
| `data-visualization` | Elegir gráficos adecuados y mejorar escalas, etiquetas, colores y accesibilidad con Plotly, matplotlib y seaborn. | [Anthropic](https://github.com/anthropics/knowledge-work-plugins/tree/main/data/skills/data-visualization) |

### Modelos predictivos y machine learning

También están disponibles las siguientes skills para incorporar modelos cuando
el análisis y la evidencia lo permitan:

| Skill | Uso | Fuente |
|---|---|---|
| `scikit-learn` | Entrenar y evaluar regresión, clasificación y agrupamiento mediante pipelines y validación cruzada. | [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/scikit-learn) |
| `statsmodels` | Ajustar modelos estadísticos y pronósticos temporales con diagnóstico e incertidumbre. | [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/statsmodels) |
| `shap` | Explicar y auditar la contribución de las variables a las predicciones, sin atribuir causalidad. | [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/shap) |

### Instalación para ambos agentes

```powershell
npx --yes skills add K-Dense-AI/scientific-agent-skills --skill exploratory-data-analysis polars --agent codex opencode --global --yes
npx --yes skills add anthropics/knowledge-work-plugins --skill validate-data statistical-analysis data-visualization --agent codex opencode --global --yes
npx --yes skills add K-Dense-AI/scientific-agent-skills --skill scikit-learn statsmodels shap --agent codex opencode --global --yes
```

Las skills aportan instrucciones y recursos para los agentes; las dependencias
de Python se instalan por separado y los modelos se entrenan o cargan según el
caso. No son requisitos del runtime publicado. Los modelos se evalúan con datos
reservados y los pronósticos respetan el orden temporal para evitar filtración
de información futura.

Su uso mantiene el contrato de la ontología: consultas por MCP o la CLI
canónica, evidencia trazable y evaluación de cruces mediante
`MEX-Ontologi/scripts/consultar_cruces.py`.

## Crear un dashboard nuevo

1. Descubre conjuntos mediante el MCP; si no está disponible, utiliza la CLI canónica de MEX-Ontologi:
   `onto_query("SELECT ...")` / `scripts/extraer_significados.py`
   (`MEX_ONTOLOGIA_DIR` apunta al repo de la ontología).
2. Descarga los recursos recuperados por consulta (`scripts/descargar_salud.py`
   como ejemplo). Los coordinadores de Salud y Educación utilizan el helper
   `MEX-Ontologi/scripts/descargar_ckan.py`, que conserva el `User-Agent` requerido.
3. Filtra a tu población en `scripts/preprocesar_*.py` → `data/hmo_*.parquet`
   (los `*.xlsx` crudos están en `.gitignore`; se regeneran con el paso 2).
4. Crea `dashboards/<tema>/app.py` con Streamlit + Plotly.
5. Documenta conjuntos, filtros y totales en este README y conserva fuentes,
   huellas y transformaciones en `config/artefactos.json` y `data/procedencia_*.json`.

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
- **Significados:** el extractor consulta los conjuntos seleccionados por sus
  identificadores, pagina con orden determinista y conserva el conteo completo.
  Salud y Educación publican los significados, sus IRI, diccionarios y estados
  en `data/significados_*.csv` y `data/ontologia_*.json`. Las correspondencias
  con columnas se conservan por separado; una candidata sigue siendo hipótesis.
- **Límites:** sin cruces entre conjuntos sin validación y sin inferir
  cobertura; por eso cada serie se reporta por separado como total declarado.

El **MCP `mex-ontologia`** (`opencode.json`) expone consultas de solo lectura
con `onto_query`, `onto_stats`, `onto_status`, `onto_validate` y `onto_shacl`.
El lanzador y la CLI de MEX-Ontologi comparten un backend persistente por almacén;
cada cliente tiene su propia sesión. Las consultas libres requieren `LIMIT`
entre 1 y 2000. No se leen archivos TTL ni se abre directamente el motor.

### Procedencia de Salud y Educación

`config/recursos.json` selecciona identificadores y nombres locales. Las URL y
las IRI proceden de consultas guardadas en `data/ontologia_*.json`.
`data/descargas_*.json` registra URL, fecha de descarga y SHA-256;
`config/artefactos.json` documenta hojas, filtros y agregaciones, y
`data/procedencia_*.json` vincula cada Parquet con sus fuentes y evidencia.
Ambos dashboards muestran esta información en «Fuentes y metodología».

La fecha de extracción, la fecha de generación y la fecha de carga son distintas.
Si la carga no está acreditada, se conserva `null` y se muestra el hueco.
El alcance de esta integración de procedencia es Salud y Educación; Seguridad
conserva sus artefactos y requiere su propia ampliación de evidencia.

## Desarrollo local

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
uv run streamlit run dashboards/hermosillo-salud/app.py
```

Requiere Python 3.12 y `uv`. MEX-Ontologi se busca como carpeta hermana;
para otra ubicación, define `MEX_ONTOLOGIA_DIR`. El configurador registra el MCP
en `opencode.json`. El extractor usa MCP por defecto; `--transporte cli` selecciona
explícitamente la CLI canónica. `--tema todos` exporta Salud y Educación.
El runtime publicado utiliza los artefactos preparados, sin conexión al MCP.

## Publicar en Streamlit Community Cloud

Una app por ruta de archivo principal dentro del mismo repo:

- **Main file path:** `dashboards/hermosillo-salud/app.py`
- Las dependencias salen de `requirements.txt`; los datos ya procesados
  (`data/*.parquet`, `*.csv`) viajan en el repo, sin descargar nada en la nube.
