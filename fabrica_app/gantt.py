from datetime import datetime
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import cor_por_status, formatar_data_br


# ==============================
# GERAR DATAFRAME PARA GANTT
# ==============================
def gerar_dataframe(eventos):
    if not eventos:
        return pd.DataFrame()

    dados = []

    for e in eventos:
        inicio = datetime.fromisoformat(e["inicio"])
        fim = datetime.fromisoformat(e["fim"])

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
            "Cor": cor_por_status(e["status"]),
            "Duração (h)": round((fim - inicio).total_seconds() / 3600, 2),
            "Início Formatado": formatar_data_br(inicio),
            "Fim Formatado": formatar_data_br(fim)
        })

    return pd.DataFrame(dados)


# ==============================
# EXIBIR GANTT
# ==============================
def exibir_gantt(eventos, st):
    df = gerar_dataframe(eventos)

    if df.empty:
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
            "Início Formatado",
            "Fim Formatado",
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

    st.plotly_chart(fig, use_container_width=True)
