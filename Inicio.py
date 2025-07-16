# Inicio.py
import streamlit as st
from PIL import Image # Importar Image para las imágenes de instrucciones

st.set_page_config(
    page_title="Simple by Jose",
    layout="wide",
    page_icon="🏠" # Opcional: un icono para la pestaña del navegador
)

st.title("Bienvenido a la Aplicación de Costos Privado 🛸")
st.markdown("---")

st.subheader("🚀 Funcionalidades:")
st.write("""
Esta aplicación te permite:
- **Extraer referencias de I-Construye desde archivos Excel** y normalizar datos.
- **Visualizar la base de datos** de las referencias extraídas.
- **Validar estado de recepciones** reproceso del archivo.
""")

st.markdown("---")


st.markdown("---")
st.info("Utiliza la barra lateral para navegar a las diferentes secciones de la aplicación.")

# Los botones de navegación directa (st.switch_page) se eliminan/comentan
# porque la navegación principal es a través de la barra lateral.
# if st.button("Ir a Procesar Excel"):
#     st.switch_page("pages/1_Limpiar_DTE_IC.py")

# if st.button("🔍 Ver Base de Datos (Acceso Rápido)"):
#     st.switch_page("pages/2_ver_base_datos.py")