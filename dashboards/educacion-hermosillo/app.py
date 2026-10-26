"""Dashboard Educacion Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Becas con filtro municipal (HMO); matricula, titulados, egresados, nuevo
ingreso, reprobacion y aprovechamiento institucionales UTH (radicadas en
Hermosillo); capacitacion SEC estatal. Totales declarados por la fuente.
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import numpy as np
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


def col(df, *keys):
    """Primera columna cuyo nombre contiene todas las keys (case-insensitive)."""
    for c in df.columns:
        s = str(c).lower()
        if all(k.lower() in s for k in keys):
            return c
    return None


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
apr = load("aprovechamiento_uth.parquet")
cap = load("capacitacion_sec.parquet")

anios = sorted(bec["anio"].unique())
sel = st.sidebar.multiselect("Años (becas)", anios, default=anios)
bec_f = bec[bec["anio"].isin(sel)] if sel else bec

fuentes("edu", "edu_hmo/becas_hmo.parquet", "edu_hmo/matriculas_uth_hmo.parquet", "edu_hmo/titulados_uth.parquet", "edu_hmo/egresados_uth.parquet")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Becas HMO", f"{len(bec_f):,}", f"${int(bec_f['importe'].sum()):,}")
k2.metric("Matrícula UTH HMO 2022-2", f"{len(mat):,}")
k3.metric("Titulados UTH 22-25", f"{int(tit['n'].sum()):,}")
k4.metric("Egresados UTH 22-25", f"{int(egr['n'].sum()):,}")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    ["Becas", "Trayectoria UTH", "Reprobación", "Matrícula", "Modelos",
     "Aprovech. y Capacitación", "Ontología"])

with t1:
    fuentes("edu", 'edu_hmo/becas_hmo.parquet')
    que("Becas autorizadas a residentes de Hermosillo por año (2021-2025): cada barra "
        "es un año y su altura el número de becas. Cuenta registros publicados; no acredita cobertura del programa.")
    s = bec_f.groupby("anio").agg(becas=("importe", "size"),
                                   importe=("importe", "sum")).reset_index()
    st.plotly_chart(px.bar(s, x="anio", y="becas", title="Becas crecen 2021-2024 y bajan en 2025",
                           labels={"anio": "año", "becas": "becas"}),
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
        "el recurso del programa en Hermosillo. Ojo: los importes tienen cola derecha "
        "(mediana $5,000 vs media $7,694): el total lo jalan pocas becas grandes; "
        "no leer 'beca promedio'.")
    top_esc = bec_f.groupby("escuela")["importe"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_esc, x="importe", y="escuela", orientation="h",
                           title="Top 12 escuelas por importe acumulado"),
                    use_container_width=True)
    # --- Distribución del importe (media vs mediana) ---
    que("Cuánto recibe cada beca: la media ($7,694) supera a la mediana ($5,000) "
        "porque unas pocas becas grandes jalan el promedio (sesgo a la derecha).")
    fh3 = px.histogram(bec_f[bec_f["importe"] <= 50000], x="importe",
                       nbins=60, title="Becas: distribución del importe "
                       "(recorte en $50k para visualizar)")
    fh3.add_vline(x=float(bec_f["importe"].median()), line_dash="dot",
                  annotation_text="mediana $5,000")
    st.plotly_chart(fh3, use_container_width=True)
    st.caption("p25=$2,200 · p50=$5,000 · p75=$10,000 · p99=$42,500 · max=$500,000 "
               "(periodo completo; el filtro de años solo afecta las gráficas). "
               "El histograma recorta en $50k (≈99% de los casos).")
    # --- Ticket por año ---
    que("Ticket promedio vs mediano por año: el programa da más becas pero de menor "
        "monto (2021 mean $10,210 → 2024 mean $6,173, mediana fija en $5,000; "
        "periodo completo).")
    ticket = bec_f.groupby("anio")["importe"].agg(
        media="mean", mediana="median", becas="size").reset_index()
    ticket_m = ticket.melt(id_vars="anio", value_vars=["media", "mediana"],
                           var_name="medida", value_name="pesos")
    st.plotly_chart(px.bar(ticket_m, x="anio", y="pesos", color="medida",
                           barmode="group", title="Ticket por año: media vs mediana"),
                    use_container_width=True)
    # --- Programa, ciclo, convocatoria ---
    que("De qué programa viene cada beca, de qué ciclo escolar y qué convocatoria "
        "la otorgó.")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(bec_f.groupby("programa").size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(10),
                           x="n", y="programa", orientation="h",
                           title="Top 10 programas de beca",
                           labels={"n": "becas"}),
                    use_container_width=True)
    c2.plotly_chart(px.bar(bec_f.groupby("ciclo").size().reset_index(name="n")
                           .sort_values("n", ascending=False),
                           x="ciclo", y="n", title="Becas por ciclo escolar",
                           labels={"ciclo": "ciclo escolar", "n": "becas"}),
                    use_container_width=True)
    st.plotly_chart(px.bar(bec_f.groupby("convocatoria").size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(12),
                           x="convocatoria", y="n",
                           title="Top 12 convocatorias por becas",
                           labels={"convocatoria": "convocatoria", "n": "becas"}),
                    use_container_width=True)
    # --- Brecha de género en importe ---
    que("Brecha de género en el monto: los hombres promedian $8,106 y las mujeres "
        "$7,391 con la misma mediana ($5,000; periodo completo).")
    bg = bec_f.groupby("genero")["importe"].agg(
        media="mean", mediana="median", becas="size").reset_index()
    bg_m = bg.melt(id_vars="genero", value_vars=["media", "mediana"],
                   var_name="medida", value_name="pesos")
    st.plotly_chart(px.bar(bg_m, x="genero", y="pesos", color="medida",
                           barmode="group", title="Importe por género: media vs mediana"),
                    use_container_width=True)
    que("Distribución del importe por nivel: la caja muestra mediana y cuartiles, "
        "los puntos son becas atípicas. En ambos niveles la media queda por encima "
        "de la mediana (cola derecha).")
    st.plotly_chart(px.box(bec_f[bec_f["importe"] <= 50000], x="nivel", y="importe",
                           title="Importe por nivel (recorte $50k)",
                           labels={"nivel": "nivel", "importe": "pesos"}),
                    use_container_width=True)

with t2:
    fuentes("edu", 'edu_hmo/titulados_uth.parquet', 'edu_hmo/egresados_uth.parquet', 'edu_hmo/nuevo_ingreso_uth.parquet')
    que("Comparativa por corte de las tres etapas de la trayectoria UTH: nuevo ingreso, "
        "egresados y titulados. Cada grupo de barras es un periodo; permite ver la "
        "comparación del volumen de cada serie institucional. No hay seguimiento de las mismas personas ni tasas de transición.")
    tray = pd.concat([
        tit.assign(etapa="Titulados"), egr.assign(etapa="Egresados"),
        ing.assign(etapa="Nuevo ingreso")])
    st.plotly_chart(px.bar(tray.groupby(["anio", "etapa"])["n"].sum().reset_index(),
                           x="anio", y="n", color="etapa", barmode="group",
                           title="Trayectoria UTH por corte",
                           labels={"anio": "corte", "n": "estudiantes"}),
                    use_container_width=True)
    st.caption("Ojo: el corte 2022-1 trae un solo programa reportado (n=10); no es "
               "comparable con los demás cortes.")
    que("Los 10 programas educativos con más titulados y con más egresados "
        "(2022-2025): qué carreras aportan más profesionistas en la UTH Hermosillo.")
    c1, c2 = st.columns(2)
    for df, nom, cc in ((tit, "Titulados", c1), (egr, "Egresados", c2)):
        top = df.groupby("programa")["n"].sum().nlargest(10).reset_index()
        cc.plotly_chart(px.bar(top, x="n", y="programa", orientation="h",
                               title=f"{nom}: top 10 programas",
                               labels={"n": "estudiantes"}),
                        use_container_width=True)
    # --- Tasa de titulación por programa ---
    que("Tasa titulados/egresados por programa (transversal 2022-2025, NO es cohorte: "
        "los que se titulan no son los mismos que egresaron ese año).")
    tt = tit.groupby("programa")["n"].sum()
    ee = egr.groupby("programa")["n"].sum()
    tasa = pd.DataFrame({"titulados": tt, "egresados": ee}).fillna(0)
    tasa = tasa[tasa["egresados"] > 0].copy()
    tasa["tasa"] = tasa["titulados"] / tasa["egresados"]
    tasa = tasa.sort_values("titulados", ascending=False).head(15).reset_index()
    st.plotly_chart(px.bar(tasa, x="tasa", y="programa", orientation="h",
                           title="Tasa titulación (top 15 por titulados)",
                           labels={"tasa": "Titulados / Egresados"}),
                    use_container_width=True)
    st.caption("Tasa >1 es posible porque los cortes no siguen a la misma generación.")
    # --- Serie año x sexo ---
    que("¿Se cierra la brecha de género? Hombres ~60% en titulación y egreso; "
        "la serie por año y sexo lo muestra.")
    ts = tray.groupby(["anio", "etapa", "sexo"])["n"].sum().reset_index()
    st.plotly_chart(px.bar(ts, x="anio", y="n", color="sexo", barmode="group",
                           facet_col="etapa",
                           title="Trayectoria por año y sexo",
                           labels={"anio": "corte", "n": "estudiantes"}),
                    use_container_width=True)

with t3:
    fuentes("edu", 'edu_hmo/reprobacion_uth.parquet')
    que("Categorías de la fuente con mayor promedio aritmético del índice de reprobación de semana 16 "
        "(2022, presencial y remota), sin ponderación. El "
        "histograma muestra cómo se distribuye ese índice entre los registros disponibles.")
    idx_all = [c for c in rep.columns if "16VA" in c.upper() and "REPROB" in c.upper()]
    idx, idx2 = idx_all[0], (idx_all[1] if len(idx_all) > 1 else idx_all[0])
    mat_col = [c for c in rep.columns if "PROGRAMA" in c.upper()][0]
    top_r = rep.groupby(mat_col)[idx].mean().sort_values(ascending=False).head(15)
    top_r = top_r.reset_index().rename(columns={idx: "indice"})
    st.plotly_chart(px.bar(top_r, x="indice", y=mat_col, orientation="h",
                           title="Reprobación: mayor índice promedio sem. 16"),
                    use_container_width=True)
    fh = px.histogram(rep, x=idx, nbins=30,
                      title="Índice con sesgo a la derecha: media 17, mediana 12")
    fh.add_vline(x=float(rep[idx].mean()), line_dash="dash", annotation_text="media")
    fh.add_vline(x=float(rep[idx].median()), line_dash="dot", annotation_text="mediana")
    st.plotly_chart(fh, use_container_width=True)
    # --- Comparar cortes ---
    que("Presencial vs remota: la remota (n=64) trae media 34.2 en sem 16 frente a "
        "~17.3 presencial. Con n chica, leer como rango, no como punto.")
    rep_c = rep.copy()
    rep_c["sem16"] = rep_c[idx].fillna(rep_c[idx2])
    corte = rep_c.groupby("corte")["sem16"].agg(
        media="mean", mediana="median", materias="size").reset_index()
    st.plotly_chart(px.bar(corte, x="corte", y="media",
                           title="Reprobación sem 16: media por corte",
                           labels={"media": "índice medio"}),
                    use_container_width=True)
    st.dataframe(corte, use_container_width=True)
    # --- Evolución 4ta→16va ---
    que("La reprobación sube a mitad del semestre y cae hacia la semana 16 "
        "(medianas 14.6 → 21.4 → 21.4 → 11.9, presencial).")
    WEEKS = ("4TA", "8VA", "12VA", "16VA")
    sems = [c for c in rep.columns
            if "SEMANA" in c.upper() and "REPROB" in c.upper()]
    sems = sorted(set(sems), key=lambda c: WEEKS.index(
        next(w for w in WEEKS if w in c.upper())))
    evo = pd.DataFrame([{"semana": next(w for w in WEEKS if w in c.upper()),
                         "mediana": rep[c].median(), "media": rep[c].mean(),
                         "n": rep[c].count()} for c in sems])
    st.plotly_chart(px.line(evo, x="semana", y=["media", "mediana"],
                            markers=True, title="Evolución del índice por semana"),
                    use_container_width=True)

with t4:
    fuentes("edu", 'edu_hmo/matriculas_uth_hmo.parquet')
    que("Registros de matrícula UTH seleccionados por unidad o municipio Hermosillo: reparto por unidad "
        "académica y por sexo, histograma de edades y periodo escolar de ingreso. "
        "Describe quiénes estudian en la universidad.")
    uni = col(mat, "unidad")
    sexo = [c for c in mat.columns if str(c).strip().lower() == "sexo"][0]
    edad = [c for c in mat.columns if str(c).strip().lower() == "edad"][0]
    ping = col(mat, "periodo", "ingreso")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(mat.groupby(uni).size().reset_index(name="n"),
                           names=uni, values="n",
                           title="Matrícula por unidad académica"),
                    use_container_width=True)
    c2.plotly_chart(px.pie(mat.groupby(sexo).size().reset_index(name="n"),
                           names=sexo, values="n", title="Matrícula por sexo"),
                    use_container_width=True)
    fh2 = px.histogram(mat, x=edad, color=sexo, nbins=25, barmode="overlay",
                       title="Edad UTH por sexo: grueso 18-25; 11 registros en 122 (error de captura)",
                       labels={edad: "Edad (años)", sexo: "Sexo"})
    fh2.add_vline(x=float(mat[edad].mean()), line_dash="dash", annotation_text="media")
    fh2.add_vline(x=float(mat[edad].median()), line_dash="dot", annotation_text="mediana")
    st.plotly_chart(fh2, use_container_width=True)
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
    # --- Programas, modalidad, regularidad ---
    que("Qué estudian y en qué modalidad: top de programas, 91% escolarizado, "
        "70% regulares vs 30% irregulares.")
    prog = col(mat, "programa educativo")
    mod_ = col(mat, "modalidad")
    reg = col(mat, "regulares")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(mat.groupby(prog).size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(15),
                           x="n", y=prog, orientation="h",
                           title="Top 15 programas (matrícula)",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    c2.plotly_chart(px.pie(mat.groupby(mod_).size().reset_index(name="n"),
                           names=mod_, values="n", title="Por modalidad"),
                    use_container_width=True)
    st.plotly_chart(px.pie(mat.groupby(reg).size().reset_index(name="n"),
                           names=reg, values="n", title="Regulares vs irregulares"),
                    use_container_width=True)
    # --- Antecedente y avance ---
    que("Con qué promedio de bachillerato llegan (mediana ~80, 531 sin dato) y en "
        "qué semestre van (picos en 1, 3, 5, 7, 9: generaciones completas).")
    pb = col(mat, "promedio", "bachillerato")
    sc = col(mat, "semestres", "incluye")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.histogram(mat.dropna(subset=[pb]), x=pb, nbins=30,
                                 title="Promedio de bachillerato"),
                    use_container_width=True)
    c2.plotly_chart(px.bar(mat.groupby(sc).size().reset_index(name="n")
                           .sort_values(sc),
                           x=sc, y="n", title="Semestres cursados (con actual)",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    # --- Origen ---
    que("De qué escuela y municipio vienen: GRIMAC, CECYTES y CBTIS dominan; "
        "77% reside en Hermosillo.")
    bch = col(mat, "bachillerato")
    mun = [c for c in mat.columns if str(c).strip().lower() == "municipio"][0]
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(mat[mat[bch].astype(str).str.strip() != ""]
                           .groupby(bch).size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(12),
                           x="n", y=bch, orientation="h",
                           title="Top 12 bachilleratos de origen",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    c2.plotly_chart(px.bar(mat[mat[mun].astype(str).str.strip() != ""]
                           .groupby(mun).size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(12),
                           x="n", y=mun, orientation="h",
                           title="Top 12 municipios",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    # --- Inclusión ---
    que("Inclusión: 204 con discapacidad (visual 119), 109 de grupo indígena, "
        "estado civil casi todo soltero.")
    disc = col(mat, "discapacidad")
    indg = col(mat, "pertenece")
    eciv = col(mat, "estado civil")
    c1, c2 = st.columns(2)
    dd = mat[mat[disc].notna()].groupby(disc).size().reset_index(name="n") \
        .sort_values("n", ascending=False)
    c1.plotly_chart(px.bar(dd, x="n", y=disc, orientation="h",
                           title="Discapacidad (casos con dato)",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    c2.plotly_chart(px.bar(mat.groupby(eciv).size().reset_index(name="n")
                           .sort_values("n", ascending=False),
                           x="n", y=eciv, orientation="h",
                           title="Estado civil",
                           labels={"n": "estudiantes"}),
                    use_container_width=True)
    st.caption(f"Grupo indígena (pertenece=SI): "
               f"{int((mat[indg].astype(str).str.upper() == 'SI').sum())} estudiantes.")

with t5:
    import plotly.graph_objects as go
    que("Materias con mayor probabilidad de riesgo (índice sem.16 ≥ 30%) según "
        "RandomForest entrenado con semanas 4/8/12: alerta temprana para intervenir "
        "antes del cierre del semestre.")
    me = json.loads((DATA / "modelos" / "metricas_edu.json").read_text(encoding="utf-8"))
    riesgo = pd.read_parquet(DATA / "modelos" / "inferencias" / "riesgo_materias.parquet")
    mcol = next(c for c in riesgo.columns if "PROGRAMA" in str(c).upper())
    top = riesgo.groupby(mcol)["p_riesgo"].max().sort_values(ascending=False).head(12)
    top = top.reset_index().rename(columns={"p_riesgo": "p"})
    st.plotly_chart(px.bar(top, x="p", y=mcol, orientation="h",
                           title="Riesgo de reprobación: top 12 materias (p)",
                           labels={"p": "P(riesgo)"}),
                    use_container_width=True)
    st.caption(f"Modelo: balanced accuracy {me['riesgo_reprobacion']['balanced_accuracy_cv']} "
               f"(±{me['riesgo_reprobacion']['balanced_accuracy_cv_std']}, validación cruzada "
               f"por materia: la misma materia nunca está en train y test; n="
               f"{me['riesgo_reprobacion']['n']}, prevalencia de riesgo "
               f"{me['riesgo_reprobacion']['prevalencia_riesgo']}). Materias sin semanas "
               "tempranas (2022-1, remota) quedan fuera: sin p. Probabilidad, no destino.")
    que("Segmentos de estudiantes (KMeans k=4 sobre semestre, promedios, créditos y "
        "sexo, ciclo 2021-2022) proyectados en 2D: cada punto es un estudiante. "
        "Describe perfiles (p. ej. avanzados vs. iniciales), no etiquetas oficiales.")
    seg = pd.read_parquet(DATA / "modelos" / "inferencias" / "segmentos_uth.parquet")
    st.plotly_chart(px.scatter(seg, x="pca1", y="pca2", color=seg.segmento.astype(str),
                               title="Segmentos de estudiantes UTH (PCA 2D)",
                               labels={"color": "Segmento"},
                               hover_data=["programa", "semestre"]),
                    use_container_width=True)
    st.caption(f"Tamaños: {me['segmentos']['tamano']}. El segmento 2 (2 registros con "
               "promedios en escala 0-100 en vez de 0-10) es probable error de captura.")
    que("Tendencia de becas HMO con estimación 2026 (regresión lineal, n=5): el punto "
        "naranja es ESTIMACIÓN frágil, no compromiso; úsese solo como referencia.")
    tb = pd.read_parquet(DATA / "modelos" / "inferencias" / "tendencia_becas.parquet")
    fig = go.Figure()
    h = tb[tb.tipo == "observado"]
    e = tb[tb.tipo == "estimacion"]
    fig.add_trace(go.Scatter(x=h.anio, y=h.n, mode="lines+markers", name="Observado"))
    fig.add_trace(go.Scatter(x=e.anio, y=e.n, mode="markers",
                             marker=dict(color="rgba(255,165,0,0.2)", size=9,
                                           line=dict(color="orange", width=2)),
                             name="Estimación 2026"))
    fig.update_layout(title="Becas HMO: observado + estimación 2026",
                      xaxis_title="Año", yaxis_title="Becas")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"R² {me['tendencia_becas']['r2']}, MAE {me['tendencia_becas']['mae']}. "
               f"{me['tendencia_becas']['advertencia']}.")
    que("Riesgo de irregularidad por alumno (RandomForest con datos de entrada: "
        "edad, promedio de bachillerato, programa, modalidad, sexo y semestres; "
        "sin promedios generales ni créditos para no filtrar el resultado).")
    mi = me["irregularidad"]
    imp = pd.Series(mi["importancias"]).sort_values(ascending=False).reset_index()
    imp.columns = ["variable", "importancia"]
    st.plotly_chart(px.bar(imp, x="importancia", y="variable", orientation="h",
                           title="Irregularidad: qué pesa más"),
                    use_container_width=True)
    irr = pd.read_parquet(DATA / "modelos" / "inferencias"
                          / "irregularidad_matricula.parquet")
    pcol = "p_irregular"
    prog_irr = [c for c in irr.columns if c != pcol][0]
    st.plotly_chart(px.histogram(irr, x=pcol, nbins=40,
                                 title="Irregularidad: distribución de P(irregular)",
                                 labels={"p_irregular": "P(irregular)"}),
                    use_container_width=True)
    top_irr = irr.groupby(prog_irr)[pcol].mean().sort_values(
        ascending=False).head(15).reset_index()
    st.plotly_chart(px.bar(top_irr, x=pcol, y=prog_irr, orientation="h",
                           title="P(irregular) promedio: top 15 programas",
                           labels={"p_irregular": "P(irregular) promedio"}),
                    use_container_width=True)
    st.caption(f"Modelo: balanced accuracy {mi['balanced_accuracy']} en prueba "
               f"(n={mi['n']}, prevalencia irregular {mi['prevalencia_irregular']}). "
               "El promedio de bachillerato y los semestres cursados pesan más; "
               "sexo y modalidad casi nada. Probabilidad, no destino.")
    que("Por qué marca riesgo cada modelo (SHAP TreeExplainer exacto sobre "
        "P(clase=1), aditividad verificada err<1e-6; muestra held-out en "
        "irregularidad y train en riesgo n=140): cada punto es una fila. "
        "Describe al modelo, no causalidad.")
    import plotly.graph_objects as go

    def _beeswarm(parquet, titulo, nota):
        vv = pd.read_parquet(DATA / "modelos" / "shap" / parquet)
        feats = [c for c in vv.columns if not c.startswith(("base", "p_modelo", "valor_"))]
        vals = vv[feats].values
        raw = vv[[f"valor_{j}" for j in range(len(feats))]].values
        base = {}
        for j, c in enumerate(feats):
            b = c.split("_")[0] if ("_" in c and not c.startswith(("Edad", "Promedio", "Semestres"))) else c
            base.setdefault(b, []).append(j)
        agg = {b: vals[:, js].sum(axis=1) for b, js in base.items()}
        order = pd.DataFrame(agg).abs().mean().sort_values(ascending=False).head(8).index.tolist()
        fig = go.Figure()
        rng = np.random.RandomState(0)
        for k, f_ in enumerate(reversed(order)):
            js = base[f_]
            x = vals[:, js].sum(axis=1)
            cols = raw[:, js].mean(axis=1)
            n = len(x)
            fig.add_trace(go.Scatter(x=x, y=np.full(n, k) + rng.uniform(-0.25, 0.25, n),
                                     mode="markers", name=f_,
                                     marker=dict(size=4, color=cols, colorscale="RdBu",
                                                 showscale=False, reversescale=True),
                                     showlegend=False))
        fig.update_layout(title=titulo, xaxis_title="SHAP (cambio en P)",
                          yaxis=dict(tickvals=list(range(len(order))),
                                     ticktext=list(reversed(order))))
        st.plotly_chart(fig, use_container_width=True)
        st.caption(nota)

    _beeswarm("valores_riesgo_reprobacion.parquet", "SHAP: riesgo de reprobación",
              "La semana 8 (promedio e índice) es lo que más mueve la predicción, "
              "seguida de la 12; la 4 pesa menos. Punto a la derecha = empuja a riesgo.")
    _beeswarm("valores_irregularidad_uth.parquet", "SHAP: irregularidad (agrupado)",
              "Semestres cursados, promedio de bachillerato y edad dominan; "
              "programa, sexo y modalidad son marginales.")
    que("Ejemplo local: la fila con mayor P de cada modelo y qué la empujó. "
        "La barra base es el promedio del background; cada tramo suma/resta "
        "hasta la predicción final.")
    for pq, titulo in (("valores_riesgo_reprobacion.parquet", "Waterfall: mayor riesgo"),
                       ("valores_irregularidad_uth.parquet", "Waterfall: mayor irregularidad")):
        vv = pd.read_parquet(DATA / "modelos" / "shap" / pq)
        feats = [c for c in vv.columns if not c.startswith(("base", "p_modelo", "valor_"))]
        i = int(vv["p_modelo"].idxmax())
        contrib = vv.loc[i, feats].sort_values()
        fig = go.Figure(go.Waterfall(x=contrib.index.tolist() + ["predicción"],
                                     y=contrib.values.tolist() + [0],
                                     base=float(vv.loc[i, "base_value"]),
                                     measure=["relative"] * len(contrib) + ["total"]))
        fig.update_layout(title=titulo)
        st.plotly_chart(fig, use_container_width=True)
    que("Top 20 alumnos con mayor P(irregular) y sus 3 principales impulsores "
        "SHAP (valor + cambio en P).")
    st.dataframe(pd.read_csv(DATA / "modelos" / "shap" / "top20_irregularidad.csv"),
                 use_container_width=True)

with t6:
    que("Aprovechamiento 2021-2 por programa (80 filas): promedio global y % con "
        "menos de 7. Ordenado por promedio; el n pequeño miente si no se muestra.")
    pg = col(apr, "promedio global")
    ev = col(apr, "evaluados")
    pe = col(apr, "programa educativo")
    m7 = col(apr, "menos de 7")
    ap2 = apr.copy()
    ap2["pct_menos7"] = ap2[m7].fillna(0) / ap2[ev] * 100  # NaN = 0 (bandas suman Evaluados)
    ap2 = ap2.sort_values(pg, ascending=False)
    st.plotly_chart(px.bar(ap2.head(10), x=pg, y=pe, orientation="h",
                           title="Top 10 promedio global",
                           labels={pg: "Promedio global", pe: "Programa"}),
                    use_container_width=True)
    st.plotly_chart(px.bar(ap2.tail(10).sort_values(pg), x=pg, y=pe,
                           orientation="h",
                           title="Bottom 10 promedio global",
                           labels={pg: "Promedio global", pe: "Programa"}),
                    use_container_width=True)
    st.dataframe(ap2[[pe, ev, pg, "pct_menos7"]]
                 .rename(columns={pe: "Programa", ev: "Evaluados",
                                  pg: "Promedio", "pct_menos7": "% <7"}),
                 use_container_width=True)
    st.caption("Ojo: Ing. en Tecnología de Alimentos promedia 6.0 con n=1; "
               "Ing. en Geociencias (Hermosillo) 7.81 con n=405 — ponderar por Evaluados.")
    que("Capacitación docente SEC (22 eventos, 2022): pocos datos, solo tabla y "
        "total de participantes por modalidad.")
    np_ = col(cap, "participantes")
    mo = col(cap, "modalidad")
    evn = col(cap, "evento")
    cap2 = cap.rename(columns={evn: "Evento", np_: "Participantes", mo: "Modalidad"})
    st.dataframe(cap2[["Evento", "Participantes", "Modalidad"]],
                 use_container_width=True)
    st.plotly_chart(px.bar(cap2.groupby("Modalidad")["Participantes"].sum()
                           .reset_index(),
                           x="Modalidad", y="Participantes",
                           title="Participantes por modalidad"),
                    use_container_width=True)

with t7:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "significados documentales; las correspondencias con columnas se muestran por separado y requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_edu_hermosillo.csv", "text/csv")

    fuentes("edu")
