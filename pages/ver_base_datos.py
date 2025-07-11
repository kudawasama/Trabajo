import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO


st.set_page_config(page_title="Ver Base de Datos", layout="wide")
st.title("📊 Ver Base de Datos")


def eliminar_duplicados_sqlite(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        # Cargar toda la tabla a DataFrame
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)

        # Eliminar duplicados según columnas clave
        columnas_clave = ["OC Extraída", "Guía Extraída", "Ref NC/ND Extraída"]
        df_limpio = df.drop_duplicates(subset=columnas_clave)

        # Sobrescribir la tabla con datos sin duplicados
        df_limpio.to_sql(nombre_tabla, conn, if_exists="replace", index=False)
        conn.close()
        st.success("✅ Duplicados eliminados correctamente de la base de datos.")
    except Exception as e:
        st.error(f"❌ Error al eliminar duplicados: {e}")

st.markdown("---")
if st.button("🧹 Eliminar duplicados de la base de datos"):
    eliminar_duplicados_sqlite()





# Conectar y leer
def cargar_base(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al cargar la base: {e}")
        return pd.DataFrame()

df = cargar_base()

if not df.empty:
    # Convertir nombres de columnas a minúsculas para comparación
    columnas = df.columns
    columnas_lower = list(map(str.lower, columnas))

    # Filtros
    with st.expander("🔎 Filtros avanzados"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_oc = st.text_input("🔍 Filtrar por OC")
        with col2:
            filtro_guia = st.text_input("🔍 Filtrar por Guía")
        with col3:
            filtro_factura = st.text_input("🔍 Filtrar por Ref NC/ND")
        with col4:
            # Buscar columna "fecha emisión" sin importar mayúsculas
            if "fecha emisión" in columnas_lower:
                idx = columnas_lower.index("fecha emisión")
                fecha_col = columnas[idx]
                df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
                fecha_min = df[fecha_col].min()
                fecha_max = df[fecha_col].max()
                rango_fechas = st.date_input("📅 Filtrar por fecha", [fecha_min, fecha_max])
            else:
                rango_fechas = None

    # Aplicar filtros
    if filtro_oc:
        df = df[df["OC Extraída"].str.contains(filtro_oc, na=False, case=False)]
    if filtro_guia:
        df = df[df["Guía Extraída"].str.contains(filtro_guia, na=False, case=False)]
    if filtro_factura:
        df = df[df["Ref NC/ND Extraída"].str.contains(filtro_factura, na=False, case=False)]
    if rango_fechas and 'fecha_col' in locals():
        df = df[
            (df[fecha_col] >= pd.to_datetime(rango_fechas[0])) &
            (df[fecha_col] <= pd.to_datetime(rango_fechas[1]))
        ]

    st.dataframe(df, use_container_width=True)


    # Descargar base filtrada
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label="📥 Exportar base como Excel",
        data=buffer,
        file_name="base_datos_filtrada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ No hay datos en la base.")


st.markdown("---")

if st.button("🔙 Volver al inicio"):
    st.info("Usa el menú lateral (izquierda) para volver a la página principal.")
