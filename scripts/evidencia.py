"""Serialización y normalización de evidencia; no abre archivos RDF."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from rdflib.util import from_n3

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def ahora():
    return datetime.now(timezone.utc).isoformat()


def huella(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def guardar(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    temp.replace(path)


def filas(payload):
    if payload.get('error'):
        raise RuntimeError(payload)
    raw = payload.get('resultados', payload.get('results'))
    if isinstance(raw, dict):
        return [{k: v['value'] for k, v in row.items()} for row in raw['bindings']]
    if raw is None:
        raise ValueError('Respuesta sin results/resultados')
    out = []
    for row in raw:
        decoded = {}
        for key, value in row.items():
            if isinstance(value, str) and value.startswith(('<', '"', '_:')):
                value = str(from_n3(value))
            decoded[key] = value
        out.append(decoded)
    return out


def recursos(tema):
    return json.loads((ROOT / 'config/recursos.json').read_text(encoding='utf-8'))[tema]
