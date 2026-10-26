# Ajuste de consulta y procedencia

La preparación utiliza el MCP mex-ontologia; la alternativa explícita utiliza la
CLI canónica del repo de ontología. Se retiró la lectura directa de RDF y se
centralizaron las descargas en el helper CKAN autorizado.

Se regeneraron los datos desde las fuentes descargadas con fecha y huella. Los
15 Parquet son iguales a los de la revisión anterior en filas, columnas y valores.
Las dos apps pasan AppTest con la selección inicial y sin años seleccionados.
El detalle está en [verificacion.json](verificacion.json).

## Cambio del alcance documental

El filtro anterior de significados usaba fragmentos del título. Incluía
publicaciones distintas a las seleccionadas por los descargadores y omitía otras
que no coincidían con esos fragmentos, por ejemplo títulos acentuados.

Ahora el alcance es la selección explícita de conjuntos que contienen los
recursos de `config/recursos.json`, contrastada mediante consulta al grafo. Por eso
el CSV de Salud pasa de 230 a 212 filas, retirando 18 significados ajenos a esa
selección. Educación pasa de 124 a 115: se retiran 58 filas y se agregan 49 del
alcance seleccionado. Esto no cambia las cifras ni afirma que los significados
retirados sean inexistentes o incorrectos en sus conjuntos de origen.

Las listas completas de filas agregadas y retiradas están en `verificacion.json`.
Las IRI, URL de diccionario, estados y consultas están en
`../data/ontologia_salud.json` y `../data/ontologia_edu.json`. Los estados de
correspondencia permanecen separados de los estados semánticos.

## Hueco conservado

El manifiesto documenta una fecha de generación, pero no una fecha acreditada de
carga. Se conserva `fecha_carga_ontologia: null` y se muestra el aviso en las apps.
La fecha de extracción y la fecha de descarga se conservan como eventos distintos.

## Interpretación de los gráficos

Se retiraron atribuciones causales de variaciones, traducciones no documentadas
de códigos de periodo y expresiones que sugerían seguimiento de cohortes. La
suma de la columna `acumulado` se identifica por su operación y no se presenta
como incidencia semanal. Los cálculos numéricos existentes se conservaron.

## Dependencia del repo de ontología

Esta migración requiere también el lanzador compartido y la CLI actualizada de
MEX-Ontologi. Se verificaron seis clientes simultáneos en cada transporte: CLI,
MCP HTTP y MCP stdio, incluida una respuesta con acentos. El backend conserva el
modo persistente y solo anuncia las cinco herramientas autorizadas.
