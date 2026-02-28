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
    /* Estilo do Título Principal */
    .main-title {
        text-align: center;
        background: linear-gradient(90deg, #2c3e50, #4ca1af);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem !important;
        margin-bottom: 2rem;
    }
    
    /* Estilo dos Subtítulos (Abas) */
    .stMarkdown h2 {
        font-weight: 700;
        color: #2c3e50;
        border-bottom: 2px solid #4ca1af;
        padding-bottom: 10px;
        margin-top: 1.5rem;
    }
    
    /* Estilo dos Títulos de Seção (h3) */
    .stMarkdown h3 {
        font-weight: 600;
        color: #7f8c8d;
        margin-top: 1rem;
    }

    /* Estilização dos Cards de Status abaixo do Gantt */
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

# Lógica de Login (Inalterada)
def tela_login():
    st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Acesso Restrito", unsafe_allow_html=True)
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
# 2. BANCO DE DADOS (Inalterado)
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
# 3. FUNÇÕES DE APOIO (Inalteradas)
# ===============================
def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["hora_ini"] = df["inicio"].dt.strftime('%H:%M')
        df["hora_fim"] = df["fim"].dt.strftime('%H:%M')
        # CORREÇÃO DO TEXTO DENTRO DA BARRA (Duas linhas)
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
# 4. SIDEBAR (Tipografia Melhorada)
# ===============================
with st.sidebar:
    st.markdown("## 📊 Painel de Controle", unsafe_allow_html=True)
    st.markdown(f"### Usuário: **{'ADMIN' if is_admin else 'OPERADOR'}**", unsafe_allow_html=True)
    st.markdown(f"**⏱️ Relógio:** {agora.strftime('%H:%M:%S')}", unsafe_allow_html=True)
    st.markdown(f"**📅 Data:** {agora.strftime('%d/%m/%Y')}", unsafe_allow_html=True)
    st.markdown("---")
    
    df_exp = carregar_dados()
    if not df_exp.empty:
        st.markdown("### 📥 Backup", unsafe_allow_html=True)
        csv = df_exp.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Dados (CSV)", csv, "pcp_william.csv", "text/csv", key="side_dl")
    
    st.markdown("---")
    if st.button("Sair do Sistema", use_container_width=True):
        st.session_state.auth_ok = False
        st.rerun()

# ===============================
# 5. ABAS PRINCIPAIS (Lógica Congelada, UI Melhorada)
# ===============================
# O Título Principal está definido fora das abas para ficar fixo no topo
st.markdown("<h1 class='main-title'>🏭 PCP William Industrial</h1>", unsafe_allow_html=True)

aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançamentos", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Carga"])

# --- ABA 1: LANÇAMENTOS (Preservada, organizada em contêineres) ---
with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True): # Melhoria Visual: Contêiner com borda
            st.markdown("### ➕ Programar Produção", unsafe_allow_html=True)
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
                sug = proximo_horario(maq_s)
                c1, c2 = st.columns(2)
                dat_n = c1.date_input("Data Início", sug.date(), key="d_new_l")
                hor_n = c2.time_input("Hora Início", sug.time(), key="h_new_l")
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
        with st.container(border=True): # Melhoria Visual: Contêiner com borda
            st.markdown("### ⚙️ Setup/Manutenção", unsafe_allow_html=True)
            with st.form("f_new_set"):
                maq_av = st.selectbox("Máquina ", MAQUINAS); desc_av = st.text_input("Motivo"); dur_av = st.number_input("Minutos", value=60)
                sug_av = proximo_horario(maq_av); c3, c4 = st.columns(2)
                d_av = c3.date_input("Data ", sug_av.date(), key="d_av_l"); h_av = c4.time_input("Hora ", sug_av.time(), key="h_av_l")
                if st.form_submit_button("Lançar Setup", use_container_width=True):
                    i_av = datetime.combine(d_av, h_av); f_av = i_av + timedelta(minutes=dur_av)
                    with conectar() as conn:
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_av, "SETUP", desc_av, i_av.strftime('%Y-%m-%d %H:%M:%S'), f_av.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0))
                    st.rerun()

# --- ABA 2: GANTT (Visual do Gráfico e Cards Melhorados) ---
with aba2:
    st.markdown("### 📊 Cronograma de Máquinas (Tempo Real)", unsafe_allow_html=True)
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", 
            color="status_cor", text="rotulo_barra", # Texto em duas linhas
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "hora_ini", "hora_fim", "item", "qtd"], # Card Limpo
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#95a5a6", "Executando": "#e67e22"} # Cores mais vibrantes
        )
        
        # RESTAURAÇÃO: Relógio na Linha Vermelha
        fig.add_vline(x=agora, line_dash="dash", line_color="#e74c3c", line_width=2)
        fig.add_annotation(x=agora, y=1, text=f"AGORA: {agora.strftime('%H:%M')}", showarrow=False, yref="paper", xanchor="left", font=dict(color="#e74c3c", size=14, font="Impact"))
        
        # Ajustes Visuais Internos do Gráfico
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            textfont=dict(size=12, color="white"), # Fonte interna branca
            # Card (Tooltip) Limpo conforme imagem 'exemplo'
            hovertemplate="<b>%{customdata[0]}</b><br>Início : %{customdata[1]}<br>Fim: %{customdata[2]}<br>Cód: %{customdata[3]}<br>Qtd: %{customdata[4]}<extra></extra>"
        )
        fig.update_yaxes(autorange="reversed", title="") # Tira título do eixo Y
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, title=""), # Legenda horizontal embaixo
            margin=dict(l=0, r=0, t=30, b=0) # Tira margens extras
        )
        st.plotly_chart(fig, use_container_width=True)

    # Cards de Status Abaixo do Gráfico (Visual robusto com HTML)
    st.markdown("---")
    cols_st = st.columns(len(MAQUINAS))
    for i, m in enumerate(MAQUINAS):
        df_m = df_g[(df_g["maquina"] == m) & (df_g["status"] != "Concluído")] if not df_g.empty else pd.DataFrame()
        if df_m.empty: 
            style = "background-color: #f39c12;" # Amarelo (Aviso)
            icon, status = "⚠️", "LIVRE"
        elif not df_m[df_m["fim"] < agora].empty: 
            style = "background-color: #e74c3c;" # Vermelho (Perigo)
            icon, status = "🚨", "ATRASO"
        else: 
            style = "background-color: #2ecc71;" # Verde (OK)
            icon, status = "✅", "EM DIA"
            
        with cols_st[i]:
            st.markdown(f"""
                <div class="status-card" style="{style}">
                    <span class="card-icon">{icon}</span>
                    <span class="card-machine">{m}</span><br>
                    <span class="card-status">{status}</span>
                </div>
                """, unsafe_allow_html=True)

