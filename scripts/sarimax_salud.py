"""SARIMAX mensual urgencias/consulta HMO con intervalos de prediccion.

Workflow skill statsmodels: ADF (estacionariedad), rejilla de ordenes por AIC
en train 2018-2020, Ljung-Box en residuos, backtest 2021, pronostico 2023 con
IC95%. Si no supera al Ridge estacional, se publica igual con su metrica.
"""

import itertools
import json
from pathlib import Path

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "modelos" / "inferencias"


def serie(nombre, col, ycol):
    df = pd.read_parquet(DATA / nombre)
    yc = next((c for c in df.columns if str(c).lower().startswith("a") or c == "Year"), None)
    if yc is None:
        raise ValueError(f"sin columna de año en {list(df.columns)[:5]}")
    g = df.groupby([yc, "Mes"])[col].sum().reset_index()
    g.columns = ["anio", "mes", "n"]
    g = g.sort_values(["anio", "mes"]).reset_index(drop=True)
    g["t"] = pd.to_datetime(g["anio"].astype(str) + "-" + g["mes"].astype(str) + "-01")
    return g.set_index("t")["n"].asfreq("MS")


def main():
    met = {}
    for nombre, col, f in [("urgencias", "Total_Urgencias", "hmo_urgencias.parquet"),
                           ("consulta", "Total", "hmo_consulta.parquet")]:
        y = serie(f, col, None)
        adf = adfuller(y.loc["2018":"2020"].dropna())
        tr, te = y.loc["2018":"2020"], y.loc["2021"]
        te = te.dropna()
        mejor, best = None, (None, float("inf"))
        for order, sorder in itertools.product(
                [(1, 0, 0), (1, 1, 0), (0, 1, 1)], [(1, 0, 0, 12), (0, 1, 1, 12)]):
            try:
                r = SARIMAX(tr, order=order, seasonal_order=sorder,
                            enforce_stationarity=False,
                            enforce_invertibility=False).fit(disp=False)
                if r.aic < best[1]:
                    best, mejor = (order, sorder, float(r.aic)), r
            except Exception:
                continue
        lb = acorr_ljungbox(mejor.resid.dropna(), lags=[12], return_df=True)
        fc = mejor.get_forecast(len(te))
        pred = fc.predicted_mean
        mae = float((te.values - pred.values).__abs__().mean())
        mape = float((abs(te.values - pred.values) / te.values).mean() * 100)
        f23 = mejor.get_forecast(12)
        idx = pd.date_range("2023-01-01", periods=12, freq="MS")
        infer = pd.DataFrame({"anio": 2023, "mes": range(1, 13),
                              "pronostico": f23.predicted_mean.values.round().astype(int),
                              "lo95": f23.conf_int(alpha=0.05).iloc[:, 0].values.round().astype(int),
                              "hi95": f23.conf_int(alpha=0.05).iloc[:, 1].values.round().astype(int),
                              "servicio": nombre})
        infer.to_parquet(OUT / f"sarimax_{nombre}.parquet", index=False)
        met[nombre] = {"orden": best[0], "sorden": best[1], "aic": round(best[2], 1),
                       "adf_p": round(float(adf[1]), 4),
                       "ljungbox_p": round(float(lb["lb_pvalue"].iloc[0]), 4),
                       "mae_2021": round(mae, 1), "mape_2021": round(mape, 1)}
    (DATA / "modelos" / "metricas_sarimax.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
