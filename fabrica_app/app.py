import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os

# =================================================================
# CONFIGURAÇÕES
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

# =================================================================
# BANCO DE DADOS PERSISTENTE
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
# VERIFICAR CONFLITO
# =================================================================


def verificar_conflito(df, maquina, inicio_novo, fim_novo):

    df_maquina = df[df["maquina"] == maquina]

    if df_maquina.empty:
        return False

    conflito = df_maquina[
        (inicio_novo < df_maquina["fim"]) &
        (fim_novo > df_maquina["inicio"])
    ]

    return not conflito.empty

# =================================================================
# PRÓXIMO HORÁRIO
# =================================================================


def proximo_horario(maq):
    df = carregar_dados()

    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq) &
            (df["status"].isin(["Pendente", "Setup", "Manutenção"]))
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

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:

        email = st.text_input("E-mail autorizado:").lower().strip()

        if st.button("Acessar Sistema", use_container_width=True):

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
# ABAS
# =================================================================

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(
    ["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"]
)

# =================================================================
# ABA LANÇAR
# =================================================================

with aba1:

    st.subheader("➕ Novo Lançamento")

    df_prod = df_produtos.copy()

    maq_sel = st.selectbox("Máquina", TODAS_MAQUINAS)

    item_sel = st.selectbox("ID ITEM", df_prod["id_item"].tolist())

    descricao = "N/A"
    cliente = "N/A"
    carga = CARGA_UNIDADE

    if item_sel:

        prod = df_prod[df_prod["id_item"] == item_sel]

        if not prod.empty:

            prod = prod.iloc[0]

            descricao = prod["descricao"]
            cliente = prod["cliente"]
            carga = int(prod["qtd_carga"])

    st.text_input("Descrição", descricao, disabled=True)
    st.text_input("Cliente", cliente, disabled=True)

    op_num = st.text_input("Número OP")

    qtd = st.number_input("Quantidade", value=carga)

    sugestao = proximo_horario(maq_sel)

    data = st.date_input("Data", sugestao.date())
    hora = st.time_input("Hora", sugestao.time())

    if st.button("🚀 CONFIRMAR E AGENDAR", use_container_width=True):

        inicio = datetime.combine(data, hora)
        fim = inicio + timedelta(hours=qtd / CADENCIA_PADRAO)

        eventos = carregar_dados()

        if verificar_conflito(eventos, maq_sel, inicio, fim):

            st.error("⚠️ Conflito de horário nesta máquina!")
            st.stop()

        with conectar() as conn:

            conn.execute("""
            INSERT INTO agenda
            (maquina,pedido,item,inicio,fim,status,qtd)
            VALUES (?,?,?,?,?,?,?)
            """, (
                maq_sel,
                f"{cliente} | OP:{op_num}",
                item_sel,
                inicio.strftime("%Y-%m-%d %H:%M:%S"),
                fim.strftime("%Y-%m-%d %H:%M:%S"),
                "Pendente",
                qtd
            ))

            conn.commit()

        st.success("OP programada!")

        st.rerun()

# =================================================================
# PRODUTOS
# =================================================================

with aba5:
    st.dataframe(df_produtos, use_container_width=True)

# =================================================================
# CARGAS
# =================================================================

with aba6:

    df = carregar_dados()

    if not df.empty:

        df_p = df[(df["status"] == "Pendente") & (df["qtd"] > 0)]

        total = df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)]["qtd"].sum()

        st.metric(
            "Total Cargas Sopro",
            f"{total / CARGA_UNIDADE:.1f}"
        )

# =================================================================
# BACKUP
# =================================================================

st.download_button(
    "Baixar backup do banco",
    open(DB_PATH, "rb"),
    file_name="backup_pcp.db"
)

st.divider()

st.caption("PCP Industrial | William | Streamlit")
