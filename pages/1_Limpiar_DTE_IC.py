# pages/1_Limpiar_DTE_IC.py
import streamlit as st
import pandas as pd
import re 
import sqlite3
from io import BytesIO
from PIL import Image # Importar Image para las imágenes de instrucciones

# No necesitas PIL.Image aquí a menos que tengas otras imágenes específicas de esta página
# from PIL import Image # Ya no es necesario aquí si las imágenes de instrucciones están en Inicio.py

# Configuración de la página (esto afectará la pestaña del navegador para esta página específica)
st.set_page_config(
    page_title="Extraer Referencias",
    layout="wide",
    page_icon="📦" # Un icono para la pestaña
)

st.title("📦 Extraer Referencias de I-Construye desde Excel")
st.markdown("---")

# Diccionario de reemplazos para normalizar texto en columna base
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
    "Ordendecompra:0C": "Ordendecompra:OC",
}

# Funciones de procesamiento
def reemplazar_varios(texto, reemplazos):
    for buscar, nuevo in reemplazos.items():
        if buscar in texto:
            texto = texto.replace(buscar, nuevo)
    return texto

def extraer_guias(texto):
    if not isinstance(texto, str):
        return []
    return [int(g) for g in re.findall(r"Guíadedespachoelectrónica:(\d+)", texto)]

def extraer_facturas(texto):
    if not isinstance(texto, str):
        return []
    patrones = [
        r"Facturaelectrónica:(\d+)",
        r"Notadecréditoelectrónica:(\d+)",
        r"Facturaelectrónicanoafectaoexenta:(\d+)"
    ]
    resultados = []
    for patron in patrones:
        resultados.extend([int(x) for x in re.findall(patron, texto)])
    return resultados

def extraer_oc(texto):
    if not isinstance(texto, str):
        return []
    return re.findall(r"(OC-\d{2,8})", texto)

