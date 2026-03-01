import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURAÇÕES GERAIS E ESTILO (NÃO ALTERAR)
# =================================================================
st.set_page_config(page_title="PCP Industrial - SISTEMA COMPLETO", layout="wide")
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

st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 8px 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="color: white; margin: 0; font-size: 20px; font-family: 'Segoe UI', sans-serif;">📊 PCP <span style="color: #FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS</h2>
            <p style="color: #888; margin: 2px 0 0 0; font-size: 12px;">👤 Usuário: {st.session_state.user_email}</p>
        </div>
        <div style="text-align: center; border: 1px solid #FF4B4B; padding: 2px 15px; border-radius: 5px; background-color: #0E1117; min-width: 130px;">
            <h3 style="color: #FF4B4B; margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 22px; line-height: 1.2;">⏰ {agora.strftime('%H:%M:%S')}</h3>
            <p style="color: #aaa; margin: -2px 0 2px 0; font-size: 12px; border-top: 1px dashed #FF4B4B; padding-top: 2px;">{agora.strftime('%d/%m/%Y')}</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# =================================================================
# 2. BANCO DE DADOS E CARREGAMENTO
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
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
        df['cliente'] = df['CLIENTE'].astype(str).str.strip()
        df['qtd_carga'] = pd.to_numeric(df['QTD/CARGA'].astype(str).str.replace(',', '.'), errors='coerce').fillna(CARGA_UNIDADE)
        return df.fillna('N/A')
    except Exception as e:
        return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    conn.close()
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}", axis=1)
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty: return max(agora, df_maq["fim"].max())
    return agora

# =================================================================
# 3. SEGURANÇA E CABEÇALHO (RESTAURADO)
# =================================================================
if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]: 
                st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
    st.stop()

df_produtos = carregar_produtos_google()

st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 10px 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h2 style="color: white; margin: 0; font-size: 20px; font-family: 'Segoe UI', sans-serif;">📊 PCP <span style="color: #FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS</h2>
            <p style="color: #888; margin: 0; font-size: 12px;">👤 Usuário: {st.session_state.user_email}</p>
        </div>
        <div style="text-align: right; border: 1px solid #FF4B4B; padding: 2px 12px; border-radius: 5px; background-color: #0E1117;">
            <h3 style="color: #FF4B4B; margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 18px;">⏰ {agora.strftime('%H:%M:%S')}</h3>
            <p style="color: #888; margin: 0; font-size: 10px;">{agora.strftime('%d/%m/%Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =================================================================
# 4. GRÁFICOS E STATUS (RESTAURADO)
# =================================================================
def renderizar_setor(lista_maquinas, altura=500):
    df_all = carregar_dados()
    if df_all.empty:
        st.info("Nenhuma OP agendada.")
        return

    df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
    if df_g.empty:
        st.info("Sem dados para este setor.")
        return

    df_g["status_cor"] = df_g["status"]
    df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"

    fig = px.timeline(
        df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
        category_orders={"maquina": lista_maquinas},
        color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
    )

    fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False)
    fig.update_traces(textposition='inside', insidetextanchor='start', width=0.92)
    fig.update_xaxes(type='date', range=[agora - timedelta(hours=2), agora + timedelta(hours=36)], dtick=10800000, tickformat="%H:%M\n%d/%m")
    
    fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
    fig.add_annotation(x=agora, y=-0.18, text=f"AGORA: {agora.strftime('%H:%M')}", showarrow=False, xref="x", yref="paper", font=dict(color="red", size=13, family="Arial Black"), bgcolor="rgba(0,0,0,0.9)", bordercolor="red", borderpad=2)

    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=50, b=100), bargap=0.01, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})

    # CARDS DE STATUS ABAIXO DO GRÁFICO
    st.markdown("### 📊 Status do Setor")
    c1, c2, c3, c4 = st.columns(4)
    atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
    em_uso = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído")]["maquina"].nunique()
    total_setor = len(lista_maquinas)
    
    c1.metric("🚨 OPs Atrasadas", atrasadas)
    c2.metric("⚙️ Máquinas em Uso", em_uso)
    c3.metric("💤 Máquinas Livres", total_setor - em_uso)
    c4.metric("📈 Taxa de Ocupação", f"{(em_uso/total_setor)*100:.1f}%")
    st.divider()

# =================================================================
# 5. ABAS E LÓGICA DE NEGÓCIO
# =================================================================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"])

