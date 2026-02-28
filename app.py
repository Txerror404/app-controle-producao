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
                else:
                    st.error("Por favor, insira um e-mail.")

if not st.session_state.auth_ok:
    tela_login()
    st.stop()

# Verificar se é Admin
is_admin = st.session_state.user_email == ADMIN_EMAIL

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
        df["rotulo_grafico"] = df.apply(lambda r: "SETUP" if r['status'] == "Setup" else f"{r['pedido']} | Qtd: {int(r['qtd'])}", axis=1)
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
st.sidebar.title(f"👤 {'ADMIN' if is_admin else 'OPERADOR'}")
st.sidebar.write(f"Logado: {st.session_state.user_email}")
if st.sidebar.button("Sair"):
    st.session_state.auth_ok = False
    st.rerun()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Novo Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 2: GANTT (VISUALIZAÇÃO IGUAL PARA TODOS) ---
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
            custom_data=["pedido", "inicio_format", "fim_format", "item", "qtd"],
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
        fig.update_traces(
            textposition='inside', insidetextanchor='start',
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{customdata[0]}</b><br>Início: %{customdata[1]}<br>Fim: %{customdata[2]}<br>Cód: %{customdata[3]}<br>Qtd: %{customdata[4]}<extra></extra>"
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

# --- ABA 1: NOVO PEDIDO (TODOS ADICIONAM) ---
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
            item_a = p_sel.split(" | ")[0] if p_sel else ""; cli_a = df_p[df_p['codigo'] == item_a]['cliente'].values[0] if p_sel else ""
        else: st.error("Admin deve cadastrar produtos no Catálogo."); item_a, cli_a = "", ""

    with st.form("form_p"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Nº Pedido")
        cli_n = c1.text_input("Cliente", value=cli_a)
        qtd_n = c2.number_input("Quantidade", value=2380)
        set_n = c2.number_input("Setup (min)", value=30)
        c3, c4 = st.columns(2)
        dat_n = c3.date_input("Data", sugestao.date()); hor_n = c4.time_input("Hora", sugestao.time())
        if st.form_submit_button("Confirmar Lançamento"):
            if ped_n and p_sel:
                ini = datetime.combine(dat_n, hor_n)
                fim = ini + timedelta(hours=qtd_n/CADENCIA)
                with conectar() as conn:
                    label = f"{cli_n} | {ped_n}"
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                (maq_s, label, item_a, ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                    if set_n > 0:
                        fim_s = fim + timedelta(minutes=set_n)
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), fim_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0))
                st.success("Salvo!"); st.rerun()

# --- ABA 3: GERENCIAR (DIFERENCIADA) ---
with aba3:
    df_ger = carregar_dados()
    t_p, t_c = st.tabs(["⚡ Em Aberto", "✅ Histórico"])
    with t_p:
        if not df_ger.empty:
            df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values("inicio")
            for _, r in df_ab.iterrows():
                with st.expander(f"{r['maquina']} | {r['pedido']}"):
                    col_info, col_edit = st.columns(2)
                    with col_info:
                        st.write(f"**Cód Item:** {r['item']}")
                        st.write(f"**Qtd:** {int(r['qtd'])}")
                        # Operador pode concluir
                        if st.button("✅ CONCLUIR", key=f"c{r['id']}", use_container_width=True):
                            with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],)); st.rerun()
                        # Somente Admin pode excluir
                        if is_admin:
                            if st.button("🗑️ EXCLUIR", key=f"d{r['id']}", use_container_width=True):
                                with conectar() as c: c.execute("DELETE FROM agenda WHERE id=?", (r['id'],)); st.rerun()
                    
                    with col_edit:
                        if is_admin:
                            st.markdown("🔧 **Ajuste de Admin**")
                            nd = st.date_input("Nova Data", r['inicio'].date(), key=f"dt{r['id']}")
                            nh = st.time_input("Nova Hora", r['inicio'].time(), key=f"hr{r['id']}")
                            if st.button("💾 Salvar Alteração", key=f"up{r['id']}"):
                                ni = datetime.combine(nd, nh); nf = ni + (r['fim'] - r['inicio'])
                                with conectar() as c: c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (ni.strftime('%Y-%m-%d %H:%M:%S'), nf.strftime('%Y-%m-%d %H:%M:%S'), r['id'])); st.rerun()
                        else:
                            st.info("Somente Administradores podem editar horários.")

    with t_c:
        if not df_ger.empty:
            df_con = df_ger[df_ger["status"] == "Concluído"].sort_values("fim", ascending=False)
            if is_admin:
                # Admin pode reabrir ordens
                for _, r in df_con.iterrows():
                    with st.expander(f"✅ {r['maquina']} | {r['pedido']}"):
                        if st.button("Reabrir Ordem", key=f"re{r['id']}"):
                            with conectar() as c: c.execute("UPDATE agenda SET status='Pendente' WHERE id=?", (r['id'],)); st.rerun()
            st.dataframe(df_con, use_container_width=True)

# --- ABA 4: CATÁLOGO (SOMENTE ADMIN) ---
with aba4:
    if is_admin:
        st.subheader("Gerenciar Catálogo")
        with st.form("f_prod"):
            c1, c2, c3 = st.columns(3); cod = c1.text_input("Código"); des = c2.text_input("Descrição"); cli = c3.text_input("Cliente")
            if st.form_submit_button("Salvar Produto"):
                with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (cod, des, cli)); st.rerun()
    else:
        st.warning("⚠️ Apenas o Administrador pode cadastrar novos itens.")
    
    st.markdown("### Itens Cadastrados")
    st.dataframe(carregar_produtos(), use_container_width=True)
