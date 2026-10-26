"""Compara los Parquet y modelos con una revisión Git y ejecuta las tres apps."""
import argparse
import hashlib
import io
import json
import subprocess
import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest
from evidencia import ROOT, DATA, ahora, guardar, huella


def verificar(base):
    reference = base
    base = subprocess.run(['git','rev-parse',base], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    report = {'verificado_en_utc': ahora(), 'referencia_base': reference,
              'revision_base': base, 'artefactos': {}, 'apps': {}}
    tracked = subprocess.run(['git', 'ls-tree', '-r', '--name-only', base, '--', 'data'],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    for path in tracked:
        if not path.endswith('.parquet'):
            continue
        name = path.removeprefix('data/')
        raw = subprocess.run(['git','show',base + ':data/' + name], cwd=ROOT, capture_output=True, check=True).stdout
        old, new = pd.read_parquet(io.BytesIO(raw)), pd.read_parquet(DATA / name)
        item = {'filas_anteriores': len(old), 'filas_actuales': len(new)}
        try:
            assert_frame_equal(old, new, check_dtype=False)
            item['iguales'] = True
        except AssertionError as exc:
            item.update(iguales=False, diferencia=str(exc)[:1800])
        report['artefactos'][name] = item
    report['modelos_y_seguridad'] = {}
    for path in tracked:
        if not (path.startswith('data/modelos/') or path in
                ('data/significados_seg.csv', 'data/seg/municipios.json', 'data/seg/resumen_seg.json')):
            continue
        raw = subprocess.run(['git', 'show', base + ':' + path], cwd=ROOT,
                             capture_output=True, check=True).stdout
        current = (ROOT / path).read_bytes()
        if path.endswith(('.json', '.csv')):
            # Git normaliza LF; Windows puede materializar los mismos textos con CRLF.
            raw = raw.replace(b'\r\n', b'\n')
            current = current.replace(b'\r\n', b'\n')
        report['modelos_y_seguridad'][path] = hashlib.sha256(current).hexdigest() == hashlib.sha256(raw).hexdigest()
    for tema in ('salud','edu'):
        snap = json.loads((DATA / f'ontologia_{tema}.json').read_text(encoding='utf-8'))
        report[tema] = {'conteos': snap['conteos_completos'], 'parcial': snap['parcial'], 'huecos': snap['huecos']}
        old_csv = subprocess.run(['git','show',base + f':data/significados_{tema}.csv'], cwd=ROOT, capture_output=True, check=True).stdout
        before = pd.read_csv(io.BytesIO(old_csv)).fillna('')
        after = pd.read_csv(DATA / f'significados_{tema}.csv').fillna('')
        cols = ['conjunto','variable','significado','definicion']
        left = set(map(tuple, before[cols].values.tolist()))
        right = set(map(tuple, after[cols].values.tolist()))
        report[tema]['significados_anteriores'] = len(before)
        report[tema]['significados_actuales'] = len(after)
        report[tema]['significados_retirados'] = [list(v) for v in sorted(left-right)]
        report[tema]['significados_agregados'] = [list(v) for v in sorted(right-left)]
        provenance = json.loads((DATA / f'procedencia_{tema}.json').read_text(encoding='utf-8'))
        report[tema]['procedencia_coherente'] = (
            not snap['parcial'] and provenance['snapshot_sha256'] == huella(DATA / f'ontologia_{tema}.json')
            and provenance['preprocesador_sha256'] == huella(ROOT / 'scripts' / provenance['preprocesador'])
            and all(artifact['sha256'] == huella(DATA / name)
                    for name, artifact in provenance['artefactos'].items()))
    for folder in ('hermosillo-salud','educacion-hermosillo','seguridad-sonora'):
        app = AppTest.from_file(str(ROOT / 'dashboards' / folder / 'app.py')).run(timeout=90)
        errors = [str(e.value) for e in app.exception]
        report['apps'][folder] = {'errores': errors, 'metricas': [m.value for m in app.metric]}
        if not errors:
            app.sidebar.multiselect[0].set_value([]).run(timeout=90)
            report['apps'][folder]['errores_sin_seleccion'] = [str(e.value) for e in app.exception]
    report['ok'] = (all(v['iguales'] for v in report['artefactos'].values())
        and all(report['modelos_y_seguridad'].values())
        and all(report[tema]['procedencia_coherente'] for tema in ('salud', 'edu')) and all(
        not v['errores'] and not v.get('errores_sin_seleccion') for v in report['apps'].values()))
    guardar(ROOT / 'reports/verificacion.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', default='origin/main')
    verificar(p.parse_args().base)