def guardar_en_base(df, nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        conn.execute(f"DROP TABLE IF EXISTS {nombre_tabla}") # Esto borrará la tabla cada vez que se guarde
        df.to_sql(nombre_tabla, conn, if_exists="replace", index=False)
        conn.close()
        st.info(f"📦 Datos guardados en la base '{base_datos}', tabla '{nombre_tabla}'.")
    except Exception as e:
        st.error(f"❌ Error al guardar en base de datos: {e}")

# Widget para cargar archivo Excel
archivo = st.file_uploader("📁 Sube tu archivo Excel (.xlsx)", type="xlsx")

if archivo:
    df = pd.read_excel(archivo)

    def detectar_tipo_documento(tipo):
        if not isinstance(tipo, str):
            return "Otro"
        tipo = tipo.strip().lower()
        if "guía" in tipo:
            return "Guía"
        elif "nota de crédito" in tipo or "nota de débito" in tipo:
            return "NC/ND"
        elif "factura" in tipo:
            return "Factura"
        else:
            return "Otro"

    # Asegúrate de que la columna 1 exista
    if df.shape[1] > 1:
        df["Tipo Documento"] = df.iloc[:, 1].apply(detectar_tipo_documento)
    else:
        st.error("❌ El archivo Excel no tiene suficientes columnas. Se espera al menos la columna para 'Tipo Documento'.")
        st.stop() # Detiene la ejecución si la columna no existe

    # Asegúrate de que la columna 18 exista
    if df.shape[1] > 18:
        col_base = df.columns[18]
        df[col_base] = df[col_base].apply(lambda x: reemplazar_varios(x, REEMPLAZOS) if isinstance(x, str) else x)
    else:
        st.error("❌ El archivo Excel no tiene suficientes columnas. Se espera al menos la columna 19 (índice 18) para la columna base.")
        st.stop() # Detiene la ejecución si la columna no existe


    filas_expandidas = []

    for _, fila in df.iterrows():
        tipo = fila["Tipo Documento"]
        texto = fila[col_base]

        guias = extraer_guias(texto) if tipo in ["Factura", "NC/ND"] else []
        facturas = extraer_facturas(texto) if tipo == "NC/ND" else []
        ocs = extraer_oc(texto) if tipo in ["Guía", "Factura", "NC/ND"] else []

        if tipo == "Guía":
            if not ocs:
                nueva_fila = fila.copy()
                nueva_fila["Guía Extraída"] = ""
                nueva_fila["Ref NC/ND Extraída"] = ""
                nueva_fila["OC Extraída"] = ""
                filas_expandidas.append(nueva_fila)
            else:
                for oc in ocs:
                    nueva_fila = fila.copy()
                    nueva_fila["Guía Extraída"] = ""
                    nueva_fila["Ref NC/ND Extraída"] = ""
                    nueva_fila["OC Extraída"] = oc
                    filas_expandidas.append(nueva_fila)

        elif tipo == "Factura":
            if not guias:
                nueva_fila = fila.copy()
                nueva_fila["Guía Extraída"] = ""
                nueva_fila["Ref NC/ND Extraída"] = ""
                nueva_fila["OC Extraída"] = ocs[0] if ocs else ""
                filas_expandidas.append(nueva_fila)
            else:
                for guia in guias:
                    nueva_fila = fila.copy()
                    nueva_fila["Guía Extraída"] = guia
                    nueva_fila["Ref NC/ND Extraída"] = ""
                    nueva_fila["OC Extraída"] = ocs[0] if ocs else ""
                    filas_expandidas.append(nueva_fila)

        elif tipo == "NC/ND":
            if not facturas:
                nueva_fila = fila.copy()
                nueva_fila["Ref NC/ND Extraída"] = ""
                nueva_fila["Guía Extraída"] = guias[0] if guias else ""
                nueva_fila["OC Extraída"] = ocs[0] if ocs else ""
                filas_expandidas.append(nueva_fila)
            else:
                for factura in facturas:
                    nueva_fila = fila.copy()
                    nueva_fila["Ref NC/ND Extraída"] = factura
                    nueva_fila["Guía Extraída"] = guias[0] if guias else ""
                    nueva_fila["OC Extraída"] = ocs[0] if ocs else ""
                    filas_expandidas.append(nueva_fila)

        else:
            nueva_fila = fila.copy()
            nueva_fila["Guía Extraída"] = ""
            nueva_fila["Ref NC/ND Extraída"] = ""
            nueva_fila["OC Extraída"] = ""
            filas_expandidas.append(nueva_fila)

    df_expandido = pd.DataFrame(filas_expandidas)

    st.success("✅ Archivo procesado correctamente.")
    st.dataframe(df_expandido.head(20), use_container_width=True)

    guardar_en_base(df_expandido)

    buffer = BytesIO()
    df_expandido.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="📥 Descargar archivo procesado",
        data=buffer,
        file_name="resultado_extraccion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")

st.subheader("📄 Instrucciones a considerar para el procesamiento de Excel:")
st.success("Procura habilitar el archivo Excel descargado desde I-Construye antes de subirlo.")

col1, col2, col3 = st.columns(3)
with col1:
    st.image("src/assets/images/Numero_1.png", caption="Paso 1", use_container_width=True)
    st.info("Descarga el archivo DTE y ábrelo")
with col2:
    st.image("src/assets/images/Numero_2.png", caption="Paso 2", use_container_width=True)
    st.info("Presiona HABILITAR en la parte superior del Excel")
with col3:
    # Asegúrate de que la ruta de la imagen sea correcta
    imagen = Image.open("src/assets/images/Numero_3.png")
    st.image(imagen, caption="Paso 3", use_container_width=True)
    st.info("Guarda el archivo una vez habilitado con Ctrl + G y ciérralo")
st.markdown("---")
st.info("Utiliza la barra lateral para navegar a las diferentes secciones de la aplicación.")

# Ya no necesitas este botón porque Streamlit creará automáticamente la navegación
# if st.button("🔍 Ver Base de Datos"):
#     st.switch_page("pages/2_ver_base_datos.py") # Asegúrate de que la ruta sea correcta si la mantienes
