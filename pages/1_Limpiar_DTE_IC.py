# pages/1_Limpiar_DTE_IC.py
import streamlit as st
import pandas as pd
import re 
import sqlite3
from io import BytesIO
from PIL import Image

st.set_page_config(
    page_title="Extraer Referencias",
    layout="wide",
    page_icon="📦"
)

st.title("📦 Extraer Referencias de I-Construye desde Excel")
st.markdown("---")

# Reemplazos para normalizar texto
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

# Cargar archivo
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

    if df.shape[1] > 1:
        df["Tipo Documento"] = df.iloc[:, 1].apply(detectar_tipo_documento)
    else:
        st.error("❌ El archivo Excel no tiene suficientes columnas.")
        st.stop()

    if df.shape[1] > 18:
        col_base = df.columns[18]
        df[col_base] = df[col_base].apply(lambda x: reemplazar_varios(x, REEMPLAZOS) if isinstance(x, str) else x)
    else:
        st.error("❌ El archivo Excel no tiene suficientes columnas (19 esperadas).")
        st.stop()

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

    # Crear dataframes separados
    df_facturas = df_expandido[df_expandido["Tipo Documento"] == "Factura"]
    df_guias = df_expandido[df_expandido["Tipo Documento"] == "Guía"]
    df_ncnd = df_expandido[df_expandido["Tipo Documento"] == "NC/ND"]

    # Crear DataFrame sin duplicar con columnas extraídas
    df_sin_duplicar = df.copy()
    df_sin_duplicar["Guía Extraída"] = df["Guía Extraída"] if "Guía Extraída" in df else ""
    df_sin_duplicar["Ref NC/ND Extraída"] = df["Ref NC/ND Extraída"] if "Ref NC/ND Extraída" in df else ""
    df_sin_duplicar["OC Extraída"] = df["OC Extraída"] if "OC Extraída" in df else ""

    # Guardar todas las tablas en base de datos
    try:
        conn = sqlite3.connect("facturas.db")
        df_expandido.to_sql("facturas_extraidas", conn, if_exists="replace", index=False)
        df_facturas.to_sql("solo_facturas", conn, if_exists="replace", index=False)
        df_guias.to_sql("solo_guias", conn, if_exists="replace", index=False)
        df_ncnd.to_sql("solo_nc_nd", conn, if_exists="replace", index=False)
        df_sin_duplicar.to_sql("sin_duplicar", conn, if_exists="replace", index=False)
        conn.close()
        st.success("🗃️ Todas las tablas fueron guardadas correctamente en la base de datos.")
    except Exception as e:
        st.error(f"❌ Error al guardar en base de datos: {e}")

    # Crear Excel multi-hoja
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_expandido.to_excel(writer, sheet_name="Procesado", index=False)
        df_facturas.to_excel(writer, sheet_name="Facturas", index=False)
        df_guias.to_excel(writer, sheet_name="Guias", index=False)
        df_ncnd.to_excel(writer, sheet_name="NC_ND", index=False)
        df_sin_duplicar.to_excel(writer, sheet_name="Sin Duplicar", index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Descargar Excel con hojas separadas",
        data=buffer,
        file_name="extraccion_referencias.xlsx",
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
    imagen = Image.open("src/assets/images/Numero_3.png")
    st.image(imagen, caption="Paso 3", use_container_width=True)
    st.info("Guarda el archivo una vez habilitado con Ctrl + G y ciérralo")

st.markdown("---")
st.info("Utiliza la barra lateral para navegar a las diferentes secciones de la aplicación.")
