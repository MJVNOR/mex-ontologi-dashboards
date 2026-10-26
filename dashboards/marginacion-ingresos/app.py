"""Dashboard Contexto laboral proxy: ingresos por marginación 2020.

PO2SM (% con ingresos < 2 salarios mínimos) como proxy de ingresos a nivel
municipal (72 municipios de Sonora) y entidad (Sonora vs. nacional).
Corte único 2020, valores declarados por la fuente. No mide empleo,
vacantes, colocaciones ni desempleo.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import plotly.express as px
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

fuentes("marginacion", "marg_out/municipios.parquet", "marg_out/entidades.parquet")

k1, k2, k3, k4 = st.columns(4)
k1.metric("PO2SM Sonora", f"{son['PO2SM']:.1f}%", border=True)
k2.metric("Grado Sonora", str(son["GM_2020"]), border=True)
k3.metric("Mediana municipal PO2SM", f"{mun['PO2SM'].median():.1f}%", border=True)
k4.metric("Municipios", f"{len(mun):,}", border=True)

t1, t2, t3 = st.tabs(["Municipios :material/location_city:",
                     "Entidades :material/public:",
                     "Ontología :material/hub:"])

with t1:
    fuentes("marginacion", "marg_out/municipios.parquet")
    que("PO2SM por municipio de Sonora en 2020: cada barra es un municipio y su "
        "altura el % con ingresos < 2 salarios mínimos. Valores declarados; no "
        "acreditan empleo ni cobertura de programa alguno.")
    orden = st.selectbox("Orden", ["PO2SM descendente", "PO2SM ascendente", "Alfabético"],
                         key="ord_mun")
    m = mun.copy()
    if orden == "PO2SM descendente":
        m = m.sort_values("PO2SM", ascending=False)
    elif orden == "PO2SM ascendente":
        m = m.sort_values("PO2SM", ascending=True)
    else:
        m = m.sort_values("NOM_MUN")
    st.plotly_chart(px.bar(m, x="NOM_MUN", y="PO2SM", color="GM_2020",
                           title="PO2SM por municipio (Sonora, 2020)",
                           labels={"NOM_MUN": "municipio", "PO2SM": "% < 2 SM",
                                   "GM_2020": "grado"}),
                    width="stretch")
    que("Relación entre marginación e ingresos: cada punto es un municipio; a mayor "
        "índice de marginación (IM_2020), mayor PO2SM. Correlación descriptiva, "
        "no causalidad.")
    st.plotly_chart(px.scatter(mun, x="IM_2020", y="PO2SM", color="GM_2020",
                              hover_name="NOM_MUN",
                              title="IM_2020 vs PO2SM por municipio",
                              labels={"IM_2020": "índice de marginación",
                                      "PO2SM": "% < 2 SM", "GM_2020": "grado"}),
                    width="stretch")
    que("Distribución municipal de PO2SM: dónde se concentra la mayoría de los "
        "municipios.")
    st.plotly_chart(px.histogram(mun, x="PO2SM", nbins=20,
                                title="Distribución de PO2SM municipal"),
                    width="stretch")
    grado = mun.groupby("GM_2020").agg(municipios=("PO2SM", "size"),
                                      po2sm_mediana=("PO2SM", "median")).reset_index()
    st.dataframe(grado, hide_index=True)

with t2:
    fuentes("marginacion", "marg_out/entidades.parquet")
    que("Sonora frente a las demás entidades en 2020: cada barra es una entidad. "
        "La fila Nacional no trae IM/GM declarados y se excluye del orden por índice.")
    e = ent[ent["NOM_ENT"].str.strip().str.upper() != "NACIONAL"].copy()
    st.plotly_chart(px.bar(e.sort_values("PO2SM", ascending=False), x="NOM_ENT", y="PO2SM",
                           title="PO2SM por entidad (2020)",
                           labels={"NOM_ENT": "entidad", "PO2SM": "% < 2 SM"}),
                    width="stretch")
    st.caption(f"Sonora: PO2SM {son['PO2SM']:.1f}%, grado {son['GM_2020']}, "
               f"posición nacional {son['POSICION']:.0f}.")

with t3:
    st.dataframe(significados(), hide_index=True)
