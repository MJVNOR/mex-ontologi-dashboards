"""Extrae variable -> significado documentado de los 7 conjuntos de salud.

Lee el TTL portal-completo.ttl del repo MEX-Ontologi (la misma fuente que
sirve el MCP mex-ontologia) con rdflib y guarda data/significados_salud.csv.
Solo lectura; no escribe en la ontologia.
"""

import argparse
import os
from pathlib import Path

import pandas as pd
import rdflib

ONTOLOGIA_DIR = Path(os.environ.get(
    "MEX_ONTOLOGIA_DIR", r"C:\Users\marti\Documents\MEX-Ontologi"))
TTL = ONTOLOGIA_DIR / "data" / "portal" / "portal-completo.ttl"

SALUD = ["inspeccion", "urgencia", "egreso", "nacimient", "defunci",
         "consulta externa", "vigilancia"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--salida", default="significados_salud.csv")
    p.add_argument("--claves", default=",".join(SALUD))
    args = p.parse_args()
    claves = [k for k in args.claves.split(",") if k]
    g = rdflib.Graph()
    g.parse(TTL, format="turtle")
    q = """
    SELECT ?conjunto ?variable ?significado ?definicion WHERE {
      ?dataset <http://purl.org/dc/terms/title> ?conjunto .
      ?dataset <https://example.org/mex-ontologi/vocab/variableDocumentada> ?v .
      ?v <https://example.org/mex-ontologi/vocab/nombreVariableLocal> ?variable ;
         <https://example.org/mex-ontologi/vocab/significadoDocumentado>/<http://www.w3.org/2004/02/skos/core#prefLabel> ?significado ;
         <http://purl.org/dc/terms/description> ?definicion .
    }"""
    filas = [(str(c), str(v), str(s), str(d)) for c, v, s, d in g.query(q)
             if any(k in str(c).lower() for k in claves)]
    df = pd.DataFrame(filas, columns=["conjunto", "variable", "significado", "definicion"])
    df = df.sort_values(["conjunto", "variable"]).drop_duplicates()
    dest = Path(__file__).resolve().parents[1] / "data" / args.salida
    df.to_csv(dest, index=False, encoding="utf-8")
    print(len(df), "significados ->", dest)


if __name__ == "__main__":
    main()
