"""Descarga recursos XLSX de educacion indicados por la ontologia mex-ontologi.

Origen de URLs: inventario + metadatos del repo MEX-Ontologi (grupo Educacion,
20 conjuntos). Solo lectura del portal; no modifica la ontologia.
UTH = Universidad Tecnologica de Hermosillo (sus archivos son institucionales,
radicada en Hermosillo); becas trae columna Municipio para filtrar.
"""

from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "edu"
DATA.mkdir(parents=True, exist_ok=True)
UA = "MEX-Ontologi/0.1 (resource download; contact via portal metadata)"
PORTAL = "https://datos.sonora.gob.mx"

# (dataset_id, titulo, [(resource_id, archivo)]) — archivo = nombre de descarga
RECURSOS = [
    ("e819466c-7282-46c5-84e9-65917dd8cc85", "Matriculas de Estudiantes", [
        ("58f2d5a6-0432-48f1-8a35-a5efcce78bac", "202209271427270-file.xlsx")]),
    ("e68332eb-2bac-460a-a9cf-c9945230de81", "Matriculas", [
        ("4af3e212-7253-4fc3-908d-1aec14dddb40", "matriculas-ciclo-2021-2022.xlsx")]),
    ("7acf8797-cf5b-4906-ab5a-20ef0f483eb4", "Indices de Reprobacion", [
        ("3ff37353-0d4d-4fb7-83bb-e4020d2e8265", "indices-enero-junio-2022.xlsx"),
        ("04f794bf-b691-49f8-ac53-6c0618e9f545", "indices-agosto-diciembre-2022.xlsx")]),
    ("8f60b63d-c3aa-4206-a9a9-01971095e984", "Reprobacion Remota", [
        ("16367baf-371b-4849-adb1-7eca68a9e3e1", "indices-agosto-diciembre-2022.xlsx")]),
    ("8862ad24-3b6f-4c4a-92cf-e473b9ba40c8", "Becas", [
        ("6bf4a438-3e70-482e-a06d-2bc624d38eed", "becas-autorizadas-2021.xlsx"),
        ("33150a6b-63be-41f1-a105-7c313a43c773", "becas-autorizadas-2022.xlsx"),
        ("cc0954ad-b812-436e-af4c-044c6bdfaa36", "becas-autorizadas-2023.xlsx"),
        ("55c09381-0eb9-44a2-ae6b-4af56e31f0f8", "becas-autorizadas-2024.xlsx"),
        ("8dac33ec-6b5f-4525-bd29-e1ce87920d68", "becas-autorizadas-2025.xlsx")]),
    ("e7a3d62f-4ace-479c-aa52-1c9e384dc429", "Titulados", [
        ("79362ac6-c6ad-4231-aa41-f23ab92d1ae1", "titulados-2022.xlsx"),
        ("492df0ef-58f7-4ae9-8651-fae4d2c14b00", "titulados-2023.xlsx"),
        ("2addc93b-50df-40ea-9d40-13720a624114", "titulados-2024.xlsx"),
        ("61f23932-497d-431a-9725-ba241038e99d", "titulados-2025.xlsx")]),
    ("85ee0e2b-ba05-4d9a-8177-cdbf0cb42f8f", "Egresados", [
        ("7422760b-8f99-4774-a436-c7d1f49c2cc0", "egresados-2022.xlsx"),
        ("3e3bed3e-db98-45a0-89b3-d07fb57cafe6", "egresados-2023.xlsx"),
        ("ae39974c-131d-48f1-bd25-b368d59db4b6", "egresados-2024.xlsx"),
        ("ad71c81a-01ac-40f2-821d-0b1efd06b487", "egresados-2025.xlsx")]),
    ("65bdde5d-7a7e-45a9-8524-ae43aecff879", "Nuevo ingreso", [
        ("e1dba4c6-d036-4eaf-8f93-73849909f795", "nuevo-ingreso-enero-abril-2022.xlsx"),
        ("94fa9a0a-9da2-4b1d-a3f2-f013f72c2f49", "nuevo-ingreso-septiembre-diciembre-2022.xlsx"),
        ("5907da53-1105-4568-af0a-2c3108b74ddf", "nuevo-ingreso-septiembre-diciembre-2023.xlsx")]),
    ("e465480c-18f7-4132-9daa-7abca8522c84", "Aprovechamiento", [
        ("ee73998a-cb5b-4599-92a7-317a296e336e", "aprovechamiento-academico-2021-2.xlsx")]),
    ("6cce2696-2194-408c-baae-ce9020a008d0", "Capacitacion", [
        ("d5b0ae09-b0bd-4352-b931-69a9c00001ef", "segundo-trimestre-2022-vii.17-icd-sec.xlsx")]),
]


def main():
    n = 0
    for ds_id, titulo, recs in RECURSOS:
        for res_id, dl in recs:
            u = f"{PORTAL}/dataset/{ds_id}/resource/{res_id}/download/{dl}"
            dest = DATA / f"{titulo.lower().replace(' ', '_')}_{dl}"
            if dest.exists():
                print(f"existe {dest.name}, se omite");
                continue
            print(f"descargando {titulo}/{dl} ...")
            req = Request(u, headers={"User-Agent": UA})
            with urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                f.write(r.read())
            n += 1
    print("OK, nuevos:", n)


if __name__ == "__main__":
    main()
