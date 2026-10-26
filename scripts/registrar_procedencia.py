"""Vincula cada Parquet con descargas verificadas, columnas y transformaciones."""
import argparse
import json
import subprocess
import pandas as pd
from evidencia import ROOT, DATA, ahora, guardar, huella


def registrar(tema):
    snapshot_path = DATA / f'ontologia_{tema}.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    downloads = {r['archivo']: r for r in json.loads((DATA / f'descargas_{tema}.json').read_text(encoding='utf-8'))}
    specs = json.loads((ROOT / 'config/artefactos.json').read_text(encoding='utf-8'))
    script = ROOT / 'scripts' / ('preprocesar_hmo.py' if tema == 'salud' else 'preprocesar_edu.py')
    result = {'tema': tema, 'generado_en_utc': ahora(), 'ontologia': {
        k: snapshot.get(k) for k in ('extraido_en_utc','fecha_carga_ontologia', 'ontologia_generada_en_utc', 'ontologia_manifest_sha256','transporte','parcial','conteos_completos','huecos')},
        'snapshot_sha256': huella(snapshot_path), 'preprocesador': script.name,
        'preprocesador_sha256': huella(script), 'artefactos': {}}
    for name, spec in specs.items():
        if spec['tema'] != tema:
            continue
        source_rows, resource_iris = [], set()
        for source in spec['fuentes']:
            record = downloads[source['archivo']]
            if huella(DATA / source['archivo']) != record['sha256']:
                raise RuntimeError('Fuente modificada sin registrar: ' + source['archivo'])
            if record['ontologia_snapshot_sha256'] != result['snapshot_sha256']:
                raise RuntimeError('Descargas y ontología pertenecen a exportaciones distintas; reejecutar descarga')
            source_rows.append({**record, 'hoja_utilizada': source['hoja']})
            resource_iris.add(record['recurso'])
        frame = pd.read_parquet(DATA / name)
        columns = [c for c in snapshot['columnas'] if c['recurso'] in resource_iris]
        documented = [v for v in snapshot['significados'] if v['dataset'] in {r['dataset'] for r in source_rows}]
        gaps = list(snapshot['huecos'])
        if not columns:
            gaps.append('Columnas no recuperadas en el alcance completo consultado.')
        if any(not v.get('diccionario_url') for v in documented) or not documented:
            gaps.append('Faltan diccionarios o significados documentados para parte del alcance.')
        result['artefactos'][name] = {**spec, 'sha256': huella(DATA / name), 'filas': len(frame),
            'columnas_salida': list(frame.columns), 'fuentes': source_rows,
            'columnas_ontologia': columns, 'significados_documentados': documented,
            'huecos': gaps, 'nota_correspondencias': 'Una candidata_por_nombre no acredita el significado de la columna ni autoriza cruces.'}
    guardar(DATA / f'procedencia_{tema}.json', result)
    print(tema, len(result['artefactos']), 'artefactos con procedencia')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tema', choices=['salud','edu'], required=True)
    registrar(p.parse_args().tema)
