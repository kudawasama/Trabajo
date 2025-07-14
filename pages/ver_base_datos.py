import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="Ver Base de Datos", layout="wide")
st.title("📊 Ver Base de Datos")

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

    if "Tipo Documento" not in df.columns or "Folio" not in df.columns or "Rut Emisor" not in df.columns:
        st.warning("⚠️ Faltan columnas necesarias para validar (Tipo Documento, Folio o Rut Emisor).")
        return pd.DataFrame()

    # Normalizar folios a texto sin decimales
    df["Folio"] = df["Folio"].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace(".", "").isdigit() else "")
    df["Ref NC/ND Extraída"] = df["Ref NC/ND Extraída"].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace(".", "").isdigit() else "")

    facturas = df[df["Tipo Documento"].str.lower().str.contains("factura", na=False)]
    guias = df[df["Tipo Documento"].str.lower().str.contains("guía", na=False)]
    notas = df[df["Tipo Documento"].str.lower().str.contains("nota", na=False)]

    guias_ids = set(guias["Guía Extraída"].apply(normalizar))
    oc_ids = set(df["OC Extraída"].apply(normalizar))

    # Crear columnas de concatenado: Rut + Folio
    facturas["Factura_RutFolio"] = facturas.apply(
        lambda x: f"{normalizar(x['Rut Emisor'])}_{normalizar(x['Folio'])}", axis=1
    )
    notas["NC_RutRef"] = notas.apply(
        lambda x: f"{normalizar(x['Rut Emisor'])}_{normalizar(x['Ref NC/ND Extraída'])}", axis=1
    )

    factura_rutfolios = set(facturas["Factura_RutFolio"])

    # Validación NC/ND
    for _, fila in notas.iterrows():
        ref_concat = fila["NC_RutRef"]
        if ref_concat and ref_concat not in factura_rutfolios:
            errores.append({
                "Folio": fila["Folio"],
                "Tipo": fila["Tipo Documento"],
                "Referencia": fila["Ref NC/ND Extraída"],
                "Problema": "❌ NC/ND no coincide con ninguna Factura del mismo RUT"
            })

    # Validación Guías
    for _, fila in guias.iterrows():
        ref_oc = normalizar(fila["OC Extraída"])
        if ref_oc and ref_oc not in oc_ids:
            errores.append({
                "Folio": fila["Folio"],
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_oc,
                "Problema": "❌ Guía referencia una OC inexistente"
            })

    # Validación Facturas
    for _, fila in facturas.iterrows():
        ref_guia = normalizar(fila["Guía Extraída"])
        if ref_guia and ref_guia not in guias_ids:
            errores.append({
                "Folio": fila["Folio"],
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_guia,
                "Problema": "❌ Factura referencia una guía inexistente"
            })

        oc_factura = normalizar(fila["OC Extraída"])
        oc_guia = ""
        if ref_guia in guias_ids:
            oc_guia = normalizar(guias.loc[guias["Guía Extraída"] == ref_guia, "OC Extraída"].values[0])
        if ref_guia and oc_factura and oc_guia and oc_factura != oc_guia:
            errores.append({
                "Folio": fila["Folio"],
                "Tipo": fila["Tipo Documento"],
                "Referencia": ref_guia,
                "Problema": "❌ OC de la Guía no coincide con OC de la Factura"
            })

    return pd.DataFrame(errores)

# === Carga de datos ===
df = cargar_base()

if not df.empty:
    # Convertir fecha emisión a datetime
    try:
        fecha_col = df.columns[7]
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df["Fecha Formateada"] = df[fecha_col].dt.strftime("%d-%m-%Y")
    except Exception as e:
        st.warning("⚠️ No se pudo procesar la fecha.")
        df["Fecha Formateada"] = ""

    with st.expander("🔎 Filtros avanzados"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filtro_folio = st.text_input("🔍 Filtrar por Folio")
        with col2:
            filtro_proveedor = st.text_input("🔍 Filtrar por Proveedor")
        with col3:
            tipos_disponibles = df["Tipo Documento"].dropna().unique().tolist()
            filtro_tipo = st.selectbox("🔍 Filtrar por Tipo", options=["Todos"] + tipos_disponibles)
        with col4:
            rango_fechas = st.date_input(
                "📅 Filtrar por Fecha Emisión",
                [df[fecha_col].min(), df[fecha_col].max()] if not df[fecha_col].isnull().all() else None
            )

    # Aplicar filtros
    if filtro_folio:
        df = df[df["Folio"].astype(str).str.contains(filtro_folio, case=False, na=False)]
    if filtro_proveedor and "Razón Social Emisor" in df.columns:
        df = df[df["Razón Social Emisor"].astype(str).str.contains(filtro_proveedor, case=False, na=False)]
    if filtro_tipo != "Todos":
        df = df[df["Tipo Documento"] == filtro_tipo]
    if rango_fechas and isinstance(rango_fechas, list) and len(rango_fechas) == 2:
        df = df[(df[fecha_col] >= pd.to_datetime(rango_fechas[0])) & (df[fecha_col] <= pd.to_datetime(rango_fechas[1]))]

    st.dataframe(df.drop(columns=[fecha_col]) if fecha_col in df.columns else df, use_container_width=True)

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("📥 Exportar base como Excel", buffer, "base_datos_filtrada.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")
    st.subheader("🧠 Validación de Integridad de Referencias")
    if st.button("🔄 Actualizar Validación"):
        errores_df = validar_referencias(df)
    else:
        errores_df = validar_referencias(df)

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
    st.warning("⚠️ No hay datos en la base.")

st.markdown("---")
if st.button("🔙 Volver al inicio"):
    st.info("Usa el menú lateral para volver a la página principal.")
