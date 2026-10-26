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


def sin_duplicados(df, nombre, out, key):
    n0 = len(df)
    df = df.drop_duplicates()
    out[key] = int(n0 - len(df))
    if n0 != len(df):
        print(f"{nombre}: {n0 - len(df)} filas identicas retiradas (duplicado exacto de fuente)")
    return df


def main():
    out = {}
    dedup = {}
    # 1. Urgencias / egresos / consulta externa (agregados por establecimiento)
    u = pd.read_excel(DATA / "urgencias_2018_2022.xlsx", sheet_name=0)
    yc = year_col(u)
    uh = u[u["Mun_Nombre"].astype(str).str.upper() == "HERMOSILLO"]
    uh = sin_duplicados(uh, "urgencias", dedup, "urgencias_hmo")
    uh.to_parquet(DATA / "hmo_urgencias.parquet", index=False)
    out["urgencias_hmo"] = {"filas": len(uh), "total": int(uh["Total_Urgencias"].sum()),
                            "anio_col": str(yc),
                            "por_anio": uh.groupby(yc)["Total_Urgencias"].sum().astype(int).to_dict(),
                            "por_sexo": uh.groupby("Sexo")["Total_Urgencias"].sum().astype(int).to_dict()}

    e = pd.read_excel(DATA / "egresos_2018_2022.xlsx", sheet_name=0)
    yc = year_col(e)
    eh = e[e["Mun_Nombre"].astype(str).str.upper() == "HERMOSILLO"]
    eh = sin_duplicados(eh, "egresos", dedup, "egresos_hmo")
    eh.to_parquet(DATA / "hmo_egresos.parquet", index=False)
    out["egresos_hmo"] = {"filas": len(eh), "total": int(eh["Total_Egresos"].sum()),
                          "por_anio": eh.groupby(yc)["Total_Egresos"].sum().astype(int).to_dict(),
                          "por_sexo": eh.groupby("Sexo")["Total_Egresos"].sum().astype(int).to_dict()}

    c = pd.read_excel(DATA / "consulta_externa_2018_2022.xlsx", sheet_name=0)
    ch = c[c["Nomb_Mpo"].astype(str).str.upper() == "HERMOSILLO"]
    ch = sin_duplicados(ch, "consulta", dedup, "consulta_hmo")
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

    # 3b. Vigilancia en formato largo (tidy): una fila por
    # diagnostico x semana x dimension x categoria (x sexo donde aplica)
    edad = ["menores_1", "de01_a_04", "de05_a_09", "de10_a_14", "de15_a_19",
            "de20_a_24", "de25_a_44", "de45_a_49", "de50_a_59", "de60_a_64",
            "de65_y_mas", "se_ignoran"]
    edad_f = {"de65_y_mas": "de65_y_maf", "se_ignoran": "se_ignoraf"}
    edad_f = {b: edad_f.get(b, b + "f") for b in edad}
    inst = ["ssa", "imss_ord", "issste", "otras", "imss_sol", "d_if",
            "pemex", "sedena", "sedemar"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    base = ["des_diagno", "cve_diagno", "no_semana", "acumulado"]
    filas = []
    for _, r in vh.iterrows():
        for g in edad:
            filas.append((*[r[c] for c in base], "grupo_edad", g, "total", r[g], False))
            filas.append((*[r[c] for c in base], "grupo_edad", g, "mujeres", r[edad_f[g]], False))
            filas.append((*[r[c] for c in base], "grupo_edad", g, "hombres_derivado",
                          r[g] - r[edad_f[g]], True))
        for c in inst:
            filas.append((*[r[c] for c in base], "institucion", c, "total", r[c], False))
        for c in meses:
            filas.append((*[r[c] for c in base], "mes", c, "total", r[c], False))
    vl = pd.DataFrame(filas, columns=["diagnostico", "cve_diagno", "semana", "acumulado_ref",
                                      "dimension", "categoria", "sexo", "casos", "derivado"])
    vl.to_parquet(DATA / "vigilancia_long.parquet", index=False)
    out["vigilancia_long"] = {"filas": len(vl)}
    # verificacion: suma de grupos de edad == acumulado
    chk = vl[(vl.dimension == "grupo_edad") & (vl.sexo == "total")]
    dif = (chk.groupby(["diagnostico", "semana"])["casos"].sum().reset_index())
    dif = dif.merge(vh[["des_diagno", "no_semana", "acumulado"]].rename(
        columns={"des_diagno": "diagnostico", "no_semana": "semana"}),
        on=["diagnostico", "semana"], how="left")
    print("vigilancia: (diagnostico,semana) donde suma(edades) != acumulado:",
          int((dif["casos"] != dif["acumulado"]).sum()), "de", len(dif),
          "(desglose de edad parcial en la fuente; totalm+totalf siempre cuadra)")

    # 4. Inspecciones PROAES
    i = pd.read_excel(DATA / "inspecciones_2021_t3.xlsx", sheet_name=0)
    ih = i[i["MUNICIPIO"].astype(str).str.upper() == "HERMOSILLO"]
    ih.to_parquet(DATA / "hmo_inspecciones.parquet", index=False)
    out["inspecciones_hmo"] = {"filas": len(ih)}

    out["duplicados_exactos_retirados"] = dedup
    (DATA / "resumen_hmo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar('salud')
    print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
