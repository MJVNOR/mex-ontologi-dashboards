"""Dashboard Contexto laboral proxy: ingresos por marginación 2020.

PO2SM (% con ingresos < 2 salarios mínimos) como proxy de ingresos a nivel
municipal (72 municipios de Sonora) y entidad (Sonora en el contexto de las
32 entidades). Corte único 2020, valores declarados por la fuente. No mide
empleo, vacantes, colocaciones ni desempleo.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
MARG = DATA / "marg_out"
st.set_page_config(page_title="Ingresos por marginación 2020", page_icon=":material/payments:",
                   layout="wide")
st.title("Contexto laboral proxy — ingresos por marginación 2020")
st.caption("Fuente: índices de marginación 2020, portal datos.sonora.gob.mx. "
           "Significados preparados mediante consultas a mex-ontologi. "
           "PO2SM = % de población con ingresos menores a 2 salarios mínimos. "
           "Es un proxy de ingresos, no una medición de empleo.")


def que(mensaje):
    st.caption(":material/insights: " + mensaje)


@st.cache_data
def load(name):
    return pd.read_parquet(MARG / name)


@st.cache_data
def significados():
    return pd.read_csv(DATA / "significados_marginacion.csv")


mun = load("municipios.parquet")
ent = load("entidades.parquet")
son = ent[ent["es_sonora"]].iloc[0]
import json as _json
met = _json.loads((DATA / "modelos" / "metricas_marginacion.json").read_text(encoding="utf-8"))

fuentes("marginacion", "marg_out/municipios.parquet", "marg_out/entidades.parquet")

k1, k2, k3, k4 = st.columns(4)
k1.metric("PO2SM Sonora", f"{son['PO2SM']:.1f}%", border=True)
k2.metric("Grado Sonora", str(son["GM_2020"]), border=True)
k3.metric("Mediana municipal PO2SM", f"{mun['PO2SM'].median():.1f}%", border=True)
k4.metric("Municipios", f"{len(mun):,}", border=True)
st.caption("La mediana municipal no pondera por población y los municipios grandes "
           "tienen PO2SM menor; por eso difiere del 63.2% estatal.")

t0, t1, t2, t3, t4 = st.tabs(["Hallazgos :material/auto_stories:",
                     "Municipios :material/location_city:",
                     "Entidades :material/public:",
                     "Ontología :material/hub:",
                     "Modelos :material/psychology:"])

with t0:
    st.header("Lo que los ingresos dicen (y lo que no) del trabajo en Sonora")
    que("Buscábamos medir el empleo. La ontología (89 conjuntos verificados) no "
        "tiene ninguno de empleo: este dashboard mide su proxy más cercano, el % "
        "con ingresos menores a 2 salarios mínimos (PO2SM, corte 2020). Todo lo que "
        "sigue vive dentro de ese límite.")
    st.subheader("Acto 1 — El punto de partida")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("Sonora está por debajo del promedio nacional, pero lejos del fondo")
            st.markdown("**Evidencia:** PO2SM 63.2%, lugar 22 de 32 (1 = mayor valor), "
                        "media de entidades 67.2%; grado Bajo, posición nacional 25 declarada. "
                        "(Ver en: Entidades)")
            st.caption("Límites: corte único 2020 con umbral de 2 SM de 2020; el lugar 22 es "
                       "orden por PO2SM calculado aquí, distinto de la posición 25 declarada "
                       "(orden por IM). No comparar con otros años.")
        with _c2:
            _e32 = ent[ent["NOM_ENT"].astype(str).str.strip().str.upper() != "NACIONAL"]
            _h1 = pd.DataFrame({"grupo": ["Sonora", "Media entidades", "Mediana entidades"],
                                "po2sm": [float(son["PO2SM"]), float(_e32["PO2SM"].mean()),
                                          float(_e32["PO2SM"].median())]})
            st.plotly_chart(px.bar(_h1, x="po2sm", y="grupo", orientation="h", height=260,
                                   color=["Sonora"] + ["Resto"] * 2,
                                   color_discrete_map={"Sonora": "#C44E52", "Resto": "#8A8A8A"},
                                   title="Sonora vs el país (PO2SM, 2020)",
                                   labels={"po2sm": "% < 2 SM", "grupo": "", "color": ""}),
                            width="stretch")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("El estado no es sus municipios")
            st.markdown("**Evidencia:** mediana municipal 70.5% vs 63.2% estatal; PO2SM "
                        "ponderado por población 63.8 ≈ 63.2 declarado. (Ver en: Municipios)")
            st.caption("Límites: la mediana no pondera; Hermosillo (936 mil hab., 47.2%) jala "
                       "el promedio. Diferencia explicada, no contradicción.")
        with _c2:
            _pond = float((mun["PO2SM"] * mun["POB_TOT"]).sum() / mun["POB_TOT"].sum())
            _h2 = pd.DataFrame({"medida": ["Mediana municipal", "Ponderado por población",
                                           "Estatal declarado"],
                                "po2sm": [float(mun["PO2SM"].median()), _pond,
                                          float(son["PO2SM"])]})
            st.plotly_chart(px.bar(_h2, x="po2sm", y="medida", orientation="h", height=260,
                                   title="Tres formas de resumir lo mismo (PO2SM, 2020)",
                                   labels={"po2sm": "% < 2 SM", "medida": ""}),
                            width="stretch")
    st.subheader("Acto 2 — El territorio")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("El rango es enorme y el grado no es el ingreso")
            st.markdown("**Evidencia:** 43.0% (Nacozari, Muy bajo) a 93.4% (Sáric, Bajo); "
                        "p5 53.8 · p95 87.3. (Ver en: Municipios)")
            st.caption("Límites: el grado combina 9 indicadores; leer PO2SM como "
                       "\"marginación\" es un error que estos dos casos exhiben.")
        with _c2:
            _h3 = px.strip(mun, x="PO2SM", height=260,
                           title="Cada punto es un municipio (PO2SM, 2020)",
                           labels={"PO2SM": "% < 2 SM"})
            _dest = pd.concat([mun.loc[[mun["PO2SM"].idxmax(), mun["PO2SM"].idxmin()]],
                               mun[mun["NOM_MUN"] == "Hermosillo"]])
            for _, _r in _dest.iterrows():
                _h3.add_annotation(x=float(_r["PO2SM"]), y=0, text=str(_r["NOM_MUN"]),
                                   showarrow=True, arrowhead=2)
            st.plotly_chart(_h3, width="stretch")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("Lo rural no es lo peor en este indicador")
            st.markdown("**Evidencia:** mediana rural (PL.5000 = 100%, n=45) 69.5% vs "
                        "no-rural (n=27) 75.7%. (Ver en: Municipios)")
            st.caption("Límites: descriptivo del corte, sin explicación (minería, "
                       "agricultura, migración — no lo sabemos y no lo afirmamos).")
        with _c2:
            _h4 = mun.assign(_rural=(mun["PL.5000"] == 100).map(
                {True: "Totalmente rural", False: "Con loc. ≥5 mil"})).groupby("_rural")[
                "PO2SM"].median().round(1).reset_index()
            st.plotly_chart(px.bar(_h4, x="PO2SM", y="_rural", orientation="h", height=260,
                                   title="Mediana PO2SM por ruralidad (2020)",
                                   labels={"PO2SM": "% < 2 SM", "_rural": ""}),
                            width="stretch")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("El índice corre al revés de lo que sugiere su nombre")
            st.markdown("**Evidencia:** menor IM_2020 = mayor marginación (Guerrero 10.99 "
                        "Muy alto → CDMX 23.14 Muy bajo); correlación IM–PO2SM r = −0.52. "
                        "(Ver en: Municipios)")
            st.caption("Límites: orientación documentada de la fuente, no interpretación; "
                       "la correlación es descriptiva, no causalidad.")
        with _c2:
            _h5 = mun.groupby("GM_2020")["PO2SM"].median().round(1).reset_index()
            _orden_gm = ["Muy bajo", "Bajo", "Medio", "Alto"]
            _h5["GM_2020"] = pd.Categorical(_h5["GM_2020"], _orden_gm, ordered=True)
            st.plotly_chart(px.bar(_h5.sort_values("GM_2020"), x="PO2SM", y="GM_2020",
                                   orientation="h", height=260,
                                   title="Mediana PO2SM por grado (2020)",
                                   labels={"PO2SM": "% < 2 SM", "GM_2020": "grado"}),
                            width="stretch")
    st.subheader("Acto 3 — El modelo (y su debilidad declarada)")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("Dos Sonoras por perfil de carencias")
            st.markdown("**Evidencia:** KMeans k=2 por silueta (0.51): 65 municipios "
                        "(mediana 69.3) vs 7 (mediana 83.9). (Ver en: Modelos)")
            st.caption("Límites: agrupación descriptiva de un corte; no acredita causas "
                       "ni pronostica.")
        with _c2:
            _s = met["segmentos"]
            _h6 = pd.DataFrame({"segmento": [f"Mayoría (n={_s['tamano'].get('0', _s['tamano'].get(0))})",
                                             f"Alta carencia (n={_s['tamano'].get('1', _s['tamano'].get(1))})"],
                                "mediana": [float(_s["po2sm_mediana_por_segmento"].get("0",
                                            _s["po2sm_mediana_por_segmento"].get(0))),
                                            float(_s["po2sm_mediana_por_segmento"].get("1",
                                            _s["po2sm_mediana_por_segmento"].get(1)))]})
            st.plotly_chart(px.bar(_h6, x="mediana", y="segmento", orientation="h", height=260,
                                   color="segmento",
                                   color_discrete_map={"Mayoría (n=65)": "#8A8A8A",
                                                       "Alta carencia (n=7)": "#C44E52"},
                                   title="Mediana PO2SM por segmento (2020)",
                                   labels={"mediana": "% < 2 SM", "segmento": ""}),
                            width="stretch")
    with st.container(border=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.subheader("Las carencias explican poco del ingreso")
            st.markdown("**Evidencia:** Ridge R² fuera de muestra 0.15, MAE 7.9; SHAP exacto "
                        "(err 1e-14) describe al modelo, no al mundo. (Ver en: Modelos)")
            st.caption("Límites: n=72, asociación exploratoria; coeficientes con "
                       "colinealidad no se leen como efectos.")
        with _c2:
            _h7 = pd.DataFrame({"modelo": ["Ridge OOF"],
                                 "r2": [float(met["po2sm_ridge"]["r2_oof"])]})
            _f7 = px.bar(_h7, x="r2", y="modelo", orientation="h", height=260, range_x=[0, 1],
                         title=f"R² fuera de muestra: {float(met['po2sm_ridge']['r2_oof']):.2f} de 1.0",
                         labels={"r2": "R²", "modelo": ""})
            _f7.add_vline(x=1.0, line_dash="dot", annotation_text="acuerdo perfecto")
            st.plotly_chart(_f7, width="stretch")
    st.subheader("Conclusiones (solo lo respaldado)")
    with st.container(border=True):
        st.markdown("**Firmes (certeza alta):** no hay medición de empleo en la ontología "
                    "(89 conjuntos); Sonora PO2SM 63.2%, lugar 22/32; la mediana municipal "
                    "(70.5%) no contradice al estatal (ponderado 63.8); el IM corre invertido; "
                    "el rango va 43.0–93.4 y el grado no es el ingreso.")
        st.markdown("**Con cautela (certeza moderada a baja):** lo rural no es lo peor "
                    "(69.5 vs 75.7, sin ajuste); dos perfiles de carencias (k=2, un corte); "
                    "las carencias explican poco del ingreso (R² 0.15).")
        st.markdown("**No respaldado:** causas, pronósticos, nada posterior a 2020, "
                    "inferencias a personas desde municipios, ni empleo medido.")
    st.subheader("Cierre sin conclusión forzada")
    with st.container(border=True):
        st.subheader("Procedencia y preguntas abiertas")
        st.markdown("Portal datos.sonora.gob.mx vía ontología mex-ontologi: 2 conjuntos, "
                    "6 recursos, 34 significados; valores declarados; fecha de carga no "
                    "documentada; series municipal y estatal de hojas distintas.")
        st.caption("Abierto: ¿qué significan los ceros exactos en carencias? ¿qué pasó "
                   "después de 2020? ¿cuándo se da de alta un conjunto real de empleo?")

with t1:
    fuentes("marginacion", "marg_out/municipios.parquet")
    que("PO2SM por municipio de Sonora en 2020: cada barra es un municipio y su "
        "altura el % con ingresos < 2 salarios mínimos. Valores declarados; no "
        "acreditan empleo ni cobertura de programa alguno.")
    st.caption("72/72 municipios: censo completo del corte 2020, sin incertidumbre "
               "muestral; la incertidumbre es de medición y constructo, no de muestreo.")
    orden = st.selectbox("Orden", ["PO2SM descendente", "PO2SM ascendente", "Alfabético"],
                         key="ord_mun")
    m = mun.copy()
    if orden == "PO2SM descendente":
        m = m.sort_values("PO2SM", ascending=False)
    elif orden == "PO2SM ascendente":
        m = m.sort_values("PO2SM", ascending=True)
    else:
        m = m.sort_values("NOM_MUN")
    _fmun = px.bar(m, x="PO2SM", y="NOM_MUN", color="GM_2020", orientation="h",
                     height=950,
                     title="PO2SM municipal va de 43% a 93% (Sonora, 2020)",
                     labels={"NOM_MUN": "municipio", "PO2SM": "% < 2 SM",
                             "GM_2020": "grado"})
    # ponytail: con color por trazos, el orden lo impone categoryarray, no el sort
    # (plotly dibuja la primera categoria abajo: se pasa la lista invertida)
    _fmun.update_yaxes(categoryorder="array",
                       categoryarray=m["NOM_MUN"].tolist()[::-1])
    st.plotly_chart(_fmun, width="stretch")
    que("Relación entre marginación e ingresos: cada punto es un municipio; a mayor "
        "grado de marginación, mayor PO2SM. Relación descriptiva, "
        "no causalidad. Nota: en esta fuente el IM_2020 es menor donde la "
        "marginación es mayor.")
    _r = float(mun[["IM_2020", "PO2SM"]].corr().iloc[0, 1])
    st.plotly_chart(px.scatter(mun, x="IM_2020", y="PO2SM", color="GM_2020",
                              hover_name="NOM_MUN", trendline="ols",
                              title=f"A mayor marginación, mayor PO2SM (r = {_r:.2f}, descriptivo)",
                              labels={"IM_2020": "IM_2020 (menor valor = mayor marginación)",
                                      "PO2SM": "% < 2 SM", "GM_2020": "grado"}),
                    width="stretch")
    que("Distribución municipal de PO2SM: dónde se concentra la mayoría de los "
        "municipios.")
    _h = px.histogram(mun, x="PO2SM", nbins=20,
                        title="La mitad de los municipios supera 70.5% de PO2SM",
                        labels={"PO2SM": "% < 2 SM"})
    _h.add_vline(x=float(mun["PO2SM"].median()), line_dash="dot",
                 annotation_text=f"mediana {mun['PO2SM'].median():.1f}%")
    _h.add_vline(x=float(mun["PO2SM"].mean()), line_dash="dash",
                 annotation_text=f"media {mun['PO2SM'].mean():.1f}%")
    st.plotly_chart(_h, width="stretch")
    grado = mun.groupby("GM_2020").agg(municipios=("PO2SM", "size"),
                                      po2sm_mediana=("PO2SM", "median")).reset_index()
    st.dataframe(grado, hide_index=True)
    st.caption("El grado no es el ingreso: Sáric tiene el PO2SM máximo (93.4%) con "
               "grado Bajo, y Nacozari el mínimo (43.0%) con grado Muy bajo.")
    que("Ruralidad e ingresos: 45 de los 72 municipios están totalmente en "
        "localidades de menos de 5 mil habitantes (PL.5000 = 100%). Cada caja "
        "resume la distribución de PO2SM del grupo. Descriptivo, sin causalidad.")
    m["rural"] = "Con localidades de 5 mil o más"
    m.loc[m["PL.5000"] == 100, "rural"] = "Totalmente rural (PL.5000 = 100%)"
    st.plotly_chart(px.box(m, x="rural", y="PO2SM", color="rural",
                           title="PO2SM según ruralidad del municipio",
                           labels={"rural": "grupo", "PO2SM": "% < 2 SM"}),
                    width="stretch")
    st.dataframe(m.groupby("rural")["PO2SM"].agg(
        municipios="size", mediana="median").round(1).reset_index(), hide_index=True)

with t2:
    fuentes("marginacion", "marg_out/entidades.parquet")
    que("Sonora frente a las demás entidades en 2020: cada barra es una entidad. "
        "La fila Nacional no trae IM/GM declarados y se excluye del orden por índice.")
    e = ent[ent["NOM_ENT"].str.strip().str.upper() != "NACIONAL"].copy()
    e["_resalta"] = (e["NOM_ENT"].astype(str).str.strip().str.upper() == "SONORA").map(
        {True: "Sonora", False: "Resto"})
    e = e.sort_values("PO2SM", ascending=True)
    _fent = px.bar(e, x="PO2SM", y="NOM_ENT",
                     color="_resalta", orientation="h", height=800,
                     color_discrete_map={"Sonora": "#C44E52", "Resto": "#8A8A8A"},
                     title="Sonora, lugar 22 de 32 en PO2SM (2020)",
                     labels={"NOM_ENT": "entidad", "PO2SM": "% < 2 SM", "_resalta": ""})
    _fent.update_yaxes(categoryorder="array", categoryarray=e["NOM_ENT"].tolist())
    st.plotly_chart(_fent, width="stretch")
    st.caption(f"Sonora: PO2SM {son['PO2SM']:.1f}%, grado {son['GM_2020']}, "
               f"posición nacional {son['POSICION']:.0f}.")
    rank = int((e["PO2SM"] > float(son["PO2SM"])).sum()) + 1
    que(f"Sonora ocupa el lugar {rank} de {len(e)} en PO2SM (1 = mayor valor), "
        f"por debajo de la media de las entidades ({e['PO2SM'].mean():.1f}%). "
        "Comparación descriptiva del corte 2020.")

with t3:
    st.dataframe(significados(), hide_index=True)

with t4:
    seg = pd.read_parquet(DATA / "modelos" / "inferencias" / "segmentos_marg.parquet")
    que("Segmentos municipales por perfil de carencias (KMeans + PCA, descriptivo): "
        "cada punto es un municipio. No acredita causas ni pronostica nada.")
    s = met["segmentos"]
    st.caption(f"k = {s['k']} por silueta {s['silueta_por_k']} · "
               f"tamaños {s['tamano']} · PO2SM mediana por segmento {s['po2sm_mediana_por_segmento']}")
    st.plotly_chart(px.scatter(seg, x="pca1", y="pca2", color=seg["segmento"].astype(str),
                              hover_name="NOM_MUN",
                              title="Segmentos de municipios (PCA)",
                              labels={"pca1": "PC1", "pca2": "PC2", "color": "segmento"}),
                    width="stretch")
    que("Descomposición exploratoria de PO2SM ~ carencias (Ridge + KFold): "
        "asociación, no causalidad. R² fuera de muestra bajo = las carencias "
        "explican poco de PO2SM linealmente.")
    r = met["po2sm_ridge"]
    st.caption(f"R² OOF {r['r2_oof']} · MAE OOF {r['mae_oof']} · n = {r['n']}. {r['advertencia']}")
    coef = pd.DataFrame({"carencia": list(r["coeficientes"]),
                         "coef": list(r["coeficientes"].values())}).sort_values("coef")
    st.plotly_chart(px.bar(coef, x="coef", y="carencia", orientation="h",
                           title="Coeficientes Ridge estandarizados (exploratorio)",
                           labels={"coef": "coeficiente", "carencia": "carencia"}),
                    width="stretch")
    que("Observado vs estimado fuera de muestra: cada punto es un municipio; la "
        "diagonal es acuerdo perfecto. La dispersión muestra lo que el R² ya dice: "
        "ajuste lineal débil.")
    oof = pd.read_parquet(DATA / "modelos" / "inferencias" / "po2sm_oof.parquet")
    _fig = px.scatter(oof, x="po2sm_observado", y="po2sm_oof", hover_name="NOM_MUN",
                      title="PO2SM observado vs OOF por municipio",
                      labels={"po2sm_observado": "observado", "po2sm_oof": "estimado OOF"})
    _lo, _hi = float(oof[["po2sm_observado", "po2sm_oof"]].min().min()), \
        float(oof[["po2sm_observado", "po2sm_oof"]].max().max())
    _fig.add_shape(type="line", x0=_lo, y0=_lo, x1=_hi, y1=_hi,
                   line={"dash": "dot"})
    st.plotly_chart(_fig, width="stretch")
    que("Quién es quién en cada segmento: municipios por segmento con su PO2SM.")
    st.dataframe(seg.sort_values(["segmento", "PO2SM"], ascending=[True, False])
                    [["segmento", "NOM_MUN", "GM_2020", "PO2SM"]], hide_index=True)
    que("Atribución global SHAP del Ridge (media de |SHAP| por carencia, n=72): "
        "replica el ranking de coeficientes; describe al modelo, no causalidad.")
    _sh = pd.read_parquet(DATA / "modelos" / "shap" / "valores_po2sm_ridge.parquet")
    _car = ["ANALF", "SBASC", "OVSDE", "OVSEE", "OVSAE", "OVPT", "VHAC", "PL.5000"]
    _g = pd.DataFrame({"carencia": _car,
                       "shap_medio_abs": [_sh[c].abs().mean() for c in _car]
                       }).sort_values("shap_medio_abs")
    st.plotly_chart(px.bar(_g, x="shap_medio_abs", y="carencia", orientation="h",
                           title="SHAP medio absoluto por carencia (Ridge)",
                           labels={"shap_medio_abs": "media |SHAP| (pp PO2SM)",
                                   "carencia": "carencia"}),
                    width="stretch")
    que("Por qué el modelo estima tal PO2SM para un municipio: cascada desde el "
        "promedio (base) hasta la estimación, carencia por carencia.")
    _mun = st.selectbox("Municipio (waterfall SHAP)", sorted(_sh["NOM_MUN"].unique()),
                        index=sorted(_sh["NOM_MUN"].unique()).index("Hermosillo")
                        if "Hermosillo" in set(_sh["NOM_MUN"]) else 0)
    _row = _sh[_sh["NOM_MUN"] == _mun].iloc[0]
    _ord = sorted(_car, key=lambda c: -abs(float(_row[c])))
    _wf = go.Figure(go.Waterfall(
        x=["base"] + _ord + ["estimación"],
        y=[float(_row["base_value"])] + [float(_row[c]) for c in _ord] + [0],
        measure=["absolute"] + ["relative"] * len(_car) + ["total"]))
    _wf.update_layout(title=f"Waterfall SHAP — {_mun} (estima {float(_row['pred_modelo']):.1f}%)")
    st.plotly_chart(_wf, width="stretch")
