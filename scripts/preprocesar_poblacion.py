"""Poblacion tidy desde proyecciones CONAPO/portal (tema poblacion).

Fuentes: grupos quinquenales (municipio x año x sexo x grupo) e indicadores
demograficos (totales y grandes grupos por municipio y año). Todo declarado por
la fuente; hombres_derivado = total - mujeres con marca. 60+ se solapa con
15-64 en la fuente: no se agregan grandes grupos entre si.
"""

import json
from pathlib import Path

import pandas as pd
from registrar_procedencia import registrar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
POB = DATA / "pob"
OUT = DATA / "tidy"
OUT.mkdir(exist_ok=True)


def main():
    out = {}
    q = pd.read_excel(POB / "grupos_quinquenales_son.xlsx", sheet_name=0)
    q.columns = [str(c).strip() for c in q.columns]
    acol = next(c for c in q.columns if c.startswith("A"))
    gcols = [c for c in q.columns if c.startswith("POB_")]
    q = q.rename(columns={acol: "anio", "NOM_MUN": "municipio", "CLAVE": "cve_mun",
                          "SEXO": "sexo"})
    q["municipio"] = q["municipio"].astype(str).str.strip().str.upper()
    q["sexo"] = q["sexo"].astype(str).str.strip().str.upper()
    gl = q.melt(id_vars=["cve_mun", "municipio", "anio", "sexo"],
                value_vars=gcols, var_name="grupo_edad", value_name="n")
    gl["grupo_edad"] = gl["grupo_edad"].str.replace("POB_", "", regex=False)
    gl.to_parquet(OUT / "pob_grupos.parquet", index=False)
    out["grupos"] = {"filas": len(gl), "municipios": int(gl["municipio"].nunique()),
                     "anios": [int(gl["anio"].min()), int(gl["anio"].max())]}
    tot = gl.groupby(["municipio", "anio", "sexo"], as_index=False)["n"].sum()
    tot.to_parquet(OUT / "pob_municipio_anio.parquet", index=False)
    out["municipio_anio"] = {"filas": len(tot)}

    d = pd.read_excel(POB / "indicadores_demograficos_son.xlsx", sheet_name=0)
    d.columns = [str(c).strip() for c in d.columns]
    d = d.rename(columns={"NOM_MUN": "municipio", "CLAVE": "cve_mun"})
    acol2 = next(c for c in d.columns if c == "AÑO" or (c.startswith("A") and len(c) <= 4))
    d = d.rename(columns={acol2: "anio"})
    d["municipio"] = d["municipio"].astype(str).str.strip().str.upper()
    triples = [("00_14", "MUJ_00_14", "HOM_00_14", "POB_00_14"),
               ("15_64", "MUJ_15_64", "HOM_15_64", "POB_15_64"),
               ("60_mas", "MUJ_60_MAS", "HOM_60_MAS", "POB_60_MAS")]
    filas = []
    for _, r in d.iterrows():
        for g, cm, chh, ct in triples:
            filas.append([r["cve_mun"], r["municipio"], r["anio"], g, "mujeres", r[cm], False])
            filas.append([r["cve_mun"], r["municipio"], r["anio"], g, "hombres", r[chh], False])
            filas.append([r["cve_mun"], r["municipio"], r["anio"], g, "total", r[ct], False])
    gg = pd.DataFrame(filas, columns=["cve_mun", "municipio", "anio", "grupo",
                                      "sexo", "n", "derivado"])
    gg.to_parquet(OUT / "pob_grandes_grupos.parquet", index=False)
    out["grandes_grupos"] = {"filas": len(gg), "nota": "60_mas se solapa con 15_64 en la fuente"}

    hmo = tot[(tot["municipio"] == "HERMOSILLO") & (tot["sexo"] == "TOTAL")]
    if hmo.empty:  # la fuente trae Hombres/Mujeres; total = suma
        h = tot[tot["municipio"] == "HERMOSILLO"].groupby("anio")["n"].sum()
        hmo = h.reset_index().rename(columns={"n": "n"})
        hmo["sexo"] = "TOTAL"
    hmo[["anio", "n"]].to_parquet(OUT / "pob_hermosillo_anual.parquet", index=False)
    out["hermosillo_anual"] = {"filas": len(hmo)}

    (DATA / "resumen_poblacion.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar("poblacion")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
