"""Dashboard Educacion Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Becas con filtro municipal (HMO); matricula, titulados, egresados, nuevo
ingreso, reprobacion y aprovechamiento institucionales UTH (radicada en
Hermosillo); capacitacion SEC estatal. Totales declarados por la fuente.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
EDU = DATA / "edu_hmo"
st.set_page_config(page_title="Educación Hermosillo", layout="wide")
st.title("Educación en Hermosillo — datos abiertos de Sonora")
st.caption("Fuente: portal datos.sonora.gob.mx, grupo Educación (20 conjuntos). "
           "Identificación y significados vía ontología mex-ontologi (MCP). "
           "UTH = Universidad Tecnológica de Hermosillo (datos institucionales).")


@st.cache_data
def load(name):
    return pd.read_parquet(EDU / name)


@st.cache_data
def significados():
    return pd.read_csv(DATA / "significados_edu.csv")


bec = load("becas_hmo.parquet")
mat = load("matriculas_uth_hmo.parquet")
tit = load("titulados_uth.parquet")
egr = load("egresados_uth.parquet")
ing = load("nuevo_ingreso_uth.parquet")
rep = load("reprobacion_uth.parquet")

anios = sorted(bec["anio"].unique())
sel = st.sidebar.multiselect("Años (becas)", anios, default=anios)
bec_f = bec[bec["anio"].isin(sel)] if sel else bec

k1, k2, k3, k4 = st.columns(4)
k1.metric("Becas HMO", f"{len(bec_f):,}", f"${int(bec_f['importe'].sum()):,}")
k2.metric("Matrícula UTH HMO 2022-2", f"{len(mat):,}")
k3.metric("Titulados UTH 22-25", f"{int(tit['n'].sum()):,}")
k4.metric("Egresados UTH 22-25", f"{int(egr['n'].sum()):,}")

t1, t2, t3, t4, t5 = st.tabs(
    ["Becas", "Trayectoria UTH", "Reprobación", "Matrícula", "Ontología"])

with t1:
    s = bec_f.groupby("anio").agg(becas=("importe", "size"),
                                   importe=("importe", "sum")).reset_index()
    st.plotly_chart(px.bar(s, x="anio", y="becas", title="Becas HMO por año"), use_container_width=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(bec_f.groupby("nivel").size().reset_index(name="n"),
                           names="nivel", values="n", title="Becas por nivel"), use_container_width=True)
    c2.plotly_chart(px.pie(bec_f.groupby("genero").size().reset_index(name="n"),
                           names="genero", values="n", title="Becas por género"), use_container_width=True)
    top_esc = bec_f.groupby("escuela")["importe"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_esc, x="importe", y="escuela", orientation="h",
                           title="Top 12 escuelas por importe acumulado"), use_container_width=True)

with t2:
    tray = pd.concat([
        tit.assign(etapa="Titulados"), egr.assign(etapa="Egresados"),
        ing.assign(etapa="Nuevo ingreso")])
    st.plotly_chart(px.bar(tray.groupby(["anio", "etapa"])["n"].sum().reset_index(),
                           x="anio", y="n", color="etapa", barmode="group",
                           title="Trayectoria UTH por corte"), use_container_width=True)
    c1, c2 = st.columns(2)
    for df, nom, col in ((tit, "Titulados", c1), (egr, "Egresados", c2)):
        top = df.groupby("programa")["n"].sum().nlargest(10).reset_index()
        col.plotly_chart(px.bar(top, x="n", y="programa", orientation="h",
                               title=f"{nom}: top 10 programas"), use_container_width=True)

with t3:
    idx = [c for c in rep.columns if "16VA" in c.upper() and "REPROB" in c.upper()][0]
    mat_col = [c for c in rep.columns if "PROGRAMA" in c.upper()][0]
    top_r = rep.groupby(mat_col)[idx].mean().sort_values(ascending=False).head(15)
    top_r = top_r.reset_index().rename(columns={idx: "indice"})
    st.plotly_chart(px.bar(top_r, x="indice", y=mat_col, orientation="h",
                           title="Reprobación: mayor índice promedio sem. 16"), use_container_width=True)
    st.plotly_chart(px.histogram(rep, x=idx, nbins=30,
                                 title="Distribución del índice de reprobación"), use_container_width=True)

with t4:
    uni = [c for c in mat.columns if "Unidad" in str(c)][0]
    sexo = [c for c in mat.columns if str(c).strip().lower() == "sexo"][0]
    edad = [c for c in mat.columns if str(c).strip().lower() == "edad"][0]
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(mat.groupby(uni).size().reset_index(name="n"),
                           names=uni, values="n",
                           title="Matrícula por unidad académica"), use_container_width=True)
    c2.plotly_chart(px.pie(mat.groupby(sexo).size().reset_index(name="n"),
                           names=sexo, values="n", title="Matrícula por sexo"), use_container_width=True)
    st.plotly_chart(px.histogram(mat, x=edad, nbins=25,
                                 title="Matrícula UTH HMO: edad"), use_container_width=True)

with t5:
    sig = significados()
    st.write("Variables y significados documentados en la ontología (mex-ontologi).")
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_edu_hermosillo.csv", "text/csv")
