"""Coordina descargas exclusivamente mediante MEX-Ontologi/scripts/descargar_ckan.py."""
import argparse
import importlib.util
import json
from pathlib import Path
from evidencia import DATA, ahora, guardar, huella, recursos
from ontologia import ONTO


def descargar_tema(tema, actualizar=False):
    snapshot = json.loads((DATA / f'ontologia_{tema}.json').read_text(encoding='utf-8'))
    if snapshot['parcial']:
        raise RuntimeError('Se requiere un inventario completo')
    spec = importlib.util.spec_from_file_location('descargar_ckan', ONTO / 'scripts/descargar_ckan.py')
    ckan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ckan)
    path = DATA / f'descargas_{tema}.json'
    prev = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    old = {r['archivo']: r for r in prev}
    records = []
    for item in recursos(tema):
        matches = [r for r in snapshot['recursos'] if r['recurso_id'] == item['recurso_id']
                   and r['dataset'].endswith('/' + item['dataset_id'])]
        if len(matches) != 1 or not matches[0].get('url'):
            raise RuntimeError('Recurso sin URL inequívoca en la evidencia: ' + item['recurso_id'])
        resource = matches[0]
        dest = DATA / item['archivo']
        previous = old.get(item['archivo'])
        if not actualizar and dest.exists() and previous and previous['url'] == resource['url'] and previous['sha256'] == huella(dest):
            record = {**previous, **resource,
                      'ontologia_snapshot_sha256': huella(DATA / f'ontologia_{tema}.json')}
        else:
            # El helper autorizado conserva User-Agent y obtiene la URL final.
            temp = dest.with_suffix(dest.suffix + '.part')
            info = ckan.descargar(resource['url'], temp)
            temp.replace(dest)
            record = {**item, **resource, 'url_final': info['final'], 'bytes': info['bytes'],
                      'descargado_en_utc': ahora(), 'sha256': huella(dest),
                      'ontologia_snapshot_sha256': huella(DATA / f'ontologia_{tema}.json')}
        records.append(record)
        # Checkpoint: una descarga posterior fallida no pierde las ya verificadas.
        guardar(path, records)
        print(item['archivo'], record['sha256'][:12])
    return records


def main(tema=None):
    p = argparse.ArgumentParser(description=__doc__)
    if tema is None:
        p.add_argument('--tema', choices=['salud', 'edu', 'marginacion'], required=True)
    p.add_argument('--actualizar', action='store_true')
    args = p.parse_args()
    descargar_tema(tema or args.tema, args.actualizar)


if __name__ == '__main__':
    main()
