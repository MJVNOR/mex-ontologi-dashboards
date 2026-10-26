"""Descarga los 7 recursos XLSX de salud indicados por la ontologia mex-ontologi.

Origen de URLs: data/portal/inventario.json + data/catalogo/metadatos.json del
repo MEX-Ontologi (equivale a lo que sirve el MCP mex-ontologia: store portal
con 322495 triples). Solo lectura del portal; no modifica la ontologia.
"""

import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
UA = "MEX-Ontologi/0.1 (resource download; contact via portal metadata)"

# (dataset_id, dataset_titulo, resource_id, nombre_archivo)
RECURSOS = [
    ("318b9551-47a1-4e6b-a194-232ea5a08d43", "Atencion de Urgencias",
     "3bff8e8d-424e-4da3-878f-816a338e614e", "urgencias_2018_2022.xlsx"),
    ("8993c917-47d8-4304-8141-5f481fe04301", "Egresos Hospitalarios",
     "ad6f77b8-569d-4826-8ce0-3c6efddcb098", "egresos_2018_2022.xlsx"),
    ("940de7d8-73ec-4a08-8d26-b7cc97ff17bd", "Nacimientos",
     "46977217-9396-4f9c-bddb-6616e82530b4", "nacimientos_2022.xlsx"),
    ("cd3d6e34-3789-479e-9f2b-a717b8419f9c", "Defunciones",
     "6f39fc5d-e097-4954-8cd7-10e8f9dea541", "defunciones_2022.xlsx"),
    ("d96602ac-f274-4d54-8aea-3f33a21bdd33", "Consulta Externa",
     "c70eb3c5-d965-42a2-8c0e-1bf22b20a10c", "consulta_externa_2018_2022.xlsx"),
    ("dca16d84-dbf0-4501-b702-dc6372a480ea", "Vigilancia Epidemiologica",
     "1689b19c-b0dc-4e39-bf07-e3a2e684ef1a", "vigilancia_2022.xlsx"),
    ("0bc896bc-a3c0-4c5d-b44b-8031b343f854", "Inspecciones PROAES",
     "942b5034-7b68-458b-93ad-49f7eab9e638", "inspecciones_2021_t3.xlsx"),
]

PORTAL = "https://datos.sonora.gob.mx"


def url(dataset_id, resource_id, nombre):
    return f"{PORTAL}/dataset/{dataset_id}/resource/{resource_id}/download/{nombre}"


# Nombres reales de descarga observados en el inventario de la ontologia.
DOWNLOAD_NAMES = {
    "urgencias_2018_2022.xlsx": "202209261845420-file-1.xlsx",
    "egresos_2018_2022.xlsx": "202209261836370-file.xlsx",
    "nacimientos_2022.xlsx": "202209281437030-file.xlsx",
    "defunciones_2022.xlsx": "202209281428110-file.xlsx",
    "consulta_externa_2018_2022.xlsx": "202209261854200-file-1.xlsx",
    "vigilancia_2022.xlsx": "202209281339190-file.xlsx",
    "inspecciones_2021_t3.xlsx": "conjunto-de-datos-visitas-inspeccion-3er-trim-2021.xlsx",
}


def main():
    manifiesto = []
    for ds_id, titulo, res_id, archivo in RECURSOS:
        destino = DATA / archivo
        u = url(ds_id, res_id, DOWNLOAD_NAMES[archivo])
        if not destino.exists():
            print(f"descargando {titulo} ...")
            req = Request(u, headers={"User-Agent": UA})
            with urlopen(req, timeout=120) as r, open(destino, "wb") as f:
                f.write(r.read())
        else:
            print(f"existe {archivo}, se omite descarga")
        manifiesto.append({"dataset": titulo, "dataset_id": ds_id,
                           "resource_id": res_id, "url": u,
                           "archivo": archivo, "bytes": destino.stat().st_size})
    (DATA / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK:", len(manifiesto), "archivos en", DATA)


if __name__ == "__main__":
    main()
