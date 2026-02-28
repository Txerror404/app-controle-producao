import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURAÇÕES GERAIS
# =================================================================
st.set_page_config(page_title="PCP Industrial Master", layout="wide")
st_autorefresh(interval=120000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = "sarita@deco.com.br"

MAQUINAS_SERIGRAFIA = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 22)] 
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"

# CSS PERSONALIZADO (Layout e Botões)
st.markdown("""
    <style>
        .block-container {padding-top: 1rem;}
        .modebar-container { top: 0 !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #1e1e1e; border-radius: 5px; padding: 5px 20px; color: white;
        }
        .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. BANCO DE DADOS
# =================================================================
def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, pedido TEXT, item TEXT, 
            inicio TEXT, fim TEXT, status TEXT, 
            qtd REAL, vinculo_id INTEGER
        )
    """)

@st.cache_data(ttl=600)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL)
        df.columns = df.columns.str.strip()
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str)
        df['cliente'] = df['CLIENTE'].astype(str)
        df['qtd_carga'] = pd.to_numeric(df['QTD/CARGA'].astype(str).str.replace(',', '.'), errors='coerce').fillna(CARGA_UNIDADE)
        return df.fillna('N/A')
    except: return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    conn.close()
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

# =================================================================
# 3. LOGIN
# =================================================================
if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if not st.session_state.auth_ok:
    st.title("🏭 Login PCP")
    email = st.text_input("E-mail:").lower().strip()
    if st.button("Entrar"):
        if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]:
            st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

# =================================================================
# 4. FUNÇÃO DO GRÁFICO E STATUS
# =================================================================
def renderizar_setor(lista_maquinas, altura=500):
    df_all = carregar_dados()
    if df_all.empty:
        st.info("Nenhuma OP lançada para este setor.")
        return

    df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
    if df_g.empty:
        st.info("Sem dados para estas máquinas.")
        return

    # Definir status de execução em tempo real
    df_g["status_cor"] = df_g["status"]
    df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"

    fig = px.timeline(
        df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
        category_orders={"maquina": lista_maquinas},
        color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
    )

    # Marcações visuais solicitadas
    fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor='rgba(255,255,255,0.12)', zeroline=False)
    fig.update_traces(textposition='inside', insidetextanchor='start', width=0.9)
    fig.update_xaxes(type='date', range=[agora - timedelta(hours=2), agora + timedelta(hours=36)], dtick=10800000, tickformat="%H:%M\n%d/%m")
    
    # Linha de AGORA e Relógio no rodapé
    fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
    fig.add_annotation(x=agora, y=-0.15, text=f"AGORA: {agora.strftime('%H:%M')}", showarrow=False, xref="x", yref="paper", font=dict(color="red", size=12, family="Arial Black"), bgcolor="black")

    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=80), bargap=0.02, legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

    # INDICADORES DE STATUS (O que você sentiu falta)
    st.markdown("### 📊 Status das Máquinas")
    c1, c2, c3, c4 = st.columns(4)
    
    atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
    em_uso = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído")]["maquina"].nunique()
    total_maq = len(lista_maquinas)
    
    c1.metric("🚨 OPs Atrasadas", atrasadas)
    c2.metric("⚙️ Em Produção", em_uso)
    c3.metric("💤 Ociosas", total_maq - em_uso)
    c4.metric("📈 Ocupação", f"{(em_uso/total_maq)*100:.1f}%")
    st.divider()

# =================================================================
# 5. ABAS E LÓGICA
# =================================================================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"])

with aba1:
    df_prod = carregar_produtos_google()
    with st.form("form_lancar"):
        c1, c2 = st.columns(2)
        maq = c1.selectbox("Máquina", TODAS_MAQUINAS)
        item_id = c1.selectbox("Produto (ID)", df_prod['id_item'].tolist())
        op = c2.text_input("Número da OP")
        
        info = df_prod[df_prod['id_item'] == item_id].iloc[0]
        qtd = st.number_input("Quantidade", value=int(info['qtd_carga']))
        setup = st.number_input("Setup (minutos)", value=30)
        
        sugestao = proximo_horario(maq)
        d_ini = st.date_input("Data de Início", sugestao.date())
        h_ini = st.time_input("Hora de Início", sugestao.time())
        
        if st.form_submit_button("🚀 AGENDAR PRODUÇÃO"):
            ini = datetime.combine(d_ini, h_ini)
            fim = ini + timedelta(hours=qtd/CADENCIA_PADRAO)
            with conectar() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                           (maq, f"{info['cliente']} | {op}", item_id, ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd))
                if setup > 0:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                (maq, f"SETUP {op}", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), (fim + timedelta(minutes=setup)).strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
            st.success("Agendado!"); st.rerun()

with aba2: renderizar_setor(MAQUINAS_SERIGRAFIA, 450)
with aba3: renderizar_setor(MAQUINAS_SOPRO, 900)

with aba4:
    st.subheader("⚙️ Painel de Controle (Admin)")
    df_edit = carregar_dados()
    if not df_edit.empty:
        for _, r in df_edit[df_edit["status"] != "Concluído"].sort_values("inicio").iterrows():
            with st.expander(f"📌 {r['maquina']} - {r['pedido']}"):
                col1, col2, col3 = st.columns([2,2,1])
                # Função de reprogramar sem deletar
                n_data = col1.date_input("Nova Data", r['inicio'].date(), key=f"d{r['id']}")
                n_hora = col2.time_input("Nova Hora", r['inicio'].time(), key=f"h{r['id']}")
                
                if st.button("💾 Salvar Alteração", key=f"sv{r['id']}"):
                    novo_ini = datetime.combine(n_data, n_hora)
                    duracao = r['fim'] - r['inicio']
                    novo_fim = novo_ini + duracao
                    with conectar() as c:
                        c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (novo_ini.strftime('%Y-%m-%d %H:%M:%S'), novo_fim.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                    st.rerun()
                
                if col3.button("✅ Ok", key=f"ok{r['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                    st.rerun()
                if col3.button("🗑️ Deletar", key=f"del{r['id']}"):
                    with conectar() as c: c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (r['id'], r['id']))
                    st.rerun()

with aba5: st.dataframe(carregar_produtos_google(), use_container_width=True)
with aba6:
    df_c = carregar_dados()
    if not df_c.empty:
        pendentes = df_c[(df_c["status"] == "Pendente") & (df_c["maquina"].str.contains("Sopro"))]
        st.metric("Total Cargas Pendentes", f"{pendentes['qtd'].sum()/CARGA_UNIDADE:.1f}")
        st.table(pendentes[["maquina", "pedido", "qtd"]])

st.caption(f"v5.5 | PCP Industrial | {agora}")
