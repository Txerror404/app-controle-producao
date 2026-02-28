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
st.set_page_config(page_title="PCP Industrial v4.5", layout="wide")

# Refresh automático a cada 2 minutos
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

# CSS PARA POSICIONAMENTO PERSONALIZADO (MARCAÇÕES DO USUÁRIO)
st.markdown("""
    <style>
        .block-container {padding-top: 0.5rem;}
        /* Move botões do Plotly para o topo */
        .modebar-container { top: 0 !important; bottom: auto !important; }
        /* Estilização das abas */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #1e1e1e; border-radius: 4px; padding: 4px 12px;
        }
    </style>
""", unsafe_allow_html=True)

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

@st.cache_data(ttl=300)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL, sep=',', encoding='utf-8')
        df.columns = df.columns.str.strip()
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip() if 'DESCRIÇÃO_1' in df.columns else ''
        df['cliente'] = df['CLIENTE'].astype(str).str.strip() if 'CLIENTE' in df.columns else 'N/A'
        df['qtd_carga'] = pd.to_numeric(df['QTD/CARGA'].astype(str).str.replace(',', '.'), errors='coerce').fillna(CARGA_UNIDADE)
        return df.fillna('N/A')
    except: return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])

if 'df_produtos' not in st.session_state:
    st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

def carregar_dados():
    with conectar() as c: df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"]); df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]: 
                st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

# ===============================
# CABEÇALHO COMPACTO
# ===============================
st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 10px 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="color: white; margin: 0; font-size: 20px; font-family: 'Segoe UI', sans-serif;">
                📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP
            </h2>
            <p style="color: #888; margin: 0; font-size: 12px;">👤 {st.session_state.user_email}</p>
        </div>
        <div style="text-align: right; border: 1px solid #FF4B4B; padding: 2px 12px; border-radius: 5px; background-color: #0E1117;">
            <h3 style="color: #FF4B4B; margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 18px;">
                ⏰ {agora.strftime('%H:%M:%S')}
            </h3>
            <p style="color: #888; margin: 0; font-size: 10px;">{agora.strftime('%d/%m/%Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

aba1, aba2, aba6, aba3, aba4, aba5 = st.tabs(["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"])

# ===============================
# FUNÇÃO GANTT PERSONALIZADA
# ===============================
def plotar_gantt(lista_maquinas, height_grafico=500):
    df_all = carregar_dados()
    if not df_all.empty:
        df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
        if not df_g.empty:
            df_g["status_cor"] = df_g["status"]
            df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
            
            fig = px.timeline(
                df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
                category_orders={"maquina": lista_maquinas},
                color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
            )
            
            # Linhas Horizontais sólidas e Barras "Coladas"
            fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False)
            fig.update_traces(textposition='inside', insidetextanchor='start', width=0.92)

            fig.update_xaxes(
                type='date', range=[agora - timedelta(hours=2), agora + timedelta(hours=48)], 
                dtick=10800000, tickformat="%H:%M\n%d/%m", 
                gridcolor='rgba(255,255,255,0.05)', showgrid=True, tickfont=dict(size=10, color="white")
            )
            
            fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
            
            # Relógio "AGORA" no Rodapé
            fig.add_annotation(
                x=agora, y=-0.18, text=f"AGORA: {agora.strftime('%H:%M')}", 
                showarrow=False, xref="x", yref="paper", 
                font=dict(color="red", size=13, family="Arial Black"),
                bgcolor="rgba(0,0,0,0.9)", bordercolor="red", borderpad=2
            )
            
            fig.update_layout(
                height=height_grafico, margin=dict(l=10, r=10, t=50, b=100),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                bargap=0.01, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})

            # Indicadores
            st.markdown("---")
            atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
            maqs_em_uso = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído")]["maquina"].unique()
            ociosas = [m for m in lista_maquinas if m not in maqs_em_uso]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("🚨 OPs ATRASADAS", f"{atrasadas}")
            c2.metric("💤 MÁQUINAS OCIOSAS", f"{len(ociosas)}")
            if ociosas:
                c3.warning(f"{len(ociosas)} máquinas livres")
            else:
                c3.success("✅ Setor Ocupado")

