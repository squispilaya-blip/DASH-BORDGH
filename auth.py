import streamlit as st


def check_credentials(username: str, password: str) -> bool:
    try:
        expected_user = st.secrets["auth"]["username"]
        expected_pass = st.secrets["auth"]["password"]
    except KeyError:
        st.error("Credenciales no configuradas. Contacte al administrador.")
        return False
    return username == expected_user and password == expected_pass


def login_page() -> None:
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🏥 Sistema de Vacunación")
        st.markdown("**NTS N° 196-MINSA/DGIESP-2022**")
        st.divider()
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True):
            if check_credentials(username, password):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")


def require_auth() -> None:
    """Llamar al inicio de app.py. Detiene la ejecución si no hay sesión."""
    if not st.session_state.get("authenticated"):
        login_page()
        st.stop()
