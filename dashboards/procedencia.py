"""Fuentes y metodología de los artefactos publicados, sin conexión al grafo."""
import json
from pathlib import Path
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / 'data'


@st.cache_data
def cargar(tema):
    path = DATA / f'procedencia_{tema}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def fuentes(tema, *artefactos):
    with st.expander('Fuentes y metodología'):
        record = cargar(tema)
        if record is None:
            st.warning('Procedencia pendiente de regenerar. Estos resultados aún no tienen evidencia completa publicada.')
            return
        ontology = record['ontologia']
        st.caption('Consulta de ontología: ' + str(ontology.get('extraido_en_utc')))
        st.caption('Fecha de carga de ontología: ' + (ontology.get('fecha_carga_ontologia') or 'No documentada'))
        for name in artefactos or record['artefactos']:
            artifact = record['artefactos'][name]
            st.write('**' + name.split('/')[-1].replace('.parquet','') + '**')
            st.write('Filtro: ' + artifact['filtro'])
            st.write('Cálculo: ' + artifact['agregacion'])
            st.caption(artifact['alcance'])
            for source in artifact['fuentes']:
                sheet = 'primera hoja' if source['hoja_utilizada'] == 0 else 'hoja ' + str(source['hoja_utilizada'])
                st.markdown(f"[{source.get('conjunto', 'Archivo fuente')}]({source['url']}) · {sheet}")
                st.caption('Descarga: ' + source['descargado_en_utc'])
            for gap in artifact['huecos']:
                st.warning(gap)
            st.caption(artifact['nota_correspondencias'])
            st.dataframe(artifact['columnas_ontologia'], hide_index=True)
            st.dataframe(artifact['significados_documentados'], hide_index=True)
        st.download_button('Descargar evidencia y metodología', json.dumps(record, ensure_ascii=False, indent=2),
                           f'procedencia_{tema}.json', 'application/json', key='evidencia_' + tema + '_'.join(artefactos))
