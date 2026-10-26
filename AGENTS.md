# Contrato de los dashboards

- Codex y OpenCode pueden preparar los dashboards. El grafo se consulta solo por
  MCP `mex-ontologia` (lanzador `MEX-Ontologi/scripts/servir_ontologia_mcp.py`,
  almacenamiento persistente compartido). Sin MCP, usar exclusivamente
  `uv run python scripts/consultar_ontologia.py` desde MEX-Ontologi.
- No abrir `.ttl` ni llamar directamente al ejecutable del motor.
- Solo lectura. Toda consulta libre requiere `LIMIT` de 1 a 2000. Para exportar,
  paginar con orden determinista y guardar conteo completo separado. Un resultado
  parcial se identifica como tal; no recuperar algo no demuestra que no existe.
- `estadoSemantico` pertenece a la variable documental; `estadoCorrespondencia`
  pertenece al enlace con la columna. Las candidatas son hipótesis. Ni siquiera
  una correspondencia documental revisada autoriza un join entre conjuntos.
- Los cruces se evalúan mediante `MEX-Ontologi/scripts/consultar_cruces.py`.
- Descargar CKAN únicamente mediante `MEX-Ontologi/scripts/descargar_ckan.py`;
  los coordinadores de este repo importan ese helper y conservan su User-Agent.
- Conservar IRI de conjunto/recurso/columna/variable, diccionario, fecha de carga,
  consulta y versión cuando estén disponibles. Señalar los huecos sin inventarlos.
  La fecha de generación del manifiesto no es fecha acreditada de carga.
- Cada artefacto tiene fuentes, huellas, hojas, filtros y transformaciones en
  `config/artefactos.json` y `data/procedencia_*.json`. Actualizar ambos al cambiar
  indicadores. No atribuir causalidad, cobertura o seguimiento de cohortes sin evidencia.
- El runtime publicado usa artefactos preparados; no requiere acceso al MCP.
- En OpenCode, usar Muse 1.3: `opencode-go/muse-spark-1.3-contributor`.
  Si falta cuota, informar y esperar indicación; no cambiar automáticamente.
