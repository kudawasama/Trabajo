import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Consolidar NC/ND", layout="wide")
st.title("🔄 Consolida NC/ND con Facturas")

# === Cargar base de datos ===
def cargar_base(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    conn = sqlite3.connect(base_datos)
    df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    conn.close()
    return df

# === Consolidar NC/ND con Facturas ===
def consolidar_nc_nd(df):
    df_facturas = df[df["Tipo"].str.contains("Factura", case=False, na=False)].copy()
    df_ncnd = df[df["Tipo"].str.contains("Nota de Crédito|Nota de Debito", case=False, na=False)].copy()

    # Normaliza referencias y folios como números
    df_facturas["Folio"] = pd.to_numeric(df_facturas["Folio"], errors="coerce")
    df_ncnd["Ref NC/ND Extraída"] = pd.to_numeric(df_ncnd["Ref NC/ND Extraída"], errors="coerce")

    df_merged = pd.merge(
        df_facturas,
        df_ncnd,
        left_on="Folio",
        right_on="Ref NC/ND Extraída",
        how="inner",
        suffixes=("_Factura", "_NCND")
    )

    # Calcular diferencia y tipo de ajuste
    df_merged["Diferencia Monto"] = df_merged["Monto Total_Factura"] - df_merged["Monto Total_NCND"]
    df_merged["Clasificación"] = df_merged["Diferencia Monto"].apply(lambda x: "Anula Factura" if abs(x) < 100 else "NC Parcial")

    return df_merged

# === Cargar y consolidar ===
df = cargar_base()

if df.empty:
    st.warning("No hay datos en la base de datos.")
else:
    df_consolidado = consolidar_nc_nd(df)
    st.subheader("📋 Resultado de Consolidación")

    st.dataframe(df_consolidado, use_container_width=True)

    # Filtro por folio o clasificación
    with st.expander("🔍 Filtros"):
        folio = st.text_input("Buscar por Folio (Factura o NC/ND)")
        clasificacion = st.selectbox("Filtrar por clasificación", options=["Todos", "Anula Factura", "NC Parcial"])
        
        df_filtrado = df_consolidado.copy()
        if folio:
            df_filtrado = df_filtrado[
                df_filtrado["Folio"].astype(str).str.contains(folio, na=False) |
                df_filtrado["Folio_NCND"].astype(str).str.contains(folio, na=False)
            ]
        if clasificacion != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Clasificación"] == clasificacion]

        st.dataframe(df_filtrado, use_container_width=True)

    # Exportar a Excel
    def exportar_excel(df):
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Consolidado")
        return output.getvalue()

    st.download_button(
        label="📥 Exportar a Excel",
        data=exportar_excel(df_consolidado),
        file_name="consolidado_facturas_nc_nd.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
