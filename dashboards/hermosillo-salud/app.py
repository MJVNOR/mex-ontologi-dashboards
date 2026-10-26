"""Dashboard Salud Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Fuente: 7 conjuntos del grupo Salud del portal datos.sonora.gob.mx, identificados
por consultas a mex-ontologia; variables, significados y evidencia
en data/significados_salud.csv y data/procedencia_salud.json. Descarga: scripts/descargar_salud.py.
Filtro Hermosillo: scripts/preprocesar_hmo.py -> data/hmo_*.parquet.
"""

import json
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

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    ["Series anuales", "Urgencias / Egresos", "Consulta externa",
     "Nacimientos / Defunciones", "Vigilancia", "Pronóstico", "Ontología"])

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
        "reparto por sexo dentro de cada grupo (barras al 100%). La brecha hacia "
        "mujeres se concentra entre 15 y 49 años e incluso se invierte en infancia; "
        "descriptivo, sin atribuir causa.")
    c1, c2 = st.columns(2)
    ce_edad = con_f.groupby("Grupo_Edad")["Total"].sum().reset_index().sort_values("Total")
    c1.plotly_chart(px.bar(ce_edad, x="Total", y="Grupo_Edad", orientation="h",
                           title="Consulta externa por grupo de edad"), use_container_width=True)
    sx = con_f.groupby(["Grupo_Edad", "Sexo"])["Total"].sum().reset_index()
    sx = sx[sx.Sexo.isin(["HOMBRE", "MUJER"])]
    sx["pct"] = sx["Total"] / sx.groupby("Grupo_Edad")["Total"].transform("sum") * 100
    c2.plotly_chart(px.bar(sx, x="Grupo_Edad", y="pct", color="Sexo", barmode="stack",
                           title="Consulta externa: sexo por grupo de edad (%)",
                           labels={"pct": "% del grupo"}),
                    use_container_width=True)
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
    que("Vigilancia epidemiológica 2022 en HMO (36 semanas con reporte): valores de la columna acumulado por diagnóstico "
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
    que("Pronóstico mensual 2023 por servicio (mejor variante por servicio "
        "entrenada en 2018-2020: urgencias = tendencia+estacionalidad, consulta = "
        "Ridge mensual; variante elegida por ganar en 2021, así que su error es "
        "optimista): la línea es la estimación y la banda ±1 desviación entre años. "
        "Son ESTIMACIONES, no datos oficiales; 2021-2022 vienen parciales en la fuente.")
    import plotly.graph_objects as go
    fc = pd.read_parquet(DATA / "modelos" / "inferencias" / "pronostico_mensual.parquet")
    met = json.loads((DATA / "modelos" / "metricas_salud.json").read_text(encoding="utf-8"))
    fig = go.Figure()
    for serv, color in (("urgencias", "blue"), ("consulta", "red")):
        d = fc[fc.servicio == serv].sort_values("mes")
        fig.add_trace(go.Scatter(x=d.mes, y=d.pronostico, mode="lines+markers",
                                 name=f"{serv} (est.)", line=dict(color=color)))
        fig.add_trace(go.Scatter(x=d.mes, y=d.pronostico + d.banda, mode="lines",
                                 line=dict(width=0), showlegend=False,
                                 hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=d.mes, y=(d.pronostico - d.banda).clip(lower=0),
                                 mode="lines", line=dict(width=0), showlegend=False,
                                 fill="tonexty", fillcolor=f"rgba(0,0,255,0.1)" if serv == "urgencias"
                                 else "rgba(255,0,0,0.1)", hoverinfo="skip"))
    fig.update_layout(title="Perfil estacional mensual 2023 (referencia, no pronóstico)",
                      xaxis_title="Mes", yaxis_title="Atenciones estimadas")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Error medido en 2021: urgencias MAE {met['urgencias']['mae']} "
               f"(MAPE {met['urgencias']['mape_pct']}%, R² {met['urgencias']['r2']}, "
               f"variante {met['urgencias']['modelo']}), "
               f"consulta MAE {met['consulta']['mae']} "
               f"(MAPE {met['consulta']['mape_pct']}%, R² {met['consulta']['r2']}, "
               f"variante {met['consulta']['modelo']}). "
               "R² negativo = peor que predecir el promedio mensual: úsese como "
               "perfil estacional de referencia, no como pronóstico operativo.")
    que("Semanas epidemiológicas atípicas (IsolationForest sobre la suma de la columna "
        "acumulado por semana): los puntos rojos son semanas cuyo valor se aparta del patrón "
        "habitual y ameritan revisión. Nota de método: IQR univariado solo marca 3 y 4; "
        "la 15 la detecta el bosque por alejarse del patrón conjunto, no por extremo simple.")
    ano = pd.read_parquet(DATA / "modelos" / "inferencias" / "anomalias_vigilancia.parquet")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=ano.no_semana, y=ano.acumulado, mode="lines",
                              name="Suma de acumulado"))
    flag = ano[ano.anomalia == -1]
    fig2.add_trace(go.Scatter(x=flag.no_semana, y=flag.acumulado, mode="markers",
                              marker=dict(color="red", size=10), name="Atípica"))
    fig2.update_layout(title="Vigilancia HMO: semanas atípicas detectadas",
                       xaxis_title="Semana epidemiológica", yaxis_title="Suma de acumulado")
    st.plotly_chart(fig2, use_container_width=True)

with t7:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "significados documentales; las correspondencias con columnas se muestran por separado y requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_salud_hermosillo.csv", "text/csv")
    fuentes("salud")