with aba1:
    with st.container(border=True):
        st.subheader("➕ Novo Lançamento")
        c1, c2 = st.columns(2)
        with c1:
            maq_sel = st.selectbox("🏭 Máquina destino", TODAS_MAQUINAS)
            item_sel = st.selectbox("📌 Selecione o ID_ITEM", df_produtos['id_item'].tolist())
            # BUSCA AUTOMÁTICA DE DESCRIÇÃO E CLIENTE (RESTAURADO)
            info_prod = df_produtos[df_produtos['id_item'] == item_sel].iloc[0] if not df_produtos.empty else {}
            desc_auto = info_prod.get('descricao', 'N/A')
            cli_auto = info_prod.get('cliente', 'N/A')
            carga_auto = info_prod.get('qtd_carga', CARGA_UNIDADE)
            
            st.text_input("📝 Descrição do Produto", value=desc_auto, disabled=True)
        
        with c2:
            op_num = st.text_input("🔢 Número da OP")
            st.text_input("👥 Cliente", value=cli_auto, disabled=True)
            qtd_lanc = st.number_input("📊 Quantidade Total", value=int(carga_auto))
        
        st.divider()
        c3, c4, c5 = st.columns(3)
        setup_min = c3.number_input("⏱️ Tempo de Setup (min)", value=30)
        sugestao_h = proximo_horario(maq_sel)
        data_ini = c4.date_input("📅 Data de Início", sugestao_h.date())
        hora_ini = c5.time_input("⏰ Hora de Início", sugestao_h.time())
        
        if st.button("🚀 CONFIRMAR E AGENDAR", type="primary", use_container_width=True):
            if op_num:
                inicio_dt = datetime.combine(data_ini, hora_ini)
                fim_dt = inicio_dt + timedelta(hours=qtd_lanc/CADENCIA_PADRAO)
                with conectar() as conn:
                    cur = conn.cursor()
                    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                               (maq_sel, f"{cli_auto} | {op_num}", item_sel, inicio_dt.strftime('%Y-%m-%d %H:%M:%S'), fim_dt.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_lanc))
                    if setup_min > 0:
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
                                    (maq_sel, f"SETUP {op_num}", "Ajuste", fim_dt.strftime('%Y-%m-%d %H:%M:%S'), (fim_dt + timedelta(minutes=setup_min)).strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
                    conn.commit()
                st.success("Lançamento concluído com sucesso!"); st.rerun()

with aba2: renderizar_setor(MAQUINAS_SERIGRAFIA, 450)
with aba3: renderizar_setor(MAQUINAS_SOPRO, 1000)

with aba4:
    st.subheader("⚙️ Gerenciamento e Reprogramação")
    df_ger = carregar_dados()
    if not df_ger.empty:
        is_admin = st.session_state.user_email == ADMIN_EMAIL
        for _, prod in df_ger[df_ger["status"].isin(["Pendente", "Setup"])].sort_values("inicio").iterrows():
            with st.expander(f"📌 {prod['maquina']} | {prod['pedido']}"):
                col1, col2, col3 = st.columns([2, 2, 1.2])
                
                # REPROGRAMAR (RESTAURADO)
                if is_admin:
                    n_data = col1.date_input("Nova Data", prod['inicio'].date(), key=f"d_{prod['id']}")
                    n_hora = col2.time_input("Nova Hora", prod['inicio'].time(), key=f"t_{prod['id']}")
                    if st.button("💾 Salvar Novo Horário", key=f"s_{prod['id']}"):
                        novo_i = datetime.combine(n_data, n_hora)
                        novo_f = novo_i + (prod['fim'] - prod['inicio'])
                        with conectar() as c:
                            c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (novo_i.strftime('%Y-%m-%d %H:%M:%S'), novo_f.strftime('%Y-%m-%d %H:%M:%S'), prod['id']))
                            c.commit()
                        st.rerun()
                
                if col3.button("✅ Finalizar OP", key=f"ok_{prod['id']}", use_container_width=True):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (prod['id'],)); c.commit()
                    st.rerun()
                if col3.button("🗑️ Deletar", key=f"del_{prod['id']}", use_container_width=True):
                    with conectar() as c: c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (prod['id'], prod['id'])); c.commit()
                    st.rerun()

with aba5: st.dataframe(df_produtos, use_container_width=True)

with aba6:
    df_c = carregar_dados()
    if not df_c.empty:
        df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        st.metric("Total Geral de Cargas Sopro", f"{df_p[df_p['maquina'].isin(MAQUINAS_SOPRO)]['qtd'].sum() / CARGA_UNIDADE:.1f}")
        st.table(df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)][["maquina", "pedido", "qtd"]])

st.divider()
st.caption(f"v5.8 | PCP Industrial William | Atualização em tempo real ativa")
