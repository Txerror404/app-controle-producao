import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# =================================================================
# 1. CONFIGURAÇÕES GERAIS E ESTILO
# =================================================================
st.set_page_config(page_title="PCP Industrial - SISTEMA COMPLETO", layout="wide")
st_autorefresh(interval=120000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = ["sarita@will.com.br", "oneida@will.com.br"]

MAQUINAS_SERIGRAFIA = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]  # 16 MÁQUINAS
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"

st.markdown("""
    <style>
        .block-container {padding-top: 0.5rem;}
        .modebar-container { top: 0 !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #1e1e1e; border-radius: 5px; padding: 5px 20px; color: white;
        }
        .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. BANCO DE DADOS E CARREGAMENTO (ATUALIZADO COM METADADOS)
# =================================================================
def conectar(): 
    return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, pedido TEXT, item TEXT, 
            inicio TEXT, fim TEXT, status TEXT, 
            qtd REAL, vinculo_id INTEGER,
            criado_por TEXT, criado_em TEXT,
            alterado_por TEXT, alterado_em TEXT
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

# =================================================================
# FUNÇÃO CORRIGIDA PARA EVITAR SOBREPOSIÇÃO
# =================================================================
def proximo_horario(maq):
    """
    Retorna o próximo horário livre para a máquina,
    considerando o fim da última OP (produção ou setup)
    """
    df = carregar_dados()
    if not df.empty:
        # Filtra apenas eventos desta máquina que não estão concluídos
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup", "Manutenção"]))]
        if not df_maq.empty:
            # Pega o MAIOR fim (último evento)
            ultimo_fim = df_maq["fim"].max()
            # Retorna o maior entre agora e o fim do último evento
            return max(agora, ultimo_fim)
    return agora

# =================================================================
# 3. SEGURANÇA E CABEÇALHO
# =================================================================
if "auth_ok" not in st.session_state: 
    st.session_state.auth_ok = False
if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL] + OPERACIONAL_EMAIL: 
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()
    st.stop()

# Carregar produtos e armazenar no session_state
if 'df_produtos' not in st.session_state:
    with st.spinner("Sincronizando com Google Sheets..."):
        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

# CABEÇALHO
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
# 4. GRÁFICOS E STATUS (COM HOVER CORRIGIDO)
# =================================================================
def renderizar_setor(lista_maquinas, altura=500, pos_y_agora=-0.30):
    df_all = carregar_dados()
    if df_all.empty:
        st.info("Nenhuma OP agendada.")
        return

    df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
    if df_g.empty:
        st.info("Sem dados para este setor.")
        return

    # Status para cores
    df_g["status_cor"] = df_g["status"]
    df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] == "Pendente"), "status_cor"] = "Executando"
    
    # CRIAR COLUNA DE COR PERSONALIZADA
    df_g["cor_barra"] = df_g["status_cor"]
    df_g.loc[(df_g["fim"] < agora) & (df_g["status"] == "Pendente"), "cor_barra"] = "Atrasada"
    df_g.loc[df_g["status"] == "Setup", "cor_barra"] = "Setup"
    df_g.loc[df_g["status"] == "Manutenção", "cor_barra"] = "Manutenção"

    # FORMATAR DATAS PARA O HOVER (SOLUÇÃO CORRIGIDA)
    df_g["fim_formatado"] = df_g["fim"].dt.strftime('%d/%m %H:%M')
    df_g["ini_formatado"] = df_g["inicio"].dt.strftime('%d/%m %H:%M')

    fig = px.timeline(
        df_g, 
        x_start="inicio", 
        x_end="fim", 
        y="maquina", 
        color="cor_barra", 
        text="rotulo_barra",
        category_orders={"maquina": lista_maquinas},
        color_discrete_map={
            "Pendente": "#3498db", 
            "Concluído": "#2ecc71", 
            "Setup": "#7f7f7f",
            "Executando": "#ff7f0e",
            "Atrasada": "#FF4B4B",
            "Manutenção": "#9b59b6"
        },
        custom_data=["pedido", "item", "qtd", "ini_formatado", "fim_formatado"]
    )
    
    # Personalizar o hover (tooltip)
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>📦 OP: %{customdata[0]}</b>",
            "🔧 <b>Item:</b> %{customdata[1]}",
            "📊 <b>Quantidade:</b> %{customdata[2]:,.0f} unidades",
            "⏱️ <b>Início programado:</b> %{customdata[3]}",
            "⏱️ <b>Término programado:</b> %{customdata[4]}",
            "⚙️ <b>Cadência:</b> 2380 unid/hora",
            "<extra></extra>"
        ])
    )

    fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False)
    fig.update_traces(textposition='inside', insidetextanchor='start', width=0.92)
    
    fig.update_xaxes(
        type='date', 
        range=[agora - timedelta(hours=2), agora + timedelta(hours=36)], 
        dtick=10800000, 
        tickformat="%H:%M\n%d/%m",
        gridcolor='rgba(255,255,255,0.1)',
        showgrid=True,
        tickangle=0,
        tickfont=dict(size=11)
    )
    
    fig.add_vline(
        x=agora, 
        line_dash="dash", 
        line_color="red", 
        line_width=1,
        opacity=0.8,
        yref="paper",
        y0=1,
        y1=pos_y_agora
    )
    
    fig.add_annotation(
        x=agora, 
        y=pos_y_agora, 
        text=f"AGORA: {agora.strftime('%H:%M')}", 
        showarrow=False, 
        xref="x", 
        yref="paper", 
        font=dict(color="red", size=13, family="Arial Black"), 
        bgcolor="rgba(0,0,0,0.9)", 
        bordercolor="red", 
        borderpad=2
    )

    fig.update_layout(
        height=altura, 
        margin=dict(l=10, r=10, t=50, b=100), 
        bargap=0.01, 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})

    # ============================================================
    # CARDS DE STATUS DETALHADOS
    # ============================================================
    st.markdown("### 📊 Status do Setor")
    
    # Função auxiliar para buscar descrição do produto pelo ID_ITEM
    def get_descricao_produto(id_item):
        if df_produtos is not None and not df_produtos.empty:
            produto = df_produtos[df_produtos['id_item'] == id_item]
            if not produto.empty:
                return produto.iloc[0]['descricao']
        return "Descrição não encontrada"
    
    # 1. CARDS DE OPs EM EXECUÇÃO
    ops_em_execucao = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] == "Pendente")]
    
    if not ops_em_execucao.empty:
        st.markdown("#### 🔴 OPs em Execução Agora:")
        
        for i in range(0, len(ops_em_execucao), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ops_em_execucao):
                    op = ops_em_execucao.iloc[i + j]
                    
                    pedido_split = op['pedido'].split(' | ')
                    cliente = pedido_split[0] if len(pedido_split) > 0 else "N/A"
                    op_numero = pedido_split[1].replace('OP:', '') if len(pedido_split) > 1 else "N/A"
                    
                    descricao_produto = get_descricao_produto(op['item'])
                    
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color: #ff7f0e20; padding: 15px; border-radius: 10px; border-left: 5px solid #ff7f0e; margin-bottom: 15px;">
                            <p style="color: #ff7f0e; margin: 0 0 5px 0; font-size: 14px; font-weight: bold;">🏭 {op['maquina']}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #888;">Cliente:</span> {cliente}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #888;">Item:</span> {op['item']}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #888;">Descrição:</span> {descricao_produto}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #888;">OP:</span> {op_numero}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #888;">QTD:</span> {int(op['qtd'])}</p>
                            <p style="color: #aaa; margin: 5px 0 0 0; font-size: 11px; border-top: 1px solid #ff7f0e50; padding-top: 5px;">
                                {op['inicio'].strftime('%H:%M')} - {op['fim'].strftime('%H:%M')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
        st.divider()
    else:
        st.info("⏸️ Nenhuma OP em execução no momento.")
        st.divider()
    
    # 2. CARDS DE OPs ATRASADAS
    ops_atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"] == "Pendente")]
    
    if not ops_atrasadas.empty:
        st.markdown("#### 🚨 OPs ATRASADAS")
        
        for i in range(0, len(ops_atrasadas), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ops_atrasadas):
                    op = ops_atrasadas.iloc[i + j]
                    
                    pedido_split = op['pedido'].split(' | ')
                    cliente = pedido_split[0] if len(pedido_split) > 0 else "N/A"
                    op_numero = pedido_split[1].replace('OP:', '') if len(pedido_split) > 1 else "N/A"
                    
                    descricao_produto = get_descricao_produto(op['item'])
                    
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color: #FF4B4B20; padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; margin-bottom: 15px;">
                            <p style="color: #FF4B4B; margin: 0 0 5px 0; font-size: 14px; font-weight: bold;">🏭 {op['maquina']}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #FF4B4B;">Cliente:</span> {cliente}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #FF4B4B;">Item:</span> {op['item']}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #FF4B4B;">Descrição:</span> {descricao_produto}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #FF4B4B;">OP:</span> {op_numero}</p>
                            <p style="color: white; margin: 0; font-size: 13px;"><span style="color: #FF4B4B;">QTD:</span> {int(op['qtd'])}</p>
                            <p style="color: #aaa; margin: 5px 0 0 0; font-size: 11px; border-top: 1px solid #FF4B4B50; padding-top: 5px;">
                                Deveria ter terminado: {op['fim'].strftime('%d/%m %H:%M')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
        st.divider()
    
    # 3. MÁQUINAS SEM PROGRAMAÇÃO
    maquinas_com_op = df_g[df_g["status"] == "Pendente"]["maquina"].unique()
    maquinas_sem_programacao = [m for m in lista_maquinas if m not in maquinas_com_op]
    
    if maquinas_sem_programacao:
        st.markdown("#### 💤 Máquinas sem Programação")
        
        for i in range(0, len(maquinas_sem_programacao), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(maquinas_sem_programacao):
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color: #7f7f7f20; padding: 10px; border-radius: 10px; border-left: 5px solid #7f7f7f; text-align: center;">
                            <p style="color: #7f7f7f; margin: 0; font-size: 14px; font-weight: bold;">🏭 {maquinas_sem_programacao[i+j]}</p>
                            <p style="color: #aaa; margin: 0; font-size: 11px;">Sem OP programada</p>
                        </div>
                        """, unsafe_allow_html=True)
        st.divider()
    
    # 4. MÉTRICAS GERAIS
    st.markdown("#### 📊 Métricas Gerais")
    c1, c2, c3, c4 = st.columns(4)
    
    atrasadas_count = len(ops_atrasadas)
    em_uso_count = ops_em_execucao["maquina"].nunique() if not ops_em_execucao.empty else 0
    total_setor = len(lista_maquinas)
    total_ops = df_g[df_g["status"] == "Pendente"].shape[0]
    
    c1.metric("🚨 OPs Atrasadas", atrasadas_count)
    c2.metric("⚙️ OPs em Execução", em_uso_count)
    c3.metric("📦 Total OPs Pendentes", total_ops)
    c4.metric("📈 Taxa de Ocupação", f"{(em_uso_count/total_setor)*100:.1f}%" if total_setor > 0 else "0%")
    st.divider()

