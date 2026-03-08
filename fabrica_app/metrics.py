import streamlit as st

def mostrar_metricas(atrasadas, execucao, total, maquinas):

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("🚨 OPs Atrasadas", atrasadas)

    c2.metric("⚙️ OPs em Execução", execucao)

    c3.metric("📦 Total OPs", total)

    taxa = (execucao/maquinas)*100 if maquinas > 0 else 0

    c4.metric("📈 Ocupação", f"{taxa:.1f}%")
