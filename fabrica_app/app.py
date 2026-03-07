import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os

# =================================================================
# 1. CONFIGURAÇÕES GERAIS E ESTILO
# =================================================================
st.set_page_config(page_title="PCP Industrial - SISTEMA COMPLETO", layout="wide")
st_autorefresh(interval=120000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = ["sarita@will.com.br", "oneida@will.com.br"]

MAQUINAS_SERIGRAFIA = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504

fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"

st.markdown("""
<style>
.block-container {padding-top:0.5rem;}
.modebar-container {top:0!important;}
.stTabs [data-baseweb="tab-list"] {gap:10px;}
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

# =================================================================
# 2. BANCO DE DADOS PERSISTENTE
# =================================================================

if os.path.exists("/mount/data"):
    DB_PATH = "/mount/data/pcp.db"
else:
    DB_PATH = "pcp.db"

def conectar():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maquina TEXT,
            pedido TEXT,
            item TEXT,
            inicio TEXT,
            fim TEXT,
            status TEXT,
            qtd REAL,
            vinculo_id INTEGER
        )
    """)

# =================================================================
# GOOGLE SHEETS
# =================================================================

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

    except:
        return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])

# =================================================================
# CARREGAR DADOS
# =================================================================

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    conn.close()

    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)

        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1
        )

    return df

# =================================================================
# PRÓXIMO HORÁRIO
# =================================================================

def proximo_horario(maq):
    df = carregar_dados()

    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq) &
            (df["status"].isin(["Pendente","Setup","Manutenção"]))
        ]

        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)

    return agora

# =================================================================
# LOGIN
# =================================================================

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:

    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)

    col1,col2,col3 = st.columns([1,1.5,1])

    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()

        if st.button("Acessar Sistema",use_container_width=True):
            if email in [ADMIN_EMAIL] + OPERACIONAL_EMAIL:
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()

    st.stop()

# =================================================================
# PRODUTOS
# =================================================================

if 'df_produtos' not in st.session_state:
    with st.spinner("Sincronizando com Google Sheets..."):
        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

# =================================================================
# CABEÇALHO
# =================================================================

st.markdown(f"""
<div style="background:#1E1E1E;padding:8px 15px;border-radius:8px;border-left:8px solid #FF4B4B;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;">
<div>
<h2 style="color:white;margin:0;font-size:20px;">📊 PCP <span style="color:#FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS</h2>
<p style="color:#888;margin:2px 0 0 0;font-size:12px;">👤 Usuário: {st.session_state.user_email}</p>
</div>

<div style="text-align:center;border:1px solid #FF4B4B;padding:2px 15px;border-radius:5px;background:#0E1117;">
<h3 style="color:#FF4B4B;margin:0;font-family:'Courier New';font-size:22px;">
⏰ {agora.strftime('%H:%M:%S')}
</h3>
<p style="color:#aaa;margin:-2px 0 2px 0;font-size:12px;border-top:1px dashed #FF4B4B;padding-top:2px;">
{agora.strftime('%d/%m/%Y')}
</p>
</div>
</div>
""",unsafe_allow_html=True)


st.divider()
st.caption("v6.4 | Industrial By William | Serigrafia | Sopro | Hover Personalizado | Pesquisa na Gerenciar")
