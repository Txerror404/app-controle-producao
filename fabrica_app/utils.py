# =================================================================
# FUNÇÕES UTILITÁRIAS - CORRIGIDO
# =================================================================

import streamlit as st
import pandas as pd
from config import CARGA_UNIDADE, GOOGLE_SHEETS_URL

def get_descricao_produto(id_item):
    if 'df_produtos' in st.session_state:
        df_produtos = st.session_state.df_produtos
        if df_produtos is not None and not df_produtos.empty:
            # Garantir que id_item seja string para comparação
            id_item_str = str(id_item).strip()
            df_produtos['id_item'] = df_produtos['id_item'].astype(str).str.strip()
            
            produto = df_produtos[df_produtos['id_item'] == id_item_str]
            if not produto.empty:
                return produto.iloc[0]['descricao']
    return "Descrição não encontrada"

@st.cache_data(ttl=600)
def carregar_produtos_google():
    """
    Carrega produtos do Google Sheets e retorna DataFrame
    """
    try:
        st.info("🔄 Carregando produtos do Google Sheets...")
        
        # Ler CSV do Google Sheets
        df = pd.read_csv(GOOGLE_SHEETS_URL)
        
        # Limpar nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Verificar se as colunas necessárias existem
        colunas_necessarias = ['ID_ITEM', 'DESCRIÇÃO_1', 'CLIENTE', 'QTD/CARGA']
        colunas_existentes = df.columns.tolist()
        
        st.sidebar.info(f"Colunas encontradas: {colunas_existentes}")
        
        # Mapear colunas
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
        df['cliente'] = df['CLIENTE'].astype(str).str.strip()
        
        # Converter QTD/CARGA para número
        df['qtd_carga'] = pd.to_numeric(
            df['QTD/CARGA'].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).fillna(CARGA_UNIDADE)
        
        # Preencher N/A
        df = df.fillna('N/A')
        
        # Log de sucesso
        st.sidebar.success(f"✅ {len(df)} produtos carregados!")
        
        # Mostrar primeiros registros no sidebar para debug
        st.sidebar.write("Primeiros 5 produtos:")
        st.sidebar.dataframe(df[['id_item', 'descricao', 'cliente']].head())
        
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ Erro ao carregar produtos: {e}")
        # Retornar DataFrame vazio em caso de erro
        return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])
