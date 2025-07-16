# pages/2_ver_base_datos.py
import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(
    page_title="Ver Base de Datos",
    layout="wide",
    page_icon="📊" # Añadimos un icono para la pestaña del navegador
)

st.title("📊 Visualización de la Base de Datos")
st.markdown("---")

# === Cargar base de datos ===
def cargar_base(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    try:
        conn = sqlite3.connect(base_datos)
        df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al cargar la base: {e}")
        return pd.DataFrame()

# === Validación de integridad con concatenado Rut+Folio ===
def validar_referencias(df):
    errores = []

    def normalizar(valor):
        if pd.isna(valor):
            return ""
        return str(valor).strip().upper()

    # Comprobaciones iniciales de columnas
    required_cols = ["Tipo Documento", "Folio", "Rut Emisor"]
    if not all(col in df.columns for col in required_cols):
        st.warning(f"⚠️ Faltan columnas necesarias para validar: {', '.join([col for col in required_cols if col not in df.columns])}.")
        return pd.DataFrame()

    # Normalizar folios a texto sin decimales
    if "Folio" in df.columns:
        df["Folio"] = df["Folio"].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace(".", "").isdigit() else "")
    if "Ref NC/ND Extraída" in df.columns:
        df["Ref NC/ND Extraída"] = df["Ref NC/ND Extraída"].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace(".", "").isdigit() else "")


    # Filtra los DataFrames antes de intentar acceder a las columnas para evitar errores si no hay filas
    facturas = df[df["Tipo Documento"].str.lower().str.contains("factura", na=False)].copy() # .copy() para evitar SettingWithCopyWarning
    guias = df[df["Tipo Documento"].str.lower().str.contains("guía", na=False)].copy()
    notas = df[df["Tipo Documento"].str.lower().str.contains("nota", na=False)].copy()

    # Asegúrate de que las columnas existan en los sub-DataFrames antes de usarlas en set()
    guias_ids = set(guias["Guía Extraída"].apply(normalizar)) if "Guía Extraída" in guias.columns else set()
    oc_ids = set(df["OC Extraída"].apply(normalizar)) if "OC Extraída" in df.columns else set()


    # Crear columnas de concatenado: Rut + Folio (solo si las columnas existen en el DF filtrado)
    factura_rutfolios = set()
    if not facturas.empty and "Rut Emisor" in facturas.columns and "Folio" in facturas.columns:
        facturas["Factura_RutFolio"] = facturas.apply(
            lambda x: f"{normalizar(x['Rut Emisor'])}_{normalizar(x['Folio'])}", axis=1
        )
        factura_rutfolios = set(facturas["Factura_RutFolio"])

    if not notas.empty and "Rut Emisor" in notas.columns and "Ref NC/ND Extraída" in notas.columns:
        notas["NC_RutRef"] = notas.apply(
            lambda x: f"{normalizar(x['Rut Emisor'])}_{normalizar(x['Ref NC/ND Extraída'])}", axis=1
        )
    
    # Validación NC/ND
    for _, fila in notas.iterrows():
        # Verifica si 'NC_RutRef' existe en la fila antes de intentar acceder
        if 'NC_RutRef' in fila and fila["NC_RutRef"]:
            ref_concat = fila["NC_RutRef"]
            if ref_concat and ref_concat not in factura_rutfolios: # Añadido 'ref_concat' para evitar añadir si está vacío
                errores.append({
                    "Folio": fila.get("Folio", ""), # Usar .get para evitar KeyError
                    "Tipo": fila.get("Tipo Documento", ""),
                    "Referencia": fila.get("Ref NC/ND Extraída", ""),
                    "Problema": "❌ NC/ND no coincide con ninguna Factura del mismo RUT"
                })

    # Validación Guías
    for _, fila in guias.iterrows():
        # Verifica si 'OC Extraída' existe en la fila antes de intentar acceder
        if 'OC Extraída' in fila:
            ref_oc = normalizar(fila["OC Extraída"])
            if ref_oc and ref_oc not in oc_ids:
                errores.append({
                    "Folio": fila.get("Folio", ""),
                    "Tipo": fila.get("Tipo Documento", ""),
                    "Referencia": ref_oc,
                    "Problema": "❌ Guía referencia una OC inexistente"
                })

    # Validación Facturas
    for _, fila in facturas.iterrows():
        # Verifica si 'Guía Extraída' y 'OC Extraída' existen en la fila
        ref_guia = normalizar(fila.get("Guía Extraída", ""))
        oc_factura = normalizar(fila.get("OC Extraída", ""))

        if ref_guia and ref_guia not in guias_ids:
            errores.append({
                "Folio": fila.get("Folio", ""),
                "Tipo": fila.get("Tipo Documento", ""),
                "Referencia": ref_guia,
                "Problema": "❌ Factura referencia una guía inexistente"
            })

        oc_guia = ""
        # Verifica que 'Guía Extraída' exista en el dataframe de guias antes de filtrar
        if ref_guia and ref_guia in guias_ids and "Guía Extraída" in guias.columns and "OC Extraída" in guias.columns:
            matching_guia_rows = guias[guias["Guía Extraída"] == ref_guia]
            if not matching_guia_rows.empty:
                oc_guia = normalizar(matching_guia_rows["OC Extraída"].iloc[0]) # Usar .iloc[0] en lugar de .values[0]

        if ref_guia and oc_factura and oc_guia and oc_factura != oc_guia:
            errores.append({
                "Folio": fila.get("Folio", ""),
                "Tipo": fila.get("Tipo Documento", ""),
                "Referencia": ref_guia,
                "Problema": "❌ OC de la Guía no coincide con OC de la Factura"
            })

    return pd.DataFrame(errores)

