import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

st.set_page_config(page_title="Consolidar NC/ND", layout="wide")
st.title("🔄 Consolidación de Facturas y Notas de Crédito / Débito")

# === Cargar datos desde SQLite ===
def cargar_base(nombre_tabla="facturas_extraidas", base_datos="facturas.db"):
    conn = sqlite3.connect(base_datos)
    df = pd.read_sql(f"SELECT * FROM {nombre_tabla}", conn)
    conn.close()
    return df

# === Consolidar Facturas con sus NC/ND ===
def consolidar_nc(df):
    df_fact = df[df["Tipo"].str.lower().str.contains("factura", na=False)].copy()
    df_ncnd = df[df["Tipo"].str.lower().str.contains("nota credito|nota débito", na=False)].copy()

    # Convertir a numérico para comparar correctamente
    df_fact["Folio"] = pd.to_numeric(df_fact["Folio"], errors="coerce")
    df_ncnd["Folio"] = pd.to_numeric(df_ncnd["Folio"], errors="coerce")

    df_ncnd["Ref NC/ND Extraída"] = pd.to_numeric(df_ncnd["Ref NC/ND Extraída"], errors="coerce")
    df_fact["Guía Extraída"] = pd.to_numeric(df_fact["Guía Extraída"], errors="coerce")
    df_fact["OC Extraída"] = pd.to_numeric(df_fact["OC Extraída"], errors="coerce")

    resultados = []

    for _, factura in df_fact.iterrows():
        folio_factura = factura["Folio"]
        monto_factura = factura["Monto Total"]

        # Buscar documentos relacionados por las referencias
        docs_relacionados = df_ncnd[
            (df_ncnd["Ref NC/ND Extraída"] == folio_factura) |
            (df_ncnd["Guía Extraída"] == folio_factura) |
            (df_ncnd["OC Extraída"] == folio_factura)
        ]

        if not docs_relacionados.empty:
            for _, ncnd in docs_relacionados.iterrows():
                monto_ncnd = ncnd["Monto Total"]
                diferencia = monto_factura + monto_ncnd

                observacion = "NC Parcial"
                if abs(diferencia) < 10:
                    observacion = "Anula Factura"

                resultados.append({
                    "Folio (factura)": folio_factura,
                    "Tipo Documento": factura["Tipo"],
                    "Referencia factura": factura.get("OC Extraída", ""),
                    "Monto factura": monto_factura,
                    "Nota Crédito/Débito": ncnd["Folio"],
                    "Referencia NC/ND": ncnd["Ref NC/ND Extraída"],
                    "Monto NC/ND": monto_ncnd,
                    "Diferencia": diferencia,
                    "Observación": observacion,
                    "Fecha Emisión": factura.get("Fecha Emisión", "")
                })
        else:
            resultados.append({
                "Folio (factura)": folio_factura,
                "Tipo Documento": factura["Tipo"],
                "Referencia factura": factura.get("OC Extraída", ""),
                "Monto factura": monto_factura,
                "Nota Crédito/Débito": None,
                "Referencia NC/ND": None,
                "Monto NC/ND": None,
                "Diferencia": None,
                "Observación": "Sin NC/ND relacionada",
                "Fecha Emisión": factura.get("Fecha Emisión", "")
            })

    return pd.DataFrame(resultados)

# === Descargar Excel ===
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name="Consolidado")
    output.seek(0)
    return output

# === Carga y procesamiento ===
df_base = cargar_base()
df_consolidado = consolidar_nc(df_base)

# === Filtros ===
st.subheader("🔍 Filtros")
col1, col2, col3 = st.columns(3)

with col1:
    folio_filtro = st.text_input("Buscar por Folio de Factura")
with col2:
    ref_filtro = st.text_input("Buscar por Referencia OC / Guía / Ref NC")
with col3:
    fecha_filtro = st.text_input("Buscar por Fecha de Emisión")

df_filtrado = df_consolidado.copy()

if folio_filtro:
    df_filtrado = df_filtrado[df_filtrado["Folio (factura)"].astype(str).str.contains(folio_filtro)]

if ref_filtro:
    df_filtrado = df_filtrado[
        df_filtrado["Referencia factura"].astype(str).str.contains(ref_filtro) |
        df_filtrado["Referencia NC/ND"].astype(str).str.contains(ref_filtro)
    ]

if fecha_filtro:
    df_filtrado = df_filtrado[df_filtrado["Fecha Emisión"].astype(str).str.contains(fecha_filtro)]

# === Mostrar tabla ===
st.subheader("📄 Tabla Consolidada")
st.dataframe(df_filtrado, use_container_width=True)

# === Exportar ===
st.download_button(
    label="📥 Descargar Excel",
    data=exportar_excel(df_filtrado),
    file_name="consolidado_factura_ncnd.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
