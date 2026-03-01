import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz

# ==========================================================
# CONFIGURAÇÕES INICIAIS
# ==========================================================
st.set_page_config(page_title="PCP Industrial", layout="wide")

MAQUINAS_SERIGRAFIA = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504

fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# ==========================================================
# BANCO
# ==========================================================
def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

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
            qtd REAL
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
        df["rotulo_barra"] = df["pedido"]

    return df

def proximo_horario(maquina):
    df = carregar_dados()
    if df.empty:
        return agora

    df_m = df[df["maquina"] == maquina]
    if df_m.empty:
        return agora

    return max(agora, df_m["fim"].max())

# ==========================================================
# FUNÇÃO DO GRÁFICO
# ==========================================================
def renderizar_setor(lista_maquinas):

    df = carregar_dados()
    if df.empty:
        st.info("Nenhuma OP cadastrada.")
        return

    df_g = df[df["maquina"].isin(lista_maquinas)]
    if df_g.empty:
        st.info("Sem dados para este setor.")
        return

    fig = px.timeline(
        df_g,
        x_start="inicio",
        x_end="fim",
        y="maquina",
        color="status",
        text="rotulo_barra",
        category_orders={"maquina": lista_maquinas},
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# ABAS
# ==========================================================
aba1, aba2, aba3, aba4 = st.tabs([
    "➕ Lançar",
    "🎨 Serigrafia",
    "🍼 Sopro",
    "📋 Agenda"
])

# ==========================================================
# ABA 1 - LANÇAMENTO (100% CORRIGIDA)
# ==========================================================
with aba1:
    with st.container(border=True):

        st.subheader("➕ Novo Lançamento")

        c1, c2 = st.columns(2)

        with c1:
            maq_sel = st.selectbox("🏭 Máquina", TODAS_MAQUINAS)
            op_num = st.text_input("🔢 Número da OP")
            item = st.text_input("📦 Item")

        with c2:
            qtd = st.number_input("📊 Quantidade", min_value=1, value=10000)
            data_ini = st.date_input("📅 Data", agora.date())
            hora_ini = st.time_input("⏰ Hora", agora.time())

        setup_min = st.number_input("⏱ Setup (min)", min_value=0, value=30)

        # BOTÃO (INDENTAÇÃO CORRETA)
        if st.button("🚀 CONFIRMAR E AGENDAR", type="primary", use_container_width=True):

            if not op_num:
                st.error("Digite o número da OP")
                st.stop()

            inicio_dt = datetime.combine(data_ini, hora_ini)
            fim_dt = inicio_dt + timedelta(hours=qtd / CADENCIA_PADRAO)

            with conectar() as conn:
                conn.execute("""
                    INSERT INTO agenda 
                    (maquina, pedido, item, inicio, fim, status, qtd)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    maq_sel,
                    f"OP:{op_num}",
                    item,
                    inicio_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    fim_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "Pendente",
                    qtd
                ))
                conn.commit()

            st.success("✅ OP cadastrada com sucesso!")
            st.rerun()

# ==========================================================
# ABA 2 - SERIGRAFIA
# ==========================================================
with aba2:
    st.subheader("🎨 Cronograma Serigrafia")
    renderizar_setor(MAQUINAS_SERIGRAFIA)

# ==========================================================
# ABA 3 - SOPRO
# ==========================================================
with aba3:
    st.subheader("🍼 Cronograma Sopro")
    renderizar_setor(MAQUINAS_SOPRO)

# ==========================================================
# ABA 4 - AGENDA COMPLETA
# ==========================================================
with aba4:
    st.subheader("📋 Todas as OPs")
    st.dataframe(carregar_dados(), use_container_width=True)

st.divider()
st.caption("PCP Industrial v7.0 - William 🚀")
