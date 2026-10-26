"""Modelos educacion Hermosillo.

1. riesgo_reprobacion.pkl: RandomForestClassifier — con indices y promedios de
   las semanas 4/8/12 predice indice16 >= 30 (riesgo alto). Split aleatorio
   estratificado 80/20.
2. segmentos_uth.pkl: KMeans(k=4) sobre ciclo 2021-2022 (semestre, promedios,
   creditos, sexo) + PCA(2) para graficar. Descriptivo, no predictivo.
3. tendencia_becas.pkl: LinearRegression año->becas HMO (n=5, cautela explícita)
   + estimacion 2026 con R2 a la vista.
4. irregularidad_uth.pkl: RandomForestClassifier — con datos de entrada
   (edad, promedio bachillerato, programa, modalidad, sexo, semestres)
   predice alumno irregular. Sin promedios generales ni creditos (fuga).
Guarda modelos .pkl, metricas e inferencias en data/modelos/.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (balanced_accuracy_score, classification_report,
                             mean_absolute_error, r2_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
EDU = ROOT / "data" / "edu_hmo"
OUT = ROOT / "data" / "modelos"
(OUT / "inferencias").mkdir(parents=True, exist_ok=True)


def col(df, *keys):
    for c in df.columns:
        if all(k.lower() in str(c).lower() for k in keys):
            return c
    raise KeyError(keys)


def main():
    met = {}
    # 1. Riesgo de reprobacion
    rep = pd.read_parquet(EDU / "reprobacion_uth.parquet")
    import re
    idx = lambda n: next(c for c in rep.columns
                         if re.search(rf"\b{n}(TA|VA)\b", c.upper()) and "REPROB" in c.upper())
    prom = lambda n: next(c for c in rep.columns
                          if re.search(rf"\b{n}(TA|VA)\b", c.upper()) and "PROM" in c.upper())
    feats = [idx(4), idx(8), idx(12), prom(4), prom(8), prom(12)]
    r = rep[feats + [idx(16)]].apply(pd.to_numeric, errors="coerce").dropna()
    X, y = r[feats], (r[idx(16)] >= 30).astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    clf = Pipeline([("sc", StandardScaler()),
                    ("rf", RandomForestClassifier(n_estimators=200, random_state=42))])
    clf.fit(Xtr, ytr)
    yp = clf.predict(Xte)
    met["riesgo_reprobacion"] = {
        "balanced_accuracy": round(float(balanced_accuracy_score(yte, yp)), 3),
        "prevalencia_riesgo": round(float(y.mean()), 3), "n": len(r),
        "reporte": classification_report(yte, yp, output_dict=True, zero_division=0)}
    joblib.dump({"modelo": clf, "features": feats, "umbral": 30}, OUT / "riesgo_reprobacion.pkl")
    rep_out = rep.copy()
    rep_out["p_riesgo"] = clf.predict_proba(
        rep[feats].apply(pd.to_numeric, errors="coerce").fillna(rep[feats].median(numeric_only=True))
    )[:, 1].round(3)
    rep_out.to_parquet(OUT / "inferencias" / "riesgo_materias.parquet", index=False)

    # 2. Segmentos estudiantes (ciclo 2021-2022)
    c = pd.read_excel(ROOT / "data/edu/matriculas_matriculas-ciclo-2021-2022.xlsx", sheet_name=0)
    c.columns = ["programa", "semestre", "sexo", "prom_act", "prom_gral",
                 "creditos", "residencias", "seguro", "discapacidad"]
    num = ["semestre", "prom_act", "prom_gral", "creditos"]
    pre = ColumnTransformer([("num", StandardScaler(), num),
                             ("sex", OneHotEncoder(handle_unknown="ignore"), ["sexo"])])
    Z = pre.fit_transform(c[num + ["sexo"]])
    km = KMeans(n_clusters=4, n_init=20, random_state=42).fit(Z)
    xy = PCA(n_components=2, random_state=42).fit_transform(Z.toarray() if hasattr(Z, "toarray") else Z)
    joblib.dump({"kmeans": km, "pre": pre}, OUT / "segmentos_uth.pkl")
    seg = c.assign(segmento=km.labels_, pca1=np.round(xy[:, 0], 3), pca2=np.round(xy[:, 1], 3))
    seg.to_parquet(OUT / "inferencias" / "segmentos_uth.parquet", index=False)
    met["segmentos"] = {"k": 4, "n": len(c),
                        "tamano": pd.Series(km.labels_).value_counts().sort_index().to_dict(),
                        "medias": seg.groupby("segmento")[num].mean(numeric_only=True)
                        .round(2).to_dict()}

    # 3. Tendencia becas HMO (n=5: presentarla como referencia fragil)
    b = pd.read_parquet(EDU / "becas_hmo.parquet")
    t = b.groupby("anio").size().reset_index(name="n")
    lr = LinearRegression().fit(t[["anio"]], t["n"])
    pred = lr.predict(t[["anio"]])
    est2026 = int(lr.predict(pd.DataFrame({"anio": [2026]}))[0])
    met["tendencia_becas"] = {"r2": round(float(r2_score(t.n, pred)), 3),
                              "mae": round(float(mean_absolute_error(t.n, pred)), 1),
                              "estimacion_2026": est2026,
                              "advertencia": "n=5: referencia fragil, no compromiso"}
    joblib.dump(lr, OUT / "tendencia_becas.pkl")
    est = pd.DataFrame(
        {"anio": [2026], "n": [est2026], "tipo": ["estimacion"]})
    hist = t.assign(tipo="observado")
    pd.concat([hist, est], ignore_index=True).to_parquet(
        OUT / "inferencias" / "tendencia_becas.parquet", index=False)

    # 4. Irregularidad matricula UTH HMO (solo datos de entrada, sin fuga)
    from sklearn.impute import SimpleImputer
    m = pd.read_parquet(EDU / "matriculas_uth_hmo.parquet")
    ycol, ecol = col(m, "regulares"), col(m, "edad")
    pb, prog, mod_, sex, sem = (col(m, "promedio", "bachillerato"),
                                col(m, "programa educativo"), col(m, "modalidad"),
                                "Sexo", col(m, "semestres", "incluye"))
    # ponytail: sin promedios generales ni creditos (contienen el resultado)
    mm = m[[ycol, ecol, pb, prog, mod_, sex, sem]].copy()
    mm = mm[mm[ycol].astype(str).str.strip() != ""]
    yy = (mm[ycol].astype(str).str.contains("irregular", case=False)).astype(int)
    num4, cat4 = [ecol, pb, sem], [prog, mod_, sex]
    pre4 = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                          ("sc", StandardScaler())]), num4),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat4)])
    Xtr4, Xte4, ytr4, yte4 = train_test_split(
        mm[num4 + cat4], yy, test_size=0.2, stratify=yy, random_state=42)
    rf4 = Pipeline([("pre", pre4),
                    ("rf", RandomForestClassifier(n_estimators=100, random_state=42))])
    rf4.fit(Xtr4, ytr4)
    yp4 = rf4.predict(Xte4)
    rep4 = classification_report(yte4, yp4, output_dict=True, zero_division=0)
    oh_names = list(rf4.named_steps["pre"].named_transformers_["cat"]
                    .named_steps["oh"].get_feature_names_out(cat4))
    feat_names = num4 + oh_names
    imp4 = pd.Series(rf4.named_steps["rf"].feature_importances_, index=feat_names)
    agg = {}
    for name, v in imp4.items():
        base = next((c for c in cat4 if name.startswith(c + "_")), name)
        agg[base] = agg.get(base, 0) + v
    imp4 = pd.Series(agg)
    met["irregularidad"] = {
        "balanced_accuracy": round(float(balanced_accuracy_score(yte4, yp4)), 3),
        "prevalencia_irregular": round(float(yy.mean()), 3), "n": len(mm),
        "importancias": imp4.sort_values(ascending=False).round(3).to_dict(),
        "reporte": rep4}
    joblib.dump({"pipeline": rf4, "num": num4, "cat": cat4},
                OUT / "irregularidad_uth.pkl", compress=3)
    mm_out = m[[prog, mod_]].copy()
    mm_out["p_irregular"] = rf4.predict_proba(mm[num4 + cat4])[:, 1].round(3)
    mm_out.to_parquet(OUT / "inferencias" / "irregularidad_matricula.parquet",
                      index=False)

    (OUT / "metricas_edu.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
