"""Instantanea de evidencia ontologica para un tema (replica el esquema
de ontologia_{salud,edu,marginacion}.json): 3 pares de consultas
(conteo + exportacion paginada con orden determinista) via MCP o CLI.
Sin este snapshot, registrar_procedencia.py no puede vincular IRIs."""

import argparse
import json

from evidencia import DATA, ahora, guardar
from ontologia import Ontologia

# Conjuntos que alimentan los dashboards de seguridad (+ geometrias y
# vigilancia, usados por el mapa y la tabla long).
DATASETS_SEG = [
    "93ca5e1c-702e-4e62-bc61-638907be184a",  # Incidencia delictiva municipal
    "caf587a5-23ac-496b-85d4-6ceb1d615d78",  # Victimas fuero comun
    "923b485b-515e-4fb9-a4ac-cccbeb88cc92",  # Llamadas 911 procedentes
    "19e5036d-dbe3-4e1d-b021-df5d47b6fb1f",  # Llamadas 911 improcedentes
    "36c2016f-dd3d-4ac5-a746-cec4945f3cf0",  # Personas detenidas
    "4c1084b7-b038-4084-83b2-5fe042b09ffb",  # Personas desaparecidas
    "f58a3196-6874-4163-8161-730e5bffb244",  # Geometrias municipales
    "dca16d84-dbf0-4501-b702-dc6372a480ea",  # Vigilancia epidemiologica
]

PREF = ("PREFIX mex: <https://example.org/mex-ontologi/vocab/>\n"
        "PREFIX dct: <http://purl.org/dc/terms/>\n"
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n")


def valores(ids):
    return " ".join(f"<https://example.org/mex-ontologi/dataset/{i}>" for i in ids)


def consultas(ids):
    v = valores(ids)
    rec = (f"?dataset dct:title ?conjunto ; mex:recurso ?recurso . "
           f"?recurso dct:identifier ?recurso_id . "
           f"OPTIONAL {{ ?recurso mex:urlDeclarada ?url }}")
    sig = (f"?dataset dct:title ?conjunto ; mex:variableDocumentada ?variable_iri . "
           f"?variable_iri mex:nombreVariableLocal ?variable ; "
           f"mex:significadoDocumentado/skos:prefLabel ?significado . "
           f"OPTIONAL {{ ?variable_iri dct:description ?definicion }} "
           f"OPTIONAL {{ ?variable_iri mex:estadoSemantico ?estadoSemantico }} "
           f"OPTIONAL {{ ?variable_iri mex:definicionOriginal ?definicion_iri . "
           f"?diccionario_iri mex:definicionVariable ?definicion_iri . "
           f"OPTIONAL {{ ?diccionario_iri mex:urlDeclarada ?diccionario_url }} }}")
    col = (f"?dataset mex:recurso ?recurso . "
           f"?recurso (mex:esquemaArchivo|mex:esquema) ?esquema . "
           f"?esquema mex:columna ?columna_iri . "
           f"?columna_iri mex:nombreCampo ?campo . "
           f"OPTIONAL {{ ?esquema mex:nombreHoja ?hoja }} "
           f"OPTIONAL {{ ?correspondencia mex:columnaOrigen ?columna_iri ; "
           f"mex:variableDestino ?variable_iri ; "
           f"mex:estadoCorrespondencia ?estadoCorrespondencia }}")
    return [
        ("recursos",
         f"SELECT (COUNT(*) AS ?n) WHERE {{ SELECT DISTINCT ?dataset ?conjunto ?recurso ?recurso_id ?url WHERE {{ VALUES ?dataset {{ {v} }} {rec} }} }} LIMIT 1",
         f"SELECT DISTINCT ?dataset ?conjunto ?recurso ?recurso_id ?url WHERE {{ VALUES ?dataset {{ {v} }} {rec} }} ORDER BY ?dataset ?recurso ?url LIMIT 500 OFFSET {{o}}"),
        ("significados",
         f"SELECT (COUNT(*) AS ?n) WHERE {{ SELECT DISTINCT ?dataset ?conjunto ?variable_iri ?variable ?significado ?definicion ?estadoSemantico ?definicion_iri ?diccionario_iri ?diccionario_url WHERE {{ VALUES ?dataset {{ {v} }} {sig} }} }} LIMIT 1",
         f"SELECT DISTINCT ?dataset ?conjunto ?variable_iri ?variable ?significado ?definicion ?estadoSemantico ?definicion_iri ?diccionario_iri ?diccionario_url WHERE {{ VALUES ?dataset {{ {v} }} {sig} }} ORDER BY ?dataset ?variable_iri ?significado ?diccionario_iri ?diccionario_url LIMIT 500 OFFSET {{o}}"),
        ("columnas",
         f"SELECT (COUNT(*) AS ?n) WHERE {{ SELECT DISTINCT ?dataset ?recurso ?esquema ?columna_iri ?campo ?hoja ?correspondencia ?variable_iri ?estadoCorrespondencia WHERE {{ VALUES ?dataset {{ {v} }} {col} }} }} LIMIT 1",
         f"SELECT DISTINCT ?dataset ?recurso ?esquema ?columna_iri ?campo ?hoja ?correspondencia ?variable_iri ?estadoCorrespondencia WHERE {{ VALUES ?dataset {{ {v} }} {col} }} ORDER BY ?dataset ?recurso ?columna_iri ?correspondencia LIMIT 500 OFFSET {{o}}"),
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tema", default="seg")
    p.add_argument("--transporte", choices=["mcp", "cli"], default="mcp")
    args = p.parse_args()
    ids = DATASETS_SEG
    out = {"tema": args.tema, "extraido_en_utc": ahora(),
           "transporte": args.transporte, "ontologia_manifest_sha256": None,
           "ontologia_generada_en_utc": None, "fecha_carga_ontologia": None,
           "huecos": ["Manifest del store no recalculado en esta extraccion.",
                      "Fecha de carga no documentada; generado_en_utc no acredita la carga."],
           "datasets_solicitados": [f"https://example.org/mex-ontologi/dataset/{i}" for i in ids],
           "parcial": False, "conteos_completos": {},
           "estado_mcp": None, "recursos": [], "significados": [],
           "columnas": [], "consultas": []}
    with Ontologia(transporte=args.transporte) as onto:
        if args.transporte == "mcp":
            out["estado_mcp"] = onto.call("onto_status")
        from evidencia import filas as dec
        for nombre, qcount, qfull in consultas(ids):
            total = None
            for intento, q in ((0, PREF + qcount),):
                out["consultas"].append(q)
                crudo = onto.query(q)
                fr = dec(crudo if isinstance(crudo, dict) else {"results": crudo})
                total = int(fr[0]["n"])
            out["conteos_completos"][nombre] = total
            out["consultas"].append(PREF + qfull.replace("{o}", "0"))
            rows, o = [], 0
            while True:
                crudo = onto.query(PREF + qfull.replace("{o}", str(o)))
                lote = dec(crudo)
                rows.extend(lote)
                if len(lote) < 500:
                    break
                o += 500
            out[nombre] = rows
            if len(rows) != total:
                out["huecos"].append(
                    f"{nombre}: conteo {total} != exportadas {len(rows)} (parcial).")
                out["parcial"] = True
    guardar(DATA / f"ontologia_{args.tema}.json", out)
    print(args.tema, {k: (len(v) if isinstance(v, list) else v)
                      for k, v in out.items()
                      if k in ("recursos", "significados", "columnas")},
          "parcial:" , out["parcial"])


if __name__ == "__main__":
    main()
