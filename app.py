import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import io
from streamlit_autorefresh import st_autorefresh

# ===============================
# 1. CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")

# ATUALIZAÇÃO AUTOMÁTICA: 30 segundos
st_autorefresh(interval=30000, key="pcp_refresh")

# Acesso liberado
EMAILS_AUTORIZADOS = ["will@admin.com.br"]

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🔐 PCP William</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            email_input = st.text_input("E-mail autorizado:").lower().strip()
            if st.button("Liberar Acesso", use_container_width=True):
                if email_input in EMAILS_AUTORIZADOS:
                    st.session_state.auth_ok = True
                    st.rerun()
                else:
                    st.error("E-mail não autorizado.")

if not st.session_state.auth_ok:
    tela_login()
    st.stop()

# ===============================
# 2. VARIÁVEIS E BANCO
# ===============================
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT, qtd REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")
    try:
        conn.execute("ALTER TABLE agenda ADD COLUMN qtd REAL DEFAULT 0")
    except:
        pass 

# ===============================
# 3. FUNÇÕES DE APOIO
# ===============================
def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        
        # LÓGICA DE RÓTULO: Se for Setup, escreve apenas SETUP. Senão, mostra Pedido + Qtd.
        df["rotulo_grafico"] = df.apply(
            lambda r: "SETUP" if r['status'] == "Setup" 
            else f"{r['pedido']} | Qtd: {int(r['qtd'])}", 
            axis=1
        )
    return df

def carregar_produtos():
    with conectar() as c:
        return pd.read_sql_query("SELECT * FROM produtos", c)

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# ===============================
# 4. INTERFACE PRINCIPAL
# ===============================
st.title("🏭 Gestão de Produção Industrial")

with st.sidebar:
    st.title("👤 Usuário")
    st.write(f"🕒 {agora.strftime('%H:%M:%S')}")
    if st.button("Sair"):
        st.session_state.auth_ok = False
        st.rerun()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Novo Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 2: GANTT ---
with aba2:
    st.subheader("Cronograma de Máquinas")
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", 
            color="status_cor", text="rotulo_grafico",
            category_orders={"maquina": MAQUINAS},
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(size=12, color="white")
        )
        
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.add_annotation(x=agora, y=1.05, yref="paper", text=f"⏱️ AGORA: {agora.strftime('%H:%M')}", showarrow=False, font=dict(color="white", size=14), bgcolor="red", borderpad=4)
        st.plotly_chart(fig, use_container_width=True)
    
    # Cards de Status
    cols = st.columns(len(MAQUINAS))
    for i, m in enumerate(MAQUINAS):
        df_m = df_g[(df_g["maquina"] == m) & (df_g["status"] != "Concluído")] if not df_g.empty else pd.DataFrame()
        if df_m.empty: cols[i].warning(f"⚠️ {m.upper()}\n\nSem carga.")
        elif not df_m[df_m["fim"] < agora].empty: cols[i].error(f"🚨 {m.upper()}\n\nEM ATRASO")
        else: cols[i].success(f"✅ {m.upper()}\n\nEm dia.")

# --- ABA 1: NOVO PEDIDO ---
with aba1:
    st.subheader("Programar Máquina")
    df_p = carregar_produtos()
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_s = st.selectbox("Máquina", MAQUINAS)
        sugestao = proximo_horario(maq_s)
    with col_prod:
        if not df_p.empty:
            lista_p = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            p_sel = st.selectbox("Produto", [""] + lista_p)
            item_a = p_sel.split(" | ")[1] if p_sel else ""; cli_a = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
        else: st.error("Cadastre produtos no Catálogo."); item_a, cli_a = "", ""

    with st.form("form_p"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Nº Pedido")
        cli_n = c
