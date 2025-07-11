import streamlit as st
import pandas as pd
import re
import sqlite3
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Extrae by Jose", layout="wide")
st.title("📦 Extraer Referencias de I-Construye desde Excel")
st.markdown("---")

# Diccionario de reemplazos
REEMPLAZOS = {
    " ": "",
    "OC:OC:": "OC",
    "Nª": "",
    "Ordendecompra:OC-3": "Ordendecompra:OC-03",
    "Ordendecompra:OC03": "Ordendecompra:OC-03",
    "Ordendecompra:OC3": "Ordendecompra:OC-03",
    "Ordendecompra:03": "Ordendecompra:OC-03",
    "Ordendecompra:3": "Ordendecompra:OC-03",
    "Ordendecompra:oc": "Ordendecompra:OC",
    "Ordendecompra:OC-2": "Ordendecompra:OC-02",
    "Ordendecompra:OC02": "Ordendecompra:OC-02",
    "Ordendecompra:OC2": "Ordendecompra:OC-02",
    "Ordendecompra:02": "Ordendecompra:OC-02",
    "Ordendecompra:2": "Ordendecompra:OC-02",
}

# Funciones de procesamiento
def reemplazar_varios(texto, reemplazos):
    for buscar, nuevo in reemplazos.items():
        if buscar in texto:
            texto = texto.replace(buscar, nuevo)
    return texto

#Extrae Guia
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

#extrae Referencia de NC y ND
def extraer_ref_factura(texto):
    if not isinstance(texto, str):
        return ""
    claves = ["Facturaelectrónica:", "Notadecréditoelectrónica:", "Facturaelectrónicanoafectaoexenta:"]
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

#Extrae la Orden de compra
def extraer_oc(texto):
    if not isinstance(texto, str):
        return ""
    try:
        inicio = texto.index("OC-0")
        return texto[inicio:inicio + 11]
    except ValueError:
        return ""

def guardar_en_base(df, nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        # Definir columnas clave para detectar duplicados, cambia según tu DataFrame
        columnas_clave = ["OC Extraída", "Guía Extraída", "Ref NC/ND Extraída"]
        
        # Eliminar duplicados basados en columnas clave
        df_sin_duplicados = df.drop_duplicates(subset=columnas_clave)
        
        # Guardar en SQLite, agregando datos
        df_sin_duplicados.to_sql(nombre_tabla, conn, if_exists="append", index=False)
        conn.close()
        st.info(f"📦 Datos guardados en la base '{base_datos}', tabla '{nombre_tabla}'.")
    except Exception as e:
        st.error(f"❌ Error al guardar en base de datos: {e}")


# Cargar archivo Excel
archivo = st.file_uploader("📁 Sube tu archivo Excel (.xlsx)", type="xlsx")

if archivo:
    df = pd.read_excel(archivo)

    # Normalizar datos
    col_base = df.columns[18]
    df[col_base] = df[col_base].apply(lambda x: reemplazar_varios(x, REEMPLAZOS) if isinstance(x, str) else x)
 

   

    # Procesar sobre la primera columna
    col_base = df.columns[18]
    df["Guía Extraída"] = df[col_base].apply(extraer_guia)
    df["OC Extraída"] = df[col_base].apply(extraer_oc)
    df["Ref NC/ND Extraída"] = df[col_base].apply(extraer_ref_factura)

    st.success("✅ Archivo procesado correctamente.")
    st.dataframe(df.head(20), use_container_width=True)

    guardar_en_base(df)

    # Botón descarga
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar archivo procesado",
        data=buffer,
        file_name="resultado_extraccion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Ver base de datos (navegar)
st.markdown("---")
if st.button("🔍 Ver Base de Datos"):
    st.switch_page("pages/ver_base_datos.py")  # si está en carpeta /pages/

# Instrucciones
st.subheader("📄 Instrucciones a considerar")
st.success("Procura habilitar el archivo Excel descargado desde I-Construye antes de subirlo.")

# Imágenes guía
col1, col2, col3 = st.columns(3)
with col1:
    st.image("Numero_1.png", caption="Paso 1", use_container_width=True)
    st.info("Descarga el archivo DTE y ábrelo")
with col2:
    st.image("Numero_2.png", caption="Paso 2", use_container_width=True)
    st.info("Presiona HABILITAR en la parte superior del Excel")
with col3:
    imagen = Image.open("Numero_3.png")
    st.image(imagen, caption="Paso 3", use_container_width=True)
    st.info("Guarda el archivo una vez habilitado con Ctrl + G y cierralo")