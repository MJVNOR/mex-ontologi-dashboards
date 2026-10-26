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

k1, k2, k3, k4 = st.columns(4)
k1.metric("Becas HMO", f"{len(bec_f):,}", f"${int(bec_f['importe'].sum()):,}")
k2.metric("Matrícula UTH HMO 2022-2", f"{len(mat):,}")
k3.metric("Titulados UTH 22-25", f"{int(tit['n'].sum()):,}")
k4.metric("Egresados UTH 22-25", f"{int(egr['n'].sum()):,}")

t1, t2, t3, t4, t5 = st.tabs(
    ["Becas", "Trayectoria UTH", "Reprobación", "Matrícula", "Ontología"])

with t1:
    que("Becas autorizadas a residentes de Hermosillo por año (2021-2025): cada barra "
        "es un año y su altura el número de becas. Muestra el crecimiento del programa.")
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
    que("Comparativa por corte de las tres etapas de la trayectoria UTH: nuevo ingreso, "
        "egresados y titulados. Cada grupo de barras es un periodo; permite ver la "
        "relación entre los que entran, los que egresan y los que se titulan.")
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
    que("Materias con mayor índice promedio de reprobación en la semana 16 del semestre "
        "(2022, presencial y remota): señala dónde se concentran los rezagos. El "
        "histograma muestra cómo se distribuye ese índice entre todas las materias.")
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
    que("Matrícula UTH Hermosillo 2022-2 (8,227 estudiantes): reparto por unidad "
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
    st.caption("⚠️ Dato curioso: 11 registros aparecen con 122 años "
               "(probable error de captura, no edad real).")
    que("Periodo escolar de ingreso de la matrícula actual: de qué generación "
        "viene cada inscrito (año-periodo).")
    ing_c = mat.groupby(ping).size().reset_index(name="n").sort_values(ping)


    def _per(p):  # ponytail: YY+periodo UTH (222->2022-2), siglo 19 si YY>=90
        try:
            p = int(p)
            yy, t = divmod(p, 10)
            return f"{19 if yy >= 90 else 20}{yy:02d}-{t}"
        except (TypeError, ValueError):
            return str(p)


    ing_c["ingreso"] = ing_c[ping].map(_per)
    ing_c["periodo"] = ing_c["ingreso"].str.slice(-1).map(
        {"1": "1 · ene-abr", "2": "2 · sep-dic", "3": "3 · verano*"})
    st.plotly_chart(px.bar(ing_c, x="ingreso", y="n", color="periodo",
                           title="Matrícula por año de ingreso",
                           labels={"ingreso": "Ingreso (año-periodo)",
                                   "n": "Inscritos", "periodo": "Periodo"},
                           category_orders={"ingreso": ing_c["ingreso"].tolist()}),
                    use_container_width=True)
    st.caption("* La fuente no define 1/2/3; se infiere de nuevo ingreso "
               "(2022-1 = enero-abril, 2022-2 = septiembre-diciembre) y de que "
               "el 3 va casi todo a cuatrimestrales.")

with t5:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "qué significa cada columna de los conjuntos de educación según la fuente.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_edu_hermosillo.csv", "text/csv")
