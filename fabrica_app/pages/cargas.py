# =================================================================
# ABA 6 - CARGAS SOPRO
# =================================================================

import streamlit as st
from config import MAQUINAS_SOPRO, CARGA_UNIDADE
from database import carregar_dados

def mostrar_cargas():
    st.subheader("📊 Cargas Sopro")
    
    df_c = carregar_dados()
    
    if not df_c.empty:
        df_p = df_c[
            (df_c["status"] == "Pendente") &
            (df_c["qtd"] > 0)
        ]
        
        df_sopro = df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)]
        
        if not df_sopro.empty:
            total_cargas = df_sopro["qtd"].sum() / CARGA_UNIDADE
            
            st.metric(
                "Total Geral de Cargas Sopro",
                f"{total_cargas:.1f}"
            )
            
            st.subheader("Distribuição por Máquina")
            for maquina in MAQUINAS_SOPRO:
                df_maq = df_sopro[df_sopro["maquina"] == maquina]
                if not df_maq.empty:
                    cargas_maq = df_maq["qtd"].sum() / CARGA_UNIDADE
                    with st.expander(f"{maquina} - {cargas_maq:.1f} cargas"):
                        st.dataframe(
                            df_maq[["pedido", "qtd"]],
                            use_container_width=True,
                            hide_index=True
                        )
        else:
            st.info("Nenhuma carga de sopro pendente")
    else:
        st.info("Nenhuma OP cadastrada")
