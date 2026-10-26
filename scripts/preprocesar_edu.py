"""Filtra Hermosillo / UTH de los XLSX de educacion y genera parquet + resumen.

Becas trae Municipio (filtro HMO directo). Matriculas UTH trae Unidad Academica
y Municipio (Hermosillo = unidad Hermosillo / municipio HMO). Titulados,
egresados, nuevo ingreso, reprobacion, aprovechamiento y capacitacion son
institucionales UTH/SEC (radicados en Hermosillo), se reportan como tales.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EDU = ROOT / "data" / "edu"
OUT = ROOT / "data" / "edu_hmo"
OUT.mkdir(exist_ok=True)


def melt_sexo(df, anio, h, m):
    d = df.iloc[:, [0, 1, h, m]].copy()
    d.columns = ["nivel", "programa", "hombres", "mujeres"]
    d["anio"] = anio
    return d.melt(id_vars=["anio", "nivel", "programa"], value_vars=["hombres", "mujeres"],
                  var_name="sexo", value_name="n")


def main():
    out = {}
    # Becas 2021-2025 (con Municipio)
    b = pd.concat([
        pd.read_excel(EDU / f"becas_becas-autorizadas-{a}.xlsx", sheet_name=0).assign(anio=a)
        for a in (2021, 2022, 2023, 2024, 2025)], ignore_index=True)
    b.columns = ["ciclo", "convocatoria", "programa", "nivel", "escuela",
                 "clave", "municipio", "importe", "genero", "anio"]
    b["municipio"] = b["municipio"].astype(str).str.strip().str.upper()
    b["genero"] = b["genero"].astype(str).str.strip().str.upper()
    bh = b[b["municipio"] == "HERMOSILLO"]
    bh.to_parquet(OUT / "becas_hmo.parquet", index=False)
    out["becas_hmo"] = {"filas": len(bh), "importe": int(bh["importe"].sum()),
                        "por_anio": bh.groupby("anio").size().astype(int).to_dict(),
                        "por_nivel": bh.groupby("nivel").size().astype(int).to_dict()}

    # Matriculas UTH 2022-2 (Unidad Academica + Municipio)
    m = pd.read_excel(EDU / "matriculas_de_estudiantes_202209271427270-file.xlsx", sheet_name=0)
    m.columns = [str(c).strip() for c in m.columns]
    muni = [c for c in m.columns if "Municipio" in str(c)][0]
    uni = [c for c in m.columns if "Unidad" in str(c)][0]
    sexo = [c for c in m.columns if str(c).strip().lower() == "sexo"][0]
    mh = m[(m[uni].astype(str).str.strip().str.upper() == "HERMOSILLO") |
           (m[muni].astype(str).str.strip().str.upper().str.startswith("HERMOSILLO"))]
    mh.to_parquet(OUT / "matriculas_uth_hmo.parquet", index=False)
    out["matriculas_hmo"] = {"filas": len(mh),
                             "por_sexo": mh[sexo].value_counts().astype(int).to_dict()}

    # Titulados / egresados 2022-2025 por programa y sexo
    for nombre, patron, h, m_ in [
            ("titulados", "titulados-{}.xlsx", 3, 4),
            ("egresados", "egresados-{}.xlsx", 3, 4)]:
        hojas = {"2022": "2022", "2023": "2023", "2024": "2024", "2025": "2025"}
        t = pd.concat([melt_sexo(pd.read_excel(EDU / f"{nombre}_{patron.format(a)}",
                                              sheet_name=hojas[a]), a, h, m_)
                       for a in hojas], ignore_index=True)
        t.to_parquet(OUT / f"{nombre}_uth.parquet", index=False)
        out[nombre] = {"filas": len(t), "total": int(t["n"].sum()),
                       "por_anio": t.groupby("anio")["n"].sum().astype(int).to_dict()}

    # Nuevo ingreso (3 cortes)
    ni = pd.concat([
        melt_sexo(pd.read_excel(EDU / "nuevo_ingreso_nuevo-ingreso-enero-abril-2022.xlsx",
                                sheet_name="Ene 22"), "2022-1", 3, 2),
        melt_sexo(pd.read_excel(EDU / "nuevo_ingreso_nuevo-ingreso-septiembre-diciembre-2022.xlsx",
                                sheet_name="Sep 22"), "2022-2", 2, 3),
        melt_sexo(pd.read_excel(EDU / "nuevo_ingreso_nuevo-ingreso-septiembre-diciembre-2023.xlsx",
                                sheet_name="Sep 23"), "2023-2", 2, 3)], ignore_index=True)
    # ponytail: melt con columnas h/m por posicion segun cada archivo
    ni.to_parquet(OUT / "nuevo_ingreso_uth.parquet", index=False)
    out["nuevo_ingreso"] = {"filas": len(ni), "total": int(ni["n"].sum()),
                            "por_corte": ni.groupby("anio")["n"].sum().astype(int).to_dict()}

    # Reprobacion 2022 (presencial + remota)
    r1 = pd.read_excel(EDU / "indices_de_reprobacion_indices-enero-junio-2022.xlsx", sheet_name=0)
    r1.columns = [str(c).strip() for c in r1.columns]
    r2 = pd.read_excel(EDU / "indices_de_reprobacion_indices-agosto-diciembre-2022.xlsx", sheet_name=0)
    r2.columns = [str(c).strip() for c in r2.columns]
    rr = pd.read_excel(EDU / "reprobacion_remota_indices-agosto-diciembre-2022.xlsx", sheet_name=0)
    rr.columns = [str(c).strip() for c in rr.columns]
    idx = [c for c in r1.columns if "16VA" in c.upper() and "REPROB" in c.upper()][0]
    rep = pd.concat([r1.assign(corte="2022-1"), r2.assign(corte="2022-2"),
                     rr.assign(corte="2022-2-remota")], ignore_index=True)
    rep.to_parquet(OUT / "reprobacion_uth.parquet", index=False)
    out["reprobacion"] = {"filas": len(rep), "col_indice": idx}

    # Aprovechamiento + capacitacion directos
    ap = pd.read_excel(EDU / "aprovechamiento_aprovechamiento-academico-2021-2.xlsx", sheet_name=0)
    ap.to_parquet(OUT / "aprovechamiento_uth.parquet", index=False)
    out["aprovechamiento"] = {"filas": len(ap)}
    cap = pd.read_excel(EDU / "capacitacion_segundo-trimestre-2022-vii.17-icd-sec.xlsx", sheet_name=0)
    cap.to_parquet(OUT / "capacitacion_sec.parquet", index=False)
    out["capacitacion"] = {"filas": len(cap)}

    (OUT / "resumen_edu.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:1500])


if __name__ == "__main__":
    main()
