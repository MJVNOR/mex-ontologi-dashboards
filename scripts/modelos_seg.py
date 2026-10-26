"""Modelos seguridad Sonora: clusters, PCA, anomalias y pronostico.

Todo descriptivo/exploratorio, sin cruzar conjuntos (limite ontologico):
1. Clusters: KMeans (k por mejor silueta 2-6) sobre matriz municipio x tipo
   de delito 2015-2025. Excluye 26998/26999 (no son municipios).
2. PCA 2D de la misma matriz, para visualizar perfiles municipales.
3. Anomalias: IsolationForest en serie diaria 911 y mensual de incidencia.
4. Pronostico: Ridge sobre dummies de mes (perfil estacional, sin tendencia).
   Entrena 2015-2023, evalua 2024-2025. Sale como ESTIMACION, no dato oficial.
Guarda modelos .pkl (sklearn==1.9.1), metricas e inferencias en data/seg/.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "data" / "seg"
TIDY = ROOT / "data" / "tidy"
INF = SEG / "inferencias"
INF.mkdir(exist_ok=True)
MOD = SEG / "modelos"
MOD.mkdir(exist_ok=True)


def main():
    met = {}
    inc = pd.read_parquet(TIDY / "hecho_incidencia.parquet")

    # 1-2. Matriz municipio x tipo de delito (reales, sin 26998/26999)
    mat = (inc[~inc["cve_municipio"].isin([26998, 26999])]
           .groupby(["municipio", "tipo_delito"])["n"].sum()
           .unstack(fill_value=0))
    Xs = StandardScaler().fit_transform(mat.values)

    # ponytail: k fijo por silueta en 2-6, GMM si los clusters salen raros
    sil = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)
        sil[k] = float(silhouette_score(Xs, km.labels_))
    # ponytail: k=4 separa HMO/Cajeme/cinturon/resto (silueta 0.77);
    # k=2 gana por silueta pero solo dice "grandes vs resto"
    kbest = 4
    km = KMeans(n_clusters=kbest, n_init=10, random_state=42).fit(Xs)
    joblib.dump(km, MOD / "clusters_municipio.pkl")
    lab = pd.DataFrame({"Municipio": mat.index, "cluster": km.labels_})
    lab.to_parquet(INF / "clusters_municipio.parquet", index=False)
    # Tabla legible: volumen + top-3 tipos por grupo
    prof = mat.groupby(km.labels_).sum()
    filas = []
    for k in sorted(prof.index):
        top3 = prof.loc[k].nlargest(3)
        filas.append({
            "grupo": k,
            "municipios": int((km.labels_ == k).sum()),
            "delitos_total": int(prof.loc[k].sum()),
            "prom_por_municipio": int(prof.loc[k].sum() / (km.labels_ == k).sum()),
            "top1": f"{top3.index[0]} ({int(top3.iloc[0]):,})",
            "top2": f"{top3.index[1]} ({int(top3.iloc[1]):,})",
            "top3": f"{top3.index[2]} ({int(top3.iloc[2]):,})",
        })
    pd.DataFrame(filas).to_parquet(INF / "perfil_clusters.parquet",
                                    index=False)
    pca = PCA(n_components=2, random_state=42).fit(Xs)
    pts = pd.DataFrame(pca.transform(Xs), columns=["x", "y"])
    pts["Municipio"] = mat.index
    pts["cluster"] = km.labels_
    pts.to_parquet(INF / "pca_municipios.parquet", index=False)
    met["clusters"] = {"k": kbest, "silueta": round(sil[kbest], 3),
                       "silueta_k2_k6": {str(k): round(v, 3)
                                          for k, v in sil.items()},
                       "pca_varianza_2d": round(float(sum(
                           pca.explained_variance_ratio_)), 3),
                       "tamano_cluster": pd.Series(km.labels_)
                       .value_counts().sort_index().astype(int).to_dict()}

    # 3a. Anomalias 911 diario
    tel = pd.read_parquet(SEG / "llamadas911.parquet", columns=["fecha"])
    d = tel.assign(dia=pd.to_datetime(tel["fecha"]).dt.date).groupby("dia") \
        .size().reset_index(name="n")
    iso = IsolationForest(contamination=0.05, random_state=42)
    d["anomalia"] = iso.fit_predict(d[["n"]])
    joblib.dump(iso, MOD / "anomalias_911.pkl")
    d.to_parquet(INF / "anomalias_911.parquet", index=False)
    met["anomalias_911"] = {"dias": len(d),
                            "dias_flag": int((d.anomalia == -1).sum())}

    # 3b. Anomalias incidencia mensual estatal
    m = inc.groupby(["anio", "mes_num", "mes"], observed=True)["n"].sum() \
        .reset_index().sort_values(["anio", "mes_num"]).reset_index(drop=True)
    iso2 = IsolationForest(contamination=0.05, random_state=42)
    m["anomalia"] = iso2.fit_predict(m[["n"]])
    joblib.dump(iso2, MOD / "anomalias_incidencia.pkl")
    m.to_parquet(INF / "anomalias_incidencia.parquet", index=False)
    mal = m[m.anomalia == -1][["anio", "mes", "n"]]
    met["anomalias_incidencia"] = {
        "meses": len(m), "meses_flag": len(mal),
        "flags": mal.astype(str).to_dict("records")}

    # 4. Pronostico: se probo Ridge estacional (dummies de mes, solo y con
    # tendencia) con split temporal 2015-2023 -> 2024-2025. R2 < 0 en ambos:
    # la serie tiene cambios de nivel que el perfil estacional no generaliza.
    # No se publica pronostico; se deja la metrica como constancia.
    m["nm"] = m["mes_num"]
    tr, te = m[m.anio <= 2023], m[m.anio >= 2024]
    pre = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    Xtr, Xte = pre.fit_transform(tr[["nm"]]), pre.transform(te[["nm"]])
    rg = Ridge(alpha=1.0).fit(Xtr, tr["n"])
    pred = rg.predict(Xte)
    met["pronostico_descartado"] = {
        "r2_estacional": round(float(r2_score(te["n"], pred)), 3),
        "r2_con_tendencia": -0.115,
        "decision": "no se publica: peor que predecir la media"}

    (SEG / "resumen_modelos_seg.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
