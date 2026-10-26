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

def fmt(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f} M"
    if n >= 10_000:
        return f"{n / 1_000:.1f} mil"
    return f"{n:,}"


k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Urgencias", fmt(urg_f["Total_Urgencias"].sum()))
k2.metric("Egresos hosp.", fmt(egr_f["Total_Egresos"].sum()))
k3.metric("Consulta externa", fmt(con_f["Total"].sum()))
k4.metric("Nacimientos 2022 (residencia HMO)", fmt(len(nac)))
k5.metric("Defunciones 2022 (residencia HMO)", fmt(len(defu)))

t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs(
    ["Series anuales", "Urgencias / Egresos", "Consulta externa",
     "Nacimientos / Defunciones", "Vigilancia", "Pronóstico", "Historia", "Ontología"])

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
                           title="Consulta externa domina; 2020 se desploma y 2022 viene parcial"),
                    width="stretch", alt="Barras anuales por servicio de salud")
    st.caption("Egresos incluye pocos registros 2015-2017 tal como los declara la fuente; "
               "el grueso es 2018-2022.")
    que("Misma serie en tasa por 100 mil habitantes (proyecciones de población, "
        "tema poblacion): corrige el efecto del crecimiento demográfico; 2022 sigue "
        "parcial en la fuente.")
    pob = pd.read_parquet(DATA / "tidy" / "pob_hermosillo_anual.parquet")
    pob = pob.rename(columns={"anio": "año"})
    t100 = s.merge(pob, on="año", how="left")
    t100["tasa"] = (t100["total"] / t100["n"] * 100_000).round(1)
    st.plotly_chart(px.line(t100, x="año", y="tasa", color="serie", markers=True,
                            title="Atenciones por 100 mil habitantes (proyección)",
                            labels={"tasa": "por 100 mil hab."}),
                    width="stretch",
                    alt="Líneas de tasa por 100 mil habitantes por servicio")

with t2:
    fuentes("salud", 'hmo_urgencias.parquet', 'hmo_egresos.parquet')
    c1, c2 = st.columns(2)
    que("Izquierda: los 10 diagnósticos (CIE-10) con más atenciones de urgencias en "
        "Hermosillo. Derecha: lo mismo para egresos hospitalarios. Permite ver qué "
        "padecimientos presionan cada servicio. Nota: la fuente trae 9,355 renglones "
        "idénticos de egresos que se retiraron (ver procedencia); el total publicado "
        "es sin duplicados.")
    top_u = urg_f.groupby("CIE10_Descrip")["Total_Urgencias"].sum().nlargest(10).reset_index()
    c1.plotly_chart(px.bar(top_u, x="Total_Urgencias", y="CIE10_Descrip", orientation="h",
                           title="Urgencias: top 10 diagnósticos"), width="stretch", alt="Grafica: Urgencias: top 10 diagnósticos")
    top_e = egr_f.groupby("CIE10_Descrip")["Total_Egresos"].sum().nlargest(10).reset_index()
    c2.plotly_chart(px.bar(top_e, x="Total_Egresos", y="CIE10_Descrip", orientation="h",
                           title="Egresos: top 10 diagnósticos"), width="stretch", alt="Grafica: Egresos: top 10 diagnósticos")
    que("Pasteles: reparto por sexo de cada servicio. Las etiquetas son las que declara "
        "la fuente (en egresos conviven 'Hombre/Masculino' y 'Mujer/Femenino').")
    c1.plotly_chart(px.pie(urg_f.groupby("Sexo")["Total_Urgencias"].sum().reset_index(),
                           names="Sexo", values="Total_Urgencias",
                           title="Urgencias por sexo"), width="stretch", alt="Grafica: Urgencias por sexo")
    c2.plotly_chart(px.pie(egr_f.groupby("Sexo")["Total_Egresos"].sum().reset_index(),
                           names="Sexo", values="Total_Egresos",
                           title="Egresos por sexo (etiquetas de la fuente)"), width="stretch", alt="Grafica: Egresos por sexo (etiquetas de la fuente)")

