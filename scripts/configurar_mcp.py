"""Genera la configuración OpenCode con la ubicación local de MEX-Ontologi."""
import json
from evidencia import ROOT, guardar
from ontologia import ONTO


def main():
    if not (ONTO / 'scripts/servir_ontologia_mcp.py').exists():
        raise SystemExit('Define MEX_ONTOLOGIA_DIR con la ubicación del repo de ontología')
    path = ROOT / 'opencode.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    config.setdefault('mcp', {}).pop('servers', None)
    config['mcp']['mex-ontologia'] = {'type': 'local', 'enabled': True,
        'command': ['uv', 'run', '--directory', str(ONTO), 'python', 'scripts/servir_ontologia_mcp.py'],
        'environment': {'OPEN_ONTOLOGIES_STORAGE_MODE': 'persistent'}}
    guardar(path, config)
    print('Configurado MCP mex-ontologia en', ONTO)


if __name__ == '__main__':
    main()
