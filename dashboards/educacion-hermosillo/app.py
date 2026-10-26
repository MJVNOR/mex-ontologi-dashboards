"""Dashboard Educacion Hermosillo — datos abiertos Sonora via ontologia mex-ontologi.

Becas con filtro municipal (HMO); matricula, titulados, egresados, nuevo
ingreso, reprobacion y aprovechamiento institucionales UTH (radicadas en
Hermosillo); capacitacion SEC estatal. Totales declarados por la fuente.
"""

import json
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

k1, k2, k3, k4 = st.columns(4)
k1.metric("Becas HMO", f"{len(bec_f):,}", f"${int(bec_f['importe'].sum()):,}")
k2.metric("Matrícula UTH HMO 2022-2", f"{len(mat):,}")
k3.metric("Titulados UTH 22-25", f"{int(tit['n'].sum()):,}")
k4.metric("Egresados UTH 22-25", f"{int(egr['n'].sum()):,}")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    ["Becas", "Trayectoria UTH", "Reprobación", "Matrícula", "Modelos",
     "Aprovech. y Capacitación", "Ontología"])

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
    # --- Distribución del importe (media vs mediana) ---
    que("Cuánto recibe cada beca: la media ($7,694) supera a la mediana ($5,000) "
        "porque unas pocas becas grandes jalan el promedio (sesgo a la derecha).")
    st.plotly_chart(px.histogram(bec_f[bec_f["importe"] <= 50000], x="importe",
                                 nbins=60, title="Becas: distribución del importe "
                                 "(recorte en $50k para visualizar)"),
                    use_container_width=True)
    st.caption("p25=$2,200 · p50=$5,000 · p75=$10,000 · p99=$42,500 · max=$500,000. "
               "El histograma recorta en $50k (≈99% de los casos).")
    # --- Ticket por año ---
    que("Ticket promedio vs mediano por año: el programa da más becas pero de menor "
        "monto (2021 mean $10,210 → 2024 mean $6,173, mediana fija en $5,000).")
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
                           title="Top 10 programas de beca"),
                    use_container_width=True)
    c2.plotly_chart(px.bar(bec_f.groupby("ciclo").size().reset_index(name="n")
                           .sort_values("n", ascending=False),
                           x="ciclo", y="n", title="Becas por ciclo escolar"),
                    use_container_width=True)
    st.plotly_chart(px.bar(bec_f.groupby("convocatoria").size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(12),
                           x="convocatoria", y="n",
                           title="Top 12 convocatorias por becas"),
                    use_container_width=True)
    # --- Brecha de género en importe ---
    que("Brecha de género en el monto: los hombres promedian $8,106 y las mujeres "
        "$7,391 con la misma mediana ($5,000).")
    bg = bec_f.groupby("genero")["importe"].agg(
        media="mean", mediana="median", becas="size").reset_index()
    bg_m = bg.melt(id_vars="genero", value_vars=["media", "mediana"],
                   var_name="medida", value_name="pesos")
    st.plotly_chart(px.bar(bg_m, x="genero", y="pesos", color="medida",
                           barmode="group", title="Importe por género: media vs mediana"),
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
    for df, nom, cc in ((tit, "Titulados", c1), (egr, "Egresados", c2)):
        top = df.groupby("programa")["n"].sum().nlargest(10).reset_index()
        cc.plotly_chart(px.bar(top, x="n", y="programa", orientation="h",
                               title=f"{nom}: top 10 programas"),
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
                           title="Trayectoria por año y sexo"),
                    use_container_width=True)