# --- ABA 3: GERENCIAR (Inalterada, apenas organizada) ---
with aba3:
    st.markdown("### ⚙️ Gestão de Ordens de Produção", unsafe_allow_html=True)
    df_ger = carregar_dados()
    t_p, t_c = st.tabs(["⚡ Em Aberto", "✅ Histórico Concluído"])
    with t_p:
        if not df_ger.empty:
            df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values("inicio")
            for _, r in df_ab.iterrows():
                if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
                with st.expander(f"🛠️ {r['maquina']} | {r['pedido']}"):
                    c1, c2, c3 = st.columns([1, 1.2, 1.2])
                    with c1:
                        st.markdown(f"**Item:** `{r['item']}`", unsafe_allow_html=True)
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
                            st.markdown("**🔄 Ajustar Tempo/Data**", unsafe_allow_html=True)
                            nd = st.date_input("Data", r['inicio'].date(), key=f"d_ed_{r['id']}")
                            nh = st.time_input("Hora", r['inicio'].time(), key=f"t_ed_{r['id']}")
                            if st.button("Mover Tudo (Vinculado)", key=f"m_ed_{r['id']}", use_container_width=True):
                                ni = datetime.combine(nd, nh); ds = (ni - r['inicio']).total_seconds(); nf = r['fim'] + (ni - r['inicio'])
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (ni.strftime('%Y-%m-%d %H:%M:%S'), nf.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio = datetime(inicio, ? || ' seconds'), fim = datetime(fim, ? || ' seconds') WHERE vinculo_id = ?", (ds, ds, r['id']))
                                st.rerun()
                    with c3:
                        if is_admin:
                            st.markdown("**📦 Ajustar Quantidade**", unsafe_allow_html=True)
                            nova_qtd = st.number_input("Nova Qtd", value=float(r['qtd']), key=f"q_ed_{r['id']}")
                            if st.button("Atualizar Qtd (Recalcular)", key=f"bq_ed_{r['id']}", use_container_width=True):
                                novo_fim = r['inicio'] + timedelta(hours=nova_qtd/CADENCIA_PADRAO)
                                seg_dif = (novo_fim - r['fim']).total_seconds()
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET qtd=?, fim=? WHERE id=?", (nova_qtd, novo_fim.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                    c.execute("UPDATE agenda SET inicio = ?, fim = datetime(fim, ? || ' seconds') WHERE vinculo_id = ?", 
                                              (novo_fim.strftime('%Y-%m-%d %H:%M:%S'), seg_dif, r['id']))
                                st.rerun()
    with t_c:
        if not df_ger.empty: st.dataframe(df_ger[df_ger["status"] == "Concluído"].sort_values("fim", ascending=False), use_container_width=True)

# --- ABA 4: CATÁLOGO (Inalterada, apenas organizada) ---
with aba4:
    st.markdown("### 📦 Catálogo de Produtos e Clientes", unsafe_allow_html=True)
    if is_admin:
        with st.container(border=True):
            st.markdown("### ➕ Cadastrar Novo Item", unsafe_allow_html=True)
            with st.form("f_cat"):
                c1, c2, c3 = st.columns(3); co = c1.text_input("Código"); de = c2.text_input("Descrição"); cl = c3.text_input("Cliente")
                if st.form_submit_button("Salvar Produto no Catálogo", use_container_width=True):
                    with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (co, de, cl)); st.rerun()
    
    st.markdown("### Itens Cadastrados")
    st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conectar()), use_container_width=True)

# --- ABA 5: DASHBOARD (Inalterada) ---
with aba5:
    st.markdown("### 📉 Dashboard de Carga de Máquina", unsafe_allow_html=True)
    df_dash = carregar_dados()
    if not df_dash.empty:
        df_ab = df_dash[df_dash["status"] != "Concluído"]
        st.markdown(f"Horas Pendentes por Máquina (Base: {CADENCIA_PADRAO} un/h)")
        c_m = st.columns(len(MAQUINAS))
        for i, m in enumerate(MAQUINAS):
            hrs = ((df_ab[df_ab["maquina"] == m]["fim"] - df_ab[df_ab["maquina"] == m]["inicio"]).dt.total_seconds() / 3600).sum()
            c_m[i].metric(label=f"{m.upper()}", value=f"{hrs:.1f} h", delta=None, delta_color="normal")
            st.progress(min(hrs / 120, 1.0)) # Barra de progresso baseada em 120h semanais
