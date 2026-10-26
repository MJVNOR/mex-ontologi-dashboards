"""Filtra Hermosillo de los 7 XLSX de salud y genera parquet + resumen.

Criterio municipal (columna D = nombre descriptivo, segun ontologia
mex-ontologi "Referencia municipal" / "Municipio de residencia"):
- urgencias/egresos: Mun_Nombre == HERMOSILLO
- consulta externa: Nomb_Mpo == HERMOSILLO
- nacimientos: MUNICIPIORESIDENCIAD == HERMOSILLO
- defunciones: MUNICIPIORESIDENCIAD == HERMOSILLO
- vigilancia: des_munici == Hermosillo
- inspecciones: MUNICIPIO == HERMOSILLO
"""

import json
from pathlib import Path

import pandas as pd
from registrar_procedencia import registrar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def year_col(df):
    for c in df.columns:
        s = str(c).lower()
        if s in ("año", "a?o") or (s.startswith("a") and s.endswith("o") and len(s) <= 4):
            return c
    return None


def main():
    out = {}
    # 1. Urgencias / egresos / consulta externa (agregados por establecimiento)
    u = pd.read_excel(DATA / "urgencias_2018_2022.xlsx", sheet_name=0)
    yc = year_col(u)
    uh = u[u["Mun_Nombre"].astype(str).str.upper() == "HERMOSILLO"]
    uh.to_parquet(DATA / "hmo_urgencias.parquet", index=False)
    out["urgencias_hmo"] = {"filas": len(uh), "total": int(uh["Total_Urgencias"].sum()),
                            "anio_col": str(yc),
                            "por_anio": uh.groupby(yc)["Total_Urgencias"].sum().astype(int).to_dict(),
                            "por_sexo": uh.groupby("Sexo")["Total_Urgencias"].sum().astype(int).to_dict()}

    e = pd.read_excel(DATA / "egresos_2018_2022.xlsx", sheet_name=0)
    yc = year_col(e)
    eh = e[e["Mun_Nombre"].astype(str).str.upper() == "HERMOSILLO"]
    eh.to_parquet(DATA / "hmo_egresos.parquet", index=False)
    out["egresos_hmo"] = {"filas": len(eh), "total": int(eh["Total_Egresos"].sum()),
                          "por_anio": eh.groupby(yc)["Total_Egresos"].sum().astype(int).to_dict(),
                          "por_sexo": eh.groupby("Sexo")["Total_Egresos"].sum().astype(int).to_dict()}

    c = pd.read_excel(DATA / "consulta_externa_2018_2022.xlsx", sheet_name=0)
    ch = c[c["Nomb_Mpo"].astype(str).str.upper() == "HERMOSILLO"]
    ch.to_parquet(DATA / "hmo_consulta.parquet", index=False)
    out["consulta_hmo"] = {"filas": len(ch), "total": int(ch["Total"].sum()),
                           "por_anio": ch.groupby("Year")["Total"].sum().astype(int).to_dict(),
                           "por_sexo": ch.groupby("Sexo")["Total"].sum().astype(int).to_dict()}

    # 2. Nacimientos / defunciones (registro individual)
    n = pd.read_excel(DATA / "nacimientos_2022.xlsx", sheet_name=0)
    nh = n[n["MUNICIPIORESIDENCIAD"].astype(str).str.upper() == "HERMOSILLO"]
    nh.to_parquet(DATA / "hmo_nacimientos.parquet", index=False)
    out["nacimientos_hmo_residencia"] = {"filas": len(nh)}

    d = pd.read_excel(DATA / "defunciones_2022.xlsx", sheet_name=0)
    dh = d[d["MUNICIPIORESIDENCIAD"].astype(str).str.upper() == "HERMOSILLO"]
    dh.to_parquet(DATA / "hmo_defunciones.parquet", index=False)
    out["defunciones_hmo_residencia"] = {"filas": len(dh)}

    # 3. Vigilancia epidemiologica (casos por diagnostico/semana)
    v = pd.read_excel(DATA / "vigilancia_2022.xlsx", sheet_name=0)
    vh = v[v["des_munici"].astype(str).str.upper() == "HERMOSILLO"]
    vh.to_parquet(DATA / "hmo_vigilancia.parquet", index=False)
    out["vigilancia_hmo"] = {"filas": len(vh), "casos": int(vh["acumulado"].sum())}

    # 4. Inspecciones PROAES
    i = pd.read_excel(DATA / "inspecciones_2021_t3.xlsx", sheet_name=0)
    ih = i[i["MUNICIPIO"].astype(str).str.upper() == "HERMOSILLO"]
    ih.to_parquet(DATA / "hmo_inspecciones.parquet", index=False)
    out["inspecciones_hmo"] = {"filas": len(ih)}

    (DATA / "resumen_hmo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar('salud')
    print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
