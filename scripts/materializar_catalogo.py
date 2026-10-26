"""Catalogo tidy desde metadatos locales versionados (sin descarga CKAN).

Fuente: MEX-Ontologi/data/catalogo/metadatos.json (snapshot de la API del portal)
+ reports/portal-carga.json (manifiesto del store). Se registran huellas de ambas
fuentes en data/procedencia_catalogo.json y specs en config/artefactos.json.
"""

import json
from pathlib import Path

import pandas as pd

from evidencia import DATA, ROOT, ahora, guardar, huella

ONTO = Path(__import__("os").environ.get(
    "MEX_ONTOLOGIA_DIR", str(ROOT.parent / "MEX-Ontologi"))).resolve()


def main():
    meta_path = ONTO / "data" / "catalogo" / "metadatos.json"
    manifest_path = ONTO / "reports" / "portal-carga.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cj, rc = [], []
    for d in meta:
        grupos = ";".join(sorted({(g.get("title") or g.get("name") or "").strip()
                                  for g in (d.get("groups") or []) if g}))
        org = d.get("organization") or {}
        cj.append({"dataset_id": d.get("id"), "titulo": d.get("title"),
                   "nombre": d.get("name"), "grupos": grupos,
                   "organizacion": (org.get("title") or org.get("name")),
                   "n_recursos": len(d.get("resources") or [])})
        for r in (d.get("resources") or []):
            rc.append({"dataset_id": d.get("id"), "recurso_id": r.get("id"),
                       "nombre": r.get("name"), "formato": r.get("format")})
    cj = pd.DataFrame(cj).sort_values("titulo")
    rc = pd.DataFrame(rc)
    (DATA / "tidy").mkdir(exist_ok=True)
    cj.to_parquet(DATA / "tidy" / "catalogo_conjuntos.parquet", index=False)
    rc.to_parquet(DATA / "tidy" / "catalogo_recursos.parquet", index=False)
    proc = {"tema": "catalogo", "generado_en_utc": ahora(),
            "preprocesador": "materializar_catalogo.py",
            "preprocesador_sha256": huella(ROOT / "scripts" / "materializar_catalogo.py"),
            "fuentes": {
                "metadatos.json": {"sha256": huella(meta_path),
                                    "conjuntos": len(meta)},
                "portal-carga.json": {"sha256": huella(manifest_path),
                                       "triples": manifest.get("triples_combinados"),
                                       "generado_en_utc": manifest.get("generado_en_utc")}},
            "artefactos": {
                "tidy/catalogo_conjuntos.parquet": {
                    "filas": len(cj), "sha256": huella(DATA / "tidy" / "catalogo_conjuntos.parquet")},
                "tidy/catalogo_recursos.parquet": {
                    "filas": len(rc), "sha256": huella(DATA / "tidy" / "catalogo_recursos.parquet")}},
            "huecos": ["Fecha de carga del portal no documentada; generado_en_utc no acredita carga."]}
    guardar(DATA / "procedencia_catalogo.json", proc)
    art = json.loads((ROOT / "config" / "artefactos.json").read_text(encoding="utf-8"))
    art["tidy/catalogo_conjuntos.parquet"] = {
        "tema": "catalogo",
        "fuentes": [{"archivo": "MEX-Ontologi/data/catalogo/metadatos.json"}],
        "filtro": "ninguno (89 conjuntos)",
        "transformacion": "Una fila por conjunto: id, titulo, grupos, organizacion, n_recursos.",
        "medidas": ["n_recursos"], "agregacion": "Sin agregar.",
        "alcance": "Snapshot de metadatos versionado por huella."}
    art["tidy/catalogo_recursos.parquet"] = {
        "tema": "catalogo",
        "fuentes": [{"archivo": "MEX-Ontologi/data/catalogo/metadatos.json"}],
        "filtro": "ninguno",
        "transformacion": "Una fila por recurso: dataset, recurso, nombre, formato.",
        "medidas": [], "agregacion": "Sin agregar.",
        "alcance": "Snapshot de metadatos versionado por huella."}
    (ROOT / "config" / "artefactos.json").write_text(
        json.dumps(art, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("catalogo:", len(cj), "conjuntos,", len(rc), "recursos")


if __name__ == "__main__":
    main()