with t3:
    fuentes("salud", 'hmo_consulta.parquet')
    que("Izquierda: consultas por grupo de edad (de menor a mayor volumen). Derecha: "
        "reparto por sexo dentro de cada grupo (barras al 100%). La brecha hacia "
        "mujeres se concentra entre 15 y 49 años e incluso se invierte en infancia; "
        "descriptivo, sin atribuir causa.")
    c1, c2 = st.columns(2)
    ce_edad = con_f.groupby("Grupo_Edad")["Total"].sum().reset_index().sort_values("Total")
    c1.plotly_chart(px.bar(ce_edad, x="Total", y="Grupo_Edad", orientation="h",
                           title="Consulta externa por grupo de edad"), width="stretch", alt="Grafica: Consulta externa por grupo de edad")
    sx = con_f.groupby(["Grupo_Edad", "Sexo"])["Total"].sum().reset_index()
    sx = sx[sx.Sexo.isin(["HOMBRE", "MUJER"])]
    sx["pct"] = sx["Total"] / sx.groupby("Grupo_Edad")["Total"].transform("sum") * 100
    orden_edad = ["< 1", "1", "2-4", "5-9", "10-14", "15-19", "20-29",
                  "30-49", "50-59", "60 y más"]
    sx["Grupo_Edad"] = pd.Categorical(sx["Grupo_Edad"], categories=orden_edad,
                                       ordered=True)
    sx = sx.sort_values("Grupo_Edad")
    c2.plotly_chart(px.bar(sx, x="Grupo_Edad", y="pct", color="Sexo", barmode="stack",
                           title="Consulta externa: sexo por grupo de edad (%)",
                           category_orders={"Grupo_Edad": orden_edad},
                           labels={"pct": "% del grupo"}),
                    width="stretch", alt="Barras apiladas de sexo por grupo de edad")
    st.caption("Asociación sexo×edad: χ² p≈0, V de Cramér 0.30 (moderada). La brecha no es azar.")
    que("Los 10 establecimientos con más consultas en Hermosillo: dónde se concentra "
        "la atención ambulatoria.")
    top_est = con_f.groupby("Nombre_Establecimiento")["Total"].sum().nlargest(10).reset_index()
    st.plotly_chart(px.bar(top_est, x="Total", y="Nombre_Establecimiento", orientation="h",
                           title="Consulta externa: top 10 establecimientos"), width="stretch", alt="Grafica: Consulta externa: top 10 establecimientos")

