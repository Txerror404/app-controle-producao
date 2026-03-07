# =================================================================
# ABA 3 - NOVO LANÇAMENTO
# =================================================================

import streamlit as st
from datetime import datetime
from config import TODAS_MAQUINAS, CARGA_UNIDADE
from database import proximo_horario, calcular_fim_op, inserir_producao

def mostrar_novo_lancamento():
    with st.container(border=True):
        st.subheader("➕ Novo Lançamento")
        
        df_prod = st.session_state.df_produtos.copy()
        df_prod['id_item'] = df_prod['id_item'].astype(str).str.strip()
        
        c1, c2 = st.columns(2)
        
        with c1:
            maq_sel = st.selectbox(
                "🏭 Máquina destino",
                TODAS_MAQUINAS,
                key="nova_maquina"
            )
            
            opcoes_itens = df_prod['id_item'].tolist()
            item_sel = st.selectbox(
                "📌 Selecione o ID_ITEM",
                opcoes_itens,
                key="novo_item"
            )
            
            descricao_texto = "N/A"
            cliente_texto = "N/A"
            carga_sugerida = CARGA_UNIDADE
            
            if item_sel:
                produto_info = df_prod[df_prod['id_item'] == item_sel]
                if not produto_info.empty:
                    info = produto_info.iloc[0]
                    descricao_texto = info['descricao']
                    cliente_texto = info['cliente']
                    carga_sugerida = int(info['qtd_carga'])
            
            st.text_input(
                "📝 Descrição",
                value=descricao_texto,
                disabled=True,
                key="nova_descricao"
            )
        
        with c2:
            op_num = st.text_input("🔢 Número da OP", key="nova_op")
            
            st.text_input(
                "👥 Cliente",
                value=cliente_texto,
                disabled=True,
                key="nova_cliente"
            )
            
            qtd_lanc = st.number_input(
                "📊 Quantidade Total",
                value=int(carga_sugerida),
                key="nova_qtd"
            )
        
        sugestao_h = proximo_horario(maq_sel)
        
        d1, d2 = st.columns(2)
        
        data_ini = d1.date_input(
            "📅 Data",
            sugestao_h.date(),
            key="nova_data"
        )
        
        hora_ini = d2.time_input(
            "⏰ Hora",
            sugestao_h.time(),
            key="nova_hora"
        )
        
        if st.button("🚀 CONFIRMAR E AGENDAR (com setup automático de 30min)", key="btn_confirmar"):
            if op_num and item_sel:
                inicio_dt = datetime.combine(data_ini, hora_ini)
                fim_dt = calcular_fim_op(inicio_dt, qtd_lanc)
                
                resultado = inserir_producao(
                    maq_sel,
                    f"{cliente_texto} | OP:{op_num}",
                    item_sel,
                    inicio_dt,
                    fim_dt,
                    qtd_lanc,
                    st.session_state.user_email
                )
                
                if resultado:
                    st.success("✅ OP lançada com sucesso! Setup de 30 minutos agendado automaticamente.")
                    st.balloons()
                    st.rerun()
            else:
                st.error("Preencha OP e Item")
