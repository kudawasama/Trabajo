# pages/2_ver_base_datos.py
import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO

# Verifica si hay sesión activa
if "usuario" not in st.session_state:
    st.warning("🔐 Debes iniciar sesión para acceder a esta página.")
    st.stop()

st.set_page_config(page_title="Validar NC con Facturas", layout="wide")
st.title("🔍 Validación de Notas de Crédito/Débito contra Facturas")

# Función para conectarse a la base de datos
def conectar_db(db_path="facturas.db"):
    return sqlite3.connect(db_path)

# Función que ejecuta la consulta para validar NC/ND con Facturas
def validar_nc_con_facturas():
    conn = conectar_db()
    query = """
    SELECT 
        f."Folio" AS folio_factura,
        f."Rut Emisor" AS rut_factura,
        f."Fecha Emisión" AS fecha_factura,
        f."Monto Total" AS monto_factura,
        nc.folio AS folio_nc,
        nc.rut_emisor AS rut_nc,
        nc.fecha_emision AS fecha_nc,
        nc.monto_total AS monto_nc,
        nc.ref_nc_nd_extraida AS ref_nc_nd
    FROM nc_nd nc
    JOIN facturas f 
        ON CAST(nc.ref_nc_nd_extraida AS INTEGER) = f."Folio"
        AND nc.rut_emisor = f."Rut Emisor"
    ORDER BY f."Folio"
    """
    try:
        df = pd.read_sql(query, conn)
        # Cálculo adicional
        df["diferencia_monto"] = df["monto_factura"] - df["monto_nc"]
        df["clasificación"] = df["diferencia_monto"].apply(
            lambda x: "Anula Factura" if abs(x) < 10 else "NC Parcial"
        )
    except Exception as e:
        st.error(f"❌ Error durante la validación: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# Función para exportar el DataFrame a Excel
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Validación NC")
    return output.getvalue()

# Ejecutar la validación y mostrar resultados
df_validado = validar_nc_con_facturas()

if not df_validado.empty:
    st.success(f"✅ Se encontraron {len(df_validado)} registros relacionados entre NC/ND y Facturas.")
    st.dataframe(df_validado, use_container_width=True)

    st.download_button(
        label="📥 Descargar Excel",
        data=exportar_excel(df_validado),
        file_name="validacion_nc_facturas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("⚠️ No se encontraron registros relacionados o hubo un error.")
