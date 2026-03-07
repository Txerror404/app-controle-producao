import psycopg2
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# CONFIGURAÇÃO DA PÁGINA

st.set_page_config(
    page_title="PCP Industrial - SISTEMA COMPLETO",
    layout="wide"
)

# CONEXÃO COM BANCO SUPABASE

DATABASE_URL = "postgresql://postgres.ogxrgnaedmcbaqgryosg:pcp2026supabase@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"


def conectar():
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10
        )
        return conn

    except Exception as e:
        st.error(f"Erro ao conectar no Supabase: {e}")
        st.stop()

# TESTE DE CONEXÃO

try:
    conn = conectar()
    conn.close()
except Exception as e:
    st.error(f"Falha na conexão com Supabase: {e}")
    st.stop()

# CRIAÇÃO DA TABELA (CASO NÃO EXISTA)

try:
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id SERIAL PRIMARY KEY,
            maquina TEXT,
            pedido TEXT,
            item TEXT,
            inicio TIMESTAMP,
            fim TIMESTAMP,
            status TEXT,
            qtd NUMERIC,
            vinculo_id INTEGER,
            criado_por TEXT,
            criado_em TIMESTAMP,
            alterado_por TEXT,
            alterado_em TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Erro ao criar tabela: {e}")
    st.stop()

# AUTO REFRESH

st_autorefresh(interval=120000, key="pcp_refresh_global")

# CONFIGURAÇÕES GERAIS

ADMIN_EMAIL = "will@admin.com.br"

OPERACIONAL_EMAIL = [
    "sarita@will.com.br",
    "oneida@will.com.br"
]

MAQUINAS_SERIGRAFIA = [
    "maquina 13001",
    "maquina 13002",
    "maquina 13003",
    "maquina 13004"
]

MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]

TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380

CARGA_UNIDADE = 49504

# FUSO HORÁRIO

fuso_br = pytz.timezone("America/Sao_Paulo")

agora = datetime.now(fuso_br).replace(tzinfo=None)

# GOOGLE SHEETS

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"


# ESTILO DA INTERFACE

st.markdown("""
<style>

.block-container {
    padding-top: 0.5rem;
}

.modebar-container {
    top:0!important;
}

.stTabs [data-baseweb="tab-list"]{
    gap:10px;
}

.stTabs [data-baseweb="tab"]{
    background-color:#1e1e1e;
    border-radius:5px;
    padding:5px 20px;
    color:white;
}

.stTabs [aria-selected="true"]{
    background-color:#FF4B4B!important;
}

</style>
""", unsafe_allow_html=True)
