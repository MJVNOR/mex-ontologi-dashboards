"""Filtra marginación 2020 y genera parquet + resumen.

Municipios: las 72 filas ya son Sonora (CVE_ENT=26); se conservan tal cual.
Entidades: 33 filas (32 entidades + nacional); se conserva tal cual con marca
es_sonora. Valores declarados por la fuente, sin agregar ni imputar.
"""

import json
from pathlib import Path

import pandas as pd
from registrar_procedencia import registrar

ROOT = Path(__file__).resolve().parents[1]
MARG = ROOT / "data" / "marg"
OUT = ROOT / "data" / "marg_out"
OUT.mkdir(exist_ok=True)


def main():
    m = pd.read_excel(MARG / "indice-de-marginacion-municipios-2020.xlsx",
                      sheet_name="IMM_2020")
    assert sorted(m["CVE_ENT"].unique().tolist()) == [26], "se esperaba solo Sonora"
    assert len(m) == 72, f"se esperaban 72 municipios, hay {len(m)}"
    m.to_parquet(OUT / "municipios.parquet", index=False)

    e = pd.read_excel(MARG / "indice-de-marginacion-estados-2020.xlsx",
                      sheet_name="IME_2020")
    e["es_sonora"] = e["NOM_ENT"].astype(str).str.strip().str.upper() == "SONORA"
    assert int(e["es_sonora"].sum()) == 1, "Sonora debe aparecer una vez"
    # La fila Nacional trae marcadores no numéricos en IM/IMN/POSICION; se
    # convierten a NaN sin tocar los valores declarados de las entidades.
    for c in ("IM_2020", "IMN_2020", "POSICION"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e.to_parquet(OUT / "entidades.parquet", index=False)

    son = e[e["es_sonora"]].iloc[0]
    out = {
        "municipios": {"filas": len(m),
                       "po2sm_mediana": float(m["PO2SM"].median()),
                       "po2sm_min": float(m["PO2SM"].min()),
                       "po2sm_max": float(m["PO2SM"].max())},
        "entidades": {"filas": len(e),
                      "sonora_po2sm": float(son["PO2SM"]),
                      "sonora_grado": str(son["GM_2020"]),
                      "sonora_posicion": str(son["POSICION"])},
    }
    (OUT / "resumen_marginacion.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar("marginacion")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
