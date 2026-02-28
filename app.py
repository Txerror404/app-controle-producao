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

# URL da sua planilha publicada
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

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

# ===============================
# FUNÇÃO PARA CARREGAR PRODUTOS DO GOOGLE SHEETS
# ===============================
@st.cache_data(ttl=300)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL, sep=',', encoding='utf-8')
        df.columns = df.columns.str.strip()
        if 'ID_ITEM' not in df.columns:
            return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])
        
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip() if 'DESCRIÇÃO_1' in df.columns else ''
        
        if 'CLIENTE' in df.columns:
            df['cliente'] = df['CLIENTE'].astype(str).str.strip().replace('nan', 'N/A')
        else:
            df['cliente'] = 'N/A'
            
        if 'QTD/CARGA' in df.columns:
            df['qtd_carga'] = pd.to_numeric(df['QTD/CARGA'].astype(str).str.replace(',', '.'), errors='coerce').fillna(CARGA_UNIDADE)
        else:
            df['qtd_carga'] = CARGA_UNIDADE
            
        return df.fillna('N/A')
    except Exception as e:
        st.error(f"Erro planilha: {e}")
        return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])

if 'df_produtos' not in st.session_state:
    st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

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
            else: st.error("E-mail não autorizado.")
    st.stop()

st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-family: 'Segoe UI', sans-serif;">
            📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
        <p style="color: #888; margin: 5px 0 0 0;">👤 {st.session_state.user_email}</p>
    </div>
    """, unsafe_allow_html=True)

aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançar OP", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📋 Produtos (Google)", "📈 Cargas"])

# ABA 2 - GANTT
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        fig = px.timeline(df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
                         category_orders={"maquina": MAQUINAS},
                         color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"})
        fig.update_xaxes(type='date', range=[agora - timedelta(hours=2), agora + timedelta(hours=48)], dtick=10800000, tickformat="%d/%m\n%H:%M")
        fig.update_yaxes(autorange="reversed", title="")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.update_layout(height=500, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
        # Cards de apoio
        atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
        st.metric("🚨 OPs ATRASADAS", f"{atrasadas} itens")

# ABA 1 - LANÇAR
with aba1:
    with st.container(border=True):
        st.subheader("➕ Lançar Nova Ordem de Produção")
        col1, col2 = st.columns(2)
        with col1:
            maquina_sel = st.selectbox("🏭 Máquina", MAQUINAS)
            id_item_sel = st.selectbox("📌 ID_ITEM", df_produtos['id_item'].tolist()) if not df_produtos.empty else None
            info = df_produtos[df_produtos['id_item'] == id_item_sel].iloc[0] if id_item_sel else {}
        with col2:
            op_num = st.text_input("🔢 Número da OP")
            cliente_in = st.text_input("👥 Cliente", value=info.get('cliente', 'N/A'), disabled=True)
            desc_in = st.text_input("📝 Descrição", value=info.get('descricao', ''), disabled=True)
        
        col3, col4, col5 = st.columns(3)
        qtd = col3.number_input("📊 Quantidade", min_value=1, value=int(info.get('qtd_carga', CARGA_UNIDADE)) if id_item_sel else int(CARGA_UNIDADE))
        setup_min = col4.number_input("⏱️ Setup (min)", min_value=0, value=30)
        sugestao = proximo_horario(maquina_sel)
        data_ini = col5.date_input("📅 Início", sugestao.date())
        hora_ini = col5.time_input("⏰ Hora", sugestao.time())
        
        if st.button("🚀 LANÇAR PRODUÇÃO", type="primary", use_container_width=True):
            if op_num and id_item_sel:
                inicio = datetime.combine(data_ini, hora_ini)
                fim_prod = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)
                with conectar() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                (maquina_sel, f"{cliente_in} | OP:{op_num}", id_item_sel, inicio.strftime('%Y-%m-%d %H:%M:%S'), fim_prod.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd))
                    if setup_min > 0:
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                    (maquina_sel, f"SETUP OP:{op_num}", "Ajuste", fim_prod.strftime('%Y-%m-%d %H:%M:%S'), (fim_prod + timedelta(minutes=setup_min)).strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
                st.success("✅ Lançado!"); st.rerun()

# ABA 3 - GERENCIAR (CORRIGIDA)
with aba3:
    st.subheader("⚙️ Gerenciar OPs")
    df_ger = carregar_dados()
    if not df_ger.empty:
        for _, prod in df_ger[df_ger["status"] == "Pendente"].sort_values("inicio").iterrows():
            with st.expander(f"📦 {prod['maquina']} | {prod['pedido']}"):
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**Período:** {prod['inicio'].strftime('%d/%m %H:%M')} às {prod['fim'].strftime('%H:%M')}")
                col_a.write(f"**Qtd:** {int(prod['qtd'])} unidades")
                if col_b.button("✅ Concluir", key=f"c_{prod['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", (prod['id'], prod['id']))
                    st.rerun()
                if col_b.button("🗑️ Apagar", key=f"d_{prod['id']}"):
                    with conectar() as c: c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (prod['id'], prod['id']))
                    st.rerun()

# ABA 4 - PRODUTOS
with aba4:
    st.subheader("📋 Catálogo")
    st.dataframe(df_produtos, use_container_width=True)

# ABA 5 - CARGAS
with aba5:
    st.subheader(f"📈 Cargas (Base: {CARGA_UNIDADE})")
    df_c = carregar_dados()
    if not df_c.empty:
        df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        cols = st.columns(4)
        for i, m in enumerate(MAQUINAS):
            total = df_p[df_p["maquina"] == m]["qtd"].sum()
            cols[i].metric(m.upper(), f"{total/CARGA_UNIDADE:.1f} cargas")

st.divider()
st.caption(f"🕒 Atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')}")
