import streamlit as st
from PIL import Image
import os
import datetime

# === Diccionario de usuarios (ajusta según tu necesidad) ===
USUARIOS = {
    "jose.cespedes@casinoexpress.cl": {"password": "Ceco026_", "rol": "admin"},
    "aa": {"password": "aa", "rol": "admin"},
    "usuario@ejemplo.com": {"password": "usuario123", "rol": "usuario"},
}

# Inicializar estado
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "rol" not in st.session_state:
    st.session_state.rol = None
if "logueado" not in st.session_state:
    st.session_state.logueado = False

# === Función Login ===
def login():
    st.markdown("### 🔐 Iniciar sesión")
    correo = st.text_input("Correo electrónico")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Iniciar sesión"):
        if correo in USUARIOS and clave == USUARIOS[correo]["password"]:
            st.session_state.usuario = correo
            st.session_state.rol = USUARIOS[correo]["rol"]
            st.session_state.logueado = True
            st.success(f"Bienvenido, {correo}")
            st.toast("Inicio de sesión exitoso", icon="✅")
            st.query_params["logged"] = "1"
            st.rerun()  # ✅ Refresca inmediatamente para ir a la vista de usuarioo
        else:
            st.error("Correo o contraseña incorrectos")

# === Función Logout ===
def logout():
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.logueado = False
    st.query_params.clear()
    st.rerun()  # ✅ Refresca para mostrar la vista de login inmediatamente


# === Configuración inicial ===
st.set_page_config(page_title="Simple by Jose", layout="wide", page_icon="🏠")

# === Mostrar logout si está logueado ===
if st.session_state.logueado:
    with st.sidebar:
        st.markdown("---")
        st.caption(f"👤 Usuario: `{st.session_state.usuario}`")
        if st.button("Cerrar sesión"):
            logout()
            st.success("Sesión cerrada correctamente")
            st.stop()

# === Lógica de navegación ===
if not st.session_state.logueado:
    login()
    st.stop()

# === Página principal ===
st.title("Bienvenido a la Aplicación de Costos Privado 🛸")
st.markdown("---")

# === Mostrar estado de la base ===
BASE_DATOS_PATH = "facturas.db"

if os.path.exists(BASE_DATOS_PATH):
    modificado = os.path.getmtime(BASE_DATOS_PATH)
    fecha_hora = datetime.datetime.fromtimestamp(modificado).strftime("%d/%m/%Y a las %H:%M:%S")
    st.success(f"📦 Base de datos actualizada el **{fecha_hora}**.")
else:
    st.warning("⚠️ No se encontró la base de datos.")

st.subheader("🚀 Funcionalidades:")
st.markdown("""
- **Extrae datos desde Excel de I-Construye** y los normaliza.
- **Consulta la base de datos** cargada.
- **Valida relaciones entre documentos** y referencias.
""")

st.info("Usa el menú lateral izquierdo para navegar entre las secciones.")

with st.sidebar:
    st.markdown("---")

    # Contenido principal de la sidebar aquí (menús, filtros, etc.)

    # Espaciador invisible para empujar el contenido hacia abajo
    st.markdown("<div style='height:400px;'></div>", unsafe_allow_html=True)

    # Firma fija abajo de la sidebar
    st.markdown(
        """
        <div style="
            position: absolute;
            bottom: 20px;
            left: 20px;
            font-size: 13px;
            color: gray;
        ">
            Hecho por <strong>José Cortés</strong><br>
            📧 jose.cespedes@casinoexpress.cl<br>
            💻 v1.0 - 2025
        </div>
        """,
        unsafe_allow_html=True
    )


