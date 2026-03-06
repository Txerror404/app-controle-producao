import plotly.express as px
from datetime import timedelta

def gerar_gantt(df, maquinas, agora):

    df_g = df[df["maquina"].isin(maquinas)].copy()

    df_g["status_cor"] = df_g["status"]

    df_g.loc[
        (df_g["inicio"] <= agora)
        & (df_g["fim"] >= agora)
        & (df_g["status"]=="Pendente"),
        "status_cor"
    ]="Executando"

    fig = px.timeline(
        df_g,
        x_start="inicio",
        x_end="fim",
        y="maquina",
        color="status_cor",
        text="rotulo_barra"
    )

    fig.update_yaxes(autorange="reversed")

    fig.update_xaxes(
        range=[agora - timedelta(hours=2), agora + timedelta(hours=36)]
    )

    return fig
