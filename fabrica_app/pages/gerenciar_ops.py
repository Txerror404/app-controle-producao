# =================================================================
# ABA 4 - GERENCIAR OPs
# =================================================================

import streamlit as st
from datetime import datetime
from database import carregar_dados, finalizar_op, deletar_op, reprogramar_op
from utils import get_descricao_produto

def mostrar_gerenciar_ops():
    st.subheader("⚙️ Gerenciamento de OPs")
    st.markdown("Aqui você pode finalizar, deletar ou reprogramar OPs. Ao reprogramar, todas as OPs seguintes são ajustadas automaticamente.")
    
    df_ger = carregar_dados()
    
    if not df_ger.empty:
        df_programadas = df_ger[
            df_ger["status"].isin(["Pendente", "Setup"])
        ].sort_values(["maquina", "inicio"])
        
        if df_programadas.empty:
            st.info("Nenhuma OP pendente encontrada")
        else:
            for maquina in sorted(df_programadas["maquina"].unique()):
                with st.expander(f"🏭 {maquina}", expanded=False):
                    df_maq = df_programadas[df_programadas["maquina"] == maquina]
                    
                    for _, prod in df_maq.iterrows():
                        if prod["status"] == "Setup" and prod["vinculo_id"]:
                            continue
                            
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
                        
                        with col1:
                            st.write(f"**{prod['pedido']}**")
                            if prod["status"] == "Setup":
                                st.caption("🔧 SETUP")
                            else:
                                desc = get_descricao_produto(prod['item'])
                                st.caption(f"Item: {prod['item']} - {desc[:30]}...")
                        
                        with col2:
                            st.write(f"Início: {prod['inicio'].strftime('%d/%m %H:%M')}")
                            st.write(f"Fim: {prod['fim'].strftime('%d/%m %H:%M')}")
                        
                        with col3:
                            if prod["status"] != "Setup":
                                st.metric("QTD", f"{int(prod['qtd']):,}")
                            else:
                                st.write("Setup")
                        
                        with col4:
                            if prod["status"] == "Pendente":
                                if prod["em_execucao"]:
                                    st.markdown("🟠 **Executando**")
                                elif prod["atrasada"]:
                                    st.markdown("🔴 **Atrasada**")
                                else:
                                    st.markdown("🔵 **Pendente**")
                            else:
                                st.markdown("⚪ **Setup**")
                        
                        with col5:
                            if prod["status"] == "Pendente":
                                if st.button("✅ Finalizar", key=f"fin_{prod['id']}"):
                                    finalizar_op(prod["id"])
                                    st.success("OP finalizada!")
                                    st.rerun()
                                
                                with st.popover("📅 Reprogramar"):
                                    st.markdown(f"**Reprogramar {prod['pedido']}**")
                                    
                                    nova_data = st.date_input(
                                        "Nova data",
                                        value=prod['inicio'].date(),
                                        key=f"data_{prod['id']}"
                                    )
                                    
                                    nova_hora = st.time_input(
                                        "Nova hora",
                                        value=prod['inicio'].time(),
                                        key=f"hora_{prod['id']}"
                                    )
                                    
                                    if st.button("Confirmar reprogramação", key=f"conf_{prod['id']}"):
                                        novo_inicio = datetime.combine(nova_data, nova_hora)
                                        reprogramar_op(prod["id"], novo_inicio, st.session_state.user_email)
                                        st.success("OP reprogramada! OPs seguintes ajustadas.")
                                        st.rerun()
                            
                            if st.button("🗑️ Deletar", key=f"del_{prod['id']}"):
                                deletar_op(prod["id"])
                                st.success("OP e setup deletados!")
                                st.rerun()
                        
                        st.divider()
    else:
        st.info("Nenhuma OP cadastrada")
