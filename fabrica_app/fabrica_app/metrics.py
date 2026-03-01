import pandas as pd
from datetime import datetime
import streamlit as st


# ==============================
# GERAR DATAFRAME
# ==============================
def gerar_dataframe_metricas(eventos):
    if not eventos:
        return pd.DataFrame()

    dados = []

    for e in eventos:
        inicio = datetime.fromisoformat(e["inicio"])
        fim = datetime.fromisoformat(e["fim"])

        duracao = (fim - inicio).total_seconds() / 3600

        dados.append({
            "ID": e["id"],
            "Máquina": e["maquina"],
            "Status": e["status"],
            "Início": inicio,
            "Fim": fim,
            "Duração (h)": duracao
        })

    return pd.DataFrame(dados)


# ==============================
# EXIBIR DASHBOARD
# ==============================
def exibir_metricas(eventos):
    df = gerar_dataframe_metricas(eventos)

    if df.empty:
        st.info("Sem dados para exibir métricas.")
        return

    agora = datetime.now()

    total = len(df)
    em_producao = len(df[df["Status"] == "Em Produção"])
    finalizadas = len(df[df["Status"] == "Finalizado"])
    atrasadas = len(df[(df["Fim"] < agora) & (df["Status"] != "Finalizado")])
    horas_totais = round(df["Duração (h)"].sum(), 2)

    # ==============================
    # KPIs
    # ==============================
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total OPs", total)
    col2.metric("Em Produção", em_producao)
    col3.metric("Finalizadas", finalizadas)
    col4.metric("Atrasadas", atrasadas)
    col5.metric("Horas Programadas", f"{horas_totais} h")

    st.divider()

    # ==============================
    # UTILIZAÇÃO POR MÁQUINA
    # ==============================
    st.subheader("Utilização por Máquina")

    utilizacao = (
        df.groupby("Máquina")["Duração (h)"]
        .sum()
        .reset_index()
        .sort_values(by="Duração (h)", ascending=False)
    )

    st.dataframe(utilizacao, use_container_width=True)
