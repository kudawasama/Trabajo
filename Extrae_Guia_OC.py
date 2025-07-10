import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Extraer Guía y OC", layout="wide")
st.title("📦 Extraer Guía de Despacho y Orden de Compra desde Excel")

# Diccionario de reemplazos
REEMPLAZOS = {
    " ": "",
    "Ordendecompra:OC-3": "Ordendecompra:OC-03",
    "Ordendecompra:OC03": "Ordendecompra:OC-03",
    "Ordendecompra:OC3": "Ordendecompra:OC-03",
    "Ordendecompra:03": "Ordendecompra:OC-03",
    "Ordendecompra:3": "Ordendecompra:OC-03",
    "Ordendecompra:OC-2": "Ordendecompra:OC-02",
    "Ordendecompra:OC02": "Ordendecompra:OC-02",
    "Ordendecompra:OC2": "Ordendecompra:OC-02",
    "Ordendecompra:02": "Ordendecompra:OC-02",
    "Ordendecompra:2": "Ordendecompra:OC-02",
}

# Función para reemplazo múltiple
def reemplazar_varios(texto, reemplazos):
    for buscar, nuevo in reemplazos.items():
        if buscar in texto:
            texto = texto.replace(buscar, nuevo)
    return texto

# Función para extraer guía
def extraer_guia(texto):
    if not isinstance(texto, str):
        return ""
    claves = ["Guíadedespachoelectrónica:", "Guíadedespacho:"]
    for clave in claves:
        pos = texto.find(clave)
        if pos != -1:
            inicio = pos + len(clave)
            break
    else:
        return ""
    caracteres_fin = r'[.,\s\-\/;!@#$%^&*\(\)_+=\[\]\{\}\|":<>\?`~]'
    match = re.search(caracteres_fin, texto[inicio:])
    fin = inicio + match.start() if match else len(texto)
    return texto[inicio:fin]

# Función para extraer OC
def extraer_oc(texto):
    if not isinstance(texto, str):
        return ""
    try:
        inicio = texto.index("OC-0")
        return texto[inicio:inicio + 11]
    except ValueError:
        return ""

# Interfaz
archivo = st.file_uploader("📁 Sube tu archivo Excel (.xlsx) Procura que Referencias esten en la primera columna (Columna A)", type="xlsx")

if archivo:
    df = pd.read_excel(archivo)

    # Reemplazos en todo el archivo
    df = df.applymap(lambda x: reemplazar_varios(x, REEMPLAZOS) if isinstance(x, str) else x)

    # Procesar sobre la primera columna
    col_base = df.columns[18]
    df["Guía Extraída"] = df[col_base].apply(extraer_guia)
    df["OC Extraída"] = df[col_base].apply(extraer_oc)

    st.success("✅ Archivo procesado correctamente.")
    st.dataframe(df.head(20), use_container_width=True)

    # Botón de descarga
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar archivo procesado",
        data=buffer,
        file_name="resultado_extraccion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
