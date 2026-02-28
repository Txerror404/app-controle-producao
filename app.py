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
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

# --- CSS Customizado para Melhoria Visual ---
st.markdown("""
<style>
    .main-title {
        text-align: center;
        background: linear-gradient(90deg, #2c3e50, #4ca1af);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem !important;
        margin-bottom: 2rem;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    .card-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
    .card-machine { font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px; }
    .card-status { font-size: 1.5rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

def tela_login():
    st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Acesso Restrito")
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
def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, pedido TEXT, item TEXT, 
            inicio TEXT, fim TEXT, status TEXT, 
            qtd REAL, vinculo_id INTEGER
        )""")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")

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
        df["h_ini"] = df["inicio"].dt.strftime('%H:%M')
        df["h_fim"] = df["fim"].dt.strftime('%H:%M')
        df["rotulo_barra"] = df.apply(
            lambda r: "SETUP" if r['status'] == "Setup" 
            else f"<b>{r['pedido']}</b><br>QUANT: {int(r['qtd'])}", axis=1
        )
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

# ===============================
# 4. SIDEBAR
# ===============================
with st.sidebar:
    st.markdown("## 📊 Painel de Controle")
    st.markdown(f"### Usuário: **{'ADMIN' if is_admin else 'OPERADOR'}**")
    st.markdown(f"**⏱️ Relógio:** {agora.strftime('%H:%M:%S')}")
    st.markdown("---")
    df_exp = carregar_dados()
    if not df_exp.empty:
        csv = df_exp.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Dados (CSV)", csv, "pcp_william.csv", "text/csv")
    if st.button("Sair do Sistema", use_container_width=True):
        st.session_state.auth_ok = False
        st.rerun()

# ===============================
# 5. ABAS PRINCIPAIS
# ===============================
st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançamentos", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Carga"])

# --- ABA 1: LANÇAMENTOS ---
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
                qtd_n = st.number_input("Quantidade", value=2380)
                set_n = st.number_input("Setup Automático (min)", value=30)
                sug = proximo_horario(maq_s); c1, c2 = st.columns(2)
                dat_n = c1.date_input("Data Início", sug.date(), key="d_n"); hor_n = c2.time_input("Hora Início", sug.time(), key="h_n")
                if st.form_submit_button("Confirmar Lançamento", use_container_width=True):
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
                        st.rerun()
    with col_b:
        with st.container(border=True):
            st.markdown("### ⚙️ Setup/Manutenção")
            with st.form("f_new_set"):
                maq_av = st.selectbox("Máquina ", MAQUINAS); desc_av = st.text_input("Motivo"); dur_av = st.number_input("Minutos", value=60)
                sug_av = proximo_horario(maq_av); c3, c4 = st.columns(2)
                d_av = c3.date_input("Data ", sug_av.date(), key="d_a"); h_av = c4.time_input("Hora ", sug_av.time(), key="h_a")
                if st.form_submit_button("Lançar Setup", use_container_width=True):
                    i_av = datetime.combine(d_av, h_av); f_av = i_av + timedelta(minutes=dur_av)
                    with conectar() as conn:
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_av, "SETUP", desc_av, i_av.strftime('%Y-%m-%d %H:%M:%S'), f_av.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0))
                    st.rerun()