with aba2: plotar_gantt(MAQUINAS_SERIGRAFIA, 450)
with aba6: plotar_gantt(MAQUINAS_SOPRO, 1100)

with aba1:
    with st.container(border=True):
        st.subheader("➕ Lançar OP")
        c1, c2 = st.columns(2)
        with c1:
            maquina_sel = st.selectbox("🏭 Máquina", TODAS_MAQUINAS)
            id_item_sel = st.selectbox("📌 ID_ITEM", df_produtos['id_item'].tolist()) if not df_produtos.empty else None
            info = df_produtos[df_produtos['id_item'] == id_item_sel].iloc[0] if id_item_sel else {}
        with c2:
            op_num = st.text_input("🔢 OP")
            st.text_input("📝 DESC", value=info.get('descricao', ''), disabled=True)
            st.text_input("👥 Cliente", value=info.get('cliente', 'N/A'), disabled=True)
        
        c3, c4, c5 = st.columns(3)
        qtd = c3.number_input("📊 Qtd", min_value=1, value=int(info.get('qtd_carga', CARGA_UNIDADE)) if id_item_sel else CARGA_UNIDADE)
        setup_min = c4.number_input("⏱️ Setup (min)", value=30)
        sugestao = proximo_horario(maquina_sel)
        data_ini = c5.date_input("📅 Data", sugestao.date()); hora_ini = c5.time_input("⏰ Hora", sugestao.time())
        
        if st.button("🚀 LANÇAR", type="primary", use_container_width=True):
            if op_num and id_item_sel:
                inicio = datetime.combine(data_ini, hora_ini); fim_prod = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)
                with conectar() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)", (maquina_sel, f"{info.get('cliente','N/A')} | {op_num}", id_item_sel, inicio.strftime('%Y-%m-%d %H:%M:%S'), fim_prod.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd))
                    if setup_min > 0: conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)", (maquina_sel, f"SETUP {op_num}", "Ajuste", fim_prod.strftime('%Y-%m-%d %H:%M:%S'), (fim_prod + timedelta(minutes=setup_min)).strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
                    conn.commit()
                st.rerun()

with aba3:
    st.subheader("⚙️ Painel de Ajuste Rápido (Reprogramar)")
    df_ger = carregar_dados()
    if not df_ger.empty:
        is_admin = st.session_state.user_email == ADMIN_EMAIL
        for _, prod in df_ger[df_ger["status"].isin(["Pendente", "Setup"])].sort_values("inicio").iterrows():
            with st.expander(f"📌 {prod['maquina']} | {prod['pedido']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                if is_admin:
                    n_data = col1.date_input("Nova Data", prod['inicio'].date(), key=f"d_{prod['id']}")
                    n_hora = col2.time_input("Nova Hora", prod['inicio'].time(), key=f"t_{prod['id']}")
                    if st.button("💾 Salvar Alteração", key=f"s_{prod['id']}"):
                        n_inicio = datetime.combine(n_data, n_hora)
                        n_fim = n_inicio + (prod['fim'] - prod['inicio'])
                        with conectar() as c:
                            c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", 
                                     (n_inicio.strftime('%Y-%m-%d %H:%M:%S'), n_fim.strftime('%Y-%m-%d %H:%M:%S'), prod['id']))
                            c.commit()
                        st.rerun()
                
                if col3.button("✅ Concluir", key=f"ok_{prod['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (prod['id'],)); c.commit()
                    st.rerun()
                if col3.button("🗑️ Excluir", key=f"del_{prod['id']}"):
                    with conectar() as c: c.execute("DELETE FROM agenda WHERE id=?", (prod['id'],)); c.commit()
                    st.rerun()

with aba4: st.dataframe(df_produtos, use_container_width=True)

with aba5:
    df_c = carregar_dados()
    if not df_c.empty:
        df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        st.metric("Total Sopro (Cargas)", f"{df_p[df_p['maquina'].isin(MAQUINAS_SOPRO)]['qtd'].sum() / CARGA_UNIDADE:.1f}")
        st.dataframe(df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)][["maquina", "pedido", "qtd"]], use_container_width=True)

st.divider()
st.caption(f"v4.5 | Refresh 2min | {agora.strftime('%H:%M:%S')}")
