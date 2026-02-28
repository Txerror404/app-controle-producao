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
st.set_page_config(page_title="PCP Industrial", layout="wide")
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
        df["rotulo_barra"] = df.apply(lambda r: "SET.UP" if r['status'] == "Setup" else f"{r['pedido']}<br>QUANT: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

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
# 2. TÍTULO PROFISSIONAL (ESPAÇO SUPERIOR)
# ===============================
st.markdown("""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-family: 'Segoe UI', sans-serif;">
            📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
    </div>
    """, unsafe_allow_html=True)

# ===============================
# 3. INTERFACE DE ABAS
# ===============================
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançar OP", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Cargas"])

with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "qtd"],
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )

        # CONFIGURAÇÃO DA LINHA DO TEMPO LIMPA (SÓ HORA NAS SEQUÊNCIAS)
        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=1), agora + timedelta(hours=47)],
            dtick=10800000, # 3 em 3 horas
            tickformatstops=[
                dict(dtickrange=[None, 1000 * 60 * 60 * 24], value="%H:%M"), # Menos de 24h: apenas Hora
                dict(dtickrange=[1000 * 60 * 60 * 24, None], value="%d/%m\n%H:%M") # Virada de dia: Data + Hora
            ],
            # Formato base para o primeiro tick
            tickformat="%d/%m\n%H:%M",
            gridcolor='rgba(255,255,255,0.05)',
            showgrid=True
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        fig.add_annotation(
            x=agora, y=1.12, 
            text=f"AGORA: {agora.strftime('%H:%M')}", 
            showarrow=False, yref="paper", 
            font=dict(color="#FF4B4B", size=18, family="Arial Black")
        )
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            width=0.82, 
            hovertemplate="<b>OP: %{customdata[0]}</b><br>Qtd: %{customdata[1]}<extra></extra>"
        )
        
        fig.update_layout(
            height=500,
            bargap=0.08,
            margin=dict(l=10, r=10, t=90, b=10),
            legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)

with aba1:
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.subheader("Programar Produção")
            df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
            with st.form("f_new_op"):
                maq_s = st.selectbox("Máquina", MAQUINAS)
                p_lista = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
                p_sel = st.selectbox("Produto", [""] + p_lista)
                op_n = st.text_input("Nº OP") # Nome atualizado
                cli_sug = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
                cli_n = st.text_input("Cliente", value=cli_sug)
                qtd_n = st.number_input("Quantidade", value=CARGA_UNIDADE)
                set_n = st.number_input("Setup Automático (min)", value=30)
                sug = proximo_horario(maq_s); c1, c2 = st.columns(2)
                dat_n = c1.date_input("Data Início", sug.date()); hor_n = c2.time_input("Hora Início", sug.time())
                
                if st.form_submit_button("Lançar Ordem de Produção", use_container_width=True):
                    if op_n and p_sel:
                        ini = datetime.combine(dat_n, hor_n); fim = ini + timedelta(hours=qtd_n/CADENCIA_PADRAO)
                        with conectar() as conn:
                            cur = conn.cursor()
                            cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)", 
                                        (maq_s, f"{cli_n} | {op_n}", p_sel.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                            p_id = cur.lastrowid
                            if set_n > 0:
                                f_s = fim + timedelta(minutes=set_n)
                                conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)", (maq_s, "SETUP", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, p_id))
                        st.rerun()

# Manutenção das demais funcionalidades (Gerenciar, Catálogo, Cargas)
with aba3:
    df_ger = carregar_dados()
    if not df_ger.empty:
        for _, r in df_ger[df_ger["status"] != "Concluído"].iterrows():
            if r['status'] == "Setup" and r['vinculo_id'] is not None: continue 
            with st.expander(f"📦 {r['maquina']} | {r['pedido']}"):
                if st.button("CONCLUIR", key=f"c_{r['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", (r['id'], r['id'])); st.rerun()

with aba5:
    st.subheader(f"Cargas Semanais (Ref: {CARGA_UNIDADE})")
    df_c = carregar_dados()
    if not df_c.empty:
        cols = st.columns(len(MAQUINAS))
        for i, m in enumerate(MAQUINAS):
            total = df_c[(df_c["maquina"] == m) & (df_c["status"] != "Concluído")]["qtd"].sum()
            cols[i].metric(m, f"{total/CARGA_UNIDADE:.1f} Cargas")
