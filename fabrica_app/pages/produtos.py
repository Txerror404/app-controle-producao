# =================================================================
# ABA 5 - PRODUTOS
# =================================================================

import streamlit as st

def mostrar_produtos():
    st.subheader("📋 Produtos")
    st.dataframe(
        st.session_state.df_produtos,
        use_container_width=True,
        hide_index=True
    )
