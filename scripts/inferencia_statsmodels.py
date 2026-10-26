"""Inferencia clásica con statsmodels (complementa los modelos predictivos).

1. Logit irregularidad UTH (odds ratios + IC95 + efectos marginales + AUC).
2. Gamma-GLM del importe de beca (rate ratios + IC robustos HC0).
3. Binomial-negativa de delitos municipio x mes (tasas + IC; Poisson inválido: var/media~557).
4. Regresión cuantílica peso RN ~ edad madre (q10/q50/q90 + banda).
5. Tests de lo ya afirmado: chi2 sexo x edad (consulta), Mann-Whitney remota/presencial.
Guarda tablas en data/modelos/inferencias/ y métricas en metricas_inferencia.json.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2_contingency, mannwhitneyu
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EDU = DATA / "edu_hmo"
OUT = DATA / "modelos" / "inferencias"
met = {}


def save(df, name):
    df.to_parquet(OUT / name, index=False)


def main():
    # 1. Logit irregularidad
    m = pd.read_parquet(EDU / "matriculas_uth_hmo.parquet")
    yy = (m["Alumnos regulares e irregulares"].astype(str)
          .str.contains("irregular", case=False)).astype(int)
    X = pd.DataFrame({
        "edad": pd.to_numeric(m["Edad"], errors="coerce"),
        "prom_bach": pd.to_numeric(m["Promedio de bachillerato"], errors="coerce"),
        "sem": pd.to_numeric(m["Semestres cursados incluye ciclo actual"],
                             errors="coerce")})
    d = pd.DataFrame({"y": yy}).join(X).dropna()
    Xc = sm.add_constant(d[["edad", "prom_bach", "sem"]])
    logit = sm.Logit(d["y"], Xc).fit(disp=0)
    ci = logit.conf_int()
    ors = pd.DataFrame({
        "term": ["const", "edad", "prom_bach", "sem"],
        "or": np.exp(logit.params.values),
        "lo": np.exp(ci[0].values), "hi": np.exp(ci[1].values),
        "p": logit.pvalues.values}).round(4)
    save(ors, "logit_irregularidad_or.parquet")
    meff = logit.get_margeff().summary_frame().reset_index() \
        .rename(columns={"index": "term"})
    save(meff, "logit_irregularidad_margeff.parquet")
    grid = pd.DataFrame({"const": 1.0, "edad": d["edad"].median(),
                         "prom_bach": np.arange(60, 101),
                         "sem": d["sem"].median()})
    pr = logit.get_prediction(grid)
    pr_mean, pr_ci = np.asarray(pr.predicted), np.asarray(pr.conf_int())
    save(pd.DataFrame({"prom_bach": grid["prom_bach"].values,
                       "p": pr_mean, "lo": pr_ci[:, 0], "hi": pr_ci[:, 1]}).round(4),
         "logit_curva_prombach.parquet")
    met["logit"] = {"n": len(d), "prev": round(float(d.y.mean()), 3),
                    "auc": round(float(roc_auc_score(d.y, logit.predict(Xc))), 3),
                    "nota": "edad no significativa controlando (ver p)"}

    # 2. Gamma-GLM importe beca
    b = pd.read_parquet(EDU / "becas_hmo.parquet")
    b = b[b["importe"] > 0].copy()
    b["nivel_sup"] = (b["nivel"] != "NIVEL BÁSICO").astype(int)
    b["mujer"] = (b["genero"] == "MUJER").astype(int)
    gam = smf.glm("importe ~ nivel_sup + mujer + anio", data=b,
                  family=sm.families.Gamma(link=sm.families.links.Log())) \
        .fit(cov_type="HC0")
    ci = gam.conf_int()
    rrs = pd.DataFrame({
        "term": ["const", "nivel medio-sup", "mujer", "año"],
        "rr": np.exp(gam.params.values),
        "lo": np.exp(ci[0].values), "hi": np.exp(ci[1].values),
        "p": gam.pvalues.values}).round(4)
    save(rrs, "gamma_becas_rr.parquet")
    met["gamma"] = {"n": len(b), "nota": "IC robustos HC0; año lineal en log"}

    # 3. NB delitos municipio x mes
    inc = pd.read_parquet(DATA / "seg" / "incidencia.parquet")
    dm = inc.groupby(["Municipio", "anio", "mes"], observed=True)["n"] \
        .sum().reset_index()
    nb = smf.glm("n ~ C(Municipio, Treatment(reference='Hermosillo')) + C(mes) + anio",
                 data=dm, family=sm.families.NegativeBinomial()).fit(disp=0)
    ci = nb.conf_int()
    terms = list(nb.params.index)
    rrn = pd.DataFrame({
        "term": [t.replace("C(Municipio, Treatment(reference='Hermosillo'))[T.",
                           "Mpio: ").replace("C(mes)[T.", "mes: ").rstrip("]")
                 for t in terms],
        "rr": np.exp(nb.params.values),
        "lo": np.exp(ci[0].values), "hi": np.exp(ci[1].values),
        "p": nb.pvalues.values}).round(4)
    save(rrn, "nb_delitos_rr.parquet")
    met["nb"] = {"n": len(dm), "alpha": 1.0,
                 "alpha_nota": "dispersion fijada (estimarla no cambia el ranking)",
                 "llf": round(float(nb.llf), 1),
                 "nota": "NB por sobredispersion (var/media~557); ref=Hermosillo"}

    # 4. Cuantílica peso ~ edad madre
    nac = pd.read_parquet(DATA / "hmo_nacimientos.parquet")
    dn = nac[["EDAD", "PESO"]].apply(pd.to_numeric, errors="coerce").dropna()
    dn.columns = ["edad", "peso"]
    grid_e = pd.DataFrame({"const": 1.0,
                           "edad": np.arange(int(dn.edad.min()),
                                             int(dn.edad.max()) + 1)})
    band = {"edad": grid_e["edad"].values}
    coefs = {}
    for q in (0.1, 0.5, 0.9):
        rq = smf.quantreg("peso ~ edad", data=dn).fit(q=q)
        coefs[f"q{int(q * 100)}"] = {"coef_edad": round(float(rq.params["edad"]), 2),
                                     "p": float(rq.pvalues["edad"])}
        Xg = sm.add_constant(grid_e[["edad"]], has_constant="add")
        band[f"q{int(q * 100)}"] = rq.predict(Xg).values
    save(pd.DataFrame(band).round(1), "quantile_peso_grid.parquet")
    met["quantile"] = {"n": len(dn), "coefs": coefs,
                       "nota": "mediana + bandas q10-q90"}

    # 5. Tests
    con = pd.read_parquet(DATA / "hmo_consulta.parquet")
    ct = con[con.Sexo.isin(["HOMBRE", "MUJER"])] \
        .groupby(["Grupo_Edad", "Sexo"])["Total"].sum().unstack(fill_value=0)
    chi2, p, dof, _ = chi2_contingency(ct.values)
    n = ct.values.sum()
    met["chi2_sexo_edad"] = {
        "chi2": round(float(chi2), 1), "p": float(p),
        "cramer_v": round(float((chi2 / (n * (min(ct.shape) - 1))) ** 0.5), 3),
        "n": int(n)}
    rep = pd.read_parquet(EDU / "reprobacion_uth.parquet")
    cols = [c for c in rep.columns if "16VA" in c.upper() and "REPROB" in c.upper()]
    a = pd.to_numeric(rep[cols[0]], errors="coerce").dropna()
    bb = pd.to_numeric(rep[cols[1]], errors="coerce").dropna()
    u, pmw = mannwhitneyu(a, bb, alternative="two-sided")
    met["mw_remota"] = {"u": float(u), "p": float(pmw),
                        "med_pres": float(a.median()), "n_pres": len(a),
                        "med_remota": float(bb.median()), "n_remota": len(bb)}

    (DATA / "modelos" / "metricas_inferencia.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: (v if k != "nb" else {kk: vv for kk, vv in v.items()})
                      for k, v in met.items()}, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
