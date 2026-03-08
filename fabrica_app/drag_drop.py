# =================================================================
# FUNCIONALIDADE DE ARRASTAR E SOLTAR PARA O GRÁFICO GANTT
# =================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from database import reprogramar_op, carregar_dados

def criar_interface_drag_drop():
    """
    Cria interface para arrastar e soltar OPs no gráfico
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🖱️ Arrastar e Soltar")
    st.sidebar.markdown("Selecione uma OP e ajuste o horário")
    
    # Buscar dados atuais
    df = carregar_dados()
    
    if df.empty:
        st.sidebar.info("Nenhuma OP para reprogramar")
        return
    
    # Filtrar apenas OPs pendentes (não concluídas)
    df_pendentes = df[df["status"] == "Pendente"].copy()
    
    if df_pendentes.empty:
        st.sidebar.info("Nenhuma OP pendente")
        return
    
    # Criar selectbox para escolher a OP
    opcoes = []
    for _, row in df_pendentes.iterrows():
        opcoes.append(f"{row['maquina']} - {row['pedido']} ({row['inicio'].strftime('%d/%m %H:%M')})")
    
    op_selecionada = st.sidebar.selectbox(
        "Selecione a OP para mover:",
        opcoes,
        key="drag_op_select"
    )
    
    if op_selecionada:
        # Extrair ID da OP selecionada
        idx = opcoes.index(op_selecionada)
        op_id = df_pendentes.iloc[idx]['id']
        op_maquina = df_pendentes.iloc[idx]['maquina']
        op_inicio = df_pendentes.iloc[idx]['inicio']
        
        # Controles de arrasto
        st.sidebar.markdown(f"### 🏭 {op_maquina}")
        st.sidebar.markdown(f"**Horário atual:** {op_inicio.strftime('%d/%m %H:%M')}")
        
        # =================================================================
        # CORREÇÃO: Usar date_input e time_input em vez de slider com timestamp
        # =================================================================
        st.sidebar.markdown("#### 📅 Ajustar horário:")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            nova_data = st.date_input(
                "Data",
                value=op_inicio.date(),
                key=f"drag_data_{op_id}"
            )
        
        with col2:
            nova_hora = st.time_input(
                "Hora",
                value=op_inicio.time(),
                key=f"drag_hora_{op_id}"
            )
        
        # Combinar data e hora
        novo_horario = datetime.combine(nova_data, nova_hora)
        
        # Mostrar diferença
        diferenca = novo_horario - op_inicio
        if diferenca.total_seconds() != 0:
            horas = diferenca.total_seconds() / 3600
            if horas > 0:
                st.sidebar.info(f"⏩ **+{horas:.1f} horas**")
            else:
                st.sidebar.info(f"⏪ **{horas:.1f} horas**")
        
        # Botão para confirmar
        if st.sidebar.button("🔄 Confirmar reprogramação", key=f"drag_confirm_{op_id}"):
            with st.spinner("Reprogramando em cascata..."):
                reprogramar_op(op_id, novo_horario, st.session_state.user_email)
                st.sidebar.success("✅ OP reprogramada com sucesso!")
                st.rerun()

def criar_botoes_ajuste_rapido():
    """
    Cria botões para ajuste rápido de horários
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("## ⚡ Ajuste Rápido")
    st.sidebar.markdown("Move TODAS as OPs pendentes:")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("⏪ -1 hora", use_container_width=True, key="rapido_menos_1h"):
            st.session_state.ajuste_rapido = -1
    with col2:
        if st.button("⏩ +1 hora", use_container_width=True, key="rapido_mais_1h"):
            st.session_state.ajuste_rapido = 1
    
    col3, col4 = st.sidebar.columns(2)
    
    with col3:
        if st.button("⏪ -1 dia", use_container_width=True, key="rapido_menos_1d"):
            st.session_state.ajuste_rapido = -24
    with col4:
        if st.button("⏩ +1 dia", use_container_width=True, key="rapido_mais_1d"):
            st.session_state.ajuste_rapido = 24

def processar_ajuste_rapido():
    """
    Processa os ajustes rápidos
    """
    if 'ajuste_rapido' in st.session_state and st.session_state.ajuste_rapido is not None:
        delta_horas = st.session_state.ajuste_rapido
        df = carregar_dados()
        
        if df.empty:
            st.session_state.ajuste_rapido = None
            return
        
        # Filtrar OPs pendentes
        df_pendentes = df[df["status"] == "Pendente"].copy()
        
        if df_pendentes.empty:
            st.session_state.ajuste_rapido = None
            st.sidebar.warning("Nenhuma OP pendente para ajustar")
            return
        
        # Contador de sucessos
        sucessos = 0
        
        # Para cada OP, ajustar horário
        for _, row in df_pendentes.iterrows():
            try:
                novo_inicio = row['inicio'] + timedelta(hours=delta_horas)
                reprogramar_op(row['id'], novo_inicio, st.session_state.user_email)
                sucessos += 1
            except Exception as e:
                st.sidebar.error(f"Erro na OP {row['id']}: {e}")
        
        st.sidebar.success(f"✅ {sucessos} OPs ajustadas em {delta_horas}h")
        st.session_state.ajuste_rapido = None
        st.rerun()

def mostrar_info_sidebar():
    """
    Mostra informações resumidas no sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Status Rápido")
    
    df_status = carregar_dados()
    if not df_status.empty:
        pendentes = len(df_status[df_status["status"] == "Pendente"])
        atrasadas = len(df_status[df_status["atrasada"] == True]) if 'atrasada' in df_status.columns else 0
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("📦 Pendentes", pendentes)
        with col2:
            st.metric("🚨 Atrasadas", atrasadas)
