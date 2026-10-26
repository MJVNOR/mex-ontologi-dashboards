"""Predictor mensual por municipio + SHAP (solo si valida).

Diseno: filas municipio x mes (2015-2025), target = total del mes siguiente.
Features causales: lags 1/12, medias moviles 3/12, mes, anio, municipio.
Split temporal por anio-target: train <=2022, test >=2023.
Modelo: RandomForestRegressor en Pipeline (one-hot dentro, sin fuga).
Baseline honesta: naive estacional (mismo mes anio anterior).
SHAP (PermutationExplainer sobre rf.predict, background=train) solo si R2_test > 0.3 y supera al
baseline. Salida: metricas + importancias + waterfall (Hermosillo, ultimo
mes de test). Todo descriptivo del modelo, no causal.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "data" / "seg"
INF = SEG / "inferencias"
MOD = SEG / "modelos"

ORDEN = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
         "Diciembre"]


def main():
    met = {}
    inc = pd.read_parquet(SEG / "incidencia.parquet",
                          columns=["Cve. Municipio", "Municipio", "anio",
                                   "mes", "n"])
    inc = inc[~inc["Cve. Municipio"].isin([26998, 26999])]
    m = inc.groupby(["Municipio", "anio", "mes"], observed=True)["n"].sum() \
        .reset_index()
    m["nm"] = m["mes"].map({v: i + 1 for i, v in enumerate(ORDEN)})
    m = m.sort_values(["Municipio", "anio", "nm"]).reset_index(drop=True)
    g = m.groupby("Municipio")["n"]
    m["lag1"] = g.shift(1)
    m["lag12"] = g.shift(12)
    m["roll3"] = g.shift(1).rolling(3).mean().reset_index(level=0, drop=True)
    m["roll12"] = g.shift(1).rolling(12).mean().reset_index(level=0, drop=True)
    m["target"] = g.shift(-1)
    m["target_anio"] = m["anio"].where(m["nm"] < 12, m["anio"] + 1)
    feats = ["Municipio", "nm", "anio", "lag1", "lag12", "roll3", "roll12"]
    d = m.dropna(subset=feats + ["target"]).reset_index(drop=True)
    tr, te = d[d.target_anio <= 2022], d[d.target_anio >= 2023]

    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
          ["Municipio", "nm"])], remainder="passthrough")
    Xtr, Xte = pre.fit_transform(tr[feats]), pre.transform(te[feats])
    ytr, yte = tr["target"].values, te["target"].values
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                               random_state=42, n_jobs=-1).fit(Xtr, ytr)
    pred = rf.predict(Xte)
    naive = te["lag12"].values
    met["predictor"] = {
        "filas_train": len(tr), "filas_test": len(te),
        "r2": round(float(r2_score(yte, pred)), 3),
        "mae": round(float(mean_absolute_error(yte, pred)), 1),
        "baseline_naive_r2": round(float(r2_score(yte, naive)), 3),
        "train": "target<=2022", "test": "target>=2023",
        "nota": "features solo pasado; split por anio-target",
    }
    print(json.dumps(met, ensure_ascii=False, indent=2))
    ok = met["predictor"]["r2"] > 0.3 and \
        met["predictor"]["r2"] > met["predictor"]["baseline_naive_r2"]
    met["predictor"]["valida"] = bool(ok)
    if not ok:
        met["decision"] = "no se publica SHAP: el modelo no supera el corte"
        (SEG / "resumen_supervisado_seg.json").write_text(
            json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
        print("DESCARTADO")
        return

    joblib.dump({"modelo": rf, "pre": pre, "feats": feats},
                MOD / "predictor_municipio.pkl")
    te2 = te.assign(pred=pred).reset_index(drop=True)
    te2.to_parquet(INF / "pred_municipio.parquet", index=False)

    import numpy as np
    import shap
    met["shap_version"] = shap.__version__
    names = list(pre.get_feature_names_out())
    bg = pd.DataFrame(shap.sample(pd.DataFrame(Xtr, columns=names), 100,
                                  random_state=7), columns=names)
    Xm_all = pd.DataFrame(Xte[:200], columns=names)
    # Waterfall: Hermosillo reciente debe estar entre las filas explicadas
    herm = te[te.Municipio == "Hermosillo"].index
    if herm.max() >= 200:
        extra = pd.DataFrame(pre.transform(te.loc[herm[-5:], feats]),
                             columns=names, index=herm[-5:])
        Xm = pd.concat([Xm_all.iloc[:-5], extra]).reset_index(drop=True)
        wf_label = te.loc[herm[-1], ["anio", "nm"]].tolist()
    else:
        Xm = Xm_all
        wf_label = None
    masker = shap.maskers.Independent(bg, max_samples=len(bg))
    explainer = shap.Explainer(lambda X: rf.predict(np.asarray(X)),
                               masker, algorithm="permutation", seed=7)
    budget = 2 * Xm.shape[1] + 1
    exp = explainer(Xm, max_evals=budget)
    assert exp.values.shape == Xm.shape
    rec = np.asarray(exp.base_values) + exp.values.sum(axis=1)
    np.testing.assert_allclose(rec, rf.predict(Xm.values),
                               rtol=1e-5, atol=1e-6)
    met["shap"] = {
        "output": "delitos mes siguiente (conteo, regresion)",
        "background": "100 filas train", "filas_explicadas": len(Xm),
        "additivity_ok": True,
        "nota": "describe al modelo, no causalidad",
    }
    impa = pd.DataFrame({"feature": names,
                         "mean_abs_shap": np.abs(exp.values).mean(axis=0)})
    impa.to_parquet(INF / "shap_importancia.parquet", index=False)
    # Waterfall: Hermosillo, ultimo mes de test explicado
    if wf_label is None:
        cand = te2[(te2.Municipio == "Hermosillo")].iloc[-1]
        i = int(te2.index.get_loc(cand.name)) \
            if cand.name in te2.index[:len(Xm)] else 0
        wf_label = [int(cand.anio), int(cand.nm)]
    else:
        i = len(Xm) - 1
    row = exp[i]
    wf = pd.DataFrame({"feature": Xm.columns.tolist(),
                       "shap_value": np.asarray(row.values).ravel(),
                       "feature_value": np.asarray(row.data).ravel()})
    wf["base_value"] = float(np.asarray(row.base_values).ravel()[0])
    wf["prediccion"] = float(rf.predict(Xm.values[[i]])[0])
    wf.to_parquet(INF / "shap_waterfall_hmo.parquet", index=False)
    met["shap"]["waterfall_fila"] = \
        f"Hermosillo {int(wf_label[0])}-{int(wf_label[1]):02d} " \
        "(mes de features; target = mes siguiente)"
    met["shap"]["filas_explicadas_nota"] = \
        "195 primeras de test + 5 Hermosillo recientes"

    (SEG / "resumen_supervisado_seg.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print("VALIDADO + SHAP OK")


if __name__ == "__main__":
    main()
