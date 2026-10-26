"""Dashboard Educacion Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Becas con filtro municipal (HMO); matricula, titulados, egresados, nuevo
ingreso, reprobacion y aprovechamiento institucionales UTH (radicada en
Hermosillo); capacitacion SEC estatal. Totales declarados por la fuente.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
EDU = DATA / "edu_hmo"
st.set_page_config(page_title="Educación Hermosillo", layout="wide")
st.title("Educación en Hermosillo — datos abiertos de Sonora")
st.caption("Fuente: archivos seleccionados del portal datos.sonora.gob.mx. "
           "Fuentes y significados preparados mediante consultas a mex-ontologi. "
           "UTH = Universidad Tecnológica de Hermosillo (datos institucionales).")


def que(mensaje):
    st.caption("📊 " + mensaje)


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

fuentes("edu", "edu_hmo/becas_hmo.parquet", "edu_hmo/matriculas_uth_hmo.parquet", "edu_hmo/titulados_uth.parquet", "edu_hmo/egresados_uth.parquet")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Becas HMO", f"{len(bec_f):,}", f"${int(bec_f['importe'].sum()):,}")
k2.metric("Matrícula UTH HMO 2022-2", f"{len(mat):,}")
k3.metric("Titulados UTH 22-25", f"{int(tit['n'].sum()):,}")
k4.metric("Egresados UTH 22-25", f"{int(egr['n'].sum()):,}")

t1, t2, t3, t4, t5 = st.tabs(
    ["Becas", "Trayectoria UTH", "Reprobación", "Matrícula", "Ontología"])

with t1:
    fuentes("edu", 'edu_hmo/becas_hmo.parquet')
    que("Becas autorizadas a residentes de Hermosillo por año (2021-2025): cada barra "
        "es un año y su altura el número de becas. Cuenta registros publicados; no acredita cobertura del programa.")
    s = bec_f.groupby("anio").agg(becas=("importe", "size"),
                                   importe=("importe", "sum")).reset_index()
    st.plotly_chart(px.bar(s, x="anio", y="becas", title="Becas HMO por año"),
                    use_container_width=True)
    que("Reparto de las becas por nivel educativo (básico vs. medio superior y "
        "superior) y por género declarado. Cada rebanada es la proporción del total.")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(bec_f.groupby("nivel").size().reset_index(name="n"),
                           names="nivel", values="n", title="Becas por nivel"),
                    use_container_width=True)
    c2.plotly_chart(px.pie(bec_f.groupby("genero").size().reset_index(name="n"),
                           names="genero", values="n", title="Becas por género"),
                    use_container_width=True)
    que("Las 12 escuelas con mayor importe acumulado en becas: dónde se concentra "
        "el recurso del programa en Hermosillo.")
    top_esc = bec_f.groupby("escuela")["importe"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_esc, x="importe", y="escuela", orientation="h",
                           title="Top 12 escuelas por importe acumulado"),
                    use_container_width=True)

with t2:
    fuentes("edu", 'edu_hmo/titulados_uth.parquet', 'edu_hmo/egresados_uth.parquet', 'edu_hmo/nuevo_ingreso_uth.parquet')
    que("Comparativa por corte de las tres etapas de la trayectoria UTH: nuevo ingreso, "
        "egresados y titulados. Cada grupo de barras es un periodo; permite ver la "
        "volumen de cada serie institucional. No hay seguimiento de las mismas personas ni tasas de transición.")
    tray = pd.concat([
        tit.assign(etapa="Titulados"), egr.assign(etapa="Egresados"),
        ing.assign(etapa="Nuevo ingreso")])
    st.plotly_chart(px.bar(tray.groupby(["anio", "etapa"])["n"].sum().reset_index(),
                           x="anio", y="n", color="etapa", barmode="group",
                           title="Trayectoria UTH por corte"),
                    use_container_width=True)
    que("Los 10 programas educativos con más titulados y con más egresados "
        "(2022-2025): qué carreras aportan más profesionistas en la UTH Hermosillo.")
    c1, c2 = st.columns(2)
    for df, nom, col in ((tit, "Titulados", c1), (egr, "Egresados", c2)):
        top = df.groupby("programa")["n"].sum().nlargest(10).reset_index()
        col.plotly_chart(px.bar(top, x="n", y="programa", orientation="h",
                               title=f"{nom}: top 10 programas"),
                         use_container_width=True)

with t3:
    fuentes("edu", 'edu_hmo/reprobacion_uth.parquet')
    que("Categorías de la fuente con mayor promedio aritmético del índice de reprobación de semana 16 "
        "(2022, presencial y remota), sin ponderación. El "
        "histograma muestra cómo se distribuye ese índice entre los registros disponibles.")
    idx = [c for c in rep.columns if "16VA" in c.upper() and "REPROB" in c.upper()][0]
    mat_col = [c for c in rep.columns if "PROGRAMA" in c.upper()][0]
    top_r = rep.groupby(mat_col)[idx].mean().sort_values(ascending=False).head(15)
    top_r = top_r.reset_index().rename(columns={idx: "indice"})
    st.plotly_chart(px.bar(top_r, x="indice", y=mat_col, orientation="h",
                           title="Reprobación: mayor índice promedio sem. 16"),
                    use_container_width=True)
    st.plotly_chart(px.histogram(rep, x=idx, nbins=30,
                                 title="Distribución del índice de reprobación"),
                    use_container_width=True)

with t4:
    fuentes("edu", 'edu_hmo/matriculas_uth_hmo.parquet')
    que("Registros de matrícula UTH seleccionados por unidad o municipio Hermosillo: reparto por unidad "
        "académica y por sexo, histograma de edades y periodo escolar de ingreso. "
        "Describe quiénes estudian en la universidad.")
    uni = [c for c in mat.columns if "Unidad" in str(c)][0]
    sexo = [c for c in mat.columns if str(c).strip().lower() == "sexo"][0]
    edad = [c for c in mat.columns if str(c).strip().lower() == "edad"][0]
    ping = [c for c in mat.columns
            if "periodo" in str(c).lower() and "ingreso" in str(c).lower()][0]
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(mat.groupby(uni).size().reset_index(name="n"),
                           names=uni, values="n",
                           title="Matrícula por unidad académica"),
                    use_container_width=True)
    c2.plotly_chart(px.pie(mat.groupby(sexo).size().reset_index(name="n"),
                           names=sexo, values="n", title="Matrícula por sexo"),
                    use_container_width=True)
    st.plotly_chart(px.histogram(mat, x=edad, nbins=25,
                                 title="Matrícula UTH HMO: edad (años)",
                                 labels={edad: "Edad (años)"}),
                    use_container_width=True)
    st.caption("Las edades se presentan tal como aparecen en la fuente; no se corrigen valores sin evidencia.")
    que("Periodo escolar de ingreso de la matrícula actual: de qué generación "
        "viene cada inscrito (año-periodo).")
    ing_c = mat.groupby(ping).size().reset_index(name="n").sort_values(ping)


    ing_c["ingreso"] = ing_c[ping].astype(str)
    st.plotly_chart(px.bar(ing_c, x="ingreso", y="n",
                           title="Matrícula por código de periodo de ingreso",
                           labels={"ingreso": "Código declarado", "n": "Registros"}),
                    use_container_width=True)
    st.caption("Se conservan los códigos originales: no se ha recuperado una definición documental que permita traducirlos a fechas.")

with t5:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "significados documentales; las correspondencias con columnas se muestran por separado y requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_edu_hermosillo.csv", "text/csv")

    fuentes("edu")
