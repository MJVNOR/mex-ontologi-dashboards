"""Dashboard Salud Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Fuente: 7 conjuntos del grupo Salud del portal datos.sonora.gob.mx, identificados
por consultas a mex-ontologia; variables, significados y evidencia
en data/significados_salud.csv y data/procedencia_salud.json. Descarga: scripts/descargar_salud.py.
Filtro Hermosillo: scripts/preprocesar_hmo.py -> data/hmo_*.parquet.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
st.set_page_config(page_title="Salud Hermosillo", layout="wide")
st.title("Salud en Hermosillo — datos abiertos de Sonora")
st.caption("Fuente: portal datos.sonora.gob.mx, grupo Salud (7 conjuntos). "
           "Fuentes y significados preparados mediante consultas a mex-ontologi. "
           "Los totales son los declarados por la fuente, sin inferir cobertura.")


def que(mensaje):
    st.caption("📊 " + mensaje)


@st.cache_data
def load(name):
    return pd.read_parquet(DATA / name)


@st.cache_data
def significados():
    return pd.read_csv(DATA / "significados_salud.csv")


def year_col(df):
    for c in df.columns:
        s = str(c).lower()
        if s in ("año", "a?o") or (s.startswith("a") and s.endswith("o") and len(s) <= 4):
            return c
    return "Year" if "Year" in df.columns else df.columns[0]


urg = load("hmo_urgencias.parquet")
egr = load("hmo_egresos.parquet")
con = load("hmo_consulta.parquet")
nac = load("hmo_nacimientos.parquet")
defu = load("hmo_defunciones.parquet")
vig = load("hmo_vigilancia.parquet")
ins = load("hmo_inspecciones.parquet")

yu, ye = year_col(urg), year_col(egr)
anios = sorted(set(urg[yu].dropna().unique()) | set(egr[ye].dropna().unique()))
sel = st.sidebar.multiselect("Años (urgencias / egresos / consulta)", anios, default=anios)
if sel:
    urg_f = urg[urg[yu].isin(sel)]
    egr_f = egr[egr[ye].isin(sel)]
    con_f = con[con["Year"].isin([a for a in sel if a in set(con["Year"].unique())])]
else:
    urg_f, egr_f, con_f = urg, egr, con

fuentes("salud", "hmo_urgencias.parquet", "hmo_egresos.parquet", "hmo_consulta.parquet", "hmo_nacimientos.parquet", "hmo_defunciones.parquet")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Urgencias", f"{int(urg_f['Total_Urgencias'].sum()):,}")
k2.metric("Egresos hosp.", f"{int(egr_f['Total_Egresos'].sum()):,}")
k3.metric("Consulta externa", f"{int(con_f['Total'].sum()):,}")
k4.metric("Nacimientos 2022 (residencia HMO)", f"{len(nac):,}")
k5.metric("Defunciones 2022 (residencia HMO)", f"{len(defu):,}")

t1, t2, t3, t4, t5, t6 = st.tabs(
    ["Series anuales", "Urgencias / Egresos", "Consulta externa",
     "Nacimientos / Defunciones", "Vigilancia", "Ontología"])

with t1:
    fuentes("salud", 'hmo_urgencias.parquet', 'hmo_egresos.parquet', 'hmo_consulta.parquet')
    que("Barras agrupadas por año: compara el volumen anual de urgencias, egresos "
        "hospitalarios y consulta externa en Hermosillo. No se atribuyen causas a las variaciones ni se presume cobertura anual completa.")
    s = pd.DataFrame({
        "Urgencias": urg_f.groupby(yu)["Total_Urgencias"].sum(),
        "Egresos": egr_f.groupby(ye)["Total_Egresos"].sum(),
        "Consulta externa": con_f.groupby("Year")["Total"].sum(),
    }).reset_index().melt(id_vars="index", var_name="serie", value_name="total")
    s = s.rename(columns={"index": "año"})
    st.plotly_chart(px.bar(s, x="año", y="total", color="serie", barmode="group",
                           title="Atenciones en Hermosillo por año"), use_container_width=True)
    st.caption("Egresos incluye pocos registros 2015-2017 tal como los declara la fuente; "
               "el grueso es 2018-2022.")

with t2:
    fuentes("salud", 'hmo_urgencias.parquet', 'hmo_egresos.parquet')
    c1, c2 = st.columns(2)
    que("Izquierda: los 10 diagnósticos (CIE-10) con más atenciones de urgencias en "
        "Hermosillo. Derecha: lo mismo para egresos hospitalarios. Permite ver qué "
        "padecimientos presionan cada servicio.")
    top_u = urg_f.groupby("CIE10_Descrip")["Total_Urgencias"].sum().nlargest(10).reset_index()
    c1.plotly_chart(px.bar(top_u, x="Total_Urgencias", y="CIE10_Descrip", orientation="h",
                           title="Urgencias: top 10 diagnósticos"), use_container_width=True)
    top_e = egr_f.groupby("CIE10_Descrip")["Total_Egresos"].sum().nlargest(10).reset_index()
    c2.plotly_chart(px.bar(top_e, x="Total_Egresos", y="CIE10_Descrip", orientation="h",
                           title="Egresos: top 10 diagnósticos"), use_container_width=True)
    que("Pasteles: reparto por sexo de cada servicio. Las etiquetas son las que declara "
        "la fuente (en egresos conviven 'Hombre/Masculino' y 'Mujer/Femenino').")
    c1.plotly_chart(px.pie(urg_f.groupby("Sexo")["Total_Urgencias"].sum().reset_index(),
                           names="Sexo", values="Total_Urgencias",
                           title="Urgencias por sexo"), use_container_width=True)
    c2.plotly_chart(px.pie(egr_f.groupby("Sexo")["Total_Egresos"].sum().reset_index(),
                           names="Sexo", values="Total_Egresos",
                           title="Egresos por sexo (etiquetas de la fuente)"), use_container_width=True)

with t3:
    fuentes("salud", 'hmo_consulta.parquet')
    que("Izquierda: consultas por grupo de edad (de menor a mayor volumen). Derecha: "
        "reparto por sexo. Muestran qué población usa más la consulta externa.")
    c1, c2 = st.columns(2)
    ce_edad = con_f.groupby("Grupo_Edad")["Total"].sum().reset_index().sort_values("Total")
    c1.plotly_chart(px.bar(ce_edad, x="Total", y="Grupo_Edad", orientation="h",
                           title="Consulta externa por grupo de edad"), use_container_width=True)
    c2.plotly_chart(px.pie(con_f.groupby("Sexo")["Total"].sum().reset_index(),
                           names="Sexo", values="Total",
                           title="Consulta externa por sexo"), use_container_width=True)
    que("Los 10 establecimientos con más consultas en Hermosillo: dónde se concentra "
        "la atención ambulatoria.")
    top_est = con_f.groupby("Nombre_Establecimiento")["Total"].sum().nlargest(10).reset_index()
    st.plotly_chart(px.bar(top_est, x="Total", y="Nombre_Establecimiento", orientation="h",
                           title="Consulta externa: top 10 establecimientos"), use_container_width=True)

with t4:
    fuentes("salud", 'hmo_nacimientos.parquet', 'hmo_defunciones.parquet')
    que("Nacimientos 2022 (madres residentes en HMO): edad de la madre y peso del "
        "recién nacido en gramos. Defunciones 2022 (residentes): edad al fallecer y "
        "top 10 causas básicas (CIE). Son registros individuales, no agregados.")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.histogram(nac, x="EDAD", nbins=30, title="Nacimientos: edad de la madre"),
                    use_container_width=True)
    c1.plotly_chart(px.histogram(nac, x="PESO", nbins=40, title="Nacimientos: peso del RN (g)"),
                    use_container_width=True)
    c2.plotly_chart(px.histogram(defu, x="EDAD", nbins=40,
                                 title="Defunciones: edad"), use_container_width=True)
    top_causa = defu.groupby("CIECAUSABASICAD").size().nlargest(10).reset_index(name="n")
    c2.plotly_chart(px.bar(top_causa, x="n", y="CIECAUSABASICAD", orientation="h",
                           title="Defunciones: top 10 causas básicas"), use_container_width=True)

with t5:
    fuentes("salud", 'hmo_vigilancia.parquet', 'hmo_inspecciones.parquet')
    que("Vigilancia epidemiológica 2022 en HMO: valores de la columna acumulado por diagnóstico "
        "(lideran infecciones respiratorias agudas y COVID-19) y suma de esos valores por "
        "semana epidemiológica, sin interpretar estos agregados como incidencia semanal.")
    top_v = vig.groupby("des_diagno")["acumulado"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_v, x="acumulado", y="des_diagno", orientation="h",
                           title="Vigilancia HMO: suma de valores de acumulado por diagnóstico"),
                    use_container_width=True)
    sem = vig.groupby("no_semana")["acumulado"].sum().reset_index()
    st.plotly_chart(px.line(sem, x="no_semana", y="acumulado",
                            title="Vigilancia HMO: suma de acumulado por semana declarada"),
                    use_container_width=True)
    if len(ins):
        que("Tabla de las 30 inspecciones sanitarias de PROAES realizadas en Hermosillo "
            "(3er trimestre 2021): fecha, actividad del lugar y motivo.")
        st.write("Inspecciones PROAES en Hermosillo (3er trim. 2021):", len(ins))
        st.dataframe(ins[["FECHA", "ACTIVIDAD", "MOTIVO", "MUNICIPIO"]], use_container_width=True)

with t6:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "significados documentales; las correspondencias con columnas se muestran por separado y requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_salud_hermosillo.csv", "text/csv")
    fuentes("salud")
