"""Modelos marginación Sonora 2020 (corte único, n=72 municipios).

1. segmentos_marg.pkl: KMeans sobre 9 indicadores (8 carencias + PO2SM) +
   PCA(2) para graficar. Descriptivo, no predictivo. k se elige por silueta
   en 2..6 y queda registrado.
2. po2sm_ridge.pkl: RidgeCV (carencias -> PO2SM) con Pipeline(StandardScaler)
   y R²/MAE por KFold(5). Descomposición exploratoria, no causalidad;
   n=72 exige cautela explícita.
Guarda modelos .pkl, métricas e inferencias en data/modelos/.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
MARG = ROOT / "data" / "marg_out"
OUT = ROOT / "data" / "modelos"
(OUT / "inferencias").mkdir(parents=True, exist_ok=True)

CARENCIAS = ["ANALF", "SBASC", "OVSDE", "OVSEE", "OVSAE", "OVPT", "VHAC", "PL.5000"]
FEATS = CARENCIAS + ["PO2SM"]


def main():
    met = {}
    m = pd.read_parquet(MARG / "municipios.parquet")
    assert len(m) == 72 and not m[FEATS].isna().any().any()
    Z = StandardScaler().fit_transform(m[FEATS])

    # 1. Segmentos: k por silueta en 2..6
    sil = {k: silhouette_score(Z, KMeans(n_clusters=k, n_init=20,
                                        random_state=42).fit_predict(Z))
           for k in range(2, 7)}
    k = max(sil, key=sil.get)
    km = KMeans(n_clusters=k, n_init=20, random_state=42).fit(Z)
    xy = PCA(n_components=2, random_state=42).fit_transform(Z)
    joblib.dump({"kmeans": km, "features": FEATS}, OUT / "segmentos_marg.pkl")
    seg = m[["NOM_MUN", "GM_2020", "PO2SM"]].assign(
        segmento=km.labels_, pca1=np.round(xy[:, 0], 3), pca2=np.round(xy[:, 1], 3))
    seg.to_parquet(OUT / "inferencias" / "segmentos_marg.parquet", index=False)
    met["segmentos"] = {"k": k, "n": len(m),
                        "silueta_por_k": {str(kk): round(v, 3) for kk, v in sil.items()},
                        "tamano": pd.Series(km.labels_).value_counts().sort_index().to_dict(),
                        "po2sm_mediana_por_segmento": seg.groupby("segmento")["PO2SM"]
                        .median().round(1).to_dict(),
                        "nota": "Descriptivo: agrupa perfiles de carencias, no acredita causas"}

    # 2. Descomposición PO2SM ~ carencias (RidgeCV + KFold out-of-fold)
    X, y = m[CARENCIAS], m["PO2SM"]
    pipe = Pipeline([("sc", StandardScaler()),
                     ("ridge", RidgeCV(alphas=np.logspace(-2, 3, 12)))])
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    oof = cross_val_predict(pipe, X, y, cv=cv)
    pipe.fit(X, y)
    coefs = pd.Series(pipe.named_steps["ridge"].coef_, index=CARENCIAS)
    met["po2sm_ridge"] = {
        "r2_oof": round(float(r2_score(y, oof)), 3),
        "mae_oof": round(float(mean_absolute_error(y, oof)), 2),
        "alpha": float(pipe.named_steps["ridge"].alpha_), "n": len(m),
        "coeficientes": coefs.sort_values(ascending=False).round(3).to_dict(),
        "advertencia": "n=72, corte único 2020: asociación exploratoria, no causalidad ni pronóstico"}
    joblib.dump({"pipeline": pipe, "features": CARENCIAS}, OUT / "po2sm_ridge.pkl")
    pd.DataFrame({"NOM_MUN": m["NOM_MUN"], "po2sm_observado": y.round(2),
                  "po2sm_oof": np.round(oof, 2)}).to_parquet(
        OUT / "inferencias" / "po2sm_oof.parquet", index=False)

    (OUT / "metricas_marginacion.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2)[:1200])


if __name__ == "__main__":
    main()