with t3:
    que("Materias con mayor índice promedio de reprobación en la semana 16 del semestre "
        "(2022, presencial y remota): señala dónde se concentran los rezagos. El "
        "histograma muestra cómo se distribuye ese índice entre todas las materias.")
    idx_all = [c for c in rep.columns if "16VA" in c.upper() and "REPROB" in c.upper()]
    idx, idx2 = idx_all[0], (idx_all[1] if len(idx_all) > 1 else idx_all[0])
    mat_col = [c for c in rep.columns if "PROGRAMA" in c.upper()][0]
    top_r = rep.groupby(mat_col)[idx].mean().sort_values(ascending=False).head(15)
    top_r = top_r.reset_index().rename(columns={idx: "indice"})
    st.plotly_chart(px.bar(top_r, x="indice", y=mat_col, orientation="h",
                           title="Reprobación: mayor índice promedio sem. 16"),
                    use_container_width=True)
    st.plotly_chart(px.histogram(rep, x=idx, nbins=30,
                                 title="Distribución del índice de reprobación"),
                    use_container_width=True)
    # --- Comparar cortes ---
    que("Presencial vs remota: la remota (n=64) trae media 34.2 en sem 16 frente a "
        "~17.3 presencial. Con n chica, leer como rango, no como punto.")
    rep_c = rep.copy()
    rep_c["sem16"] = rep_c[idx].fillna(rep_c[idx2])
    corte = rep_c.groupby("corte")["sem16"].agg(
        media="mean", mediana="median", materias="size").reset_index()
    st.plotly_chart(px.bar(corte, x="corte", y="media",
                           title="Reprobación sem 16: media por corte"),
                    use_container_width=True)
    st.dataframe(corte, use_container_width=True)
    # --- Evolución 4ta→16va ---
    que("La reprobación sube a mitad del semestre y cae hacia la semana 16 "
        "(medianas 14.5 → 21.4 → 21.4 → 11.9, presencial).")
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
    que("Matrícula UTH Hermosillo 2022-2 (8,227 estudiantes): reparto por unidad "
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
                           title="Top 15 programas (matrícula)"),
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
                           x=sc, y="n", title="Semestres cursados (con actual)"),
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
                           title="Top 12 bachilleratos de origen"),
                    use_container_width=True)
    c2.plotly_chart(px.bar(mat[mat[mun].astype(str).str.strip() != ""]
                           .groupby(mun).size().reset_index(name="n")
                           .sort_values("n", ascending=False).head(12),
                           x="n", y=mun, orientation="h",
                           title="Top 12 municipios"),
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
                           title="Discapacidad (casos con dato)"),
                    use_container_width=True)
    c2.plotly_chart(px.bar(mat.groupby(eciv).size().reset_index(name="n")
                           .sort_values("n", ascending=False),
                           x="n", y=eciv, orientation="h",
                           title="Estado civil"),
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
                           title="Riesgo de reprobación: top 12 materias (p)"),
                    use_container_width=True)
    st.caption(f"Modelo: balanced accuracy {me['riesgo_reprobacion']['balanced_accuracy']} "
               f"en prueba (n={me['riesgo_reprobacion']['n']}, prevalencia de riesgo "
               f"{me['riesgo_reprobacion']['prevalencia_riesgo']}). Probabilidad, no destino.")
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
                             marker=dict(color="orange", size=12), name="Estimación 2026"))
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
                                 title="Irregularidad: distribución de P(irregular)"),
                    use_container_width=True)
    top_irr = irr.groupby(prog_irr)[pcol].mean().sort_values(
        ascending=False).head(15).reset_index()
    st.plotly_chart(px.bar(top_irr, x=pcol, y=prog_irr, orientation="h",
                           title="P(irregular) promedio: top 15 programas"),
                    use_container_width=True)
    st.caption(f"Modelo: balanced accuracy {mi['balanced_accuracy']} en prueba "
               f"(n={mi['n']}, prevalencia irregular {mi['prevalencia_irregular']}). "
               "El promedio de bachillerato y los semestres cursados pesan más; "
               "sexo y modalidad casi nada. Probabilidad, no destino.")

with t6:
    que("Aprovechamiento 2021-2 por programa (80 filas): promedio global y % con "
        "menos de 7. Ordenado por promedio; el n pequeño miente si no se muestra.")
    pg = col(apr, "promedio global")
    ev = col(apr, "evaluados")
    pe = col(apr, "programa educativo")
    m7 = col(apr, "menos de 7")
    ap2 = apr.copy()
    ap2["pct_menos7"] = ap2[m7] / ap2[ev] * 100
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
             "qué significa cada columna de los conjuntos de educación según la fuente.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_edu_hermosillo.csv", "text/csv")
