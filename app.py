import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# ===============================
# 1. CONFIGURAÇÃO E ACESSO
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")
st_autorefresh(interval=30000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            email = st.text_input("E-mail autorizado:").lower().strip()
            if st.button("Liberar Acesso", use_container_width=True):
                if email:
                    st.session_state.auth_ok = True
                    st.session_state.user_email = email
                    st.rerun()

if not st.session_state.auth_ok:
    tela_login()
    st.stop()

is_admin = st.session_state.user_email == ADMIN_EMAIL

# ===============================
# 2. BANCO DE DADOS
# ===============================
def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, pedido TEXT, item TEXT, 
            inicio TEXT, fim TEXT, status TEXT, 
            qtd REAL, vinculo_id INTEGER
        )""")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")
    try: conn.execute("ALTER TABLE agenda ADD COLUMN vinculo_id INTEGER")
    except: pass
    try: conn.execute("ALTER TABLE agenda ADD COLUMN qtd REAL DEFAULT 0")
    except: pass

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
        df["inicio_format"] = df["inicio"].dt.strftime('%d/%m %H:%M')
        df["fim_format"] = df["fim"].dt.strftime('%d/%m %H:%M')
        df["rotulo_grafico"] = df.apply(lambda r: "SETUP" if r['status'] == "Setup" else f"{r['pedido']} | {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# ===============================
# 4. SIDEBAR
# ===============================
with st.sidebar:
    st.title(f"👤 {'ADMIN' if is_admin else 'OPERADOR'}")
    st.markdown(f"### 🕒 {agora.strftime('%H:%M:%S')}")
    st.write(f"📅 {agora.strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    df_exp = carregar_dados()
    if not df_exp.empty:
        csv = df_exp.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Dados (CSV)", csv, "pcp_william.csv", "text/csv")
    
    if st.button("Sair"):
        st.session_state.auth_ok = False
        st.rerun()

# ===============================
# 5. ABAS
# ===============================
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançamentos", "📊 Gantt", "⚙️ Gerenciar", "📦 Catálogo", "📈 Dashboard"])

# --- ABA 1: LANÇAMENTOS ---
with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Programar Produção")
        df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
        with st.form("form_pedido_novo"):
            maq_s = st.selectbox("Máquina", MAQUINAS)
            p_lista = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            p_sel = st.selectbox("Produto", [""] + p_lista)
            ped_n = st.text_input("Nº Pedido")
            cli_sug = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
            cli_n = st.text_input("Cliente", value=cli_sug)
            qtd_n = st.number_input("Quantidade", value=2380)
            set_n = st.number_input("Setup Automático (min)", value=30)
            sug = proximo_horario(maq_s)
            c1, c2 = st.columns(2)
            dat_n = c1.date_input("Data Início", sug.date(), key="new_date_prod")
            hor_n = c2.time_input("Hora Início", sug.time(), key="new_time_prod")
            if st.form_submit_button("Lançar Pedido + Setup"):
                if ped_n and p_sel:
                    ini = datetime.combine(dat_n, hor_n); fim = ini + timedelta(hours=qtd_n/CADENCIA_PADRAO)
                    with conectar() as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_s, f"{cli_n} | {ped_n}", p_sel.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                        pedido_id = cur.lastrowid
                        if set_n > 0:
                            f_s = fim + timedelta(minutes=set_n)
                            conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                        (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, pedido_id))
                    st.success("Lançado!"); st.rerun()

    with col_b:
        st.subheader("Setup Avulso")
        with st.form("form_avulso_novo"):
            maq_av = st.selectbox("Máquina ", MAQUINAS)
            desc_av = st.text_input("Motivo")
            dur_av = st.number_input("Duração (minutos)", value=60)
            sug_av = proximo_horario(maq_av)
            c3, c4 = st.columns(2)
            d_av = c3.date_input("Data", sug_av.date(), key="avulso_date")
            h_av = c4.time_input("Hora", sug_av.time(), key="avulso_time")
            if st.form_submit_button("Lançar Setup"):
                i_av = datetime.combine(d_av, h_av); f_av = i_av + timedelta(minutes=dur_av)
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim,
