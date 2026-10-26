"""Filtra Hermosillo / UTH de los XLSX de educacion y genera parquet + resumen.

Becas trae Municipio (filtro HMO directo). Matriculas UTH trae Unidad Academica
y Municipio (Hermosillo = unidad Hermosillo / municipio HMO). Titulados,
egresados, nuevo ingreso, reprobacion, aprovechamiento y capacitacion son
institucionales UTH/SEC (radicados en Hermosillo), se reportan como tales.
"""

import json
from pathlib import Path

import pandas as pd
from registrar_procedencia import registrar

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

    # Matriculas ciclo 2021-2022 tidy (la usaba el modelo leyendo el xlsx crudo)
    c21 = pd.read_excel(EDU / "matriculas_matriculas-ciclo-2021-2022.xlsx", sheet_name=0)
    c21.columns = ["programa", "semestre", "sexo", "prom_act", "prom_gral",
                   "creditos", "residencias", "seguro", "discapacidad"]
    c21.to_parquet(OUT / "matriculas_ciclo2122.parquet", index=False)
    out["matriculas_ciclo2122"] = {"filas": len(c21)}

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

    # Reprobacion tidy long (semanas como filas; remota homologada)
    def melt_rep(df, corte):
        def find(*keys):
            hits = [c for c in df.columns
                    if all(k in c.upper() for k in keys)]
            return hits[0] if hits else None
        prog, plan, tot = find("PROGRAMA"), find("PLAN"), find("TOTAL", "ALUMN")
        out = []
        for tag, sem in (("4TA", 4), ("8VA", 8), ("12VA", 12), ("16VA", 16)):
            idx_w, prm_w = find(tag, "REPROB"), find(tag, "PROM")
            if idx_w is None and prm_w is None:
                continue
            d = pd.DataFrame({
                "programa": df[prog] if prog else None,
                "materia": df["MATERIA"] if "MATERIA" in df.columns else None,
                "grupo": df["GRUPO"] if "GRUPO" in df.columns else None,
                "corte": corte, "semana": sem,
                "indice": (pd.to_numeric(df[idx_w], errors="coerce")
                           if idx_w else None),
                "promedio": (pd.to_numeric(df[prm_w], errors="coerce")
                             if prm_w else None),
                "total_alumnos": (pd.to_numeric(df[tot], errors="coerce")
                                  if tot else None),
                "plan": df[plan] if plan else None,
            })
            out.append(d)
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    repl = pd.concat([melt_rep(r1, "2022-1"), melt_rep(r2, "2022-2"),
                      melt_rep(rr, "2022-2-remota")], ignore_index=True)
    repl.to_parquet(OUT / "reprobacion_long.parquet", index=False)
    out["reprobacion_long"] = {"filas": len(repl)}

    # Aprovechamiento + capacitacion directos
    ap = pd.read_excel(EDU / "aprovechamiento_aprovechamiento-academico-2021-2.xlsx", sheet_name=0)
    ap.to_parquet(OUT / "aprovechamiento_uth.parquet", index=False)
    out["aprovechamiento"] = {"filas": len(ap)}
    # Aprovechamiento tidy long (rangos de calificacion como filas; NaN = 0 verificado)
    bandas = {"Menos de 7": "<7", "de 7 hasta 7.9": "7-7.9",
              "de 8 hasta 8.9": "8-8.9", "de 9 hasta 10": "9-10"}
    ua = [c for c in ap.columns if "dad" in c.lower()][0]
    pe = [c for c in ap.columns if "programa" in c.lower()][0]
    ev = [c for c in ap.columns if "evaluados" in c.lower()][0]
    pg = [c for c in ap.columns if "promedio" in c.lower() and "global" in c.lower()][0]
    apl = ap.melt(id_vars=[ua, pe, ev, pg], value_vars=list(bandas),
                  var_name="rango", value_name="n")
    apl["rango"] = apl["rango"].map(bandas)
    apl["n"] = apl["n"].fillna(0)
    apl = apl.rename(columns={ua: "unidad", pe: "programa", ev: "evaluados",
                              pg: "promedio_global"})
    apl.to_parquet(OUT / "aprovechamiento_long.parquet", index=False)
    out["aprovechamiento_long"] = {"filas": len(apl)}
    cap = pd.read_excel(EDU / "capacitacion_segundo-trimestre-2022-vii.17-icd-sec.xlsx", sheet_name=0)
    cap.to_parquet(OUT / "capacitacion_sec.parquet", index=False)
    out["capacitacion"] = {"filas": len(cap)}

    (OUT / "resumen_edu.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    registrar('edu')
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:1500])


if __name__ == "__main__":
    main()
