import streamlit as st
from datetime import datetime, date, time

from db import (
    criar_tabelas,
    inserir_evento,
    listar_eventos,
    soft_delete
)
from sheets import carregar_produtos_google
from utils import verificar_conflito
from gantt import exibir_gantt
from metrics import exibir_metricas
from sheets import botao_exportar_excel


st.set_page_config(page_title="Controle de Produção", layout="wide")

st.title("🏭 Sistema de Controle de Produção")

# Criar tabela automaticamente
criar_tabelas()

# Carregar eventos do banco
eventos = listar_eventos()

menu = st.sidebar.selectbox(
    "Menu",
    ["Cadastrar OP", "Painel Produção", "Métricas"]
)

# ==============================
# CADASTRAR OP
# ==============================
if menu == "Cadastrar OP":

    st.subheader("Nova Ordem de Produção")

    with st.form("form_op"):

        op = st.text_input("Número da OP")
        cliente = st.text_input("Cliente")
        produto = st.text_input("Produto")
        maquina = st.selectbox("Máquina", ["Máquina 1", "Máquina 2", "Máquina 3"])
        setor = st.text_input("Setor")

        data_inicio = st.date_input("Data Início", date.today())
        hora_inicio = st.time_input("Hora Início", time(8, 0))

        data_fim = st.date_input("Data Fim", date.today())
        hora_fim = st.time_input("Hora Fim", time(17, 0))

        status = st.selectbox(
            "Status",
            ["Pendente", "Em Produção", "Finalizado"]
        )

        observacao = st.text_area("Observação")

        submit = st.form_submit_button("Salvar")

    if submit:

        inicio = datetime.combine(data_inicio, hora_inicio)
        fim = datetime.combine(data_fim, hora_fim)

        conflito = verificar_conflito(
            maquina,
            inicio,
            fim,
            eventos
        )

        if conflito:
            st.error("⚠ Conflito de horário nesta máquina!")
        else:
            inserir_evento(
                op,
                cliente,
                produto,
                maquina,
                setor,
                inicio,
                fim,
                status,
                observacao
            )
            st.success("OP cadastrada com sucesso!")
            st.rerun()

# ==============================
# PAINEL PRODUÇÃO
# ==============================
elif menu == "Painel Produção":

    st.subheader("Planejamento Industrial")

    exibir_gantt(eventos)

    st.divider()
    botao_exportar_excel(eventos)

    st.divider()
    st.subheader("Gerenciar OPs")

    for e in eventos:
        col1, col2, col3, col4 = st.columns([2,2,2,1])

        col1.write(f"**OP {e['op']}** - {e['produto']}")
        col2.write(e["maquina"])
        col3.write(e["status"])

        if col4.button("Cancelar", key=e["id"]):
            soft_delete(e["id"])
            st.rerun()

# ==============================
# MÉTRICAS
# ==============================
elif menu == "Métricas":

    st.subheader("Indicadores Industriais")
    exibir_metricas(eventos)
