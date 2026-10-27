"""Dashboard Ganadería Sonora — datos abiertos via ontología mex-ontologi.

Fuente: 3 conjuntos del portal datos.sonora.gob.mx (Ganadería Sonora,
Censo Ganadero, Subastas Ganaderas), identificados por consultas al MCP
mex-ontologia (store portal, 322495 triples; 407 correspondencias
documental_revisada; significados en data/significados_ganaderia.csv).
Descarga: scripts/descargar_ganaderia.py (helper CKAN autorizado).
Filtros y agregados: scripts/preprocesar_ganaderia.py -> data/gan/*.parquet.
Totales declarados por la fuente; cada conjunto se reporta por separado,
sin cruces ni cobertura inferida.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procedencia import fuentes

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
GAN = DATA / "gan"
st.set_page_config(page_title="Ganadería Sonora", layout="wide",
                   page_icon=":material/agriculture:")
st.title("Ganadería en Sonora — datos abiertos")
st.caption("Fuente: portal datos.sonora.gob.mx (3 conjuntos pecuarios). "
           "Identificación y significados vía ontología mex-ontologi (MCP). "
           "Totales declarados por la fuente; series por separado, sin cruces.")


def que(mensaje):
    st.caption(":material/insights: " + mensaje)


def hbar(df, x, y, title):
    # ponytail: ascendente para que la barra mayor quede arriba
    return px.bar(df.sort_values(x, ascending=True), x=x, y=y,
                  orientation="h", title=title)


@st.cache_data
def load(name):
    return pd.read_parquet(GAN / name)


@st.cache_data
def significados():
    return pd.read_csv(DATA / "significados_ganaderia.csv")


prod = load("produccion.parquet")
censo = load("censo.parquet")
sub = load("subastas.parquet")

anios = sorted(prod["anio"].unique())
sel = st.sidebar.multiselect("Años (producción)", anios, default=anios)
prod_f = prod[prod["anio"].isin(sel)] if sel else prod

fuentes("ganaderia", "gan/produccion.parquet", "gan/censo.parquet",
        "gan/subastas.parquet")

ton = prod_f[prod_f["umed"] == "TONELADAS"]["val_miles_mxn"].sum()
leche = prod_f[prod_f["umed"] == "MILES DE LITROS"]["val_miles_mxn"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Valor carne/miel/huevo (miles MXN)", f"{ton:,.0f}", border=True)
k2.metric("Valor leche (miles MXN)", f"{leche:,.0f}", border=True)
k3.metric("Bovino censado 2024 (cabezas)",
          f"{int(censo[censo['anio'] == 2024]['total_bovino'].sum()):,}",
          border=True)
k4.metric("Cabezas subastadas 2007-2025", f"{int(sub['cant_cabezas'].sum()):,}",
          f"{len(sub):,} lotes", border=True)

th, t1, t2, t3, t4 = st.tabs(
    ["Hallazgos :material/auto_stories:", "Producción :material/beef:",
     "Censo :material/groups:", "Subastas :material/gavel:",
     "Ontología :material/hub:"])

with th:
    st.header("Lo que el portal cuenta (y lo que no)")
    with st.container(border=True):
        st.subheader("1. El porcino vale más que el bovino")
        st.badge("Verificado", icon=":material/check:", color="green")
        st.markdown("**CARNE de porcino: 147,667 miles de MXN** acumulados "
                    "(2006-2024, 17 años con datos) vs **82,842 bovino** y "
                    "**48,492 huevo de ave**. (Ver en: Producción)")
        st.caption("Límite: miles de pesos corrientes declarados, sin deflactar; "
                   "2013 sin datos y 2019 duplica al 2020 en la fuente.")
    with st.container(border=True):
        st.subheader("2. El hato censado cae 2022-2024")
        st.badge("Verificado", icon=":material/check:", color="green")
        st.markdown("Bovino **1,400,461 → 1,163,086 cabezas**; ganado menor "
                    "**141,452 → 83,320**; productores **30,298 → 27,387**. "
                    "(Ver en: Censo)")
        st.caption("Límite: 3 cortes transversales; no es seguimiento de cohortes, "
                   "no se afirma causa de la caída.")
    with st.container(border=True):
        st.subheader("3. La subasta mueve 1M de cabezas con precio estable")
        st.badge("Verificado", icon=":material/check:", color="green")
        st.markdown("**1,073,182 cabezas en 21,253 lotes** (2007-2025); precio "
                    "promedio ponderado global **176.44 $/kg**; "
                    "BECERROS #1 aporta 294,428 cabezas. (Ver en: Subastas)")
        st.caption("Límite: 12 municipios con subasta (cvem 1-12); no acredita "
                   "hato estatal ni precios fuera de subasta.")
    with st.container(border=True):
        st.subheader("Conclusiones y pendientes")
        st.badge("Verificado", icon=":material/check:", color="green")
        st.markdown("**Sí se sostiene**: ranking porcino > bovino en valor; caída "
                    "censal 2022-2024; volumen y precio de subasta por tipo. "
                    "**No se sostiene**: causas, cobertura del hato, precios de "
                    "mercado, nada de 2013/2019 como años propios.")
        st.badge("Pregunta abierta", icon=":material/help:", color="orange")
        st.markdown("¿Qué pasó en 2013 (recurso caído en el portal)? ¿Por qué el "
                    "2019 duplica al 2020? ¿Cuánto del hato pasa por subasta? "
                    "Cruces con agricultura/pesca pendientes de evaluar.")

with t1:
    fuentes("ganaderia", "gan/produccion.parquet")
    que("Valor anual de la producción por unidad de medida (miles de MXN): "
        "toneladas (carne, huevo, miel) y miles de litros (leche) no se suman "
        "entre sí. 2013 sin datos; 2019 reutiliza el archivo 2020 de la fuente.")
    s = prod_f.groupby(["anio", "umed"])["val_miles_mxn"].sum().reset_index()
    st.plotly_chart(px.bar(s, x="anio", y="val_miles_mxn", color="umed",
                           barmode="group", title="Valor por año y UMED",
                           labels={"anio": "año",
                                   "val_miles_mxn": "miles de MXN"}),
                    width="stretch")
    que("Especie-producto por valor acumulado en el periodo elegido: el porcino "
        "domina la carne; la leche es bovina.")
    top_e = prod_f.groupby(["especie", "produc"])["val_miles_mxn"].sum() \
        .reset_index().sort_values("val_miles_mxn", ascending=False).head(10)
    top_e["et"] = top_e["especie"] + " · " + top_e["produc"]
    st.plotly_chart(hbar(top_e, "val_miles_mxn", "et",
                         "Top especie-producto por valor"),
                    width="stretch")
    que("Municipios con más valor acumulado: Hermosillo, Navojoa y Cajeme "
        "concentran la producción declarada.")
    top_m = prod_f.groupby("nmun")["val_miles_mxn"].sum().reset_index() \
        .nlargest(12, "val_miles_mxn")
    st.plotly_chart(hbar(top_m, "val_miles_mxn", "nmun",
                         "Top 12 municipios por valor"),
                    width="stretch")

with t2:
    fuentes("ganaderia", "gan/censo.parquet")
    que("Hato y productores por año de censo (2022-2024): tres cortes "
        "transversales, sin seguimiento de cohortes.")
    s = censo.groupby("anio")[["total_bovino", "total_menor", "n_prod"]].sum() \
        .reset_index()
    st.plotly_chart(px.bar(s.melt(id_vars="anio", var_name="serie",
                                  value_name="n"),
                           x="anio", y="n", color="serie", barmode="group",
                           title="Censo por año: hato y productores",
                           labels={"anio": "año", "n": "cabezas / productores"}),
                    width="stretch")
    que("Composición del bovino 2024: vacas y becerros al frente; toros, la "
        "fracción menor. Top de municipios por hato bovino.")
    c24 = censo[censo["anio"] == 2024]
    comp = c24[["vacas", "toros", "vaquillas", "novillos", "becerras",
                "becerros"]].sum().reset_index()
    comp.columns = ["categoria", "n"]
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(comp, names="categoria", values="n",
                           title="Bovino 2024 por categoría"), width="stretch")
    top_c = c24.groupby("municipio")["total_bovino"].sum().reset_index() \
        .nlargest(12, "total_bovino")
    c2.plotly_chart(hbar(top_c, "total_bovino", "municipio",
                         "Top 12 municipios por bovino 2024"),
                    width="stretch")

with t3:
    fuentes("ganaderia", "gan/subastas.parquet")
    que("Cabezas subastadas por año y precio promedio ponderado por cabezas "
        "(no promedio simple de lotes). 2007-2025, 12 municipios.")
    s = sub.groupby("anio").apply(
        lambda d: pd.Series({"cabezas": d["cant_cabezas"].sum(),
                             "precio_pond": (d["precio_prom"]
                                             * d["cant_cabezas"]).sum()
                             / d["cant_cabezas"].sum()})).reset_index()
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(s, x="anio", y="cabezas",
                           title="Cabezas subastadas por año",
                           labels={"anio": "año"}), width="stretch")
    c2.plotly_chart(px.line(s, x="anio", y="precio_pond", markers=True,
                            title="Precio ponderado por año ($/kg)",
                            labels={"anio": "año",
                                    "precio_pond": "$/kg"}), width="stretch")
    que("Tipos de ganado por cabezas y su precio ponderado: becerros y becerras "
        "#1 concentran el volumen.")
    top_t = sub.groupby("tipo_ganado")["cant_cabezas"].sum().reset_index() \
        .nlargest(12, "cant_cabezas")
    st.plotly_chart(hbar(top_t, "cant_cabezas", "tipo_ganado",
                         "Top 12 tipos por cabezas"), width="stretch")
    pp = sub.groupby("tipo_ganado").apply(
        lambda d: (d["precio_prom"] * d["cant_cabezas"]).sum()
        / d["cant_cabezas"].sum()).reset_index(name="precio_pond")
    pp = pp[pp["tipo_ganado"].isin(set(top_t["tipo_ganado"]))]
    st.plotly_chart(hbar(pp, "precio_pond", "tipo_ganado",
                         "Precio ponderado ($/kg): top tipos por volumen"),
                    width="stretch")

with t4:
    st.write("Variables y significados documentados en la ontología (mex-ontologi): "
             "46 variables documental_revisada en 3 conjuntos; las correspondencias "
             "con columnas requieren revisar su estado.")
    sig = significados()
    st.dataframe(sig, width="stretch")
    st.download_button("Descargar significados (CSV)",
                       sig.to_csv(index=False).encode("utf-8"),
                       "significados_ganaderia.csv", "text/csv")
    st.write("Capa de consumo (`data/gan/`, snake_case): 3 tablas + 3 dimensiones, "
             "con procedencia en `data/procedencia_ganaderia.json`.")
    fuentes("ganaderia")