# === Carga de datos ===
df = cargar_base()

if not df.empty:
    # Convertir fecha emisión a datetime
    fecha_col = None
    # Intenta encontrar la columna de fecha por un nombre predecible o por índice 7
    # Asegúrate de que la columna 7 exista antes de intentar acceder a ella
    if len(df.columns) > 7:
        fecha_col = df.columns[7]
    
    if fecha_col and fecha_col in df.columns:
        try:
            df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
            df["Fecha Formateada"] = df[fecha_col].dt.strftime("%d-%m-%Y")
        except Exception as e:
            st.warning(f"⚠️ No se pudo procesar la columna de fecha '{fecha_col}': {e}")
            df["Fecha Formateada"] = ""
    else:
        st.warning("⚠️ No se encontró la columna de fecha esperada (índice 7).")
        df["Fecha Formateada"] = ""


    with st.expander("🔎 Filtros avanzados"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_folio = st.text_input("🔍 Filtrar por Folio")
        with col2:
            # Asegurarse de que la columna exista antes de intentar filtrar por ella
            filtro_proveedor = st.text_input("🔍 Filtrar por Proveedor") if "Razón Social Emisor" in df.columns else ""
        with col3:
            tipos_disponibles = df["Tipo Documento"].dropna().unique().tolist() if "Tipo Documento" in df.columns else []
            filtro_tipo = st.selectbox("🔍 Filtrar por Tipo", options=["Todos"] + tipos_disponibles)
        with col4:
            # Asegurarse de que la columna de fecha procesada exista antes de usarla para el filtro
            if "Fecha Formateada" in df.columns and not df[fecha_col].isnull().all():
                rango_fechas = st.date_input(
                    "📅 Filtrar por Fecha Emisión",
                    [df[fecha_col].min(), df[fecha_col].max()]
                )
            else:
                rango_fechas = None
                st.info("Fechas no disponibles para filtrar.")


    # Aplicar filtros
    df_filtrado = df.copy() # Usar una copia para aplicar los filtros
    if filtro_folio:
        df_filtrado = df_filtrado[df_filtrado["Folio"].astype(str).str.contains(filtro_folio, case=False, na=False)]
    if filtro_proveedor and "Razón Social Emisor" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Razón Social Emisor"].astype(str).str.contains(filtro_proveedor, case=False, na=False)]
    if filtro_tipo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Tipo Documento"] == filtro_tipo]
    if rango_fechas and isinstance(rango_fechas, list) and len(rango_fechas) == 2 and fecha_col and fecha_col in df_filtrado.columns:
        df_filtrado = df_filtrado[(df_filtrado[fecha_col] >= pd.to_datetime(rango_fechas[0])) & (df_filtrado[fecha_col] <= pd.to_datetime(rango_fechas[1]))]


    st.dataframe(df_filtrado.drop(columns=[fecha_col]) if fecha_col in df_filtrado.columns else df_filtrado, use_container_width=True)

    buffer = BytesIO()
    df_filtrado.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Exportar base como Excel", buffer, "base_datos_filtrada.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    st.subheader("🧠 Validación de Integridad de Referencias")
    # Para evitar que la validación se ejecute dos veces en cada recarga
    if st.button("🔄 Ejecutar Validación"): # Cambiado de "Actualizar Validación" para mayor claridad
        errores_df = validar_referencias(df)
        st.session_state['errores_df'] = errores_df # Guardar en session_state para persistir

    # Mostrar resultados de validación, si existen
    if 'errores_df' in st.session_state:
        errores_df = st.session_state['errores_df']
        if errores_df.empty:
            st.success("✅ Todas las referencias son válidas.")
        else:
            st.warning("⚠️ Se encontraron referencias inválidas:")
            st.dataframe(errores_df, use_container_width=True)

            buffer_errores = BytesIO()
            errores_df.to_excel(buffer_errores, index=False)
            buffer_errores.seek(0)
            st.download_button("📥 Descargar errores como Excel", buffer_errores, "errores_integridad.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    else:
        st.info("Presiona 'Ejecutar Validación' para revisar la integridad de las referencias.")


else:
    st.warning("⚠️ No hay datos en la base. Sube y procesa un archivo Excel en la página de 'Extraer Referencias' para ver datos aquí.")

st.markdown("---")
# Eliminado: st.button("🔙 Volver al inicio")
st.info("Utiliza el menú lateral para navegar entre las páginas.")
