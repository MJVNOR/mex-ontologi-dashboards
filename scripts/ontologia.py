"""Acceso de solo lectura: MCP stdio autorizado o CLI canónica explícita."""
import json
import os
import queue
import re
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTO = Path(os.environ.get('MEX_ONTOLOGIA_DIR', ROOT.parent / 'MEX-Ontologi')).resolve()


class Ontologia:
    def __init__(self, transporte='mcp'):
        self.transporte = transporte
        self.proc = None
        self.secuencia = 0
        self.consultas = []

    def __enter__(self):
        if self.transporte == 'mcp':
            import tempfile
            self.log = tempfile.TemporaryFile()
            self.proc = subprocess.Popen(
                ['uv', 'run', 'python', 'scripts/servir_ontologia_mcp.py'], cwd=ONTO,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'OPEN_ONTOLOGIES_STORAGE_MODE': 'persistent'})
            self.cola = queue.Queue()
            def leer():
                try:
                    for line in self.proc.stdout:
                        self.cola.put(line)
                finally:
                    self.cola.put(None)
            threading.Thread(target=leer, daemon=True).start()
            self.rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                                  'clientInfo': {'name': 'mex-dashboards', 'version': '0.2.0'}})
            self.enviar({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        return self

    def enviar(self, msg):
        self.proc.stdin.write(json.dumps(msg) + '\n')
        self.proc.stdin.flush()

    def rpc(self, method, params):
        self.secuencia += 1
        self.enviar({'jsonrpc': '2.0', 'id': self.secuencia, 'method': method, 'params': params})
        while True:
            try:
                line = self.cola.get(timeout=120)
            except queue.Empty:
                raise RuntimeError('MCP sin respuesta en 120 s; revisa el servidor o elige --transporte cli')
            if line is None:
                self.log.seek(0)
                raise RuntimeError('El servidor MCP terminó: ' + self.log.read().decode('utf-8', errors='replace'))
            msg = json.loads(line)
            if msg.get('id') != self.secuencia:
                continue
            if 'error' in msg:
                raise RuntimeError(msg['error'])
            return msg['result']

    def call(self, name, arguments=None):
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments or {}})
        if result.get('isError'):
            raise RuntimeError(result)
        if result.get('structuredContent'):
            return result['structuredContent']
        blocks = [c['text'] for c in result.get('content', []) if c.get('type') == 'text']
        value = json.loads('\n'.join(blocks))
        if isinstance(value, dict) and value.get('error'):
            raise RuntimeError(value)
        return value

    def query(self, q):
        from rdflib.plugins.sparql.parser import parseQuery
        try:
            parsed = parseQuery(q)[1]
        except Exception as exc:
            raise ValueError('SPARQL SELECT inválido') from exc
        if parsed.name != 'SelectQuery':
            raise ValueError('Solo SELECT acotado')
        limit = parsed['limitoffset']['limit'] if 'limitoffset' in parsed and 'limit' in parsed['limitoffset'] else None
        limits = [str(limit)] if limit is not None else []
        if not limits or any(not 0 < int(n) <= 2000 for n in limits):
            raise ValueError('Consulta requiere LIMIT entre 1 y 2000')
        if re.search(r'\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b', q, re.I):
            raise ValueError('Solo lectura')
        self.consultas.append(q)
        if self.transporte == 'mcp':
            return self.call('onto_query', {'query': q})
        p = subprocess.run(['uv', 'run', 'python', 'scripts/consultar_ontologia.py',
                            'sparql', q, '--limite', '2000'], cwd=ONTO,
                           capture_output=True, text=True, encoding='utf-8', check=True,
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        return json.loads(p.stdout)

    def __exit__(self, *args):
        if self.proc:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(self.proc.pid), '/T', '/F'], capture_output=True)
            self.log.close()
