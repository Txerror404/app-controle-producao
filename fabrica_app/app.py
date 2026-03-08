# =================================================================
# ARQUIVO PRINCIPAL - PCP INDUSTRIAL
# =================================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Configuração da página
st.set_page_config(
    page_title="PCP Industrial - SISTEMA COMPLETO",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auto refresh
st_autorefresh(interval=120000, key="pcp_refresh_global")

# Importar módulos
from config import *
from database import conectar
from utils import carregar_produtos_google
from styles import aplicar_estilos
from components import renderizar_cabecalho, renderizar_rodape
from pages.login import mostrar_login
from pages.serigrafia import mostrar_serigrafia
from pages.sopro import mostrar_sopro
from pages.novo_lancamento import mostrar_novo_lancamento
from pages.gerenciar_ops import mostrar_gerenciar_ops
from pages.produtos import mostrar_produtos
from pages.cargas import mostrar_cargas  # 👈 ATUALIZADO: cargas_sopro.py -> cargas.py

# =================================================================
# TESTE DE CONEXÃO INICIAL
# =================================================================

try:
    conn = conectar()
    conn.close()
except Exception as e:
    st.error(f"Falha na conexão com Supabase: {e}")
    st.stop()

# =================================================================
# VERIFICAÇÃO DE LOGIN
# =================================================================

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:
    mostrar_login()

# =================================================================
# CARREGAR PRODUTOS
# =================================================================

if 'df_produtos' not in st.session_state:
    with st.spinner("Sincronizando com Google Sheets..."):
        st.session_state.df_produtos = carregar_produtos_google()

# =================================================================
# APLICAR ESTILOS
# =================================================================

aplicar_estilos()

# =================================================================
# CABEÇALHO
# =================================================================

renderizar_cabecalho(st.session_state.user_email)

# =================================================================
# ABAS PRINCIPAIS
# =================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 CRONOGRAMA SERIGRAFIA",
    "📅 CRONOGRAMA SOPRO",
    "➕ NOVO LANÇAMENTO",
    "⚙️ GERENCIAR OPs",
    "📋 PRODUTOS",
    "📊 CARGAS SOPRO"
])

with tab1:
    mostrar_serigrafia()

with tab2:
    mostrar_sopro()

with tab3:
    mostrar_novo_lancamento()

with tab4:
    mostrar_gerenciar_ops()

with tab5:
    mostrar_produtos()

with tab6:
    mostrar_cargas()  # 👈 ATUALIZADO: função renomeada

# =================================================================
# RODAPÉ
# =================================================================

renderizar_rodape()
