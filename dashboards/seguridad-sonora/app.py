"""Dashboard Seguridad Sonora — datos abiertos via ontologia mex-ontologi.

Fuente: portal datos.sonora.gob.mx, conjuntos identificados con el MCP
mex-ontologia (store portal, 322495 triples; variables y significados en
data/significados_seg.csv). Descarga: scripts/descargar_seguridad.py.
Filtros y agregados: scripts/preprocesar_seg.py -> data/seg/*.parquet.
Los totales son los declarados por la fuente, sin inferir cobertura ni
cruzar series (cada conjunto se reporta por separado).
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
SEG = DATA / "seg"
st.set_page_config(page_title="Seguridad Sonora", layout="wide")
st.title("Seguridad en Sonora — datos abiertos")
st.caption("Fuente: portal datos.sonora.gob.mx (SESNSP, CBP, SS). "
           "Identificación y significados vía ontología mex-ontologi (MCP). "
           "Totales declarados por la fuente; series sin cruzar entre sí.")


def que(mensaje):
    st.caption("📊 " + mensaje)


@st.cache_data
def load(name):
    return pd.read_parquet(SEG / name)


@st.cache_data
def significados():
    return pd.read_csv(DATA / "significados_seg.csv")


@st.cache_data
def geo():
    return json.loads((SEG / "municipios.json").read_text(encoding="utf-8"))


inc = load("incidencia.parquet")
vic = load("victimas.parquet")
tel = load("llamadas911.parquet")
det = load("detenidas.parquet")
des = load("desaparecidas.parquet")

tipo_d = [c for c in inc.columns if str(c).strip() == "Tipo de delito"][0]
vtipo = [c for c in vic.columns if str(c).strip() == "Tipo de delito"][0]

anios = sorted(inc["anio"].dropna().unique().astype(int))
sel = st.sidebar.multiselect("Años (incidencia / víctimas)", anios,
                             default=anios[-5:])
inc_f = inc[inc["anio"].isin(sel)] if sel else inc
vic_f = vic[vic["anio"].isin(sel)] if sel else vic

mun_tot = (inc_f.groupby(["Cve. Municipio", "Municipio"])["n"].sum()
           .reset_index())
mun_tot["cve"] = mun_tot["Cve. Municipio"].astype(int).map(lambda c: f"{c:05d}")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Delitos (incidencia)", f"{int(inc_f['n'].sum()):,}")
k2.metric("Víctimas fuero común", f"{int(vic_f['n'].sum()):,}")
k3.metric("Llamadas 911 (2026 T1-T2)", f"{len(tel):,}")
k4.metric("Detenidas 2026 (T1-T3)", f"{len(det):,}")
k5.metric("Desaparecidas (histórico)", f"{len(des):,}")

t1, t2, t3, t4, t5, t6, t7 = st.tabs(
    ["Mapa municipal", "Delitos y comparador", "Víctimas",
     "911", "Detenidas / Desaparecidas", "Modelos", "Ontología"])

with t1:
    que("Mapa: delitos registrados por municipio en los años elegidos "
        "(rojo = más delitos). Abajo, el ranking de los 15 municipios con "
        "más registros. Hermosillo, Cajeme, SLRC y Nogales concentran el grueso.")
    fig = px.choropleth(
        mun_tot, geojson=geo(), locations="cve",
        featureidkey="properties.CVEGEO", color="n",
        hover_name="Municipio", color_continuous_scale="Reds",
        title="Incidencia delictiva por municipio")
    fig.update_geos(fitbounds="locations", visible=False)
    st.plotly_chart(fig, use_container_width=True)
    top_m = mun_tot.nlargest(15, "n")
    st.plotly_chart(px.bar(top_m, x="n", y="Municipio", orientation="h",
                           title="Top 15 municipios por delitos"),
                    use_container_width=True)

with t2:
    que("Serie anual 2015-2025: total de delitos por año. Permite ver "
        "tendencia estatal de una década.")
    s = inc_f.groupby("anio")["n"].sum().reset_index()
    st.plotly_chart(px.line(s, x="anio", y="n", markers=True,
                            title="Delitos por año en Sonora"),
                    use_container_width=True)
    que("Los 12 tipos de delito con más registros en el periodo: robo "
        "domina, seguido de homicidio y lesiones.")
    top_t = inc_f.groupby(tipo_d)["n"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_t, x="n", y=tipo_d, orientation="h",
                           title="Top 12 tipos de delito"),
                    use_container_width=True)
    que("Mapa de calor mes × año: junio y octubre concentran el pico y "
        "diciembre cae. Cada celda es el total de delitos de ese mes.")
    hm = inc_f.groupby(["anio", "mes"], observed=True)["n"].sum().reset_index()
    hm = hm.pivot(index="mes", columns="anio", values="n")
    st.plotly_chart(px.imshow(hm, title="Delitos por mes y año",
                              labels={"x": "año", "y": "mes",
                                      "color": "delitos"}),
                    use_container_width=True)
    que("Violencia familiar es la modalidad con más registros del periodo. "
        "Feminicidio aparte: 340 casos 2015-2025, con pico en 2021.")
    vf = inc_f[inc_f["Modalidad"] == "Violencia familiar"] \
        .groupby("anio")["n"].sum().reset_index()
    st.plotly_chart(px.line(vf, x="anio", y="n", markers=True,
                            title="Violencia familiar por año"),
                    use_container_width=True)
    fem = inc_f[inc_f[tipo_d] == "Feminicidio"] \
        .groupby("anio")["n"].sum().reset_index()
    st.plotly_chart(px.bar(fem, x="anio", y="n",
                           title="Feminicidio por año (Sonora)"),
                    use_container_width=True)
    que("Robo: vehículo y casa habitación lideran después de 'otros robos'. "
        "Homicidio: arma de fuego duplica a accidente de tránsito.")
    c1, c2 = st.columns(2)
    rb = inc_f[inc_f[tipo_d] == "Robo"].groupby("Subtipo de delito")["n"] \
        .sum().nlargest(8).reset_index()
    c1.plotly_chart(px.bar(rb, x="n", y="Subtipo de delito", orientation="h",
                           title="Robo: subtipos"), use_container_width=True)
    ho = inc_f[inc_f[tipo_d] == "Homicidio"].groupby("Modalidad")["n"] \
        .sum().nlargest(6).reset_index()
    c2.plotly_chart(px.bar(ho, x="n", y="Modalidad", orientation="h",
                           title="Homicidio: modalidad"), use_container_width=True)
    que("Comparador: elige municipios y ve su serie anual lado a lado.")
    opc = sorted(mun_tot["Municipio"].dropna().unique())
    comp = st.multiselect("Municipios a comparar",
                          opc, default=["Hermosillo", "Cajeme", "Nogales"])
    if comp:
        c = inc_f[inc_f["Municipio"].isin(comp)].groupby(
            ["Municipio", "anio"])["n"].sum().reset_index()
        st.plotly_chart(px.line(c, x="anio", y="n", color="Municipio",
                                markers=True, title="Comparador municipal"),
                        use_container_width=True)

with t3:
    que("Víctimas del fuero común (nivel estatal, SESNSP): serie anual y "
        "reparto por sexo y grupo de edad. Son registros de víctimas, no de "
        "delitos: no se suman con incidencia.")
    sv = vic_f.groupby("anio")["n"].sum().reset_index()
    st.plotly_chart(px.line(sv, x="anio", y="n", markers=True,
                            title="Víctimas por año (Sonora)"),
                    use_container_width=True)
    c1, c2 = st.columns(2)
    sexo_v = [c for c in vic.columns if str(c).strip().lower() == "sexo"][0]
    edad_v = [c for c in vic.columns if "edad" in str(c).lower()][0]
    c1.plotly_chart(px.pie(vic_f.groupby(sexo_v)["n"].sum().reset_index(),
                           names=sexo_v, values="n",
                           title="Víctimas por sexo"), use_container_width=True)
    c2.plotly_chart(px.bar(vic_f.groupby(edad_v)["n"].sum().reset_index(),
                           x="n", y=edad_v, orientation="h",
                           title="Víctimas por grupo de edad"),
                    use_container_width=True)
    top_vt = vic_f.groupby(vtipo)["n"].sum().nlargest(12).reset_index()
    st.plotly_chart(px.bar(top_vt, x="n", y=vtipo, orientation="h",
                           title="Víctimas: top 12 tipos de delito"),
                    use_container_width=True)

with t4:
    que("Llamadas al 911 en 2026 (T1-T2): más de un millón entre procedentes "
        "e improcedentes. Serie diaria y reparto por tipo.")
    tel = tel.assign(dia=pd.to_datetime(tel["fecha"]).dt.date)
    d = tel.groupby(["dia", "tipo"]).size().reset_index(name="n")
    st.plotly_chart(px.line(d, x="dia", y="n", color="tipo",
                            title="Llamadas 911 por día"),
                    use_container_width=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(tel.groupby("tipo").size().reset_index(name="n"),
                           names="tipo", values="n",
                           title="Procedentes vs improcedentes"),
                    use_container_width=True)
    top_tm = tel["municipio"].value_counts().nlargest(12).reset_index()
    top_tm.columns = ["municipio", "n"]
    c2.plotly_chart(px.bar(top_tm, x="n", y="municipio", orientation="h",
                           title="Top 12 municipios que más llaman"),
                    use_container_width=True)
    que("Las 12 clasificaciones más reportadas en llamadas procedentes "
        "(seguridad, médicas, servicios) y los motivos de improcedencia.")
    top_cl = tel[tel["tipo"] == "procedente"]["clasificacion"].value_counts(
        ).nlargest(12).reset_index()
    top_cl.columns = ["clasificacion", "n"]
    st.plotly_chart(px.bar(top_cl, x="n", y="clasificacion", orientation="h",
                           title="Procedentes: top clasificaciones"),
                    use_container_width=True)
    if "motivo no procedente" in tel.columns:
        colg = int((tel["motivo no procedente"]
                    == "NO CONTESTA O CUELGA LA LLAMADA").sum())
        broma = int(tel["motivo no procedente"].str.contains(
            "BROMA", na=False).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("Colgadas / no contesta", f"{colg:,}")
        m2.metric("Bromas (niños, adolescentes y adultos)", f"{broma:,}")
        m3.metric("Hora pico de llamadas", "18-21h")
        top_mo = tel[tel["tipo"] == "improcedente"]["motivo no procedente"] \
            .value_counts().nlargest(10).reset_index()
        top_mo.columns = ["motivo", "n"]
        st.plotly_chart(px.bar(top_mo, x="n", y="motivo", orientation="h",
                               title="Improcedentes: top motivos"),
                        use_container_width=True)
        st.caption("⚠️ Calidad: 37% de las llamadas trae sexo del reportante "
                   "'no registrado'; se reporta tal cual, sin imputar.")

with t5:
    que("Detenidas 2026 (T1-T3): delitos más frecuentes, reparto por sexo y "
        "edad. Delitos contra la salud y faltas administrativas lideran.")
    c1, c2 = st.columns(2)
    top_dl = det["delito"].value_counts().nlargest(12).reset_index()
    top_dl.columns = ["delito", "n"]
    c1.plotly_chart(px.bar(top_dl, x="n", y="delito", orientation="h",
                           title="Detenciones: top delitos"),
                    use_container_width=True)
    c2.plotly_chart(px.pie(det.groupby("sexo").size().reset_index(name="n"),
                           names="sexo", values="n",
                           title="Detenidas por sexo"), use_container_width=True)
    det["edad"] = pd.to_numeric(det["edad"], errors="coerce")
    st.plotly_chart(px.histogram(det.dropna(subset=["edad"]), x="edad",
                                 nbins=30, title="Detenidas: edad"),
                    use_container_width=True)
    st.caption("⚠️ Calidad: la mediana de edad es 34, pero hay registros con "
               "valores imposibles (errores de captura); se reportan tal "
               "cual, sin imputar.")
    que("Desaparecidas (histórico CBP): estatus de localización, reparto por "
        "sexo y casos por año del hecho. 6,432 siguen desaparecidas y solo "
        "36.7% aparecieron con vida (2015-2025); en 2024-25 los casos se "
        "disparan a ~1.8k/año —¿mejor registro o más casos? La fuente no "
        "trae municipio, así que no se mapea.")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(des.groupby("estatus_victima").size()
                           .reset_index(name="n"),
                           names="estatus_victima", values="n",
                           title="Estatus de localización"),
                    use_container_width=True)
    c2.plotly_chart(px.pie(des.groupby("sexo_vic").size()
                           .reset_index(name="n"),
                           names="sexo_vic", values="n",
                           title="Por sexo"), use_container_width=True)
    da = des.dropna(subset=["anio_hecho"]).groupby("anio_hecho").size() \
        .reset_index(name="n").sort_values("anio_hecho")
    st.plotly_chart(px.bar(da, x="anio_hecho", y="n",
                           title="Desapariciones por año del hecho"),
                    use_container_width=True)

with t6:
    que("KMeans (k=4) sobre el perfil delictivo de cada municipio "
        "(2015-2025): Hermosillo y Cajeme forman su propio grupo; Caborca, "
        "Guaymas, Navojoa, Nogales y SLRC el cinturón intermedio; el resto "
        "comparte perfil bajo. PCA conserva el 92% de la varianza en 2D.")
    cl = load("inferencias/clusters_municipio.parquet").merge(
        mun_tot[["Municipio", "cve"]], on="Municipio", how="left")
    nom = {0: "Resto (65)", 1: "Hermosillo", 2: "Cajeme",
           3: "Cinturón (5)"}
    cl["grupo"] = cl["cluster"].map(nom)
    st.plotly_chart(px.choropleth(
        cl, geojson=geo(), locations="cve",
        featureidkey="properties.CVEGEO", color="grupo",
        hover_name="Municipio", title="Clusters por perfil delictivo")
        .update_geos(fitbounds="locations", visible=False),
        use_container_width=True)
    pc = load("inferencias/pca_municipios.parquet")
    pc["grupo"] = pc["cluster"].map(nom)
    st.plotly_chart(px.scatter(pc, x="x", y="y", color="grupo",
                               hover_name="Municipio",
                               title="PCA de perfiles municipales (2D)"),
                    use_container_width=True)
    que("Anomalías mensuales de incidencia (IsolationForest): el pico de "
        "2016, el diciembre bajo de 2017 y marzo-2021. Son banderas para "
        "revisar, no diagnósticos.")
    am = load("inferencias/anomalias_incidencia.parquet")
    am["fecha"] = (am["anio"].astype(int).astype(str) + "-" +
                   am["mes"].astype(str).map(
                       {v: f"{i + 1:02d}" for i, v in enumerate(
                           ["Enero", "Febrero", "Marzo", "Abril", "Mayo",
                            "Junio", "Julio", "Agosto", "Septiembre",
                            "Octubre", "Noviembre", "Diciembre"])}))
    figm = px.line(am, x="fecha", y="n", title="Incidencia mensual estatal")
    figm.add_scatter(x=am[am.anomalia == -1]["fecha"],
                     y=am[am.anomalia == -1]["n"], mode="markers",
                     marker={"size": 10}, name="anomalía")
    st.plotly_chart(figm, use_container_width=True)
    que("Anomalías en llamadas 911 por día (T1-T2 2026): 9 días fuera de lo "
        "común, arriba y abajo del flujo normal.")
    a9 = load("inferencias/anomalias_911.parquet")
    fig9 = px.line(a9, x="dia", y="n", title="Llamadas 911 por día")
    fig9.add_scatter(x=a9[a9.anomalia == -1]["dia"],
                     y=a9[a9.anomalia == -1]["n"], mode="markers",
                     marker={"size": 10}, name="anomalía")
    st.plotly_chart(fig9, use_container_width=True)
    import plotly.graph_objects as go

    pr = load("inferencias/pred_municipio.parquet")
    pr["nm_t"] = pr["nm"] % 12 + 1
    pr["fecha_t"] = (pr["target_anio"].astype(int).astype(str) + "-" +
                     pr["nm_t"].map(lambda m: f"{m:02d}"))
    que("Predictor del mes siguiente por municipio (RandomForest, split "
        "temporal ≤2022 → ≥2023): R² 0.936, MAE 9.6, supera al naive "
        "estacional (0.912). Ejemplo Hermosillo: real vs pronóstico.")
    hmo = pr[pr.Municipio == "Hermosillo"].sort_values("fecha_t")
    figp = px.line(hmo, x="fecha_t", y=["target", "pred"],
                   title="Hermosillo: real vs pronóstico (test ≥2023)",
                   labels={"value": "delitos", "variable": "serie"})
    st.plotly_chart(figp, use_container_width=True)
    que("SHAP (Permutation, background=train): el promedio móvil de 3 meses "
        "y el mes anterior explican el pronóstico; municipio y mes pesan "
        "poco. Describe al modelo, no es causalidad.")
    si = load("inferencias/shap_importancia.parquet")
    si["nombre"] = si["feature"].str.replace("remainder__", "") \
        .str.replace("cat__Municipio_", "Mpio: ").str.replace("cat__nm_", "mes=")
    st.plotly_chart(px.bar(si.nlargest(15, "mean_abs_shap"),
                           x="mean_abs_shap", y="nombre", orientation="h",
                           title="SHAP: |atribución| media (top 15)"),
                    use_container_width=True)
    wf = load("inferencias/shap_waterfall_hmo.parquet")
    wf = wf.sort_values("shap_value", ascending=False)
    top = wf.head(8)
    resto = wf.iloc[8:]["shap_value"].sum()
    base = float(wf["base_value"].iloc[0])
    figw = go.Figure(go.Waterfall(
        x=["base"] + top["feature"].str.replace(
            "remainder__", "").str.replace(
            "cat__Municipio_", "Mpio: ").str.replace(
            "cat__nm_", "mes=").tolist() + ["resto", "pronóstico"],
        y=[base] + top["shap_value"].tolist() + [resto,
                                                 float(wf["prediccion"].iloc[0])],
        measure=["absolute"] + ["relative"] * (len(top) + 1) + ["total"]))
    figw.update_layout(title="Waterfall: Hermosillo nov-2025 → dic-2025 "
                             f"(pronóstico {float(wf['prediccion'].iloc[0]):.0f})")
    st.plotly_chart(figw, use_container_width=True)
    st.caption("⚠️ Se probó pronóstico estacional (Ridge, 2015-2023 → "
               "2024-2025): R² < 0, peor que predecir la media. No se "
               "publica pronóstico. Métricas en data/seg/resumen_modelos_seg.json.")

with t7:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "qué significa cada columna de los conjuntos de seguridad según la fuente.")
    sig = significados()
    st.dataframe(sig, use_container_width=True)
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_seg_sonora.csv", "text/csv")
    st.json({"conjuntos_seguridad": 7, "significados": len(sig),
             "triples_store_portal": 322495,
             "nota": "Incidencia y víctimas no se suman entre sí (distinta "
                     "unidad de conteo); desaparecidas sin municipio en fuente."})
