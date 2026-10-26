"""Capa tidy de consumo (data/tidy/) desde el staging de data/seg/.

Tidy: una variable por columna (snake_case, sin tildes), una observacion
por fila. Corrige: mezcla de esquemas en victimas (2015 trae layout
municipal sin sexo/edad -> se excluye de victimas, serie desde 2016),
`src_anio` redundante, mes solo texto (se agrega mes_num), edad mezclada
en detenidas (edad_raw + edad_num). Vigilancia se derrite a long.
Escribe diccionario_datos.csv, procedencia_seg.json y registra los
artefactos en config/artefactos.json (sin inventar IRIs: ver huecos).
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEG = DATA / "seg"
RAW = DATA / "seg_raw"
TIDY = DATA / "tidy"
TIDY.mkdir(exist_ok=True)

ORDEN = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
         "Diciembre"]
MES_NUM = {v: i + 1 for i, v in enumerate(ORDEN)}

EDADES_VIG = {"menores_1": "0", "de01_a_04": "1-4", "de05_a_09": "5-9",
              "de10_a_14": "10-14", "de15_a_19": "15-19",
              "de20_a_24": "20-24", "de25_a_44": "25-44",
              "de45_a_49": "45-49", "de50_a_59": "50-59",
              "de60_a_64": "60-64", "de65_y_mas": "65+",
              "se_ignoran": "ignorado"}


def huella(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    ahora = datetime.now(timezone.utc).isoformat()
    out = {}

    # 1. Dimension municipal (74 filas segun catalogo de la fuente)
    cat = pd.read_excel(RAW / "catalogo.xlsx", sheet_name=0)
    cat.columns = [str(c).strip() for c in cat.columns]
    dim = pd.DataFrame({"cve_municipio": pd.to_numeric(cat["Cve. Municipio"],
                                                        errors="coerce")
                        .astype(int),
                        "municipio": cat["Municipio"].astype(str).str.strip()})
    dim.to_parquet(TIDY / "dim_municipios.parquet", index=False)
    out["dim_municipios.parquet"] = {
        "filas": len(dim), "origen": "catalogo.xlsx (recurso del conjunto)"}

    # 2. Incidencia: snake_case + mes_num, sin src_anio (== anio siempre)
    inc = pd.read_parquet(SEG / "incidencia.parquet")
    assert (inc["anio"] == inc["src_anio"]).all()
    ti = pd.DataFrame({
        "anio": inc["anio"].astype(int),
        "mes_num": inc["mes"].astype(str).map(MES_NUM).astype(int),
        "mes": inc["mes"].astype(str),
        "cve_municipio": pd.to_numeric(inc["Cve. Municipio"],
                                       errors="coerce").astype("Int64"),
        "municipio": inc["Municipio"].astype(str),
        "bien_juridico": inc[[c for c in inc.columns if "Bien" in str(c)][0]]
        .astype(str),
        "tipo_delito": inc["Tipo de delito"].astype(str),
        "subtipo_delito": inc["Subtipo de delito"].astype(str),
        "modalidad": inc["Modalidad"].astype(str),
        "n": inc["n"].astype(int)})
    assert ti["n"].sum() == inc["n"].sum()
    ti.to_parquet(TIDY / "hecho_incidencia.parquet", index=False)
    out["hecho_incidencia.parquet"] = {
        "filas": len(ti), "total_n": int(ti["n"].sum()),
        "origen": "incidencia.parquet (staging 2015-2025)"}

    # 3. Victimas: SIN 2015 (trae esquema municipal sin sexo/edad,
    # distinta poblacion). Serie comparable desde 2016.
    vic = pd.read_parquet(SEG / "victimas.parquet")
    excluidas = int((vic["anio"] == 2015).sum())
    v = vic[vic["anio"] != 2015].copy()
    tv = pd.DataFrame({
        "anio": v["anio"].astype(int),
        "mes_num": v["mes"].astype(str).map(MES_NUM).astype(int),
        "mes": v["mes"].astype(str),
        "sexo": v["Sexo"].astype(str),
        "rango_edad": v["Rango de edad"].astype(str),
        "bien_juridico": v[[c for c in v.columns if "Bien" in str(c)][0]]
        .astype(str),
        "tipo_delito": v["Tipo de delito"].astype(str),
        "subtipo_delito": v["Subtipo de delito"].astype(str),
        "modalidad": v["Modalidad"].astype(str),
        "n": v["n"].astype(int)})
    tv.to_parquet(TIDY / "hecho_victimas.parquet", index=False)
    out["hecho_victimas.parquet"] = {
        "filas": len(tv), "total_n": int(tv["n"].sum()),
        "origen": "victimas.parquet (staging, excluye 2015)",
        "excluidas_2015_otro_esquema": excluidas}

    # 4. 911: solo renombre (nulos de fuente se conservan)
    tel = pd.read_parquet(SEG / "llamadas911.parquet")
    tt = tel.rename(columns={"sexo reportante": "sexo_reportante",
                             "motivo no procedente": "motivo_no_procedente"})
    tt.to_parquet(TIDY / "hecho_llamadas911.parquet", index=False)
    out["hecho_llamadas911.parquet"] = {
        "filas": len(tt), "origen": "llamadas911.parquet (staging T1-T2 2026)"}

    # 5. Detenidas: edad_raw + edad_num (basura -> NaN, documentado)
    det = pd.read_parquet(SEG / "detenidas.parquet")
    td = pd.DataFrame({
        "fecha_parte": pd.to_datetime(det["fecha_parte"], errors="coerce"),
        "municipio": det["municipio"].astype(str),
        "sexo": det["sexo"].astype(str),
        "agencia": det["agencia"].astype(str),
        "delito": det["delito"].astype(str),
        "edad_raw": det["edad"].astype(str),
        "edad_num": pd.to_numeric(det["edad"], errors="coerce"),
        "nivel_fuerza": det["nivel_fuerza"].astype(str),
        "hora_detencion": det["hora de la detencion"].astype(str),
        "motivo_origen": det["motivo del origen"].astype(str)})
    td.to_parquet(TIDY / "hecho_detenidas.parquet", index=False)
    out["hecho_detenidas.parquet"] = {
        "filas": len(td),
        "edad_no_numerica": int(td["edad_num"].isna().sum()),
        "origen": "detenidas.parquet (staging T1-T3 2026)"}

    # 6. Desaparecidas: ya snake_case; se conserva + huecos documentados
    des = pd.read_parquet(SEG / "desaparecidas.parquet")
    des.to_parquet(TIDY / "hecho_desaparecidas.parquet", index=False)
    out["hecho_desaparecidas.parquet"] = {
        "filas": len(des), "origen": "desaparecidas.parquet (staging)"}

    # 7. Vigilancia: semanal (acumulado e instituciones, mismo grano)
    # + long de bandas x sexo (acumulado NO es suma de bandas: dif mediana 8.5)
    vg = pd.read_parquet(DATA / "hmo_vigilancia.parquet")
    bandas = [b for b in EDADES_VIG if b in vg.columns]
    chk = vg[bandas].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    dif = (pd.to_numeric(vg["acumulado"], errors="coerce").fillna(0) - chk).abs()
    reg = {"acumulado_vs_suma_bandas_max_dif": float(dif.max()),
           "acumulado_vs_suma_bandas_mediana_dif": float(dif.median())}
    idv = ["no_semana", "periodo", "des_munici", "des_diagno", "cve_diagno"]
    idv = [c for c in idv if c in vg.columns]
    inst = ["acumulado", "totalm", "totalf", "ssa", "imss_ord", "issste",
            "otras", "imss_sol", "d_if", "pemex", "sedena", "sedemar"]
    inst = [c for c in inst if c in vg.columns]
    tsem = vg[idv + inst].copy().rename(
        columns={"des_munici": "municipio", "des_diagno": "diagnostico",
                 "cve_diagno": "cve_diagnostico"})
    tsem.to_parquet(TIDY / "hecho_vigilancia_semanal.parquet", index=False)
    out["hecho_vigilancia_semanal.parquet"] = {
        "filas": len(tsem),
        "origen": "hmo_vigilancia.parquet (grano semana x diagnostico)"}
    partes = []
    for b, etiqueta in EDADES_VIG.items():
        if b not in vg.columns:
            continue
        base = vg[idv].copy()
        base["grupo_edad"] = etiqueta
        base["sexo"] = "total"
        base["n"] = pd.to_numeric(vg[b], errors="coerce").fillna(0).astype(int)
        partes.append(base)
        bf = b + "f"
        if bf in vg.columns:
            f = vg[idv].copy()
            f["grupo_edad"] = etiqueta
            f["sexo"] = "femenina"
            f["n"] = pd.to_numeric(vg[bf], errors="coerce").fillna(0).astype(int)
            partes.append(f)
    tvig = pd.concat(partes, ignore_index=True).rename(
        columns={"des_munici": "municipio", "des_diagno": "diagnostico",
                 "cve_diagno": "cve_diagnostico"})
    tvig.to_parquet(TIDY / "hecho_vigilancia_edad.parquet", index=False)
    out["hecho_vigilancia_edad.parquet"] = {
        "filas": len(tvig),
        "origen": "hmo_vigilancia.parquet (bandas x sexo; acumulado vive en tabla semanal)",
        **reg}

    # 8. Diccionario de datos
    dd = [
        ("dim_municipios", "cve_municipio", "entero", "clave INEGI 26001-26072 (+26998/26999)",
         "catalogo.xlsx", None),
        ("dim_municipios", "municipio", "texto", "nombre en catalogo (mayusculas/minusculas de fuente)", "catalogo.xlsx", None),
        ("hecho_incidencia", "anio", "entero", "2015-2025", "SESNSP via portal", None),
        ("hecho_incidencia", "mes_num", "entero 1-12", "derivado de mes", "tidy_seg.py", None),
        ("hecho_incidencia", "cve_municipio", "entero", "join con dim_municipios", "catalogo.xlsx", None),
        ("hecho_incidencia", "n", "entero", "delitos registrados; incluye ceros de la matriz SESNSP", "CSV anuales", None),
        ("hecho_victimas", "anio", "entero", "2016-2025 (2015 excluido: otro esquema)", "SESNSP via portal", "serie comparable desde 2016"),
        ("hecho_victimas", "sexo", "texto", "Mujer/Hombre/...", "vict_2016+", None),
        ("hecho_victimas", "rango_edad", "texto", "grupos de la fuente", "vict_2016+", None),
        ("hecho_victimas", "n", "entero", "victimas (no sumar con incidencia: distinta unidad)", "CSV anuales", None),
        ("hecho_llamadas911", "fecha/hora", "fecha/hora", "T1-T2 2026; hora 0-23", "911 SS", "327k sin municipio/clasificacion en fuente"),
        ("hecho_llamadas911", "motivo_no_procedente", "texto", "solo improcedentes; nulo en procedentes", "911 SS", None),
        ("hecho_detenidas", "edad_num", "numerico", "NaN = valor no numerico en fuente", "parte policial", "mediana 34; no imputar"),
        ("hecho_desaparecidas", "estatus_victima", "texto", "DESAPARECIDA/LOCALIZADA CON VIDA/SIN VIDA/NO LOCALIZADA", "CBP", "sin municipio en fuente"),
        ("hecho_desaparecidas", "anio_hecho", "numerico", "NaN = fecha_hechos invalida", "CBP", None),
        ("hecho_vigilancia_semanal", "acumulado", "entero", "casos semana x diagnostico (NO es suma de bandas)", "vigilancia 2022", "mediana dif vs bandas: 8.5"),
        ("hecho_vigilancia_edad", "grupo_edad", "texto", "0,1-4,...,65+,ignorado", "vigilancia 2022", None),
        ("hecho_vigilancia_edad", "sexo", "texto", "total/femenina (masculino = total - femenina)", "vigilancia 2022", None),
        ("hecho_vigilancia_edad", "n", "entero", "casos semana x diagnostico x edad x sexo", "vigilancia 2022", None),
    ]
    pd.DataFrame(dd, columns=["tabla", "columna", "tipo", "descripcion",
                              "origen", "nota"]).to_csv(
        TIDY / "diccionario_datos.csv", index=False, encoding="utf-8")

    # 9. Procedencia (huellas reales; IRIs pendientes -> hueco declarado)
    proc = {"tema": "seguridad", "generado_en_utc": ahora,
            "preprocesador": "tidy_seg.py",
            "preprocesador_sha256": huella(ROOT / "scripts/tidy_seg.py"),
            "staging": {k: {"filas": v["filas"], "sha256": None}
                        for k, v in out.items()},
            "artefactos": {}, "huecos": [
        "Sin snapshot ontologia_seg.json: columnas_ontologia e IRIs por columna pendientes (requiere exportar evidencia del MCP).",
        "Fecha de carga no documentada; generado_en_utc no acredita la carga.",
        "victimas 2015 excluida por cambio de esquema en fuente (ver nota).",
    ]}
    for name, spec in out.items():
        p = TIDY / name if (TIDY / name).exists() else None
        df = pd.read_parquet(TIDY / name)
        proc["artefactos"][name] = {
            **spec, "sha256": huella(TIDY / name),
            "columnas_salida": list(df.columns)}
    (DATA / "procedencia_seg.json").write_text(
        json.dumps(proc, ensure_ascii=False, indent=2), encoding="utf-8")

    # 10. Artefactos (formato ligero existente; sin inventar IRIs).
    # Solo agrega claves nuevas: no reformatea lo de otras sesiones.
    art_path = ROOT / "config/artefactos.json"
    art = json.loads(art_path.read_text(encoding="utf-8"))
    nuevo = dict(art)
    nuevo["tidy/dim_municipios.parquet"] = {
        "tema": "seguridad",
        "fuentes": [{"archivo": "seg_raw/catalogo.xlsx", "hoja": 0}],
        "filtro": "ninguno (catalogo completo 74 filas)",
        "transformacion": "Renombre a cve_municipio/municipio.",
        "medidas": [], "agregacion": "Sin agregar.",
        "alcance": "Catalogo tal cual lo publica la fuente."}
    art["tidy/hecho_incidencia.parquet"] = {
        "tema": "seguridad",
        "fuentes": [{"archivo": f"seg_raw/{a}.csv"} for a in range(2015, 2026)],
        "filtro": "ninguno (estatal completo)",
        "transformacion": "Largo anio-mes; snake_case; mes_num; sin src_anio.",
        "medidas": ["n"],
        "agregacion": "Suma de n por dimensiones del grafico.",
        "alcance": "Totales declarados; ceros incluidos de la matriz SESNSP."}
    art["tidy/hecho_victimas.parquet"] = {
        "tema": "seguridad",
        "fuentes": [{"archivo": f"seg_raw/vict_{a}.csv"} for a in range(2015, 2026)],
        "filtro": "anio != 2015 (esquema municipal sin sexo/edad)",
        "transformacion": "Largo anio-mes; snake_case; mes_num.",
        "medidas": ["n"],
        "agregacion": "Suma de n; no sumar con incidencia.",
        "alcance": "Serie comparable 2016-2025; unidad victima, no delito."}
    for t, f in [("tidy/hecho_llamadas911.parquet",
                  "llamadas 911 T1-T2 2026, snake_case"),
                 ("tidy/hecho_detenidas.parquet",
                  "detenidas T1-T3 2026, edad_raw + edad_num"),
                 ("tidy/hecho_desaparecidas.parquet",
                  "desaparecidas historico, sin cambios de columnas"),
                 ("tidy/hecho_vigilancia_semanal.parquet",
                  "vigilancia 2022 semanal (acumulado + instituciones)"),
                 ("tidy/hecho_vigilancia_edad.parquet",
                  "vigilancia 2022 derretida a semana x edad x sexo")]:
        nuevo[t] = {"tema": "seguridad", "fuentes": [{"archivo": f}],
                      "filtro": "ninguno", "transformacion": f,
                      "medidas": ["n"], "agregacion": "Suma de n.",
                      "alcance": "Totales declarados por la fuente."}
    if nuevo != art:
        art_path.write_text(
            json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    print(json.dumps({k: v.get("filas") for k, v in out.items()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
