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

MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        # Rótulo das barras: CLIENTE | OP e QUANTIDADE na linha de baixo
        df["rotulo_barra"] = df.apply(lambda r: "SET.UP" if r['status'] == "Setup" else f"{r['pedido']}<br>QUANT: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 Sistema PCP</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail:").lower().strip()
        if st.button("Entrar", use_container_width=True):
            if email: st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

# ===============================
# 2. TÍTULO PROFISSIONAL (ESPAÇO MARCADO)
# ===============================
st.markdown("""
    <div style="background-color: #1E1E1E; padding: 12px; border-radius: 5px; border-bottom: 3px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 22px; font-family: 'Arial', sans-serif; letter-spacing: 1px;">
            📊 PAINEL DE CONTROLE DE PRODUÇÃO <span style="color: #FF4B4B;">|</span> CRONOGRAMA DE OP
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

        # --- AQUI ESTÁ A CORREÇÃO DA RÉGUA CONFORME A SUA IMAGEM ---
        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=2), agora + timedelta(hours=46)], # Janela de 2 dias
            dtick=10800000, # Fixado em 3 horas (3 * 60 * 60 * 1000ms)
            tickformat="%d/%m\n%H:%M", # DATA E HORA EM TODAS AS LINHAS
            showgrid=True, 
            gridcolor='rgba(255,255,255,0.1)',
            tickfont=dict(size=10, color="white")
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        
        # LINHA DO TEMPO ATUAL
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        # RELÓGIO NO TOPO
        fig.add_annotation(
            x=agora, y=1.1, 
            text=f"AGORA: {agora.strftime('%H:%M')}", 
            showarrow=False, yref="paper", 
            font=dict(color="#FF4B4B", size=18, family="Arial Black")
        )
        
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            width=0.85, # Barras grossas (Trilhos)
            hovertemplate="<b>OP: %{customdata[0]}</b><br>Qtd: %{customdata[1]}<extra></extra>"
        )
        
        fig.update_layout(
            height=500,
            bargap=0.05,
            margin=dict(l=10, r=10, t=80, b=10),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)

# As outras abas (Lançar OP, Gerenciar, etc.) seguem a mesma lógica funcional anterior.
with aba1:
    with st.container(border=True):
        st.subheader("Nova Ordem de Produção")
        df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
        with st.form("f_op"):
            m = st.selectbox("Máquina", MAQUINAS)
            p = st.selectbox("Produto", [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()])
            op = st.text_input("Nº da OP")
            cli = st.text_input("Cliente")
            qtd = st.number_input("Quantidade", value=CARGA_UNIDADE)
            sug = proximo_horario(m)
            d = st.date_input("Início", sug.date()); h = st.time_input("Hora", sug.time())
            if st.form_submit_button("Lançar"):
                ini = datetime.combine(d, h); fim = ini + timedelta(hours=qtd/CADENCIA_PADRAO)
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)", 
                                (m, f"{cli} | {op}", p.split(" | ")[0], ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd))
                st.rerun()

with aba3:
    df_ger = carregar_dados()
    if not df_ger.empty:
        for _, r in df_ger[df_ger["status"] != "Concluído"].iterrows():
            if r['status'] == "Setup": continue
            with st.expander(f"OP: {r['pedido']} ({r['maquina']})"):
                if st.button("Concluir", key=f"c_{r['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],)); st.rerun()

with aba5:
    st.subheader("Cargas")
    df_c = carregar_dados()
    if not df_c.empty:
        cols = st.columns(4)
        for i, m in enumerate(MAQUINAS):
            total = df_c[(df_c["maquina"] == m) & (df_c["status"] != "Concluído")]["qtd"].sum()
            cols[i].metric(m, f"{total/CARGA_UNIDADE:.1f}")
