"""Inferencia de series con statsmodels (no toca inferencia_statsmodels.py).

A. Wilcoxon pareado diciembre vs noviembre (11 pares-ano): respalda o no
   el pico estacional del dashboard. Una sola prueba pre-especificada.
B. SARIMAX mensual de incidencia: ADF, orden por AIC en train (<=2022),
   Ljung-Box, pronostico 2023-2025 con intervalos. Si no supera al naive,
   se descarta con metrica (igual que el Ridge).
C. Tasa de desapariciones pre/post 2024 (rate ratio con IC, descriptivo).
Todo descriptivo; sin causalidad.
"""

import json
import warnings
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import wilcoxon
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "data" / "seg"
TIDY = ROOT / "data" / "tidy"
OUT = SEG / "inferencias"
met = {}


def main():
    inc = pd.read_parquet(TIDY / "hecho_incidencia.parquet")
    m = inc.groupby(["anio", "mes_num"], observed=True)["n"].sum() \
        .reset_index().sort_values(["anio", "mes_num"]).reset_index(drop=True)

    # A. Diciembre vs noviembre, pareado por anio
    piv = m.pivot(index="anio", columns="mes_num", values="n")
    d = (piv[11] - piv[12]).dropna()
    w, p = wilcoxon(d, alternative="greater")
    met["wilcoxon_dic_nov"] = {
        "pares": int(len(d)), "mediana_dif_nov_dic": float(d.median()),
        "w": float(w), "p": float(p),
        "nota": "una prueba pre-especificada; sin correccion multiple"}

    # B. SARIMAX
    y = pd.Series(m["n"].values,
                  index=pd.date_range("2015-01-01", periods=len(m), freq="MS"))
    adf = adfuller(y[: "2022"], autolag="AIC", result_object=True)
    met["adf_train"] = {"stat": round(float(adf.statistic), 3),
                        "p": float(adf.pvalue),
                        "nota": "no rechazar no prueba raiz unitaria"}
    best, tried = None, []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p_, d_, q in product((0, 1), (0, 1), (0, 1, 2)):
            for P, D, Q in product((0, 1), (0, 1), (0, 1)):
                try:
                    r = sm.tsa.SARIMAX(
                        y[: "2022"], order=(p_, d_, q),
                        seasonal_order=(P, D, Q, 12),
                        enforce_stationarity=False,
                        enforce_invertibility=False).fit(disp=False)
                    tried.append(((p_, d_, q), (P, D, Q), float(r.aic)))
                    if best is None or r.aic < best[0].aic:
                        best = (r, ((p_, d_, q), (P, D, Q)))
                except Exception:
                    continue
    r, orden = best
    lb = acorr_ljungbox(r.resid, lags=[12], return_df=True)
    fc = r.get_forecast(steps=len(y["2023":]))
    pred = np.asarray(fc.predicted_mean)
    reali = y["2023":].values
    naive = y["2022"].values  # mismo mes anio anterior... 12 valores vs 36
    naive = np.tile(y["2022"].values, 3)[:len(reali)]
    from sklearn.metrics import mean_absolute_error, r2_score
    met["sarimax"] = {
        "orden": orden[0], "orden_estacional": orden[1], "aic": round(float(r.aic), 1),
        "ljungbox_p_lag12": float(lb["lb_pvalue"].iloc[0]),
        "mae": round(float(mean_absolute_error(reali, pred)), 1),
        "r2": round(float(r2_score(reali, pred)), 3),
        "baseline_naive_mae": round(float(mean_absolute_error(reali, naive)), 1),
        "train": "<=2022", "test": "2023-2025",
        "nota": "intervalos del modelo en inferencias/sarimax_pronostico.parquet"}
    if met["sarimax"]["r2"] < 0:
        met["sarimax"]["decision"] = "no se publica: peor que la media"
    else:
        ci = np.asarray(fc.conf_int())
        pd.DataFrame({"fecha": y["2023":].index, "real": reali,
                      "pronostico": pred, "lo": ci[:, 0], "hi": ci[:, 1]}) \
            .to_parquet(OUT / "sarimax_pronostico.parquet", index=False)

    # C. Tasa desapariciones pre/post 2024
    des = pd.read_parquet(TIDY / "hecho_desaparecidas.parquet")
    a = des["anio_hecho"].dropna()
    n_pre, t_pre = int(((a >= 2015) & (a <= 2023)).sum()), 9
    n_post, t_post = int(((a >= 2024) & (a <= 2025)).sum()), 2
    rr = (n_post / t_post) / (n_pre / t_pre)
    se = (1 / n_post + 1 / n_pre) ** 0.5
    met["tasa_desaparecidas"] = {
        "pre_2015_2023": n_pre, "post_2024_2025": n_post,
        "rate_ratio": round(rr, 2),
        "ic95": [round(float(np.exp(np.log(rr) - 1.96 * se)), 2),
                 round(float(np.exp(np.log(rr) + 1.96 * se)), 2)],
        "nota": "razon de tasas observadas; no explica causa"}

    (SEG / "resumen_series_seg.json").write_text(
        json.dumps(met, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(json.dumps(met, ensure_ascii=False, indent=2, default=str)[:1800])


if __name__ == "__main__":
    main()
