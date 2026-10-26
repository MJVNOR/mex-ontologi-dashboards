"""Tasas por 100 mil con denominadores de proyecciones (statsmodels/inferencia).

Mortalidad por grupo de edad y fecundidad por edad de la madre (Hermosillo 2022),
con IC95% Poisson exactos (chi2). Los denominadores vienen de data/tidy/pob_*.
No atribuye causalidad; son tasas observadas con incertidumbre de conteo.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "tidy"


def poisson_ic(k, alpha=0.05):
    k = np.asarray(k, dtype=float)
    lo = np.where(k == 0, 0.0, chi2.ppf(alpha / 2, 2 * k) / 2)
    hi = chi2.ppf(1 - alpha / 2, 2 * (k + 1)) / 2
    return lo, hi


def grupo_edad(edad):
    if pd.isna(edad):
        return None
    e = int(edad)
    if e < 1:
        return "00_04"
    for lo, hi, g in [(1, 4, "00_04"), (5, 9, "05_09"), (10, 14, "10_14"),
                      (15, 19, "15_19"), (20, 24, "20_24"), (25, 29, "25_29"),
                      (30, 34, "30_34"), (35, 39, "35_39"), (40, 44, "40_44"),
                      (45, 49, "45_49"), (50, 54, "50_54"), (55, 59, "55_59"),
                      (60, 64, "60_64")]:
        if lo <= e <= hi:
            return g
    if e >= 65:
        return "65_mas"
    return None


def main():
    met = {}
    pob = pd.read_parquet(OUT / "pob_grupos.parquet")
    pob22 = pob[(pob["anio"] == 2022) & (pob["municipio"] == "HERMOSILLO")
                & (pob["grupo_edad"] != "TOTAL")].copy()
    pob22["grupo_edad"] = pob22["grupo_edad"].replace(
        {"65_69": "65_mas", "70_74": "65_mas", "75_79": "65_mas",
         "80_84": "65_mas", "85_mm": "65_mas"})
    pob22 = pob22.groupby(["sexo", "grupo_edad"], as_index=False)["n"].sum()
    den_m = pob22[pob22["sexo"] == "HOMBRES"].set_index("grupo_edad")["n"]
    den_f = pob22[pob22["sexo"] == "MUJERES"].set_index("grupo_edad")["n"]
    den_t = den_m.add(den_f, fill_value=0)
    met["denominadores"] = {"sexo_vals": sorted(pob22["sexo"].unique().tolist()),
                            "hmo_2022_total": int(den_t.sum())}

    # Mortalidad: defunciones residentes HMO 2022 por grupo (ambos sexos)
    d = pd.read_parquet(DATA / "hmo_defunciones.parquet")
    d["grupo"] = d["EDAD"].apply(grupo_edad)
    mor = d.dropna(subset=["grupo"]).groupby("grupo").size()
    mr = pd.DataFrame({"grupo_edad": mor.index, "defunciones": mor.values})
    mr["poblacion"] = mr["grupo_edad"].map(den_t).fillna(0).astype(int)
    mr = mr[mr["poblacion"] > 0]
    mr["tasa_100k"] = (mr["defunciones"] / mr["poblacion"] * 100_000).round(1)
    lo, hi = poisson_ic(mr["defunciones"].values)
    mr["ic_lo"] = (lo / mr["poblacion"].values * 100_000).round(1)
    mr["ic_hi"] = (hi / mr["poblacion"].values * 100_000).round(1)
    mr.to_parquet(OUT / "tasas_mortalidad_hmo2022.parquet", index=False)
    met["mortalidad"] = {"filas": len(mr), "nota": "grupos 00-04...65_mas; denominador proyeccion CONAPO"}

    # Fecundidad: nacimientos por edad de la madre / mujeres del grupo
    n = pd.read_parquet(DATA / "hmo_nacimientos.parquet")
    n["grupo"] = n["EDAD"].apply(grupo_edad)
    fer = n.dropna(subset=["grupo"]).groupby("grupo").size()
    fr = pd.DataFrame({"grupo_edad": fer.index, "nacimientos": fer.values})
    fr["mujeres"] = fr["grupo_edad"].map(den_f).fillna(0).astype(int)
    fr = fr[fr["mujeres"] > 0]
    fr["tasa_1k"] = (fr["nacimientos"] / fr["mujeres"] * 1000).round(1)
    lo, hi = poisson_ic(fr["nacimientos"].values)
    fr["ic_lo"] = (lo / fr["mujeres"].values * 1000).round(1)
    fr["ic_hi"] = (hi / fr["mujeres"].values * 1000).round(1)
    fr.to_parquet(OUT / "tasas_fecundidad_hmo2022.parquet", index=False)
    met["fecundidad"] = {"filas": len(fr), "nota": "tasa por 1,000 mujeres del grupo"}

    (DATA / "resumen_tasas.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (v if k != "denominadores" else v) for k, v in met.items()},
                     ensure_ascii=False, indent=2)[:800])


if __name__ == "__main__":
    main()
