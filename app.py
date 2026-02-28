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
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

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
        df["rotulo_barra"] = df.apply(lambda r: "SET.UP" if r['status'] == "Setup" else f"{r['pedido']}<br>QUANT: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

# --- LOGIN ---
if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email: st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

is_admin = st.session_state.user_email == ADMIN_EMAIL

# ===============================
# 2. CABEÇALHO PROFISSIONAL (O ESPAÇO MARCADO)
# ===============================
st.markdown("""
    <div style="background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 10px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 28px;">
            📊 CONTROLE DINÂMICO DE PRODUÇÃO <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
        <p style="color: #AAAAAA; margin: 5px 0 0 0; font-size: 14px;">Monitoramento em Tempo Real - Cronograma de Máquinas</p>
    </div>
    <hr style="margin-top: 0; margin-bottom: 20px; border: 0.5px solid #333;">
    """, unsafe_allow_html=True)

# ===============================
# 3. INTERFACE DE ABAS
# ===============================
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançamentos", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Cargas"])

# ABA 2: GANTT (O CORAÇÃO DO SISTEMA)
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "h_ini", "h_fim", "item", "qtd"],
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
        
        # ESCALA DE 2 DIAS
        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=2), agora + timedelta(hours=46)],
            dtick=10800000, # 3 horas
            showgrid=True, gridcolor='rgba(255,255,255,0.05)',
            tickformat="%d/%m\n%H:%M"
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        
        # LINHA AGORA
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        # RELÓGIO AGORA (POSIÇÃO ALTA E LIMPA)
        fig.add_annotation(
            x=agora, y=1.1, 
            text=f"AGORA: {agora.strftime('%H:%M')}", 
            showarrow=False, yref="paper", 
            font=dict(color="#FF4B4B", size=18, family="Arial Black")
        )
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            width=0.85, 
            hovertemplate="<b>Pedido: %{customdata[0]}</b><br>Qtd: %{customdata[4]}<extra></extra>"
        )
        
        fig.update_layout(
            height=500,
            bargap=0.05,
            margin=dict(l=10, r=10, t=80, b=10),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)

# --- RESTANTE DAS ABAS (CÓDIGO INTEGRAL) ---
with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.subheader("Programar Produção")
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
                if st.form_submit_button("Lançar Ordem", use_container_width=True):
                    if ped_n and p_sel:
                        ini = datetime.combine(dat_n, hor_n); fim = ini + timedelta(hours=qtd_n/CADENCIA_PADRAO)
                        with conectar() as conn:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)", (maq_s, f"{cli_n} | {ped_n}", p_sel.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                            p_id = cur.lastrowid
                            if set_n > 0:
                                f_s = fim + timedelta(minutes=set_n)
                                conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)", (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, p_id))
                        st.rerun()

with aba3:
    df_ger = carregar_dados()
    if not df_ger.empty:
        df_ab = df_ger[df_ger["status"] != "Concluído"].sort_values(["maquina", "inicio"])
        for _, r in df_ab.iterrows():
            if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
            with st.expander(f"📦 {r['maquina']} | {r['pedido']}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("CONCLUIR", key=f"c_{r['id']}", use_container_width=True):
                        with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", (r['id'], r['id'])); st.rerun()
                with c2:
                    if is_admin:
                        nd = st.date_input("Data", r['inicio'].date(), key=f"d_{r['id']}"); nh = st.time_input("Hora", r['inicio'].time(), key=f"t_{r['id']}")
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

with aba4: st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conectar()), use_container_width=True)

with aba5:
    st.subheader(f"Total de Cargas da Semana (Base: {CARGA_UNIDADE} un)")
    df_c = carregar_dados()
    if not df_c.empty:
        inicio_sem = agora - timedelta(days=agora.weekday())
        df_sem = df_c[(df_c["inicio"] >= inicio_sem) & (df_c["status"] != "Concluído") & (df_c["status"] != "Setup")]
        cols = st.columns(len(MAQUINAS))
        for i, m in enumerate(MAQUINAS):
            total_un = df_sem[df_sem["maquina"] == m]["qtd"].sum()
            cols[i].metric(f"{m.upper()}", f"{total_un / CARGA_UNIDADE:.1f} Cargas")
