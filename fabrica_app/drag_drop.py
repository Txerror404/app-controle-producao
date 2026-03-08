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
    st.sidebar.markdown("Clique em uma OP no gráfico e arraste para reprogramar")
    
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
        
        # Slider para simular arrasto
        st.sidebar.markdown("#### Arraste para ajustar:")
        
        # Calcular limites (não pode mover para antes de agora)
        agora = datetime.now(pytz.timezone("America/Sao_Paulo")).replace(tzinfo=None)
        limite_min = agora
        limite_max = op_inicio + timedelta(days=2)
        
        # Converter para timestamp para o slider
        min_timestamp = float(limite_min.timestamp())
        max_timestamp = float(limite_max.timestamp())
        valor_atual = float(op_inicio.timestamp())
        
        # Slider de tempo
        novo_timestamp = st.sidebar.slider(
            "Horário",
            min_value=min_timestamp,
            max_value=max_timestamp,
            value=valor_atual,
            step=3600,  # 1 hora em segundos
            format="🕐",
            key="drag_slider"
        )
        
        # Converter timestamp de volta para datetime
        novo_horario = datetime.fromtimestamp(novo_timestamp)
        
        # Mostrar novo horário
        st.sidebar.info(f"**Novo horário:** {novo_horario.strftime('%d/%m %H:%M')}")
        
        # Botão para confirmar
        if st.sidebar.button("🔄 Confirmar reprogramação", key="drag_confirm"):
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
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("⏪ -1h", use_container_width=True):
            st.session_state.ajuste_rapido = -1
    with col2:
        if st.button("⏩ +1h", use_container_width=True):
            st.session_state.ajuste_rapido = 1
    
    col3, col4 = st.sidebar.columns(2)
    
    with col3:
        if st.button("⏪ -1d", use_container_width=True):
            st.session_state.ajuste_rapido = -24
    with col4:
        if st.button("⏩ +1d", use_container_width=True):
            st.session_state.ajuste_rapido = 24

def processar_ajuste_rapido():
    """
    Processa os ajustes rápidos
    """
    if 'ajuste_rapido' in st.session_state:
        delta_horas = st.session_state.ajuste_rapido
        df = carregar_dados()
        
        if df.empty:
            return
        
        # Filtrar OPs pendentes
        df_pendentes = df[df["status"] == "Pendente"].copy()
        
        if df_pendentes.empty:
            return
        
        # Para cada OP, ajustar horário
        for _, row in df_pendentes.iterrows():
            novo_inicio = row['inicio'] + timedelta(hours=delta_horas)
            reprogramar_op(row['id'], novo_inicio, st.session_state.user_email)
        
        st.sideansuccess(f"✅ {len(df_pendentes)} OPs ajustadas em {delta_horas}h")
        st.session_state.ajuste_rapido = None
        st.rerun()
