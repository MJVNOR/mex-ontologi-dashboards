"""Descarga los recursos de seguridad indicados por la ontologia mex-ontologi.

Origen de URLs: inventario del repo MEX-Ontologi (equivale a lo que sirve el
MCP mex-ontologia: store portal con 322495 triples). Grupos:
- Incidencia delictiva municipal (11 CSV 2015-2025 + catalogo Cve->Municipio)
- Victimas del fuero comun (11 CSV 2015-2025)
- Llamadas 911 procedentes/improcedentes (2 XLSX c/u, trim. 2026)
- Personas detenidas (3 XLSX trim. 2026), desaparecidas (1 XLSX historico)
- Geometrias municipales (map.json, para el choropleth)

Crudos van a data/seg_raw/ (gitignored); solo parquet viaja en el repo.
"""

from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "seg_raw"
RAW.mkdir(parents=True, exist_ok=True)
UA = "MEX-Ontologi/0.1 (resource download; contact via portal metadata)"
PORTAL = "https://datos.sonora.gob.mx"

# (dataset_id, [(resource_id, archivo)]) — archivo = nombre real de descarga
RECURSOS = [
    ("93ca5e1c-702e-4e62-bc61-638907be184a", [  # Incidencia delictiva municipal
        ("2513ec12-4b23-4700-8eeb-9cfb634d5553", "2015.csv"),
        ("147ead58-f894-4b0d-9881-ab06368e4cc9", "2016.csv"),
        ("4e13a33e-4738-41ac-a0a4-3ac0afab9091", "2017.csv"),
        ("d18cac7c-60dd-45ce-8cba-d90dc9fb5a18", "2018.csv"),
        ("0794d04e-7779-4fb6-b2ad-94a927e49a64", "2019.csv"),
        ("70c0bfb7-5378-42db-a20c-95da9ce1a4e4", "2020.csv"),
        ("22d74901-c3ab-4d80-9f4f-b9e7da051ba8", "2021.csv"),
        ("fc4a46ba-5318-4cc9-aadc-aa578300af15", "2022.csv"),
        ("18b58aaf-e382-478e-86d9-8f50a7b08e12", "2023.csv"),
        ("fb66e0fa-21e5-4c11-9d9d-7b4f701ee044", "2024.csv"),
        ("befd1c5e-1222-4795-a866-d46cf602637b", "2025.csv"),
        ("36d3ac85-4327-41f5-9259-538a7723a0ae", "catalogo.xlsx"),
    ]),
    ("caf587a5-23ac-496b-85d4-6ceb1d615d78", [  # Victimas fuero comun
        ("4c1f984e-a6be-412b-b274-5af2d4ff55b1", "vict_2015.csv"),
        ("15650860-3a0b-461f-becb-658422e3a597", "vict_2016.csv"),
        ("c7ab7527-c2f5-44f2-a33e-6a368574f992", "vict_2017.csv"),
        ("1d7c90a8-d10b-4dbc-a16d-61e57164d80a", "vict_2018.csv"),
        ("e26eafbe-5d74-4882-af64-89e5bddbb46e", "vict_2019.csv"),
        ("652ca41a-5c9e-4d00-aa9a-f4d006b613fe", "vict_2020.csv"),
        ("1ec37796-0ad6-44b9-ba36-30bd4ae3d526", "vict_2021.csv"),
        ("8c2618f2-b317-41b0-b0d3-8020e735ffd7", "vict_2022.csv"),
        ("10d7cb8c-4058-4b9c-85f5-c25819d0f66b", "vict_2023.csv"),
        ("8f959438-7c12-419a-be1b-e0e4a52b0a26", "vict_2024.csv"),
        ("39ff0330-1959-4b92-914e-a48c691aff01", "vict_2025.csv"),
    ]),
    ("923b485b-515e-4fb9-a4ac-cccbeb88cc92", [  # 911 procedentes
        ("6ce17dd1-5716-44e9-bc5f-603c0925afe6",
         "llamadas-procedentes-911-primer-trimestre-2026.xlsx"),
        ("943e2919-6a8b-4776-ac4f-c3d6b02bb94e",
         "llamadas-procedentes-911-segundo-trimestre-2026.xlsx"),
    ]),
    ("19e5036d-dbe3-4e1d-b021-df5d47b6fb1f", [  # 911 improcedentes
        ("54285a13-3a2a-4e47-b0af-e855861f5347",
         "llamadas-improcedentes-911-primer-trimestre-2026.xlsx"),
        ("0df8592f-bb3d-466c-aec3-6cbc91253be0",
         "llamadas-improcedentes-911-segundo-trimestre-2026.xlsx"),
    ]),
    ("36c2016f-dd3d-4ac5-a746-cec4945f3cf0", [  # Detenidas
        ("e6e387f4-5e0b-41ac-8420-bea70a30d804",
         "personas-detenidas-primer-trimestre-2026.xlsx"),
        ("cc87ef60-6e55-4899-87ee-ee720b476faa",
         "personas-detenidas-segundo-trimestre-2026.xlsx"),
        ("14b97369-ebd8-43fb-b88f-dc451d0ee76c",
         "personas-detenidas-tercer-trimestre-2026.xlsx"),
    ]),
    ("4c1084b7-b038-4084-83b2-5fe042b09ffb", [  # Desaparecidas
        ("d71a0111-d548-4c05-841f-4f789c4bed76",
         "cbp-desapariciones-sonora.xlsx"),
    ]),
    ("f58a3196-6874-4163-8161-730e5bffb244", [  # Geometrias municipales
        ("d20d36c4-6406-4054-845c-43308b380b95", "map.json"),
    ]),
]


def main():
    n = 0
    for ds_id, recs in RECURSOS:
        for res_id, dl in recs:
            u = f"{PORTAL}/dataset/{ds_id}/resource/{res_id}/download/{dl}"
            dest = RAW / dl
            if dest.exists():
                print(f"existe {dl}, se omite")
                continue
            print(f"descargando {dl} ...")
            req = Request(u, headers={"User-Agent": UA})
            with urlopen(req, timeout=180) as r, open(dest, "wb") as f:
                f.write(r.read())
            n += 1
    print("OK, nuevos:", n, "en", RAW)


if __name__ == "__main__":
    main()
