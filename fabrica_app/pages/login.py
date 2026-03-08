# =================================================================
# PÁGINA DE LOGIN
# =================================================================

import streamlit as st
from config import ADMIN_EMAIL, OPERACIONAL_EMAIL

def mostrar_login():
    st.markdown("<h1 style='text-align:center;color:#FFFFFF;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL] + OPERACIONAL_EMAIL:
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()
    st.stop()