# =================================================================
# 5. ABAS E LÓGICA DE NEGÓCIO
# =================================================================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"])

with aba1:
    with st.container(border=True):
        st.subheader("➕ Novo Lançamento")
        
        df_prod = st.session_state.df_produtos.copy()
        df_prod['id_item'] = df_prod['id_item'].astype(str).str.strip()

        c1, c2 = st.columns(2)

        with c1:
            maq_sel = st.selectbox("🏭 Máquina destino", TODAS_MAQUINAS, key="maq_lanc")
            opcoes_itens = df_prod['id_item'].tolist()
            item_sel = st.selectbox("📌 Selecione o ID_ITEM", opcoes_itens, key="item_lanc")

            # BUSCA AUTOMÁTICA
            descricao_texto = "N/A"
            cliente_texto = "N/A"
            carga_sugerida = CARGA_UNIDADE

            if item_sel:
                id_busca = str(item_sel).strip()
                produto_info = df_prod[df_prod['id_item'] == id_busca]
                if not produto_info.empty:
                    info = produto_info.iloc[0]
                    descricao_texto = info['descricao']
                    cliente_texto = info['cliente']
                    carga_sugerida = int(info['qtd_carga'])

            st.text_input("📝 Descrição do Produto", value=descricao_texto, disabled=True)
        
        with c2:
            op_num = st.text_input("🔢 Número da OP", key="op_num")
            st.text_input("👥 Cliente", value=cliente_texto, disabled=True)
            qtd_lanc = st.number_input("📊 Quantidade Total", value=carga_sugerida, key="qtd_lanc")

        st.divider()
        
        c3, c4, c5, c6 = st.columns(4)
        
        # Tipo de lançamento
        tipo_lancamento = c3.selectbox(
            "📋 Tipo de Lançamento", 
            ["Produção Normal (com setup automático)", "Apenas Setup Manual", "Apenas Manutenção"],
            key="tipo_lancamento"
        )
        
        # Tempo de setup/manutenção (editável)
        minutos_parada = 0
        if tipo_lancamento != "Produção Normal (com setup automático)":
            minutos_parada = c4.number_input(
                f"⏱️ Tempo de {tipo_lancamento.replace('Apenas ', '')} (min)", 
                min_value=0, 
                value=30, 
                key="min_parada"
            )
        else:
            # Setup automático da produção normal
            minutos_parada = c4.number_input(
                "⏱️ Tempo de Setup (min)", 
                min_value=0, 
                value=30, 
                key="setup_auto"
            )
        
        # CÁLCULO DO PRÓXIMO HORÁRIO LIVRE
        sugestao_h = proximo_horario(maq_sel)
        
        data_ini = c5.date_input("📅 Data de Início", sugestao_h.date(), key="data_lanc")
        hora_ini = c6.time_input("⏰ Hora de Início", sugestao_h.time(), key="hora_lanc")
        
        st.caption(f"⏱️ Sugestão baseada no fim da última OP: **{sugestao_h.strftime('%d/%m %H:%M')}**")

        if st.button("🚀 CONFIRMAR E AGENDAR", type="primary", use_container_width=True):
            if op_num and item_sel:
                inicio_dt = datetime.combine(data_ini, hora_ini)
                
                # PRODUÇÃO NORMAL (com setup automático)
                if tipo_lancamento == "Produção Normal (com setup automático)":
                    fim_dt = inicio_dt + timedelta(hours=qtd_lanc/CADENCIA_PADRAO)
                    
                    with conectar() as conn:
                        cur = conn.cursor()
                        # Insere a PRODUÇÃO com dados de quem criou
                        cur.execute(
                            "INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, criado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                            (maq_sel, f"{cliente_texto} | OP:{op_num}", item_sel,
                             inicio_dt.strftime('%Y-%m-%d %H:%M:%S'),
                             fim_dt.strftime('%Y-%m-%d %H:%M:%S'),
                             "Pendente", qtd_lanc,
                             st.session_state.user_email,
                             agora.strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        producao_id = cur.lastrowid
                        
                        # Insere o SETUP automático após a produção
                        if minutos_parada > 0:
                            fim_setup = fim_dt + timedelta(minutes=minutos_parada)
                            conn.execute(
                                "INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id, criado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (maq_sel, f"SETUP {op_num}", "Ajuste",
                                 fim_dt.strftime('%Y-%m-%d %H:%M:%S'),
                                 fim_setup.strftime('%Y-%m-%d %H:%M:%S'),
                                 "Setup", 0, producao_id,
                                 st.session_state.user_email,
                                 agora.strftime('%Y-%m-%d %H:%M:%S'))
                            )
                        conn.commit()
                    st.success("Produção com setup automático lançada com sucesso!")
                
                # APENAS SETUP MANUAL (sem produção)
                elif tipo_lancamento == "Apenas Setup Manual":
                    fim_parada = inicio_dt + timedelta(minutes=minutos_parada)
                    
                    with conectar() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, criado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                            (maq_sel, f"SETUP MANUAL | {op_num}", item_sel,
                             inicio_dt.strftime('%Y-%m-%d %H:%M:%S'),
                             fim_parada.strftime('%Y-%m-%d %H:%M:%S'),
                             "Setup", 0,
                             st.session_state.user_email,
                             agora.strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        conn.commit()
                    st.success("Setup manual agendado com sucesso!")
                
                # APENAS MANUTENÇÃO (sem produção)
                elif tipo_lancamento == "Apenas Manutenção":
                    fim_parada = inicio_dt + timedelta(minutes=minutos_parada)
                    
                    with conectar() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, criado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                            (maq_sel, f"MANUTENÇÃO | {op_num}", item_sel,
                             inicio_dt.strftime('%Y-%m-%d %H:%M:%S'),
                             fim_parada.strftime('%Y-%m-%d %H:%M:%S'),
                             "Manutenção", 0,
                             st.session_state.user_email,
                             agora.strftime('%Y-%m-%d %H:%M:%S'))
                        )
                        conn.commit()
                    st.success("Manutenção agendada com sucesso!")
                
                st.rerun()
            else:
                if not op_num:
                    st.error("❌ Digite o número da OP!")
                if not item_sel:
                    st.error("❌ Selecione um ID_ITEM!")

