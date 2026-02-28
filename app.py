import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import io
from streamlit_autorefresh import st_autorefresh

# ===============================
# 1. CONFIGURAÇÃO E ACESSO
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")
st_autorefresh(interval=30000, key="pcp_refresh")

ADMIN_EMAIL = "will@admin.com.br"
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🏭 Sistema PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            email = st.text_input("Digite seu e-mail para acessar:").lower().strip()
            if st.button("Entrar no Sistema", use_container_width=True):
                if email:
                    st.session_state.auth_ok = True
                    st.session_state.user_email = email
                    st.rerun()

if not st.session_state.auth_ok:
    tela_login()
    st.stop()

is_admin = st.session_state.user_email == ADMIN_EMAIL

# ===============================
# 2. BANCO DE DADOS (COM VÍNCULO)
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
        df["rotulo_grafico"] = df.apply(lambda r: "SETUP" if r['status'] == "Setup" else f"{r['pedido']} | Qtd: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return max(datetime.now(), df_maq["fim"].max())
    return datetime.now()

# ===============================
# 4. INTERFACE PRINCIPAL
# ===============================
st.sidebar.title(f"👤 {'ADMIN' if is_admin else 'OPERADOR'}")
st.sidebar.write(f"Usuário: {st.session_state.user_email}")
if st.sidebar.button("Sair"):
    st.session_state.auth_ok = False
    st.rerun()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Lançamentos", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 1: LANÇAMENTOS (PEDIDO + SETUP AVULSO) ---
with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Programar Produção")
        df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
        with st.form("form_pedido"):
            maq_s = st.selectbox("Máquina", MAQUINAS)
            p_lista = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            p_sel = st.selectbox("Produto", [""] + p_lista)
            ped_n = st.text_input("Nº Pedido")
            cli_n = st.text_input("Cliente (Manual)")
            qtd_n = st.number_input("Quantidade", value=2380)
            set_n = st.number_input("Setup Automático (min)", value=30)
            sug = proximo_horario(maq_s)
            c1, c2 = st.columns(2)
            dat_n = c1.date_input("Data Início", sug.date())
            hor_n = c2.time_input("Hora Início", sug.time())
            if st.form_submit_button("Lançar Pedido + Setup"):
                if ped_n and p_sel:
                    ini = datetime.combine(dat_n, hor_n)
                    fim = ini + timedelta(hours=qtd_n/CADENCIA_PADRAO)
                    with conectar() as conn:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_s, f"{cli_n} | {ped_n}", p_sel.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                        pedido_id = cur.lastrowid
                        if set_n > 0:
                            f_s = fim + timedelta(minutes=set_n)
                            conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                        (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, pedido_id))
                    st.success("Lançado com sucesso!"); st.rerun()

    with col_b:
        st.subheader("Setup Avulso / Manutenção")
        with st.form("form_setup_avulso"):
            maq_av = st.selectbox("Máquina ", MAQUINAS)
            desc_av = st.text_input("Motivo (Ex: Manutenção, Limpeza)")
            dur_av = st.number_input("Duração (minutos)", value=60)
            sug_av = proximo_horario(maq_av)
            c3, c4 = st.columns(2)
            d_av = c3.date_input("Data ", sug_av.date())
            h_av = c4.time_input("Hora ", sug_av.time())
            if st.form_submit_button("Lançar Setup Avulso"):
                i_av = datetime.combine(d_av, h_av)
                f_av = i_av + timedelta(minutes=dur_av)
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                (maq_av, "SETUP", desc_av, i_av.strftime('%Y-%m-%d %H:%M:%S'), f_av.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0))
                st.success("Setup avulso lançado!"); st.rerun()

# --- ABA 2: GANTT ---
with aba2:
    st.subheader("Cronograma de Máquinas")
    df_g = carregar_dados()
    if not df_g.empty:
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", 
            color="status", text="rotulo_grafico",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "inicio_format", "fim_format", "item", "qtd"],
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f"}
        )
        fig.update_traces(
            textposition='inside', insidetextanchor='start',
            hovertemplate="<b>%{customdata[0]}</b><br>Início: %{customdata[1]}<br>Fim: %{customdata[2]}<br>Cód: %{customdata[3]}<br>Qtd: %{customdata[4]}<extra></extra>"
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=datetime.now(), line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

# --- ABA 3: GERENCIAR (COM ARRASTO VINCULADO) ---
with aba3:
    df_ger = carregar_dados()
    if not df_ger.empty:
        df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values("inicio")
        for _, r in df_ab.iterrows():
            if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
            
            with st.expander(f"{r['maquina']} | {r['pedido']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Item:** {r['item']} | **Qtd:** {int(r['qtd'])}")
                    if st.button("✅ CONCLUIR", key=f"c{r['id']}", use_container_width=True):
                        with conectar() as c:
                            c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                            c.execute("UPDATE agenda SET status='Concluído' WHERE vinculo_id=?", (r['id'],))
                        st.rerun()
                with c2:
                    if is_admin:
                        nd = st.date_input("Novo Início", r['inicio'].date(), key=f"d{r['id']}")
                        nh = st.time_input("Nova Hora", r['inicio'].time(), key=f"h{r['id']}")
                        if st.button("Mover Pedido + Setup", key=f"up{r['id']}", use_container_width=True):
                            novo_ini = datetime.combine(nd, nh)
                            delta_segundos = (novo_ini - r['inicio']).total_seconds()
                            novo_fim = r['fim'] + (novo_ini - r['inicio'])
                            with conectar() as c:
                                # Move o pedido
                                c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", 
                                         (novo_ini.strftime('%Y-%m-%d %H:%M:%S'), novo_fim.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                # Move o setup vinculado na mesma proporção
                                c.execute("""UPDATE agenda SET 
                                            inicio = datetime(inicio, ? || ' seconds'), 
                                            fim = datetime(fim, ? || ' seconds') 
                                            WHERE vinculo_id = ?""", (delta_segundos, delta_segundos, r['id']))
                            st.rerun()

# --- ABA 4: CATÁLOGO ---
with aba4:
    if is_admin:
        with st.form("f_prod"):
            c1, c2, c3 = st.columns(3); cod = c1.text_input("Código"); des = c2.text_input("Descrição"); cli = c3.text_input("Cliente")
            if st.form_submit_button("Salvar Produto"):
                with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (cod, des, cli)); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conectar()), use_container_width=True)
