import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="Ver Base de Datos", layout="wide")
st.title("📊 Ver Base de Datos")

# === Eliminar duplicados ===
def eliminar_duplicados_sqlite(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
        columnas_clave = ["OC Extraída", "Guía Extraída", "Ref NC/ND Extraída"]
        df_limpio = df.drop_duplicates(subset=columnas_clave)
        df_limpio.to_sql(nombre_tabla, conn, if_exists="replace", index=False)
        conn.close()
        st.success("✅ Duplicados eliminados correctamente.")
    except Exception as e:
        st.error(f"❌ Error al eliminar duplicados: {e}")

st.markdown("---")
if st.button("🧹 Eliminar duplicados de la base de datos"):
    eliminar_duplicados_sqlite()

# === Cargar base desde SQLite ===
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

# === Validación de integridad ===
def validar_referencias(df):
    errores = []

    def normalizar(valor):
        if pd.isna(valor):
            return ""
        return str(valor).strip().upper()

    facturas = df[df["Tipo Documento"].str.lower().str.contains("factura")]
    guias = df[df["Tipo Documento"].str.lower().str.contains("guía")]
    notas = df[df["Tipo Documento"].str.lower().str.contains("nota")]

    facturas_ids = set(facturas["Ref NC/ND Extraída"].apply(normalizar))
    guias_ids = set(guias["Guía Extraída"].apply(normalizar))
    oc_ids = set(df["OC Extraída"].apply(normalizar))

    for _, fila in notas.iterrows():
        ref_factura = normalizar(fila["Ref NC/ND Extraída"])
        if ref_factura and ref_factura not in facturas_ids:
            errores.append({
                "Línea": fila.name + 2,
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_factura,
                "Problema": "❌ No se encontró la factura referenciada"
            })

    for _, fila in guias.iterrows():
        ref_oc = normalizar(fila["OC Extraída"])
        if ref_oc and ref_oc not in oc_ids:
            errores.append({
                "Línea": fila.name + 2,
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_oc,
                "Problema": "❌ Guía referencia una OC inexistente"
            })

    for _, fila in facturas.iterrows():
        ref_guia = normalizar(fila["Guía Extraída"])
        if ref_guia and ref_guia not in guias_ids:
            errores.append({
                "Línea": fila.name + 2,
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_guia,
                "Problema": "❌ Factura referencia una guía inexistente"
            })

    return pd.DataFrame(errores)

# === Mostrar errores si existen ===
if not df.empty:
    df_errores = validar_referencias(df)

    if not df_errores.empty:
        st.error("🚨 Se encontraron problemas de integridad en las referencias:")
        st.dataframe(df_errores, use_container_width=True)
    else:
        st.success("✅ Todas las referencias entre documentos son coherentes.")

    # === Filtros avanzados ===
    columnas = df.columns
    columnas_lower = list(map(str.lower, columnas))

    fecha_col = None  # Definir por si no existe

    with st.expander("🔎 Filtros avanzados"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_oc = st.text_input("🔍 Filtrar por OC")
        with col2:
            filtro_guia = st.text_input("🔍 Filtrar por Guía")
        with col3:
            filtro_factura = st.text_input("🔍 Filtrar por Ref NC/ND")
        with col4:
            try:
                fecha_col = df.columns[7]
                df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
                fecha_min = df[fecha_col].min()
                fecha_max = df[fecha_col].max()
                rango_fechas = st.date_input("📅 Filtrar por fecha de emisión", [fecha_min, fecha_max])
            except:
                rango_fechas = None

    # === Aplicar filtros ===
    if filtro_oc:
        df = df[df["OC Extraída"].str.contains(filtro_oc, na=False, case=False)]
    if filtro_guia:
        df = df[df["Guía Extraída"].str.contains(filtro_guia, na=False, case=False)]
    if filtro_factura:
        df = df[df["Ref NC/ND Extraída"].str.contains(filtro_factura, na=False, case=False)]

    # Filtrar por fecha usando columna fija: índice 7 = "Fecha Emisión"
    try:
        fecha_col = df.columns[7]
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')

        if rango_fechas:
            df = df[
                (df[fecha_col] >= pd.to_datetime(rango_fechas[0])) &
                (df[fecha_col] <= pd.to_datetime(rango_fechas[1]))
            ]

        # Mostrar la fecha en formato DD-MM-AA (después de filtrar)
        df[fecha_col] = df[fecha_col].dt.strftime('%d-%m-%y')

    except Exception as e:
        st.warning(f"⚠️ Error al procesar el filtro de fecha: {e}")



    st.dataframe(df, use_container_width=True)

    # === Descargar Excel ===
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
