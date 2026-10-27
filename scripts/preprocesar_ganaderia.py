"""Concatena producción pecuaria, censo y subastas; genera parquet + procedencia.

Granos (valores declarados por la fuente, sin imputar ni cruzar conjuntos):
- produccion.parquet: municipio x mes x especie-producto x año (2006-2012,
  2014-2018, 2020-2024). 2013 sin URL en el portal (HTTP 500); 2019 es
  duplicado byte a byte del 2020 en la fuente y se usa una sola vez.
  VOLTON conserva UMED original (TONELADAS vs MILES DE LITROS: no se suman
  entre unidades distintas). VALPROD en miles de pesos MXN (diccionario).
- censo.parquet: municipio x año (2022-2024, 72 municipios) + nombre de
  municipio desde el catálogo del conjunto. Cabezas y productores.
- subastas.parquet: lote subastado 2007-2025. cant en cabezas, precios en
  pesos/kg, peso en kg/cabeza. cvem se reporta tal cual (12 municipios con
  subasta; sin mapa: cobertura parcial declarada).
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "gan_raw"
OUT = ROOT / "data" / "gan"
OUT.mkdir(exist_ok=True)

# nombre de crudo -> recurso CKAN (de config/recursos.json, tema ganaderia)
RECURSOS = {r["archivo"].split("/", 1)[1]: r["recurso_id"] for r in
            json.loads((ROOT / "config" / "recursos.json")
                       .read_text(encoding="utf-8"))["ganaderia"]}
# nombre de crudo -> hoja utilizada (de config/artefactos.json)
HOJAS = {}
for _spec in json.loads((ROOT / "config" / "artefactos.json")
                        .read_text(encoding="utf-8")).values():
    if _spec.get("tema") != "ganaderia":
        continue
    for _f in _spec.get("fuentes", []):
        HOJAS.setdefault(_f["archivo"].split("/", 1)[1], _f.get("hoja"))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ahora():
    return datetime.now(timezone.utc).isoformat()


PROD_COLS = ["ANO", "CIERYAVAN", "CDDR", "NDDR", "CMUN", "NMUN", "CVEMES",
             "NMES", "CVESPE", "ESPECIE", "PRODUC", "UMED", "VOLTON", "VALPROD"]
PROD_RENAME = {"ANO": "anio", "CIERYAVAN": "cierre_avance", "CDDR": "cddr",
               "NDDR": "nddr", "CMUN": "cmun", "NMUN": "nmun", "CVEMES": "cvemes",
               "NMES": "nmes", "CVESPE": "cvespe", "ESPECIE": "especie",
               "PRODUC": "produc", "UMED": "umed", "VOLTON": "vol",
               "VALPROD": "val_miles_mxn"}


def hoja_unica(path):
    x = pd.ExcelFile(path)
    if len(x.sheet_names) != 1:
        raise RuntimeError(f"{path.name}: hojas {x.sheet_names}, se esperaba 1")
    return x.sheet_names[0]


def leer_prod(path):
    d = pd.read_excel(path, sheet_name=hoja_unica(path))
    if list(d.columns) != PROD_COLS:
        raise RuntimeError(f"{path.name}: columnas {list(d.columns)}")
    d = d.rename(columns=PROD_RENAME)
    for c in ("cierre_avance", "nddr", "nmun", "nmes", "especie", "produc",
              "umed"):
        d[c] = d[c].astype(str).str.strip()
    return d


CENSO_RENAME = {"DDR": "ddr", "REGION": "region", "CUENCA": "cuenca",
                "No. PROD. CENSADOS": "n_prod", "VACAS": "vacas", "TOROS": "toros",
                "VAQUILLAS": "vaquillas", "NOVILLOS": "novillos",
                "BECERRAS": "becerras", "BECERROS": "becerros",
                "TOTAL GANADO BOVINO": "total_bovino", "PORCINOS": "porcinos",
                "EQUINO": "equino", "CAPRINO": "caprino", "MULAR": "mular",
                "ASNAL": "asnal", "OVINOS": "ovinos",
                "TOTAL GANADO MENOR": "total_menor", "Año": "anio",
                "MUNI": "cmun"}


def leer_censo(path, dim_mun):
    d = pd.read_excel(path, sheet_name=hoja_unica(path))
    d = d.rename(columns=CENSO_RENAME)
    d["anio"] = pd.to_numeric(d["anio"], errors="raise")
    d = d.merge(dim_mun, on="cmun", how="left")
    if d["municipio"].isna().any():
        faltan = sorted(d.loc[d["municipio"].isna(), "cmun"].unique().tolist())
        raise RuntimeError(f"{path.name}: MUNI sin catálogo {faltan}")
    return d


SUB_RENAME = {"nsub": "nsub", "dia": "dia", "cvem": "cvem", "ano": "anio",
              "cvetg": "cvetg", "tipogan": "tipo_ganado", "cant": "cant_cabezas",
              "premin": "precio_min", "premax": "precio_max",
              "preprom": "precio_prom", "pesoprom": "peso_prom_kg"}


def leer_subastas(path):
    d = pd.read_excel(path, sheet_name=hoja_unica(path))
    if list(d.columns) != list(SUB_RENAME):
        raise RuntimeError(f"{path.name}: columnas {list(d.columns)}")
    d = d.rename(columns=SUB_RENAME)
    d["tipo_ganado"] = d["tipo_ganado"].astype(str).str.strip()
    return d


def main():
    descargas = []
    # --- catálogos (dimensiones declaradas por la fuente) ---
    dim_mun = pd.read_excel(RAW / "catalogo_ganaderia.xlsx",
                            sheet_name="Municipios")
    dim_mun = dim_mun.rename(columns={"MUNI": "cmun", "MUNICIPIOS": "municipio",
                                      "region": "region_cat"})[["cmun", "municipio"]]
    dim_esp = pd.read_excel(RAW / "catalogo_ganaderia.xlsx",
                            sheet_name="Catálogo_Ganadería")
    dim_esp = dim_esp.rename(columns={"cvespe": "cvespe", "espe": "especie",
                                      "produc": "produc",
                                      "umedida": "umed"})[["cvespe", "especie",
                                                           "produc", "umed"]]
    dim_tg = pd.read_excel(RAW / "catalogo_subastas.xlsx",
                           sheet_name="Tipos de Ganado")
    dim_tg = dim_tg.rename(columns={"cvetg": "cvetg",
                                    "Especie": "tipo_ganado"})[["cvetg", "tipo_ganado"]]

    # --- producción 2006-2012, 2014-2018, 2020-2024 ---
    prod_files = [f"ganaderia_{a}.xlsx" for a in
                  (list(range(2006, 2013)) + list(range(2014, 2019))
                   + list(range(2020, 2025)))]
    prod = pd.concat([leer_prod(RAW / f) for f in prod_files],
                     ignore_index=True)
    assert sorted(prod["anio"].unique().tolist()) == (
        list(range(2006, 2013)) + list(range(2014, 2019))
        + list(range(2020, 2025))), sorted(prod["anio"].unique().tolist())
    assert len(prod) == sum(len(leer_prod(RAW / f)) for f in prod_files)

    # --- censo 2022-2024 ---
    censo = pd.concat(
        [leer_censo(RAW / f"censo_{a}.xlsx", dim_mun) for a in (2022, 2023, 2024)],
        ignore_index=True)
    assert len(censo) == 216, len(censo)

    # --- subastas 2007-2025 ---
    sub = pd.concat(
        [leer_subastas(RAW / "subastas_2007_2017.xlsx")] +
        [leer_subastas(RAW / f"subastas_{a}.xlsx") for a in range(2018, 2026)],
        ignore_index=True)
    assert sub["anio"].min() == 2007 and sub["anio"].max() == 2025

    for name, frame in (("produccion.parquet", prod), ("censo.parquet", censo),
                        ("subastas.parquet", sub),
                        ("dim_municipios.parquet", dim_mun),
                        ("dim_especie_producto.parquet", dim_esp),
                        ("dim_tipo_ganado.parquet", dim_tg)):
        frame.to_parquet(OUT / name, index=False)

    for f in sorted(RAW.glob("*")):
        stem = f.stem
        if stem.startswith("diccionario_ganaderia") or stem.startswith("ganaderia_") or stem == "catalogo_ganaderia":
            ds = "092f6ac2-2714-44b3-a18a-bdca7893bb73"
            conjunto = "Ganadería Sonora"
        elif stem.startswith("diccionario_censo") or stem.startswith("censo_") or stem == "catalogo_censo":
            ds = "5a511ff8-6a45-4589-8ef3-22000d5676f4"
            conjunto = "Censo Ganadero de Sonora"
        else:
            ds = "932de35b-e9d4-4acb-bd1e-d54c70f6f45e"
            conjunto = "Subastas Ganaderas"
        res_id = RECURSOS.get(f.name, "")
        hoja = HOJAS.get(f.name)
        descargas.append({
            "archivo": f"gan_raw/{f.name}",
            "conjunto": conjunto,
            "dataset": f"https://example.org/mex-ontologi/dataset/{ds}",
            "dataset_id": ds,
            "recurso": (f"https://example.org/mex-ontologi/resource/{res_id}"
                        if res_id else None),
            "recurso_id": res_id,
            "url": (f"https://datos.sonora.gob.mx/dataset/{ds}/resource/"
                    f"{res_id}/download/{f.name}" if res_id else
                    f"https://datos.sonora.gob.mx/dataset/{ds}"),
            "hoja_utilizada": hoja,
            "sha256": sha(f), "descargado_en_utc": ahora(),
            "huecos": (
                "2013 sin URL en el portal (HTTP 500); 2019 duplicado del "
                "2020 en la fuente (mismo sha256) y se usa una sola vez."
                if stem.startswith("ganaderia") else None),
        })
    (ROOT / "data" / "descargas_ganaderia.json").write_text(
        json.dumps(descargas, ensure_ascii=False, indent=2), encoding="utf-8")

    snapshot = json.loads(
        (ROOT / "data" / "ontologia_ganaderia.json").read_text(encoding="utf-8"))
    specs = json.loads(
        (ROOT / "config" / "artefactos.json").read_text(encoding="utf-8"))
    import csv as _csv
    with open(ROOT / "data" / "significados_ganaderia.csv", encoding="utf-8") as _fh:
        _sig = list(_csv.DictReader(_fh))
    _sig_por_conjunto = {}
    for _row in _sig:
        _sig_por_conjunto.setdefault(_row["conjunto"], []).append(_row)
    por_artefacto = {
        "gan/produccion.parquet": ("produccion.parquet", prod, "Ganadería Sonora"),
        "gan/censo.parquet": ("censo.parquet", censo, "Censo Ganadero de Sonora"),
        "gan/subastas.parquet": ("subastas.parquet", sub, "Subastas Ganaderas"),
    }
    artefactos = {}
    for name, (fname, frame, conjunto) in por_artefacto.items():
        spec = specs[name]
        artefactos[name] = {
            **spec, "sha256": sha(OUT / fname), "filas": len(frame),
            "columnas_salida": list(frame.columns),
            "fuentes": [r for r in descargas
                        if Path(r["archivo"]).stem in spec["archivos_crudo"]],
            "columnas_ontologia": [],
            "significados_documentados": _sig_por_conjunto.get(conjunto, []),
            "huecos": (list(snapshot["huecos"]) + spec.get("huecos_extra", [])
                       + ["Columnas por recurso no exportadas a procedencia "
                          "(alcance por etiquetas de correspondencia)."]),
            "nota_correspondencias": ("documental_revisada confirma la "
                                      "interpretación documental de la columna; "
                                      "no valida filas ni autoriza cruces."),
        }
    (ROOT / "data" / "procedencia_ganaderia.json").write_text(json.dumps(
        {"tema": "ganaderia", "generado_en_utc": ahora(),
         "preprocesador": "preprocesar_ganaderia.py",
         "preprocesador_sha256": sha(ROOT / "scripts" / "preprocesar_ganaderia.py"),
         "ontologia": snapshot["ontologia"],
         "snapshot_sha256": sha(ROOT / "data" / "ontologia_ganaderia.json"),
         "artefactos": artefactos}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in
                      (("produccion", prod), ("censo", censo),
                       ("subastas", sub))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
