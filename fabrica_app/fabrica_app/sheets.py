import pandas as pd
from datetime import datetime
import streamlit as st
import io


# ==============================
# CONVERTER EVENTOS PARA DATAFRAME
# ==============================
def gerar_dataframe_exportacao(eventos):

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
            "Descrição": e["descricao"],
            "Status": e["status"],
            "Início": inicio,
            "Fim": fim,
            "Duração (h)": round(duracao, 2)
        })

    df = pd.DataFrame(dados)
    return df


# ==============================
# BOTÃO DE EXPORTAÇÃO
# ==============================
def botao_exportar_excel(eventos):

    df = gerar_dataframe_exportacao(eventos)

    if df.empty:
        st.info("Sem dados para exportar.")
        return

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Produção")

    output.seek(0)

    st.download_button(
        label="📥 Baixar Excel",
        data=output,
        file_name="controle_producao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
