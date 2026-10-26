import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evidencia import filas
from extraer_significados import paginar
from ontologia import Ontologia


class Contrato(unittest.TestCase):
    def test_rechaza_escritura_y_limites_invalidos_sin_conectar(self):
        client = Ontologia()
        for q in ('SELECT * WHERE {?s ?p ?o}', 'SELECT * WHERE {?s ?p ?o} LIMIT 2001',
                  'DELETE WHERE {?s ?p ?o} LIMIT 1', 'SELECT * WHERE {?s ?p ?o} LIMIT 0'):
            with self.assertRaises(ValueError):
                client.query(q)

    def test_formatos_de_respuesta(self):
        self.assertEqual(filas({'results':[{'a':'<https://example.org/a>', 'n':'"2"'}]}),
                         [{'a':'https://example.org/a','n':'2'}])
        self.assertEqual(filas({'results':{'bindings':[{'n':{'value':'2'}}]}}), [{'n':'2'}])
        with self.assertRaises(RuntimeError):
            filas({'error':'consulta fallida'})

    def test_paginas_completas_y_cambio_de_conteo(self):
        class Fake:
            def __init__(self, total):
                self.total = total
            def query(self, q):
                if 'COUNT' in q:
                    return {'resultados':[{'n':self.total}]}
                return {'resultados':[{'v':'a'}] if 'OFFSET 0' in q else [{'v':'b'}]}
        result, total = paginar(Fake(2), '', '?v ?p ?o', '?v', '?v', size=1)
        self.assertEqual((len(result),total),(2,2))
        class Changed(Fake):
            def query(self, q):
                return {'resultados':[{'n':2}]} if 'COUNT' in q else {'resultados':[]}
        with self.assertRaises(RuntimeError):
            paginar(Changed(2), '', '?v ?p ?o', '?v', '?v')


if __name__ == '__main__':
    unittest.main()