with aba2: 
    renderizar_setor(MAQUINAS_SERIGRAFIA, 450, -0.30)

with aba3: 
    renderizar_setor(MAQUINAS_SOPRO, 750, -0.45)

# =================================================================
# ABA 4 - GERENCIAR (VERSÃO COMPLETA COM METADADOS)
# =================================================================
with aba4:
    st.subheader("⚙️ Gerenciamento e Reprogramação")
    
    # Status count
    df_count = carregar_dados()
    if not df_count.empty:
        pendentes = len(df_count[df_count["status"] == "Pendente"])
        setups = len(df_count[df_count["status"] == "Setup"])
        manutencoes = len(df_count[df_count["status"] == "Manutenção"])
        
        # Métricas no topo
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("📦 OPs Pendentes", pendentes)
        col_m2.metric("🔧 Setups", setups)
        col_m3.metric("🔩 Manutenções", manutencoes)
        col_m4.metric("👥 Usuário", st.session_state.user_email.split('@')[0])
        
        st.divider()
    
    # Filtros avançados
    with st.expander("🔍 Filtros Avançados", expanded=False):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        # Carregar lista de usuários únicos para filtro
        df_temp = carregar_dados()
        usuarios_lista = ['Todos'] + df_temp['criado_por'].dropna().unique().tolist() if not df_temp.empty else ['Todos']
        
        with col_f1:
            filtro_status = st.multiselect(
                "Status", 
                ["Pendente", "Setup", "Manutenção"],
                default=["Pendente", "Setup", "Manutenção"]
            )
        
        with col_f2:
            filtro_usuario = st.selectbox("Criado por", usuarios_lista)
        
        with col_f3:
            filtro_dias = st.slider("Dias até início", 0, 30, 30)
    
    # Campo de pesquisa
    search_term = st.text_input("🔍 Pesquisar OP Programada", 
                                placeholder="Digite cliente, máquina, item ou número da OP...", 
                                key="search_gerenciar")
    
    df_ger = carregar_dados()
    if not df_ger.empty:
        # Filtrar APENAS OPs NÃO CONCLUÍDAS
        df_programadas = df_ger[df_ger["status"].isin(filtro_status)].copy()
        
        if df_programadas.empty:
            st.info("✅ Nenhuma OP programada no momento.")
        else:
            # Aplicar filtro de pesquisa
            if search_term:
                search_term_lower = search_term.lower()
                df_programadas['op_numero_aux'] = df_programadas['pedido'].apply(
                    lambda x: x.split('OP:')[-1] if 'OP:' in x else x
                )
                
                df_filtrado = df_programadas[
                    df_programadas["pedido"].str.lower().str.contains(search_term_lower, na=False) |
                    df_programadas["maquina"].str.lower().str.contains(search_term_lower, na=False) |
                    df_programadas["item"].str.lower().str.contains(search_term_lower, na=False) |
                    df_programadas["op_numero_aux"].str.lower().str.contains(search_term_lower, na=False)
                ].drop(columns=['op_numero_aux'])
            else:
                df_filtrado = df_programadas
            
            # Aplicar filtro de usuário
            if filtro_usuario != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['criado_por'] == filtro_usuario]
            
            # Aplicar filtro de dias
            data_limite = agora + timedelta(days=filtro_dias)
            df_filtrado = df_filtrado[df_filtrado['inicio'] <= data_limite]
            
            if df_filtrado.empty:
                st.warning(f"Nenhuma OP encontrada com os filtros selecionados")
            else:
                st.success(f"🔎 **{len(df_filtrado)}** OPs encontradas")
                
                # Botão de exportação
                if st.button("📥 Exportar para CSV"):
                    df_export = df_filtrado[['maquina', 'pedido', 'item', 'inicio', 'fim', 'status', 'qtd', 'criado_por', 'criado_em', 'alterado_por', 'alterado_em']].copy()
                    df_export['inicio'] = df_export['inicio'].dt.strftime('%d/%m/%Y %H:%M')
                    df_export['fim'] = df_export['fim'].dt.strftime('%d/%m/%Y %H:%M')
                    csv = df_export.to_csv(index=False)
                    st.download_button("⬇️ Download CSV", csv, "ops_programadas.csv", "text/csv")
                
                st.divider()
                
                # Ordenar por data de início
                df_filtrado = df_filtrado.sort_values("inicio")
                
                is_admin = st.session_state.user_email == ADMIN_EMAIL
                for _, prod in df_filtrado.iterrows():
                    # Definir emoji e cor do status
                    status_emoji = {
                        "Pendente": "📦",
                        "Setup": "🔧",
                        "Manutenção": "🔩"
                    }.get(prod['status'], "📌")
                    
                    # Calcular status de prazo
                    dias_para_inicio = (prod['inicio'] - agora).days
                    horas_para_inicio = (prod['inicio'] - agora).seconds / 3600
                    
                    if prod['inicio'] < agora:
                        status_prazo = "🔴 ATRASADA"
                        cor_prazo = "red"
                    elif dias_para_inicio == 0 and horas_para_inicio <= 2:
                        status_prazo = "🟡 Começa hoje!"
                        cor_prazo = "orange"
                    else:
                        status_prazo = f"🟢 Em {dias_para_inicio} dias"
                        cor_prazo = "green"
                    
                    with st.expander(f"{status_emoji} {prod['maquina']} | {prod['pedido']} | <span style='color:{cor_prazo}'>{status_prazo}</span>", unsafe_allow_html=True):
                        
                        # METADADOS DA OP
                        st.markdown("#### 📋 Metadados")
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        
                        with meta_col1:
                            st.markdown(f"**👤 Criado por:** {prod.get('criado_por', 'N/A')}")
                            if prod.get('criado_em'):
                                criado_em = datetime.strptime(prod['criado_em'], '%Y-%m-%d %H:%M:%S') if isinstance(prod['criado_em'], str) else prod['criado_em']
                                st.markdown(f"**📅 Criado em:** {criado_em.strftime('%d/%m/%Y %H:%M')}")
                        
                        with meta_col2:
                            st.markdown(f"**✏️ Última alteração:** {prod.get('alterado_por', 'N/A')}")
                            if prod.get('alterado_em'):
                                alterado_em = datetime.strptime(prod['alterado_em'], '%Y-%m-%d %H:%M:%S') if isinstance(prod['alterado_em'], str) else prod['alterado_em']
                                st.markdown(f"**⏰ Alterado em:** {alterado_em.strftime('%d/%m/%Y %H:%M')}")
                        
                        with meta_col3:
                            if prod['inicio'] < agora:
                                st.markdown(f"<span style='color:red; font-weight:bold'>⚠️ ATRASADA</span>", unsafe_allow_html=True)
                            elif dias_para_inicio == 0:
                                if horas_para_inicio <= 1:
                                    st.markdown(f"<span style='color:orange; font-weight:bold'>⚡ Começa em menos de 1 hora!</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<span style='color:orange; font-weight:bold'>⚡ Começa hoje às {prod['inicio'].strftime('%H:%M')}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='color:green; font-weight:bold'>✅ Em {dias_para_inicio} dias</span>", unsafe_allow_html=True)
                        
                        st.divider()
                        
                        # DETALHES DA OP
                        st.markdown("#### 📦 Detalhes da OP")
                        col1, col2, col3 = st.columns([2, 2, 1.2])
                        
                        with col1:
                            st.write(f"**Item:** {prod['item']}")
                            descricao = get_descricao_produto(prod['item']) if 'get_descricao_produto' in locals() else "N/A"
                            st.write(f"**Descrição:** {descricao}")
                        
                        with col2:
                            st.write(f"**Início:** {prod['inicio'].strftime('%d/%m %H:%M')}")
                            st.write(f"**Fim:** {prod['fim'].strftime('%d/%m %H:%M')}")
                            if prod['status'] == "Pendente":
                                st.write(f"**QTD:** {int(prod['qtd'])} unidades")
                        
                        # AÇÕES
                        st.markdown("#### 🛠️ Ações")
                        col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 1])
                        
                        with col_a:
                            if st.button("✅ Finalizar", key=f"ok_{prod['id']}", use_container_width=True):
                                with conectar() as c: 
                                    c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (prod['id'],))
                                    c.commit()
                                st.rerun()
                        
                        with col_b:
                            if is_admin:
                                if st.button("🗑️ Deletar", key=f"del_{prod['id']}", use_container_width=True):
                                    with conectar() as c: 
                                        c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (prod['id'], prod['id']))
                                        c.commit()
                                    st.rerun()
                        
                        with col_c:
                            if is_admin:
                                with st.popover("✏️ Reprogramar"):
                                    st.markdown("### Alterar horário")
                                    n_data = st.date_input("Nova Data", prod['inicio'].date(), key=f"d_{prod['id']}")
                                    n_hora = st.time_input("Nova Hora", prod['inicio'].time(), key=f"t_{prod['id']}")
                                    
                                    st.markdown(f"**Alterado por:** {st.session_state.user_email}")
                                    
                                    col_confirm1, col_confirm2 = st.columns(2)
                                    with col_confirm1:
                                        if st.button("✅ Confirmar", key=f"conf_{prod['id']}", use_container_width=True):
                                            novo_i = datetime.combine(n_data, n_hora)
                                            novo_f = novo_i + (prod['fim'] - prod['inicio'])
                                            with conectar() as c:
                                                c.execute("""
                                                    UPDATE agenda 
                                                    SET inicio=?, fim=?, 
                                                        alterado_por=?, alterado_em=? 
                                                    WHERE id=?
                                                    """, 
                                                    (novo_i.strftime('%Y-%m-%d %H:%M:%S'), 
                                                     novo_f.strftime('%Y-%m-%d %H:%M:%S'),
                                                     st.session_state.user_email,
                                                     agora.strftime('%Y-%m-%d %H:%M:%S'),
                                                     prod['id']))
                                                c.commit()
                                            st.rerun()
                                    with col_confirm2:
                                        if st.button("❌ Cancelar", key=f"cancel_{prod['id']}", use_container_width=True):
                                            st.rerun()
                        
                        with col_d:
                            # Histórico rápido
                            with st.popover("📜 Histórico"):
                                st.markdown("**📅 Criação:**")
                                st.caption(f"👤 {prod.get('criado_por', 'N/A')}")
                                if prod.get('criado_em'):
                                    criado_em = datetime.strptime(prod['criado_em'], '%Y-%m-%d %H:%M:%S') if isinstance(prod['criado_em'], str) else prod['criado_em']
                                    st.caption(f"🕒 {criado_em.strftime('%d/%m/%Y %H:%M')}")
                                
                                if prod.get('alterado_por'):
                                    st.markdown("**✏️ Última alteração:**")
                                    st.caption(f"👤 {prod['alterado_por']}")
                                    if prod.get('alterado_em'):
                                        alterado_em = datetime.strptime(prod['alterado_em'], '%Y-%m-%d %H:%M:%S') if isinstance(prod['alterado_em'], str) else prod['alterado_em']
                                        st.caption(f"🕒 {alterado_em.strftime('%d/%m/%Y %H:%M')}")
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

with aba5: 
    st.dataframe(df_produtos, use_container_width=True)

with aba6:
    df_c = carregar_dados()
    if not df_c.empty:
        df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        st.metric("Total Geral de Cargas Sopro", 
                 f"{df_p[df_p['maquina'].isin(MAQUINAS_SOPRO)]['qtd'].sum() / CARGA_UNIDADE:.1f}")
        st.table(df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)][["maquina", "pedido", "qtd"]])

st.divider()
st.caption("v7.0 | Industrial By William | Serigrafia | Sopro | Com Metadados e Rastreabilidade")
