"""Procesa crudos de seguridad a parquet + mapa simplificado + resumen.

Columnas/municipios segun ontologia mex-ontologi (variables documentadas):
- incidencia: meses Enero..Diciembre, "Cve. Municipio" -> catalogo.xlsx
- victimas: idem + Sexo + Rango de edad (estatal, Clave_Ent=26)
- 911: MUNICIPIO, CLASIFICACION, SEXO REPORTANTE, FECHA
- detenidas: municipio, delito, sexo, edad
- desaparecidas: sexo_vic, estatus_victima, fecha_hechos (sin municipio)
- map.json: CVEGEO (26001..26072) -> se simplifica a 3 decimales
"""

import io
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "seg_raw"
OUT = ROOT / "data" / "seg"
OUT.mkdir(exist_ok=True)

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def leer_csv(p):
    try:
        df = pd.read_csv(p, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(p, encoding="latin1")
    df.columns = [str(c).strip().replace("\ufeff", "").strip("'\" ")
                  for c in df.columns]
    return df


def norm_anio(c):
    s = str(c).strip().lower().replace("a?o", "anio").replace("año", "anio")
    return "anio" if s in ("anio", "ano", "a") else s


def melt_meses(df):
    df = df.rename(columns={c: "anio" for c in df.columns
                            if norm_anio(c) == "anio"})
    meses = [m for m in MESES if m in df.columns]
    idx = [c for c in df.columns if c not in meses]
    largo = df.melt(id_vars=idx, value_vars=meses,
                    var_name="mes", value_name="n")
    largo["mes"] = pd.Categorical(largo["mes"], categories=MESES, ordered=True)
    largo["n"] = pd.to_numeric(largo["n"], errors="coerce").fillna(0).astype(int)
    return largo


def main():
    out = {}

    # 1. Incidencia municipal 2015-2025 + catalogo
    cat = pd.read_excel(RAW / "catalogo.xlsx", sheet_name=0)
    cat.columns = [str(c).strip() for c in cat.columns]
    cat["Cve. Municipio"] = pd.to_numeric(cat["Cve. Municipio"],
                                          errors="coerce").astype(int)
    inc = pd.concat([melt_meses(leer_csv(RAW / f"{a}.csv")).assign(src_anio=a)
                     for a in range(2015, 2026)], ignore_index=True)
    inc["Cve. Municipio"] = pd.to_numeric(inc["Cve. Municipio"],
                                          errors="coerce").astype("Int64")
    inc = inc.merge(cat, on="Cve. Municipio", how="left")
    inc.to_parquet(OUT / "incidencia.parquet", index=False)
    out["incidencia"] = {"filas_largas": len(inc),
                         "total": int(inc["n"].sum()),
                         "sin_municipio": int(inc["Municipio"].isna().sum())}

    # 2. Victimas fuero comun 2015-2025 (estatal Sonora)
    vic = pd.concat([melt_meses(leer_csv(RAW / f"vict_{a}.csv")).assign(src_anio=a)
                     for a in range(2015, 2026)], ignore_index=True)
    vic.to_parquet(OUT / "victimas.parquet", index=False)
    out["victimas"] = {"filas_largas": len(vic), "total": int(vic["n"].sum())}

    # 3. Llamadas 911 2026 T1-T2
    llamadas = []
    for f, tipo in [("llamadas-procedentes-911-primer-trimestre-2026.xlsx",
                     "procedente"),
                    ("llamadas-procedentes-911-segundo-trimestre-2026.xlsx",
                     "procedente"),
                    ("llamadas-improcedentes-911-primer-trimestre-2026.xlsx",
                     "improcedente"),
                    ("llamadas-improcedentes-911-segundo-trimestre-2026.xlsx",
                     "improcedente")]:
        d = pd.read_excel(RAW / f, sheet_name=0)
        d.columns = [str(c).strip().lower() for c in d.columns]
        d["tipo"] = tipo
        llamadas.append(d)
    tel = pd.concat(llamadas, ignore_index=True)
    tel["fecha"] = pd.to_datetime(tel["fecha"], errors="coerce")
    tel.to_parquet(OUT / "llamadas911.parquet", index=False)
    out["llamadas911"] = {"filas": len(tel),
                          "por_tipo": tel["tipo"].value_counts().astype(int).to_dict()}

    # 4. Detenidas 2026 T1-T3
    det = pd.concat([
        pd.read_excel(RAW / f"personas-detenidas-{t}-trimestre-2026.xlsx",
                      sheet_name=0)
        for t in ("primer", "segundo", "tercer")], ignore_index=True)
    det.columns = [str(c).strip().lower() for c in det.columns]
    det["fecha_parte"] = pd.to_datetime(det["fecha_parte"], errors="coerce")
    det["hora de la detencion"] = det["hora de la detencion"].astype(str)
    det.to_parquet(OUT / "detenidas.parquet", index=False)
    out["detenidas"] = {"filas": len(det)}

    # 5. Desaparecidas historico (sin columna municipal en la fuente)
    des = pd.read_excel(RAW / "cbp-desapariciones-sonora.xlsx", sheet_name=0)
    des.columns = [str(c).strip().lower() for c in des.columns]
    des["fecha_hechos"] = pd.to_datetime(des["fecha_hechos"], errors="coerce")
    des["anio_hecho"] = des["fecha_hechos"].dt.year
    for c in ("fecha_nac_vic", "fecha_localizacion"):  # ponytail: mezcla time/int basura
        des[c] = des[c].astype(str)
    des.to_parquet(OUT / "desaparecidas.parquet", index=False)
    out["desaparecidas"] = {"filas": len(des),
                            "por_estatus": des["estatus_victima"].value_counts()
                            .astype(int).to_dict()}

    # 6. Mapa municipal simplificado (3 decimales, solo CVEGEO+NOMGEO)
    geo = json.loads((RAW / "map.json").read_text(encoding="utf-8"))

    def redondea(coords):
        if isinstance(coords[0], (int, float)):
            return [round(coords[0], 3), round(coords[1], 3)]
        return [redondea(c) for c in coords]

    feats = []
    for f in geo["features"]:
        p = f.get("properties", {})
        g = dict(f["geometry"])
        g["coordinates"] = redondea(g["coordinates"])
        feats.append({"type": "Feature",
                      "properties": {"CVEGEO": str(p.get("CVEGEO")),
                                     "NOMGEO": str(p.get("NOMGEO"))},
                      "geometry": g})
    (OUT / "municipios.json").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats},
                   ensure_ascii=False), encoding="utf-8")
    out["mapa"] = {"municipios": len(feats),
                   "bytes": (OUT / "municipios.json").stat().st_size}

    (OUT / "resumen_seg.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:1500])


if __name__ == "__main__":
    main()
