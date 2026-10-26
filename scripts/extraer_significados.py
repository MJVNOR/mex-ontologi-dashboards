"""Exporta significados respaldados y evidencia por MCP (CLI canónica opcional)."""
import argparse
import json
import pandas as pd
from ontologia import Ontologia, ONTO
from evidencia import DATA, ahora, filas, guardar, huella, recursos

PREFIX = """PREFIX mex: <{base}vocab/>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""


def paginar(client, prefix, pattern, variables, order, size=500):
    count = prefix + 'SELECT (COUNT(*) AS ?n) WHERE { SELECT DISTINCT ' + variables + ' WHERE { ' + pattern + ' } } LIMIT 1'
    total = int(filas(client.query(count))[0]['n'])
    result = []
    for offset in range(0, total, size):
        q = prefix + 'SELECT DISTINCT ' + variables + ' WHERE { ' + pattern + ' } ORDER BY ' + order + f' LIMIT {size} OFFSET {offset}'
        result.extend(filas(client.query(q)))
    if len(result) != total:
        raise RuntimeError('El grafo cambió durante la exportación; repetir sin publicar resultados parciales')
    return result, total


def exportar(tema, transporte):
    manifest_path = ONTO / 'reports/portal-carga.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    version = huella(manifest_path)
    base = manifest['base_iri']
    prefix = PREFIX.format(base=base)
    datasets = sorted({r['dataset_id'] for r in recursos(tema)})
    scope = 'VALUES ?dataset { ' + ' '.join('<' + base + 'dataset/' + d + '>' for d in datasets) + ' } '
    patterns = {
        'recursos': (scope + '?dataset dct:title ?conjunto ; mex:recurso ?recurso . ?recurso dct:identifier ?recurso_id . OPTIONAL { ?recurso mex:urlDeclarada ?url }',
                     '?dataset ?conjunto ?recurso ?recurso_id ?url', '?dataset ?recurso ?url'),
        'significados': (scope + '?dataset dct:title ?conjunto ; mex:variableDocumentada ?variable_iri . ?variable_iri mex:nombreVariableLocal ?variable ; mex:significadoDocumentado/skos:prefLabel ?significado . OPTIONAL { ?variable_iri dct:description ?definicion } OPTIONAL { ?variable_iri mex:estadoSemantico ?estadoSemantico } OPTIONAL { ?variable_iri mex:definicionOriginal ?definicion_iri . ?diccionario_iri mex:definicionVariable ?definicion_iri . OPTIONAL { ?diccionario_iri mex:urlDeclarada ?diccionario_url } }',
                     '?dataset ?conjunto ?variable_iri ?variable ?significado ?definicion ?estadoSemantico ?definicion_iri ?diccionario_iri ?diccionario_url', '?dataset ?variable_iri ?significado ?diccionario_iri ?diccionario_url'),
        'columnas': (scope + '?dataset mex:recurso ?recurso . ?recurso (mex:esquemaArchivo|mex:esquema) ?esquema . ?esquema mex:columna ?columna_iri . ?columna_iri mex:nombreCampo ?campo . OPTIONAL { ?esquema mex:nombreHoja ?hoja } OPTIONAL { ?correspondencia mex:columnaOrigen ?columna_iri ; mex:variableDestino ?variable_iri ; mex:estadoCorrespondencia ?estadoCorrespondencia }',
                     '?dataset ?recurso ?esquema ?columna_iri ?campo ?hoja ?correspondencia ?variable_iri ?estadoCorrespondencia', '?dataset ?recurso ?columna_iri ?correspondencia'),
    }
    snapshot = {'tema': tema, 'extraido_en_utc': ahora(), 'transporte': transporte,
                'ontologia_manifest_sha256': version, 'ontologia_generada_en_utc': manifest.get('generado_en_utc'),
                'fecha_carga_ontologia': manifest.get('cargado_en_utc'),
                'huecos': [] if manifest.get('cargado_en_utc') else ['Fecha de carga no documentada; generado_en_utc no acredita la carga.'],
                'datasets_solicitados': [base + 'dataset/' + d for d in datasets],
                'parcial': False, 'conteos_completos': {}}
    with Ontologia(transporte) as client:
        if transporte == 'mcp':
            snapshot['estado_mcp'] = client.call('onto_status')
        for name, (pattern, variables, order) in patterns.items():
            snapshot[name], snapshot['conteos_completos'][name] = paginar(client, prefix, pattern, variables, order)
        snapshot['consultas'] = client.consultas
    if huella(manifest_path) != version:
        raise RuntimeError('Cambió la versión de ontología durante la extracción')
    found = {r['dataset'] for r in snapshot['recursos']}
    missing = set(snapshot['datasets_solicitados']) - found
    if missing:
        raise RuntimeError('Conjuntos solicitados no recuperados en consulta completa: ' + str(missing))
    rows = snapshot['significados']
    for row in rows:
        row['fecha_carga_ontologia'] = snapshot['fecha_carga_ontologia']
        row['extraido_en_utc'] = snapshot['extraido_en_utc']
    columns = ['conjunto','variable','significado','definicion','dataset','variable_iri','estadoSemantico','definicion_iri','diccionario_iri','diccionario_url','fecha_carga_ontologia','extraido_en_utc']
    df = pd.DataFrame(rows).reindex(columns=columns).sort_values(['conjunto','variable','variable_iri'])
    # Las correspondencias permanecen en el snapshot, separadas del significado.
    df.to_csv(DATA / f'significados_{tema}.csv', index=False, encoding='utf-8')
    guardar(DATA / f'ontologia_{tema}.json', snapshot)
    print(tema, snapshot['conteos_completos'], 'huecos:', snapshot['huecos'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tema', choices=['salud', 'edu', 'marginacion', 'poblacion', 'todos'], default='todos')
    p.add_argument('--transporte', choices=['mcp', 'cli'], default='mcp')
    a = p.parse_args()
    temas = ['salud', 'edu', 'marginacion', 'poblacion'] if a.tema == 'todos' else [a.tema]
    for tema in temas:
        exportar(tema, a.transporte)


if __name__ == '__main__':
    main()