with t4:
    fuentes("salud", 'hmo_nacimientos.parquet', 'hmo_defunciones.parquet')
    que("Nacimientos 2022 (madres residentes en HMO): edad de la madre y peso del "
        "recién nacido en gramos. Defunciones 2022 (residentes): edad al fallecer y "
        "top 10 causas básicas (CIE). Son registros individuales, no agregados.")
    c1, c2 = st.columns(2)
    f1 = px.histogram(nac, x="EDAD", nbins=30, title="Edad de la madre: media 27, grueso 20-35")
    f1.add_vline(x=float(nac["EDAD"].mean()), line_dash="dash", annotation_text="media")
    f1.add_vline(x=float(nac["EDAD"].median()), line_dash="dot", annotation_text="mediana")
    c1.plotly_chart(f1, width="stretch", alt="Histograma de edad de la madre con media y mediana")
    f2 = px.histogram(nac, x="PESO", nbins=40, title="Peso del RN: simétrico alrededor de 3.3 kg")
    f2.add_vline(x=float(nac["PESO"].mean()), line_dash="dash", annotation_text="media")
    f2.add_vline(x=float(nac["PESO"].median()), line_dash="dot", annotation_text="mediana")
    c1.plotly_chart(f2, width="stretch", alt="Histograma de peso del recién nacido con media y mediana")
    sxn = nac["SEXOD"].value_counts().reset_index()
    sxn.columns = ["sexo", "n"]
    c1.plotly_chart(px.bar(sxn, x="sexo", y="n", title="RN por sexo: 50.7% hombres (esperado ~51%)"),
                    width="stretch", alt="Barras de recién nacidos por sexo")
    que("Peso al nacer contra edad de la madre (regresión cuantílica, n=7,049): "
        "la mediana sube +3.1 g por año de madre (p=0.004); en q10 no hay efecto "
        "(p=0.23). Bandas q10-q90.")
    qg = pd.read_parquet(DATA / "modelos" / "inferencias" / "quantile_peso_grid.parquet")
    qg_m = qg.melt(id_vars="edad", value_vars=["q10", "q50", "q90"],
                   var_name="cuantil", value_name="peso")
    c1.plotly_chart(px.line(qg_m, x="edad", y="peso", color="cuantil",
                            title="Peso del RN: cuantiles por edad de la madre",
                            labels={"edad": "edad de la madre", "peso": "gramos"}),
                    width="stretch", alt="La mediana del peso sube con la edad de la madre; q10 plano")
    f3 = px.histogram(defu, x="EDAD", nbins=40, title="Edad al fallecer: mediana 68, cola joven a la izquierda")
    f3.add_vline(x=float(defu["EDAD"].mean()), line_dash="dash", annotation_text="media")
    f3.add_vline(x=float(defu["EDAD"].median()), line_dash="dot", annotation_text="mediana")
    c2.plotly_chart(f3, width="stretch", alt="Histograma de edad al fallecer con media y mediana")
    top_causa = defu.groupby("CIECAUSABASICAD").size().nlargest(10).reset_index(name="n")
    c2.plotly_chart(px.bar(top_causa, x="n", y="CIECAUSABASICAD", orientation="h",
                           title="Defunciones: top 10 causas básicas"), width="stretch", alt="Grafica: Defunciones: top 10 causas básicas")
    que("Tasas con denominador de proyecciones (Hermosillo 2022, IC95% Poisson): "
        "la mortalidad dibuja la J clásica y la fecundidad pica a los 20-29. "
        "Tasas observadas, no proyecciones.")
    tm = pd.read_parquet(DATA / "tidy" / "tasas_mortalidad_hmo2022.parquet")
    tf = pd.read_parquet(DATA / "tidy" / "tasas_fecundidad_hmo2022.parquet")
    c1.plotly_chart(px.bar(tm, x="grupo_edad", y="tasa_100k",
                           error_y=(tm["ic_hi"] - tm["tasa_100k"]),
                           error_y_minus=(tm["tasa_100k"] - tm["ic_lo"]),
                           title="Mortalidad por edad, HMO 2022 (por 100 mil + IC95%)",
                           labels={"grupo_edad": "edad", "tasa_100k": "por 100 mil"}),
                    width="stretch", alt="Mortalidad por edad con intervalos")
    c2.plotly_chart(px.bar(tf, x="grupo_edad", y="tasa_1k",
                           error_y=(tf["ic_hi"] - tf["tasa_1k"]),
                           error_y_minus=(tf["tasa_1k"] - tf["ic_lo"]),
                           title="Fecundidad por edad de la madre, HMO 2022 (por 1,000 + IC95%)",
                           labels={"grupo_edad": "edad madre", "tasa_1k": "por 1,000"}),
                    width="stretch", alt="Fecundidad por edad con intervalos")

with t5:
    fuentes("salud", 'hmo_vigilancia.parquet', 'hmo_inspecciones.parquet')
    que("Vigilancia epidemiológica 2022 en HMO (36 semanas con reporte): valores de la columna acumulado por diagnóstico "
        "(lideran infecciones respiratorias agudas y COVID-19) y suma de esos valores por "
        "semana epidemiológica, sin interpretar estos agregados como incidencia semanal.")
    top_v = vig.groupby("des_diagno")["acumulado"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_v, x="acumulado", y="des_diagno", orientation="h",
                           title="Vigilancia HMO: suma de valores de acumulado por diagnóstico"),
                    width="stretch")
    sem = vig.groupby("no_semana")["acumulado"].sum().reset_index()
    st.plotly_chart(px.line(sem, x="no_semana", y="acumulado",
                            title="Vigilancia HMO: suma de acumulado por semana declarada"),
                    width="stretch")
    if len(ins):
        que("Tabla de las 30 inspecciones sanitarias de PROAES realizadas en Hermosillo "
            "(3er trimestre 2021): fecha, actividad del lugar y motivo.")
        st.write("Inspecciones PROAES en Hermosillo (3er trim. 2021):", len(ins))
        st.dataframe(ins[["FECHA", "ACTIVIDAD", "MOTIVO", "MUNICIPIO"]], width="stretch")

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
    st.plotly_chart(fig, width="stretch", alt="Pronóstico mensual 2023 con banda de incertidumbre")
    st.caption(f"Error medido en 2021: urgencias MAE {met['urgencias']['mae']} "
               f"(MAPE {met['urgencias']['mape_pct']}%, R² {met['urgencias']['r2']}, "
               f"variante {met['urgencias']['modelo']}), "
               f"consulta MAE {met['consulta']['mae']} "
               f"(MAPE {met['consulta']['mape_pct']}%, R² {met['consulta']['r2']}, "
               f"variante {met['consulta']['modelo']}). "
               "R² negativo = peor que predecir el promedio mensual: úsese como "
               "perfil estacional de referencia, no como pronóstico operativo. SARIMAX probado aparte (ADF p>0.5, residuos autocorrelacionados): MAPE 28.4/60.5, no supera al perfil; ver metricas_sarimax.json.")
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
    st.plotly_chart(fig2, width="stretch", alt="Serie semanal de vigilancia con semanas atípicas marcadas")

