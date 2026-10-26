"""Audita tidy-data de los parquet del repo con Polars.

Tidy: cada variable una columna, cada observacion una fila, cada valor una celda.
Detecta: grano (conteo de filas vs combinaciones de claves), nulos/NaN,
columnas wide candidatas a pivot (grupos con prefijo comun) y duplicados.
"""

from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# (parquet, claves que deberian definir el grano, columnas wide sospechosas)
CANDIDATOS = {
    "hmo_urgencias.parquet": (["CLUES", "Mun_Nombre", "Sexo", "Edad", "Mes"], "Total_Urgencias"),
    "hmo_egresos.parquet": (["CLUES", "Mun_Nombre", "Sexo", "Edad", "Mes"], "Total_Egresos"),
    "hmo_consulta.parquet": (["CLUES", "Nomb_Mpo", "Sexo", "Grupo_Edad", "Mes", "Year"], "Total"),
    "hmo_vigilancia.parquet": (["des_munici", "des_diagno", "no_semana"], "acumulado"),
    "hmo_nacimientos.parquet": (None, None),
    "hmo_defunciones.parquet": (None, None),
    "edu_hmo/becas_hmo.parquet": (None, None),
    "edu_hmo/matriculas_uth_hmo.parquet": (None, None),
    "edu_hmo/reprobacion_uth.parquet": (["mat", "grupo", "corte"], None),
    "edu_hmo/titulados_uth.parquet": (["anio", "nivel", "programa", "sexo"], "n"),
    "edu_hmo/egresados_uth.parquet": (["anio", "nivel", "programa", "sexo"], "n"),
    "edu_hmo/nuevo_ingreso_uth.parquet": (["anio", "nivel", "programa", "sexo"], "n"),
    "seg/incidencia.parquet": (None, None),
    "seg/victimas.parquet": (None, None),
    "seg/llamadas911.parquet": (None, None),
    "seg/detenidas.parquet": (None, None),
    "seg/desaparecidas.parquet": (None, None),
}


def main():
    for rel, (keys, val) in CANDIDATOS.items():
        p = DATA / rel
        if not p.exists():
            print(f"{rel}: NO EXISTE"); continue
        df = pl.read_parquet(p)
        n = df.height
        nulos = sum(df.null_count().row(0))
        print(f"== {rel}: filas={n} cols={len(df.columns)} nulos={nulos}")
        # duplicados exactos
        dup = n - df.unique(maintain_order=False).height
        if dup:
            print(f"   DUPLICADOS exactos: {dup}")
        # grano
        if keys:
            kk = [k for k in keys if k in df.columns]
            g = df.group_by(kk).len()
            multi = g.filter(pl.col("len") > 1).height
            print(f"   claves={kk} combos={g.height} combos-multi-fila={multi}")
        # wide: columnas numericas con prefijo comun
        if "vigilancia" in rel or "reprobacion" in rel:
            nums = [c for c, t in zip(df.columns, df.dtypes) if t.is_numeric()]
            print(f"   numericas wide: {len(nums)}: {nums[:12]}")


if __name__ == "__main__":
    main()
