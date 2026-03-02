import pandas as pd
import plotly.express as px
from datetime import datetime


# ==============================
# GERAR DATAFRAME PARA GANTT
# ==============================
def gerar_dataframe(eventos):

    if not eventos:
        return pd.DataFrame()

    dados = []

    for e in eventos:

        # Converter datas (SQLite salva como string)
        inicio = datetime.fromisoformat(str(e["inicio"]))
        fim = datetime.fromisoformat(str(e["fim"]))

        duracao = (fim - inicio).total_seconds() / 3600

        dados.append({
            "ID": e["id"],
            "OP": e["op"],
            "Cliente": e["cliente"],
            "Produto": e["produto"],
            "Máquina": e["maquina"],
            "Setor": e["setor"],
            "Início": inicio,
            "Fim": fim,
            "Status": e["status"],
            "Observação": e["observacao"],
            "Duração (h)": round(duracao, 2)
        })

    return pd.DataFrame(dados)


# ==============================
# EXIBIR GANTT
# ==============================
def exibir_gantt(eventos):

    df = gerar_dataframe(eventos)

    if df.empty:
        import streamlit as st
        st.info("Nenhuma ordem cadastrada.")
        return

    fig = px.timeline(
        df,
        x_start="Início",
        x_end="Fim",
        y="Máquina",
        color="Status",
        hover_data=[
            "OP",
            "Cliente",
            "Produto",
            "Setor",
            "Status",
            "Duração (h)",
            "Observação"
        ]
    )

    fig.update_traces(marker=dict(line=dict(width=1, color="black")))

    fig.update_layout(
        height=600,
        yaxis_title="Máquina",
        xaxis_title="Período",
        legend_title="Status",
        template="plotly_white"
    )

    fig.update_yaxes(autorange="reversed")

    import streamlit as st
    st.plotly_chart(fig, use_container_width=True)
