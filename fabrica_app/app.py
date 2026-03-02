import streamlit as st
from datetime import datetime, date, time

from db import (
    criar_tabelas,
    inserir_evento,
    listar_eventos,
    atualizar_status,
    soft_delete
)

from utils import verificar_conflito
from gantt import exibir_gantt
from metrics import exibir_metricas
from sheets import botao_exportar_excel


st.set_page_config(
    page_title="Controle de Produção",
    layout="wide"
)

st.title("🏭 Sistema de Controle de Produção")

# ==============================
# CARREGAR DADOS
# ==============================
eventos = carregar_dados()

# ==============================
# MENU LATERAL
# ==============================
menu = st.sidebar.selectbox(
    "Menu",
    ["Cadastrar OP", "Painel Produção", "Métricas"]
)

# ==============================
# CADASTRAR OP
# ==============================
if menu == "Cadastrar OP":

    st.subheader("Cadastrar Ordem de Produção")

    with st.form("form_op"):
        maquina = st.selectbox("Máquina", ["Máquina 1", "Máquina 2", "Máquina 3"])
        descricao = st.text_input("Descrição da OP")

        data_inicio = st.date_input("Data Início", date.today())
        hora_inicio = st.time_input("Hora Início", time(8, 0))

        data_fim = st.date_input("Data Fim", date.today())
        hora_fim = st.time_input("Hora Fim", time(17, 0))

        status = st.selectbox("Status", ["Planejado", "Em Produção", "Finalizado"])

        submit = st.form_submit_button("Salvar OP")

    if submit:
        inicio = datetime.combine(data_inicio, hora_inicio)
        fim = datetime.combine(data_fim, hora_fim)

        conflito = validar_conflito(eventos, maquina, inicio, fim)

        if conflito:
            st.error("⚠ Conflito de horário nesta máquina!")
        else:
            adicionar_evento(
                eventos,
                maquina,
                descricao,
                inicio,
                fim,
                status
            )
            salvar_dados(eventos)
            st.success("OP cadastrada com sucesso!")
            st.rerun()

# ==============================
# PAINEL PRODUÇÃO
# ==============================
elif menu == "Painel Produção":

    st.subheader("Painel Industrial")

    if eventos:
        exibir_gantt(eventos)

        st.divider()
        st.subheader("Gerenciar OPs")

        for e in eventos:
            col1, col2, col3, col4 = st.columns([2,2,2,1])

            col1.write(f"**{e['descricao']}**")
            col2.write(e["maquina"])
            col3.write(e["status"])

            if col4.button("Excluir", key=e["id"]):
                excluir_evento(eventos, e["id"])
                salvar_dados(eventos)
                st.rerun()
    else:
        st.info("Nenhuma OP cadastrada.")

# ==============================
# MÉTRICAS
# ==============================
elif menu == "Métricas":
    st.subheader("Indicadores de Produção")
    exibir_metricas(eventos)
