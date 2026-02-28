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
OPERACIONAL_EMAIL = "sarita@deco.com.br"
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

# Criar tabelas se não existirem
with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, 
            pedido TEXT, 
            item TEXT, 
            inicio TEXT, 
            fim TEXT, 
            status TEXT, 
            qtd REAL, 
            vinculo_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            codigo TEXT PRIMARY KEY, 
            descricao TEXT, 
            cliente TEXT
        )
    """)

def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}", 
            axis=1
        )
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# --- LOGIN ---
if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]: 
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("E-mail não autorizado.")
    st.stop()

# ===============================
# 2. TÍTULO PROFISSIONAL
# ===============================
st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-family: 'Segoe UI', sans-serif;">
            📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
        <p style="color: #888; margin: 5px 0 0 0;">👤 Usuário: {st.session_state.user_email}</p>
    </div>
    """, unsafe_allow_html=True)

# ===============================
# 3. INTERFACE DE ABAS
# ===============================
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançar OP", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Cargas"])

# ===============================
# ABA 2 - GANTT (RÉGUA DE 9 HORAS)
# ===============================
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "qtd", "item"],
            color_discrete_map={
                "Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"
            }
        )

        # AJUSTE DA RÉGUA CONFORME SOLICITADO: DATA A CADA 9 HORAS
        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=2), agora + timedelta(hours=48)],
            dtick=32400000, # 9 HORAS (9 * 60 * 60 * 1000ms)
            tickformat="%d/%m\n%H:%M", # Mostra Data e Hora em cada um dos pontos de 9h
            gridcolor='rgba(255,255,255,0.08)',
            showgrid=True,
            tickfont=dict(size=10, color="#AAAAAA")
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        fig.add_annotation(
            x=agora, y=1.1, 
            text=f"🔴 AGORA: {agora.strftime('%H:%M')}", 
            showarrow=False, yref="paper", 
            font=dict(color="#FF4B4B", size=15, family="Arial Black"),
            bgcolor="rgba(0,0,0,0.6)", borderpad=4
        )
        
        fig.update_traces(
            textposition='inside', insidetextanchor='start',
            width=0.85, 
            hovertemplate="<b>OP: %{customdata[0]}</b><br>Produto: %{customdata[2]}<br>Qtd: %{customdata[1]}<extra></extra>"
        )
        
        fig.update_layout(
            height=500, bargap=0.1,
            margin=dict(l=10, r=10, t=90, b=10),
            legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("📅 Régua configurada para marcação a cada 9 horas.")
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

# Manutenção das funcionalidades de Lançamento (Aba 1)
with aba1:
    with st.container(border=True):
        st.subheader("➕ Lançar Nova Ordem de Produção")
        df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
        
        col1, col2 = st.columns(2)
        with col1:
            maquina_sel = st.selectbox("🏭 Máquina", MAQUINAS)
            if not df_p.empty:
                opcoes_prod = [f"{row['codigo']} - {row['descricao']}" for _, row in df_p.iterrows()]
                produto_sel = st.selectbox("📦 Produto", opcoes_prod)
                codigo_prod = produto_sel.split(" - ")[0]
                cliente_auto = df_p[df_p['codigo'] == codigo_prod]['cliente'].values[0]
            else:
                st.warning("⚠️ Cadastre produtos no catálogo")
                produto_sel = None; cliente_auto = ""

        with col2:
            op_num = st.text_input("🔢 Número da OP")
            cliente_in = st.text_input("👥 Cliente", value=cliente_auto)

        c3, c4, c5 = st.columns(3)
        qtd = c3.number_input("📊 Quantidade", min_value=1, value=int(CARGA_UNIDADE))
        setup_min = c4.number_input("⏱️ Setup (min)", value=30)
        sugestao = proximo_horario(maquina_sel)
        data_i = c5.date_input("📅 Data", sugestao.date())
        hora_i = c5.time_input("⏰ Hora", sugestao.time())

        if st.button("🚀 LANÇAR PRODUÇÃO", type="primary", use_container_width=True):
            if op_num and produto_sel:
                inicio = datetime.combine(data_i, hora_i)
                fim_p = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)
                with conectar() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                (maquina_sel, f"{cliente_in} | OP:{op_num}", codigo_prod, inicio.strftime('%Y-%m-%d %H:%M:%S'), fim_p.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd))
                    if setup_min > 0:
                        f_s = fim_p + timedelta(minutes=setup_min)
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                    (maquina_sel, f"SETUP OP:{op_num}", "Ajuste", fim_p.strftime('%Y-%m-%d %H:%M:%S'), f_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
                st.success("✅ OP lançada!"); st.rerun()

# ABA 3, 4 e 5 permanecem conforme seu código original de gerenciamento e catálogo...
with aba3:
    st.subheader("⚙️ Gerenciar OPs")
    df_ger = carregar_dados()
    if not df_ger.empty:
        for _, prod in df_ger[df_ger["status"] == "Pendente"].sort_values("inicio").iterrows():
            with st.expander(f"📦 {prod['maquina']} | {prod['pedido']}"):
                if st.button("✅ Concluir", key=f"conc_{prod['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", (prod['id'], prod['id'])); st.rerun()

with aba4:
    st.subheader("📦 Catálogo")
    df_prod_cat = pd.read_sql_query("SELECT * FROM produtos", conectar())
    st.dataframe(df_prod_cat, use_container_width=True)

with aba5:
    st.subheader("📈 Cargas")
    df_c = carregar_dados()
    if not df_c.empty:
        cols = st.columns(4)
        for i, maq in enumerate(MAQUINAS):
            total = df_c[(df_c["maquina"] == maq) & (df_c["status"] == "Pendente")]["qtd"].sum()
            cols[i].metric(maq.upper(), f"{total/CARGA_UNIDADE:.1f} Cargas")

st.divider()
st.caption(f"🕒 Última atualização: {agora.strftime('%d/%m %H:%M:%S')} | Usuário: {st.session_state.user_email}")