# --- ABA 2: GANTT (CORREÇÃO DO ERRO DA ANOTAÇÃO) ---
with aba2:
    st.markdown("### 📊 Cronograma de Máquinas")
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "h_ini", "h_fim", "item", "qtd"],
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#95a5a6", "Executando": "#e67e22"}
        )
        
        # CORREÇÃO AQUI: Simplificação total para evitar o ValueError
        fig.add_vline(x=agora, line_dash="dash", line_color="#e74c3c", line_width=2)
        fig.add_annotation(x=agora, y=1, text=f"AGORA: {agora.strftime('%H:%M')}", 
                           showarrow=False, yref="paper", xanchor="left", 
                           font=dict(color="#e74c3c", size=14))
        
        fig.update_traces(textposition='inside', insidetextanchor='start',
                         hovertemplate="<b>%{customdata[0]}</b><br>Início : %{customdata[1]}<br>Fim: %{customdata[2]}<br>Cód: %{customdata[3]}<br>Qtd: %{customdata[4]}<extra></extra>")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(legend=dict(orientation="h", y=-0.2), margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # Cards de Status
    st.markdown("---")
    cols_st = st.columns(len(MAQUINAS))
    for i, m in enumerate(MAQUINAS):
        df_m = df_g[(df_g["maquina"] == m) & (df_g["status"] != "Concluído")] if not df_g.empty else pd.DataFrame()
        if df_m.empty: color, icon, status = "#f39c12", "⚠️", "LIVRE"
        elif not df_m[df_m["fim"] < agora].empty: color, icon, status = "#e74c3c", "🚨", "ATRASO"
        else: color, icon, status = "#2ecc71", "✅", "EM DIA"
        with cols_st[i]:
            st.markdown(f'<div class="status-card" style="background-color: {color};"><span class="card-icon">{icon}</span><span class="card-machine">{m}</span><br><span class="card-status">{status}</span></div>', unsafe_allow_html=True)

# --- ABA 3: GERENCIAR (CONGELADA) ---
with aba3:
    st.markdown("### ⚙️ Gestão de Ordens")
    df_ger = carregar_dados()
    t_p, t_c = st.tabs(["⚡ Em Aberto", "✅ Histórico"])
    with t_p:
        if not df_ger.empty:
            df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values("inicio")
            for _, r in df_ab.iterrows():
                if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
                with st.expander(f"🛠️ {r['maquina']} | {r['pedido']}"):
                    c1, c2, c3 = st.columns([1, 1.2, 1.2])
                    with c1:
                        st.write(f"**Item:** {r['item']}")
                        if st.button("✅ CONCLUIR", key=f"c_{r['id']}", use_container_width=True):
                            with conectar() as c:
                                c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                                c.execute("UPDATE agenda SET status='Concluído' WHERE vinculo_id=?", (r['id'],))
                            st.rerun()
                        if is_admin and st.button("🗑️ EXCLUIR", key=f"e_{r['id']}", use_container_width=True):
                            with conectar() as c:
                                c.execute("DELETE FROM agenda WHERE id=?", (r['id'],)); c.execute("DELETE FROM agenda WHERE vinculo_id=?", (r['id'],))
                            st.rerun()
                    with c2:
                        if is_admin:
                            st.markdown("**🔄 Tempo/Data**")
                            nd = st.date_input("Data", r['inicio'].date(), key=f"d_e_{r['id']}")
                            nh = st.time_input("Hora", r['inicio'].time(), key=f"t_e_{r['id']}")
                            if st.button("Mover Tudo", key=f"m_e_{r['id']}", use_container_width=True):
                                ni = datetime.combine(nd, nh); ds = (ni - r['inicio']).total_seconds(); nf = r['fim'] + (ni - r['inicio'])
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (ni.strftime('%Y-%m-%d %H:%M:%S'), nf.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio = datetime(inicio, ? || ' seconds'), fim = datetime(fim, ? || ' seconds') WHERE vinculo_id = ?", (ds, ds, r['id']))
                                st.rerun()
                    with c3:
                        if is_admin:
                            st.markdown("**📦 Quantidade**")
                            nova_qtd = st.number_input("Nova Qtd", value=float(r['qtd']), key=f"q_e_{r['id']}")
                            if st.button("Atualizar Qtd", key=f"bq_e_{r['id']}", use_container_width=True):
                                n_fim = r['inicio'] + timedelta(hours=nova_qtd/CADENCIA_PADRAO)
                                s_dif = (n_fim - r['fim']).total_seconds()
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET qtd=?, fim=? WHERE id=?", (nova_qtd, n_fim.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio = ?, fim = datetime(fim, ? || ' seconds') WHERE vinculo_id = ?", (n_fim.strftime('%Y-%m-%d %H:%M:%S'), s_dif, r['id']))
                                st.rerun()
    with t_c:
        if not df_ger.empty: st.dataframe(df_ger[df_ger["status"] == "Concluído"].sort_values("fim", ascending=False), use_container_width=True)

# --- ABA 4 e 5: CATÁLOGO E DASHBOARD (PRESERVADOS) ---
with aba4:
    if is_admin:
        with st.form("f_c"):
            c1, c2, c3 = st.columns(3); co = c1.text_input("Código"); de = c2.text_input("Descrição"); cl = c3.text_input("Cliente")
            if st.form_submit_button("Salvar Produto", use_container_width=True):
                with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (co, de, cl)); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conectar()), use_container_width=True)

with aba5:
    df_dash = carregar_dados()
    if not df_dash.empty:
        df_ab = df_dash[df_dash["status"] != "Concluído"]
        c_m = st.columns(len(MAQUINAS))
        for i, m in enumerate(MAQUINAS):
            hrs = ((df_ab[df_ab["maquina"] == m]["fim"] - df_ab[df_ab["maquina"] == m]["inicio"]).dt.total_seconds() / 3600).sum()
            c_m[i].metric(label=f"{m.upper()}", value=f"{hrs:.1f} h")
            st.progress(min(hrs / 120, 1.0))
