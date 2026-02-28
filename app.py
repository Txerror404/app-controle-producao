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
st.set_page_config(page_title="PCP William - Industrial", layout="wide", page_icon="🏭")
st_autorefresh(interval=30000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 # Valor da carga informado por você
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

# CSS Visual (Mantido conforme aprovado)
st.markdown("""
<style>
    .main-title { text-align: center; background: linear-gradient(90deg, #2c3e50, #4ca1af); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 3rem !important; margin-bottom: 2rem; }
    .status-card { padding: 20px; border-radius: 10px; text-align: center; color: white; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .card-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
    .card-machine { font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px; }
    .card-status { font-size: 1.5rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT, qtd REAL, vinculo_id INTEGER)")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")

def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["h_ini"] = df["inicio"].dt.strftime('%H:%M')
        df["h_fim"] = df["fim"].dt.strftime('%H:%M')
        df["rotulo_barra"] = df.apply(lambda r: "SETUP" if r['status'] == "Setup" else f"<b>{r['pedido']}</b><br>QUANT: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

# --- LOGIN E SIDEBAR (Mantidos) ---
if not st.session_state.auth_ok:
    st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            email = st.text_input("E-mail autorizado:").lower().strip()
            if st.button("Liberar Acesso", use_container_width=True):
                if email: st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

is_admin = st.session_state.user_email == ADMIN_EMAIL

# --- ABAS ---
st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançamentos", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Carga Semana"])

# ABA 1: LANÇAMENTOS (Preservada)
with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("### ➕ Programar Produção")
            df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
            with st.form("f_new_ped"):
                maq_s = st.selectbox("Máquina", MAQUINAS)
                p_lista = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
                p_sel = st.selectbox("Produto", [""] + p_lista)
                ped_n = st.text_input("Nº Pedido")
                cli_sug = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
                cli_n = st.text_input("Cliente", value=cli_sug)
                qtd_n = st.number_input("Quantidade", value=CARGA_UNIDADE)
                set_n = st.number_input("Setup Automático (min)", value=30)
                sug = proximo_horario(maq_s); c1, c2 = st.columns(2)
                dat_n = c1.date_input("Data Início", sug.date()); hor_n = c2.time_input("Hora Início", sug.time())
                if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
                    if ped_n and p_sel:
                        ini = datetime.combine(dat_n, hor_n); fim = ini + timedelta(hours=qtd_n/CADENCIA_PADRAO)
                        with conectar() as conn:
                            cur = conn.cursor(); cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)", (maq_s, f"{cli_n} | {ped_n}", p_sel.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                            p_id = cur.lastrowid
                            if set_n > 0:
                                f_s = fim + timedelta(minutes=set_n)
                                conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)", (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, p_id))
                        st.rerun()

# ABA 2: GANTT (CORREÇÃO DE INDEPENDÊNCIA E CARD)
with aba2:
    st.markdown("### 📊 Cronograma de Máquinas")
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        # Garantindo que cada máquina é um eixo independente e barras não se sobrepõem
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "h_ini", "h_fim", "item", "qtd"],
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#95a5a6", "Executando": "#e67e22"}
        )
        fig.add_vline(x=agora, line_dash="dash", line_color="#e74c3c", line_width=2)
        fig.add_annotation(x=agora, y=1, text=f"AGORA: {agora.strftime('%H:%M')}", showarrow=False, yref="paper", xanchor="left", font=dict(color="#e74c3c", size=14))
        fig.update_traces(textposition='inside', insidetextanchor='start', hovertemplate="<b>%{customdata[0]}</b><br>Início : %{customdata[1]}<br>Fim: %{customdata[2]}<br>Cód: %{customdata[3]}<br>Qtd: %{customdata[4]}<extra></extra>")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(legend=dict(orientation="h", y=-0.2), margin=dict(l=0, r=0, t=30, b=0), barmode='group') # barmode group isola as barras
        st.plotly_chart(fig, use_container_width=True)

# ABA 3: GERENCIAR (Independência no recálculo por máquina)
with aba3:
    df_ger = carregar_dados()
    t_p, t_c = st.tabs(["⚡ Em Aberto", "✅ Histórico"])
    with t_p:
        if not df_ger.empty:
            df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values(["maquina", "inicio"])
            for _, r in df_ab.iterrows():
                if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
                with st.expander(f"🛠️ {r['maquina']} | {r['pedido']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("✅ CONCLUIR", key=f"c_{r['id']}", use_container_width=True):
                            with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", (r['id'], r['id'])); st.rerun()
                    with c2:
                        if is_admin:
                            nd = st.date_input("Data", r['inicio'].date(), key=f"d_{r['id']}")
                            nh = st.time_input("Hora", r['inicio'].time(), key=f"t_{r['id']}")
                            if st.button("Mover", key=f"m_{r['id']}", use_container_width=True):
                                ni = datetime.combine(nd, nh); ds = (ni - r['inicio']).total_seconds(); nf = r['fim'] + (ni - r['inicio'])
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (ni.strftime('%Y-%m-%d %H:%M:%S'), nf.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio=datetime(inicio, ? || ' seconds'), fim=datetime(fim, ? || ' seconds') WHERE vinculo_id=?", (ds, ds, r['id']))
                                st.rerun()
                    with c3:
                        if is_admin:
                            nv_q = st.number_input("Qtd", value=float(r['qtd']), key=f"q_{r['id']}")
                            if st.button("Atualizar Qtd", key=f"bq_{r['id']}", use_container_width=True):
                                n_f = r['inicio'] + timedelta(hours=nv_q/CADENCIA_PADRAO); s_d = (n_f - r['fim']).total_seconds()
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET qtd=?, fim=? WHERE id=?", (nv_q, n_f.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio=?, fim=datetime(fim, ? || ' seconds') WHERE vinculo_id=?", (n_f.strftime('%Y-%m-%d %H:%M:%S'), s_d, r['id']))
                                st.rerun()

# ABA 5: CARGA SEMANAL (NOVA FUNCIONALIDADE)
with aba5:
    st.markdown(f"### 📈 Planejamento de Cargas (Base: {CARGA_UNIDADE} un)")
    df_c = carregar_dados()
    if not df_c.empty:
        # Filtra apenas a semana atual
        inicio_semana = agora - timedelta(days=agora.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        df_sem = df_c[(df_c["inicio"] >= inicio_semana) & (df_c["status"] != "Concluído") & (df_c["status"] != "Setup")]
        
        c_m = st.columns(len(MAQUINAS))
        for i, m in enumerate(MAQUINAS):
            total_un = df_sem[df_sem["maquina"] == m]["qtd"].sum()
            total_cargas = total_un / CARGA_UNIDADE
            with c_m[i]:
                with st.container(border=True):
                    st.metric(label=f"{m.upper()}", value=f"{total_cargas:.1f} Cargas")
                    st.caption(f"Total: {int(total_un)} un")

with aba4: # Catálogo Preservado
    st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conectar()), use_container_width=True)
