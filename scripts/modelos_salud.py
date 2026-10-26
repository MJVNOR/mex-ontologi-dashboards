"""Modelos salud Hermosillo: pronostico mensual + anomalias vigilancia.

1. Pronostico: Ridge sobre dummies de mes (perfil estacional, sin extrapolar
   tendencia anual). Entrena en años completos 2018-2020, evalua en meses
   disponibles de 2021 (2021-2022 vienen parciales en la fuente).
   Pronostica 12 meses siguientes como ESTIMACION, no dato oficial.
2. Anomalias: IsolationForest sobre casos semanales totales de vigilancia.
Guarda modelos .pkl, metricas e inferencias en data/modelos/.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "modelos"
(OUT / "inferencias").mkdir(parents=True, exist_ok=True)


def mensual(df, ycol, yname):
    yc = yname
    g = df.groupby([yc, "Mes"])[ycol].sum().reset_index()
    g.columns = ["anio", "mes", "total"]
    return g


def main():
    met, inf = {}, {}
    urg = pd.read_parquet(ROOT / "data" / "hmo_urgencias.parquet")
    con = pd.read_parquet(ROOT / "data" / "hmo_consulta.parquet")
    yu = next(c for c in urg.columns if str(c).lower().startswith("a"))
    series = {"urgencias": mensual(urg, "Total_Urgencias", yu),
              "consulta": mensual(con.rename(columns={"Year": "anio"}), "Total", "anio")
              if "Year" in con.columns else mensual(con, "Total", "Year")}
    pre = ColumnTransformer([("mes", OneHotEncoder(handle_unknown="ignore",
                                                      sparse_output=False), ["mes"])],
                            remainder="passthrough")
    for nombre, g in [("urgencias", series["urgencias"]),
                       ("consulta", series["consulta"])]:
        tr = g[g.anio.isin([2018, 2019, 2020])]
        te = g[g.anio == 2021].dropna(subset=["total"])
        Xtr, ytr = tr[["mes"]], tr["total"]
        Xte, yte = te[["mes"]], te["total"]
        m = Ridge(alpha=1.0)
        m.fit(pre.fit_transform(Xtr), ytr)
        pred = m.predict(pre.transform(Xte))
        met[nombre] = {"mae": round(float(mean_absolute_error(yte, pred)), 1),
                       "mape_pct": round(float((abs(yte.values - pred) / yte.values).mean() * 100), 1),
                       "r2": round(float(r2_score(yte, pred)), 3),
                       "train_anios": [2018, 2019, 2020], "test_anio": 2021,
                       "nota": "2021-2022 parciales en la fuente"}
        joblib.dump({"modelo": m, "pre": pre, "columnas": ["mes"]},
                    OUT / f"pronostico_{nombre}.pkl")
        fdf = pd.DataFrame({"mes": range(1, 13)})
        fdf["pronostico"] = m.predict(pre.transform(fdf)).round().astype(int)
        fdf["banda"] = tr.groupby("mes")["total"].std().reindex(range(1, 13)).round().astype(int).values
        fdf["anio"] = 2023
        fdf["servicio"] = nombre
        inf[nombre] = fdf
    pd.concat(inf.values(), ignore_index=True).to_parquet(
        OUT / "inferencias" / "pronostico_mensual.parquet", index=False)

    vig = pd.read_parquet(ROOT / "data" / "hmo_vigilancia.parquet")
    sem = vig.groupby("no_semana")["acumulado"].sum().reset_index()
    iso = IsolationForest(contamination=0.08, random_state=42)
    sem["anomalia"] = iso.fit_predict(sem[["acumulado"]])
    joblib.dump(iso, OUT / "anomalias_vigilancia.pkl")
    sem.to_parquet(OUT / "inferencias" / "anomalias_vigilancia.parquet", index=False)
    met["vigilancia"] = {"semanas_anomalas": int((sem.anomalia == -1).sum()),
                         "semanas": len(sem),
                         "semanas_flag": sem[sem.anomalia == -1]["no_semana"].tolist()}
    (OUT / "metricas_salud.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
