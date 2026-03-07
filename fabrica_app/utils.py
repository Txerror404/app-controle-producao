# =================================================================
# FUNÇÕES UTILITÁRIAS
# =================================================================

import streamlit as st
import pandas as pd
from config import CARGA_UNIDADE, GOOGLE_SHEETS_URL

def get_descricao_produto(id_item):
    if 'df_produtos' in st.session_state:
        df_produtos = st.session_state.df_produtos
        if df_produtos is not None and not df_produtos.empty:
            produto = df_produtos[df_produtos['id_item'] == str(id_item)]
            if not produto.empty:
                return produto.iloc[0]['descricao']
    return "Descrição não encontrada"

@st.cache_data(ttl=600)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL)
        df.columns = df.columns.str.strip()
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
        df['cliente'] = df['CLIENTE'].astype(str).str.strip()
        df['qtd_carga'] = pd.to_numeric(
            df['QTD/CARGA'].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).fillna(CARGA_UNIDADE)
        return df.fillna('N/A')
    except Exception:
        return pd.DataFrame(columns=['id_item','descricao','cliente','qtd_carga'])
