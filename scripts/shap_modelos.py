"""SHAP para riesgo_reprobacion e irregularidad_uth (PermutationExplainer).

Explica P(clase=1) de cada pipeline sobre filas held-out/muestra documentada,
con background de la poblacion de referencia. Valida aditividad
(base + suma == predict_proba) antes de guardar. Solo describe el modelo;
no establece causalidad.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "modelos" / "shap"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42


def explicar(nombre, modelo, Z_exp, Z_bg, feature_names, max_evals):
    import shap
    Z_bg = np.asarray(Z_bg, dtype=float)
    Z_exp = np.asarray(Z_exp, dtype=float)
    masker = shap.maskers.Independent(Z_bg, max_samples=len(Z_bg))
    ex = shap.Explainer(modelo.predict_proba, masker, algorithm="permutation",
                        output_names=["p0", "p1"], seed=SEED)
    exp = ex(Z_exp, max_evals=max_evals)
    if exp.values.ndim == 3:
        exp = exp[..., 1]  # P(clase=1)
    base = np.asarray(exp.base_values)
    vals = np.asarray(exp.values)
    reconstruido = base + vals.sum(axis=1)
    esperado = modelo.predict_proba(Z_exp)[:, 1]
    err = float(np.max(np.abs(reconstruido - esperado)))
    assert err < 1e-3, f"falla aditividad en {nombre}: {err}"
    v = pd.DataFrame(vals, columns=feature_names)
    v["base_value"] = base
    v["p_modelo"] = esperado
    for i, c in enumerate(feature_names):
        v[f"valor_{i}"] = Z_exp[:, i]
    meta = {"modelo": nombre, "output": "P(clase=1)", "n_explicadas": len(Z_exp),
            "n_background": len(Z_bg), "explainer": "permutation",
            "max_evals": max_evals, "seed": SEED,
            "additivity_max_err": err, "shap_version": shap.__version__,
            "nota": "describe el modelo, no causalidad"}
    v.to_parquet(OUT / f"valores_{nombre}.parquet", index=False)
    (OUT / f"meta_{nombre}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(nombre, "ok, err:", round(err, 6), "| filas:", len(v))
    return v


def main():
    import re
    ed = joblib.load(ROOT / "data" / "modelos" / "riesgo_reprobacion.pkl")
    rep = pd.read_parquet(ROOT / "data" / "edu_hmo" / "reprobacion_uth.parquet")
    idx = lambda n: next(c for c in rep.columns if re.search(rf"\b{n}(TA|VA)\b", c.upper()) and "REPROB" in c.upper())
    prom = lambda n: next(c for c in rep.columns if re.search(rf"\b{n}(TA|VA)\b", c.upper()) and "PROM" in c.upper())
    feats = [idx(4), idx(8), idx(12), prom(4), prom(8), prom(12)]
    Xr = rep[feats].apply(pd.to_numeric, errors="coerce").dropna()
    Zr = ed["modelo"].named_steps["sc"].transform(Xr)
    bg = Zr[np.random.RandomState(SEED).choice(len(Zr), min(100, len(Zr)), replace=False)]
    explicar("riesgo_reprobacion", ed["modelo"].named_steps["rf"], Zr, bg, feats,
             max_evals=2 * len(feats) + 1)

    irr = joblib.load(ROOT / "data" / "modelos" / "irregularidad_uth.pkl")
    m = pd.read_parquet(ROOT / "data" / "edu_hmo" / "matriculas_uth_hmo.parquet")
    Xn = m[irr["num"] + irr["cat"]]
    Xe = Xn.sample(200, random_state=SEED)
    Xb = Xn.sample(100, random_state=SEED + 1)
    pre = irr["pipeline"].named_steps["pre"]
    onames = list(pre.named_transformers_["cat"].named_steps["oh"]
                  .get_feature_names_out(irr["cat"]))
    Ze = pre.transform(Xe)
    Zb = pre.transform(Xb)
    Ze = Ze.toarray() if hasattr(Ze, "toarray") else Ze
    Zb = Zb.toarray() if hasattr(Zb, "toarray") else Zb
    explicar("irregularidad_uth", irr["pipeline"].named_steps["rf"], Ze, Zb,
             irr["num"] + onames, max_evals=2 * (len(irr["num"]) + len(onames)) + 1)


if __name__ == "__main__":
    main()