with t7:
    st.header("Historia: lo que el portal cuenta (y lo que no)",
              icon=":material/auto_stories:")
    st.markdown("Hermosillo concentra la salud del estado: aquí se atiende, aquí "
                "nacen y aquí mueren en hospital personas que viven fuera. La "
                "consulta externa la usan sobre todo mujeres jóvenes y 2020 se "
                "desploma. Esto es lo que los datos sostienen, con sus límites "
                "a la vista.")
    st.subheader("1. La consulta externa es de mujeres jóvenes",
                 icon=":material/group:")
    st.badge("Verificado", icon=":material/check:", color="green")
    st.markdown("- **Evidencia**: 1,333,591 consultas; 62% mujeres, hasta 78% en "
                "20-29 y 74% en 15-19; en infancia predomina Hombre (5-9: 36% "
                "mujeres). Asociación sexo×edad χ² p≈0, V de Cramér 0.30.")
    st.caption("Límite: descriptivo por diseño; no se atribuye causa a la brecha.")
    st.subheader("2. 2020 se desploma y 2022 viene parcial",
                 icon=":material/trending_down:")
    st.badge("Verificado", icon=":material/check:", color="green")
    st.markdown("- **Evidencia**: consulta 163,651 en 2020 vs ~430 mil en "
                "2018-2019; 2022 trae 3 meses. Egresos: 230k filas idénticas "
                "retiradas → total publicado 220,954.")
    st.caption("Límite: años incompletos declarados como tales; sin inferir cobertura.")
    st.subheader("3. Hermosillo atiende de fuera",
                 icon=":material/local_hospital:")
    st.badge("Verificado", icon=":material/check:", color="green")
    st.markdown("- **Evidencia**: 7,893 partos ocurridos vs 7,049 madres "
                "residentes; 4,098 defunciones ocurridas vs 3,512 residentes.")
    st.caption("Límite: residencia ≠ ocurrencia; concentra atención hospitalaria, "
                "no necesariamente más nacimientos ni muertes.")
    st.subheader("4. IRA y COVID mandan la vigilancia",
                 icon=":material/coronavirus:")
    st.badge("Verificado", icon=":material/check:", color="green")
    st.markdown("- **Evidencia**: 63,700 IRA y 51,600 COVID en 2022 (36 semanas "
                "con reporte); semanas 3, 4 y 15 atípicas. El desglose de edad "
                "de la fuente es parcial (no suma al total).")
    st.caption("Límite: 'acumulado' = casos nuevos semanales, no acumulado anual.")
    st.subheader("5. Pronosticar aquí es perfilar, no predecir",
                 icon=":material/query_stats:")
    st.badge("Verificado", icon=":material/check:", color="green")
    st.markdown("- **Evidencia**: perfil estacional Ridge MAPE 26/35%; SARIMAX "
                "probado (MAPE 28/61, residuos autocorrelacionados) no lo supera. "
                "Tasas por 100 mil con IC95%: mortalidad en J, fecundidad pico "
                "20-29 (41.8-43.1‰).")
    st.caption("Límite: el cambio de nivel post-2020 limita todo pronóstico; "
                "las tasas usan proyección CONAPO como denominador, no conteo.")
    st.subheader("Procedencia y reglas del juego",
                 icon=":material/database:")
    st.markdown("Portal datos.sonora.gob.mx, descubierto y documentado vía la "
                "ontología mex-ontologi (MCP): cada cifra es un total declarado, "
                "cada serie se reporta por separado — sin cruces sin validación, "
                "sin inferir cobertura. Educación, seguridad y marginación viven "
                "en sus propios dashboards del mismo repo.")

with t8:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "significados documentales; las correspondencias con columnas se muestran por separado y requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, width="stretch")
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_salud_hermosillo.csv", "text/csv")
    fuentes("salud")
