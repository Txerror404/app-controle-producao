import streamlit as st

from fabrica_app.db import criar_tabela, carregar_dados
from fabrica_app.sheets import carregar_produtos_google

import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURAÇÕES GERAIS E ESTILO
# =================================================================

criar_tabela()

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
# 2. BANCO DE DADOS
# =================================================================
def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda(
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

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    conn.close()

    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors="coerce").fillna(0)

        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP"
            if r["status"] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1,
        )

    return df

# =================================================================
# 3. PRÓXIMO HORÁRIO
# =================================================================
def proximo_horario(maq):
    df = carregar_dados()

    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq)
            & (df["status"].isin(["Pendente", "Setup", "Manutenção"]))
        ]

        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)

    return agora

# =================================================================
# 4. LOGIN
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
# 5. PRODUTOS GOOGLE SHEETS
# =================================================================
if "df_produtos" not in st.session_state:

    with st.spinner("Sincronizando com Google Sheets..."):
        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

# =================================================================
# 6. CABEÇALHO
# =================================================================
st.markdown(
f"""
<div style="background:#1E1E1E;padding:8px 15px;border-radius:8px;border-left:8px solid #FF4B4B;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;">
<div>
<h2 style="color:white;margin:0;font-size:20px;">📊 PCP <span style="color:#FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS</h2>
<p style="color:#888;margin:2px 0 0 0;font-size:12px;">👤 Usuário: {st.session_state.user_email}</p>
</div>
<div style="text-align:center;border:1px solid #FF4B4B;padding:2px 15px;border-radius:5px;background:#0E1117;">
<h3 style="color:#FF4B4B;margin:0;font-family:'Courier New';font-size:22px;">⏰ {agora.strftime('%H:%M:%S')}</h3>
<p style="color:#aaa;margin:-2px 0 2px 0;font-size:12px;border-top:1px dashed #FF4B4B;padding-top:2px;">
{agora.strftime('%d/%m/%Y')}
</p>
</div>
</div>
""",
unsafe_allow_html=True,
)

# =================================================================
# 7. ABAS
# =================================================================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(
[
"➕ Lançar",
"🎨 Serigrafia",
"🍼 Sopro",
"⚙️ Gerenciar",
"📋 Produtos",
"📈 Cargas",
]
)

# =================================================================
# ABA 1
# =================================================================
with aba1:

    st.subheader("➕ Novo Lançamento")

    df_prod = df_produtos.copy()

    df_prod["id_item"] = df_prod["id_item"].astype(str).str.strip()

    c1, c2 = st.columns(2)

    with c1:

        maq_sel = st.selectbox("🏭 Máquina destino", TODAS_MAQUINAS)

        item_sel = st.selectbox(
            "📌 Selecione o ID_ITEM",
            df_prod["id_item"].tolist(),
        )

        descricao = "N/A"
        cliente = "N/A"
        carga = CARGA_UNIDADE

        if item_sel:

            info = df_prod[df_prod["id_item"] == item_sel]

            if not info.empty:

                info = info.iloc[0]

                descricao = info["descricao"]
                cliente = info["cliente"]
                carga = int(info["qtd_carga"])

        st.text_input("📝 Descrição", descricao, disabled=True)

    with c2:

        op_num = st.text_input("🔢 OP")

        st.text_input("👥 Cliente", cliente, disabled=True)

        qtd = st.number_input("📊 Quantidade", value=carga)

    c3, c4, c5 = st.columns(3)

    setup = c3.number_input("⏱️ Setup (min)", value=30)

    sugestao = proximo_horario(maq_sel)

    data = c4.date_input("📅 Data", sugestao.date())

    hora = c5.time_input("⏰ Hora", sugestao.time())

    if st.button("🚀 CONFIRMAR E AGENDAR", use_container_width=True):

        if op_num:

            inicio = datetime.combine(data, hora)

            fim = inicio + timedelta(hours=qtd / CADENCIA_PADRAO)

            with conectar() as conn:

                cur = conn.cursor()

                cur.execute(
                    """
                    INSERT INTO agenda
                    (maquina,pedido,item,inicio,fim,status,qtd)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        maq_sel,
                        f"{cliente} | OP:{op_num}",
                        item_sel,
                        inicio.strftime("%Y-%m-%d %H:%M:%S"),
                        fim.strftime("%Y-%m-%d %H:%M:%S"),
                        "Pendente",
                        qtd,
                    ),
                )

                conn.commit()

            st.success("Produção agendada!")

            st.rerun()

# =================================================================
# ABA PRODUTOS
# =================================================================
with aba5:

    st.dataframe(df_produtos, use_container_width=True)

# =================================================================
# ABA CARGAS
# =================================================================
with aba6:

    df_c = carregar_dados()

    if not df_c.empty:

        df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]

        st.metric(
            "Total Geral de Cargas Sopro",
            f"{df_p[df_p['maquina'].isin(MAQUINAS_SOPRO)]['qtd'].sum() / CARGA_UNIDADE:.1f}",
        )

        st.table(df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)][["maquina", "pedido", "qtd"]])

st.divider()

st.caption("v7.0 | PCP Industrial | Estrutura Modular")
