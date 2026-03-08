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

# Auto refresh a cada 2 minutos
st_autorefresh(interval=120000, key="pcp_refresh_global")

# =================================================================
# IMPORTAÇÕES DOS MÓDULOS
# =================================================================

from config import *
from database import conectar, carregar_dados
from utils import carregar_produtos_google
from styles import aplicar_estilos
from components import renderizar_cabecalho, renderizar_rodape, renderizar_setor
from pages.login import mostrar_login
from pages.serigrafia import mostrar_serigrafia
from pages.sopro import mostrar_sopro
from pages.novo_lancamento import mostrar_novo_lancamento
from pages.gerenciar_ops import mostrar_gerenciar_ops
from pages.produtos import mostrar_produtos
from pages.cargas import mostrar_cargas

# =================================================================
# IMPORTAÇÕES DO DRAG AND DROP
# =================================================================

from drag_drop import (
    criar_interface_drag_drop,
    criar_botoes_ajuste_rapido,
    processar_ajuste_rapido,
    mostrar_info_sidebar
)

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
# SIDEBAR - CONTROLES DE OPs
# =================================================================

with st.sidebar:
    st.title("🎮 Controle de OPs")
    
    # Mostrar usuário logado
    st.markdown(f"**👤 Usuário:** {st.session_state.user_email}")
    st.markdown("---")
    
    # Status rápido das OPs
    mostrar_info_sidebar()
    
    st.markdown("---")
    
    # Botões de ajuste rápido
    st.markdown("### ⚡ Ajuste Rápido")
    st.markdown("Move TODAS as OPs pendentes:")
    criar_botoes_ajuste_rapido()
    processar_ajuste_rapido()
    
    st.markdown("---")
    
    # Interface de arrastar e soltar
    criar_interface_drag_drop()
    
    st.markdown("---")
    st.caption("💡 Dica: Selecione uma OP acima e ajuste data/hora")
    st.caption("🔄 A página atualiza a cada 2 minutos")

# =================================================================
# CABEÇALHO PRINCIPAL
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

# =================================================================
# ABA 1 - SERIGRAFIA
# =================================================================

with tab1:
    mostrar_serigrafia()

# =================================================================
# ABA 2 - SOPRO
# =================================================================

with tab2:
    mostrar_sopro()

# =================================================================
# ABA 3 - NOVO LANÇAMENTO
# =================================================================

with tab3:
    mostrar_novo_lancamento()

# =================================================================
# ABA 4 - GERENCIAR OPs
# =================================================================

with tab4:
    mostrar_gerenciar_ops()

# =================================================================
# ABA 5 - PRODUTOS
# =================================================================

with tab5:
    mostrar_produtos()

# =================================================================
# ABA 6 - CARGAS SOPRO
# =================================================================

with tab6:
    mostrar_cargas()

# =================================================================
# RODAPÉ
# =================================================================

renderizar_rodape()

# =================================================================
# DEBUG INFO (SÓ APARECE EM DESENVOLVIMENTO)
# =================================================================

if st.session_state.get('debug_mode', False):
    with st.expander("🔧 Informações de Debug"):
        st.write("### Sessão")
        st.write(st.session_state)
        
        st.write("### Produtos Carregados")
        if 'df_produtos' in st.session_state:
            st.write(f"Quantidade: {len(st.session_state.df_produtos)}")
            st.dataframe(st.session_state.df_produtos.head())
        else:
            st.write("Nenhum produto carregado")
