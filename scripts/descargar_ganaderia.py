"""Descarga los recursos de ganadería indicados por la ontología mex-ontologi.

Origen de URLs: inventario del repo MEX-Ontologi (equivale a lo que sirve el
MCP mex-ontologia: store portal, 322495 triples). Grupos:
- Ganadería Sonora (cierre/avance de producción pecuaria, 19 XLSX 2006-2024;
  2013 sin URL en el portal —HTTP 500— y 2019 duplicado byte a byte del 2020)
- Censo Ganadero (3 XLSX 2022-2024)
- Subastas Ganaderas (1 XLSX 2007-2017 + 8 XLSX 2018-2025)

Crudos van a data/gan_raw/ (gitignored igual que seg_raw); solo parquet viaja.
Descarga exclusivamente mediante MEX-Ontologi/scripts/descargar_ckan.py
(helper autorizado, conserva User-Agent).
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "gan_raw"
RAW.mkdir(parents=True, exist_ok=True)

ONTO = ROOT.parent / "MEX-Ontologi"
spec = importlib.util.spec_from_file_location(
    "descargar_ckan", ONTO / "scripts" / "descargar_ckan.py")
ckan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ckan)

PORTAL = "https://datos.sonora.gob.mx"

# (dataset_id, [(resource_id, archivo)]) — archivo = nombre estable local
RECURSOS = [
    ("092f6ac2-2714-44b3-a18a-bdca7893bb73", [  # Ganadería Sonora
        ("53b157b9-ec39-4754-b6bf-457d370bc5c3", "diccionario_ganaderia.csv"),
        ("21d44f7d-7ccc-4958-8e66-de4e808ac5cf", "catalogo_ganaderia.xlsx"),
        ("eec8f940-e1bf-45c0-923f-f852670d4784", "ganaderia_2006.xlsx"),
        ("3c21fc24-a33f-41a6-addc-43854587be9c", "ganaderia_2007.xlsx"),
        ("6100b8c5-817b-409d-8ec3-139da67ce8ef", "ganaderia_2008.xlsx"),
        ("d3661707-beb1-4ea5-8bd5-c22ce50fed44", "ganaderia_2009.xlsx"),
        ("30c6e78f-b6d9-4842-9cb6-5d3d207958d1", "ganaderia_2010.xlsx"),
        ("8bdc561b-ad88-4860-ae88-c0cc44206995", "ganaderia_2011.xlsx"),
        ("b69e3632-2484-4aa3-a344-b6c1b6a93923", "ganaderia_2012.xlsx"),
        # 2013 (65efdb48-4072-41cd-a76a-22760e6b39d9): sin URL en el portal (HTTP 500)
        ("c7055978-7577-4b1a-af1a-7e9f124ceb35", "ganaderia_2014.xlsx"),
        ("b79aaf86-ed01-4e89-9fd9-e8f071a3bed4", "ganaderia_2015.xlsx"),
        ("e4024afc-3ee8-4f84-900c-098b184e64ca", "ganaderia_2016.xlsx"),
        ("0662440f-224a-4d53-8dad-746441053e03", "ganaderia_2017.xlsx"),
        ("360b50f3-e1c7-43d5-a5e6-5f765c46ec5a", "ganaderia_2018.xlsx"),
        # 2019 (46f87907-...): duplicado byte a byte del 2020 en la fuente; se omite
        ("2ee4b63f-e1ec-45c9-9e07-2505db5d56a0", "ganaderia_2020.xlsx"),
        ("5042b5e0-7c56-453b-8535-1fc479b4f867", "ganaderia_2021.xlsx"),
        ("148571ca-009e-4cc2-84ee-b38484ca8fc7", "ganaderia_2022.xlsx"),
        ("eeff82bb-bc52-4baf-88ee-1f87bbcc697b", "ganaderia_2023.xlsx"),
        ("1b0a300d-38f6-4d83-bb94-87e4d461b96b", "ganaderia_2024.xlsx"),
    ]),
    ("5a511ff8-6a45-4589-8ef3-22000d5676f4", [  # Censo Ganadero
        ("045da7ba-ee72-498a-9b7a-071176e2a4ea", "diccionario_censo.csv"),
        ("432af774-15d7-4218-9e5f-3c050871e4dd", "catalogo_censo.xlsx"),
        ("3ff505e2-bfce-463d-bfa8-6264c14f8c44", "censo_2022.xlsx"),
        ("3da02887-db6b-450b-9a47-705d016881d0", "censo_2023.xlsx"),
        ("170e3f6d-6315-47f3-9987-3a72facdb3a7", "censo_2024.xlsx"),
    ]),
    ("932de35b-e9d4-4acb-bd1e-d54c70f6f45e", [  # Subastas Ganaderas
        ("a4eb0b8b-d6c6-44b8-b00a-f5f45c1875a5", "diccionario_subastas.csv"),
        ("7af10971-2a92-4164-bfed-0f4378be0839", "catalogo_subastas.xlsx"),
        ("ca08d529-adc7-4cbd-98de-746c877538ba", "subastas_2007_2017.xlsx"),
        ("26340eec-b8e7-4a0c-a84d-b0b51ba0977f", "subastas_2018.xlsx"),
        ("dc1cd0da-2a31-4d46-b0c3-b2955350ca65", "subastas_2019.xlsx"),
        ("71212f37-7504-4cf3-ac19-dbda4b1c9ef4", "subastas_2020.xlsx"),
        ("22a8013c-9b59-4385-84df-617425822cea", "subastas_2021.xlsx"),
        ("5c37f4e0-c2ce-472f-b8ad-2705e2a04d6f", "subastas_2022.xlsx"),
        ("018638b3-ca66-47c6-a72f-fc606e455133", "subastas_2023.xlsx"),
        ("38b4d6ff-8292-4363-a631-fbea0b8ece9e", "subastas_2024.xlsx"),
        ("67a24301-5657-473d-8a90-eb2f7c8bd27f", "subastas_2025.xlsx"),
    ]),
]


def main():
    n = 0
    for ds_id, recs in RECURSOS:
        for res_id, dl in recs:
            dest = RAW / dl
            if dest.exists():
                print(f"existe {dl}, se omite")
                continue
            u = f"{PORTAL}/dataset/{ds_id}/resource/{res_id}/download/{dl}"
            print(f"descargando {dl} ...")
            try:
                ckan.descargar(u, dest)
            except Exception:
                # El nombre local es estable; el portal puede usar otro
                # nombre de archivo: se reintenta con la URL declarada.
                for r in ckan.recursos_dataset(ds_id):
                    if r["id"] == res_id:
                        ckan.descargar(r["url"], dest)
                        break
            n += 1
    print("OK, nuevos:", n, "en", RAW)


if __name__ == "__main__":
    main()
