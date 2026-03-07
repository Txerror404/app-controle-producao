import psycopg2
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh


# =================================================================
# CONFIGURAÇÃO DA PÁGINA
# =================================================================

st.set_page_config(
    page_title="PCP Industrial - SISTEMA COMPLETO",
    layout="wide"
)


# =================================================================
# CONFIGURAÇÃO DO BANCO SUPABASE
# =================================================================

DATABASE_URL = "postgresql://postgres.ogxrgnaedmcbaqgryosg:pcp2026supabase@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"


# =================================================================
# CONEXÃO COM SUPABASE
# =================================================================

def conectar():
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar no Supabase: {e}")
        st.stop()


# =================================================================
# VERIFICAR ESTRUTURA DA TABELA
# =================================================================

def verificar_estrutura_tabela():
    """Verifica quais colunas existem na tabela agenda"""
    try:
        conn = conectar()
        cur = conn.cursor()
        
        # Consulta para obter informações das colunas
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'agenda'
            ORDER BY ordinal_position
        """)
        
        colunas = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        st.sidebar.success(f"Colunas encontradas: {', '.join(colunas)}")
        return colunas
    except Exception as e:
        st.sidebar.error(f"Erro ao verificar estrutura: {e}")
        return []


# =================================================================
# TESTE DE CONEXÃO
# =================================================================

try:
    conn = conectar()
    conn.close()
except Exception as e:
    st.error(f"Falha na conexão com Supabase: {e}")
    st.stop()


# =================================================================
# AUTO REFRESH
# =================================================================

st_autorefresh(interval=120000, key="pcp_refresh_global")


# =================================================================
# CONFIGURAÇÕES DO SISTEMA
# =================================================================

ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = ["sarita@will.com.br", "oneida@will.com.br"]

MAQUINAS_SERIGRAFIA = [
    "maquina 13001",
    "maquina 13002",
    "maquina 13003",
    "maquina 13004"
]

MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]

TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504

fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"


# =================================================================
# ESTILO DA INTERFACE
# =================================================================

st.markdown("""
<style>
.block-container {padding-top:0.5rem;}
.modebar-container {top:0!important;}
.stTabs [data-baseweb="tab-list"] {gap:10px;}
.stTabs [data-baseweb="tab"]{
background-color:#1e1e1e;
border-radius:5px;
padding:5px 20px;
color:white;
}
.stTabs [aria-selected="true"]{
background-color:#FF4B4B!important;
}
</style>
""", unsafe_allow_html=True)


# =================================================================
# BUSCAR DESCRIÇÃO DO PRODUTO
# =================================================================

def get_descricao_produto(id_item):
    if 'df_produtos' in st.session_state:
        df_produtos = st.session_state.df_produtos
        if df_produtos is not None and not df_produtos.empty:
            produto = df_produtos[df_produtos['id_item'] == str(id_item)]
            if not produto.empty:
                return produto.iloc[0]['descricao']
    return "Descrição não encontrada"


# =================================================================
# CARREGAR PRODUTOS DO GOOGLE SHEETS
# =================================================================

@st.cache_data(ttl=600)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL)
        df.columns = df.columns.str.strip()
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
        df['cliente'] = df['CLIENTE'].astype(str).str.strip()
        df['qtd_carga'] = pd.to_numeric(
            df['QTD/CARGA'].astype(str).str.replace(',', '.'),
            errors='coerce'
        ).fillna(CARGA_UNIDADE)
        return df.fillna('N/A')
    except Exception as e:
        st.error(f"Erro ao carregar produtos: {e}")
        return pd.DataFrame(columns=['id_item','descricao','cliente','qtd_carga'])


# =================================================================
# CARREGAR DADOS DO BANCO
# =================================================================

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    conn.close()
    
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1
        )
    return df


# =================================================================
# PRÓXIMO HORÁRIO DISPONÍVEL
# =================================================================

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq) &
            (df["status"].isin(["Pendente","Setup","Manutenção"]))
        ]
        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)
    return agora


# =================================================================
# INSERIR PRODUÇÃO - VERSÃO CORRIGIDA
# =================================================================

def inserir_producao(maquina, pedido, item, inicio, fim, qtd, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Primeiro, vamos verificar quais colunas existem
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'agenda'
        """)
        colunas_existentes = [row[0] for row in cur.fetchall()]
        
        # Construir a query dinamicamente baseada nas colunas existentes
        colunas = ['maquina', 'pedido', 'item', 'inicio', 'fim', 'status', 'qtd']
        valores = [maquina, pedido, item, inicio, fim, 'Pendente', qtd]
        
        # Adicionar colunas opcionais se existirem
        if 'criado_por' in colunas_existentes:
            colunas.append('criado_por')
            valores.append(usuario)
        
        if 'criado_em' in colunas_existentes:
            colunas.append('criado_em')
            valores.append(agora)
        
        # Construir a query SQL
        placeholders = ','.join(['%s'] * len(colunas))
        colunas_str = ','.join(colunas)
        
        query = f"""
            INSERT INTO agenda ({colunas_str})
            VALUES ({placeholders})
            RETURNING id
        """
        
        cur.execute(query, valores)
        producao_id = cur.fetchone()[0]
        conn.commit()
        
        return producao_id
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir produção: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


# =================================================================
# INSERIR SETUP - VERSÃO CORRIGIDA
# =================================================================

def inserir_setup(maquina, pedido, inicio, fim, vinculo, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Verificar colunas existentes
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'agenda'
        """)
        colunas_existentes = [row[0] for row in cur.fetchall()]
        
        # Construir query dinamicamente
        colunas = ['maquina', 'pedido', 'item', 'inicio', 'fim', 'status', 'qtd', 'vinculo_id']
        valores = [maquina, pedido, "Ajuste", inicio, fim, "Setup", 0, vinculo]
        
        if 'criado_por' in colunas_existentes:
            colunas.append('criado_por')
            valores.append(usuario)
        
        if 'criado_em' in colunas_existentes:
            colunas.append('criado_em')
            valores.append(agora)
        
        placeholders = ','.join(['%s'] * len(colunas))
        colunas_str = ','.join(colunas)
        
        query = f"""
            INSERT INTO agenda ({colunas_str})
            VALUES ({placeholders})
        """
        
        cur.execute(query, valores)
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir setup: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


# =================================================================
# FINALIZAR OP
# =================================================================

def finalizar_op(id_op):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agenda SET status='Concluído' WHERE id=%s",
        (id_op,)
    )
    conn.commit()
    cur.close()
    conn.close()


# =================================================================
# DELETAR OP
# =================================================================

def deletar_op(id_op):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM agenda WHERE id=%s OR vinculo_id=%s",
        (id_op,id_op)
    )
    conn.commit()
    cur.close()
    conn.close()


# =================================================================
# REPROGRAMAR OP
# =================================================================

def reprogramar_op(id_op,novo_inicio,novo_fim,usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Verificar colunas existentes
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'agenda'
        """)
        colunas_existentes = [row[0] for row in cur.fetchall()]
        
        # Construir query base
        query = "UPDATE agenda SET inicio=%s, fim=%s"
        params = [novo_inicio, novo_fim]
        
        if 'alterado_por' in colunas_existentes:
            query += ", alterado_por=%s"
            params.append(usuario)
        
        if 'alterado_em' in colunas_existentes:
            query += ", alterado_em=%s"
            params.append(agora)
        
        query += " WHERE id=%s"
        params.append(id_op)
        
        cur.execute(query, params)
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao reprogramar: {e}")
        raise e
    finally:
        cur.close()
        conn.close()


# =================================================================
# LOGIN DO SISTEMA
# =================================================================

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL] + OPERACIONAL_EMAIL:
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()
    st.stop()


# =================================================================
# CARREGAR PRODUTOS
# =================================================================

if 'df_produtos' not in st.session_state:
    with st.spinner("Sincronizando com Google Sheets..."):
        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos


# =================================================================
# MOSTRAR ESTRUTURA DA TABELA (APENAS PARA DEBUG)
# =================================================================

with st.sidebar:
    st.title("🔧 Diagnóstico")
    if st.button("Verificar estrutura da tabela"):
        colunas = verificar_estrutura_tabela()
        if colunas:
            st.success(f"Colunas encontradas: {len(colunas)}")
            st.write(colunas)


# =================================================================
# CABEÇALHO
# =================================================================

st.markdown(f"""
<div style="background-color: #1E1E1E;
padding: 8px 15px;
border-radius: 8px;
border-left: 8px solid #FF4B4B;
margin-bottom: 15px;
display:flex;
justify-content:space-between;
align-items:center">
<div>
<h2 style="color:white;margin:0;font-size:20px">
📊 PCP <span style="color:#FF4B4B">|</span> CRONOGRAMA DE MÁQUINAS
</h2>
<p style="color:#888;margin:2px 0 0 0;font-size:12px">
👤 Usuário: {st.session_state.user_email}
</p>
</div>
<div style="text-align:center;
border:1px solid #FF4B4B;
padding:2px 15px;
border-radius:5px;
background-color:#0E1117;
min-width:130px">
<h3 style="color:#FF4B4B;
margin:0;
font-family:Courier New;
font-size:22px">
⏰ {agora.strftime('%H:%M:%S')}
</h3>
<p style="color:#aaa;
margin:-2px 0 2px 0;
font-size:12px;
border-top:1px dashed #FF4B4B;
padding-top:2px">
{agora.strftime('%d/%m/%Y')}
</p>
</div>
</div>
""", unsafe_allow_html=True)


# =================================================================
# FUNÇÃO PARA RENDERIZAR SETOR
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
    
    # Status dinâmico
    df_g["status_cor"] = df_g["status"]
    df_g.loc[
        (df_g["inicio"] <= agora) &
        (df_g["fim"] >= agora) &
        (df_g["status"] == "Pendente"),
        "status_cor"
    ] = "Executando"
    
    df_g["cor_barra"] = df_g["status_cor"]
    df_g.loc[
        (df_g["fim"] < agora) &
        (df_g["status"] == "Pendente"),
        "cor_barra"
    ] = "Atrasada"
    df_g.loc[df_g["status"] == "Setup", "cor_barra"] = "Setup"
    df_g.loc[df_g["status"] == "Manutenção", "cor_barra"] = "Manutenção"
    
    # Formatando datas
    df_g["fim_formatado"] = df_g["fim"].dt.strftime('%d/%m %H:%M')
    df_g["ini_formatado"] = df_g["inicio"].dt.strftime('%d/%m %H:%M')
    
    # Criar Gantt
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
        custom_data=[
            "pedido",
            "item",
            "qtd",
            "ini_formatado",
            "fim_formatado"
        ]
    )
    
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>📦 OP: %{customdata[0]}</b>",
            "🔧 <b>Item:</b> %{customdata[1]}",
            "📊 <b>Quantidade:</b> %{customdata[2]:,.0f} unidades",
            "⏱️ <b>Início programado:</b> %{customdata[3]}",
            "⏱️ <b>Término programado:</b> %{customdata[4]}",
            "⚙️ <b>Cadência:</b> 2380 unid/hora",
            "<extra></extra>"
        ]),
        textposition='inside',
        insidetextanchor='start',
        width=0.92
    )
    
    fig.update_yaxes(
        autorange="reversed",
        title="",
        showgrid=True,
        gridcolor='rgba(255,255,255,0.15)',
        zeroline=False
    )
    
    fig.update_xaxes(
        type='date',
        range=[
            agora - timedelta(hours=2),
            agora + timedelta(hours=36)
        ],
        dtick=10800000,
        tickformat="%H:%M\n%d/%m",
        gridcolor='rgba(255,255,255,0.1)',
        showgrid=True,
        tickangle=0,
        tickfont=dict(size=11)
    )
    
    st.plotly_chart(fig, use_container_width=True, height=altura)
    
    # OPs atrasadas
    ops_atrasadas = df_g[
        (df_g["fim"] < agora) &
        (df_g["status"] == "Pendente")
    ]
    
    # OPs em execução
    ops_em_execucao = df_g[
        (df_g["inicio"] <= agora) &
        (df_g["fim"] >= agora) &
        (df_g["status"] == "Pendente")
    ]
    
    if not ops_atrasadas.empty:
        st.markdown("#### 🚨 OPs ATRASADAS")
        for i in range(0, len(ops_atrasadas), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ops_atrasadas):
                    op = ops_atrasadas.iloc[i + j]
                    descricao_produto = get_descricao_produto(op['item'])
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color:#FF4B4B20;
                        padding:15px;
                        border-radius:10px;
                        border-left:5px solid #FF4B4B">
                        <p style="color:#FF4B4B;font-weight:bold">
                        🏭 {op['maquina']}
                        </p>
                        <p style="color:white;margin:0">
                        Item: {op['item']}
                        </p>
                        <p style="color:white;margin:0">
                        Descrição: {descricao_produto}
                        </p>
                        <p style="color:white;margin:0">
                        QTD: {int(op['qtd'])}
                        </p>
                        <p style="color:#aaa;margin-top:5px">
                        Deveria terminar: {op['fim'].strftime('%d/%m %H:%M')}
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
        st.divider()
    
    # Máquinas sem programação
    maquinas_com_op = df_g[df_g["status"] == "Pendente"]["maquina"].unique()
    maquinas_sem_programacao = [
        m for m in lista_maquinas if m not in maquinas_com_op
    ]
    
    if maquinas_sem_programacao:
        st.markdown("#### 💤 Máquinas sem Programação")
        for i in range(0, len(maquinas_sem_programacao), 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(maquinas_sem_programacao):
                    with cols[j]:
                        maq = maquinas_sem_programacao[i + j]
                        st.markdown(f"""
                        <div style="background-color:#7f7f7f20;
                        padding:10px;
                        border-radius:10px;
                        border-left:5px solid #7f7f7f;
                        text-align:center">
                        <p style="color:#7f7f7f;font-weight:bold">
                        🏭 {maq}
                        </p>
                        <p style="color:#aaa">
                        Sem OP
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
        st.divider()
    
    # Métricas
    st.markdown("#### 📊 Métricas Gerais")
    c1, c2, c3, c4 = st.columns(4)
    
    atrasadas_count = len(ops_atrasadas)
    em_uso_count = len(ops_em_execucao["maquina"].unique()) if not ops_em_execucao.empty else 0
    total_setor = len(lista_maquinas)
    total_ops = df_g[df_g["status"] == "Pendente"].shape[0]
    
    c1.metric("🚨 OPs Atrasadas", atrasadas_count)
    c2.metric("⚙️ OPs em Execução", em_uso_count)
    c3.metric("📦 Total OPs Pendentes", total_ops)
    
    if total_setor > 0:
        ocup = (em_uso_count / total_setor) * 100
        c4.metric("📈 Taxa de Ocupação", f"{ocup:.1f}%")
    else:
        c4.metric("📈 Taxa de Ocupação", "0%")
    
    st.divider()


# =================================================================
# ABAS PRINCIPAIS
# =================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 CRONOGRAMA SERIGRAFIA",
    "📅 CRONOGRAMA SOPRO",
    "➕ NOVO LANÇAMENTO",
    "⚙️ GERENCIAR OPs",
    "📋 PRODUTOS",
    "📊 CARGAS SOPRO"
])


# =================================================================
# ABA 1 - SERIGRAFIA
# =================================================================

with tab1:
    renderizar_setor(MAQUINAS_SERIGRAFIA)


# =================================================================
# ABA 2 - SOPRO
# =================================================================

with tab2:
    renderizar_setor(MAQUINAS_SOPRO)


# =================================================================
# ABA 3 - NOVO LANÇAMENTO
# =================================================================

with tab3:
    with st.container(border=True):
        st.subheader("➕ Novo Lançamento")
        
        df_prod = st.session_state.df_produtos.copy()
        df_prod['id_item'] = df_prod['id_item'].astype(str).str.strip()
        
        c1, c2 = st.columns(2)
        
        with c1:
            maq_sel = st.selectbox(
                "🏭 Máquina destino",
                TODAS_MAQUINAS,
                key="nova_maquina"
            )
            
            opcoes_itens = df_prod['id_item'].tolist()
            item_sel = st.selectbox(
                "📌 Selecione o ID_ITEM",
                opcoes_itens,
                key="novo_item"
            )
            
            descricao_texto = "N/A"
            cliente_texto = "N/A"
            carga_sugerida = CARGA_UNIDADE
            
            if item_sel:
                produto_info = df_prod[df_prod['id_item'] == item_sel]
                if not produto_info.empty:
                    info = produto_info.iloc[0]
                    descricao_texto = info['descricao']
                    cliente_texto = info['cliente']
                    carga_sugerida = int(info['qtd_carga'])
            
            st.text_input(
                "📝 Descrição",
                value=descricao_texto,
                disabled=True,
                key="nova_descricao"
            )
        
        with c2:
            op_num = st.text_input("🔢 Número da OP", key="nova_op")
            
            st.text_input(
                "👥 Cliente",
                value=cliente_texto,
                disabled=True,
                key="nova_cliente"
            )
            
            qtd_lanc = st.number_input(
                "📊 Quantidade Total",
                value=carga_sugerida,
                key="nova_qtd"
            )
        
        sugestao_h = proximo_horario(maq_sel)
        
        d1, d2 = st.columns(2)
        
        data_ini = d1.date_input(
            "📅 Data",
            sugestao_h.date(),
            key="nova_data"
        )
        
        hora_ini = d2.time_input(
            "⏰ Hora",
            sugestao_h.time(),
            key="nova_hora"
        )
        
        if st.button("🚀 CONFIRMAR E AGENDAR", key="btn_confirmar"):
            if op_num and item_sel:
                inicio_dt = datetime.combine(data_ini, hora_ini)
                fim_dt = inicio_dt + timedelta(
                    hours=qtd_lanc / CADENCIA_PADRAO
                )
                
                try:
                    inserir_producao(
                        maq_sel,
                        f"{cliente_texto} | OP:{op_num}",
                        item_sel,
                        inicio_dt,
                        fim_dt,
                        qtd_lanc,
                        st.session_state.user_email
                    )
                    
                    st.success("✅ OP lançada com sucesso!")
                    st.balloons()
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao lançar OP: {e}")
            else:
                st.error("Preencha OP e Item")


# =================================================================
# ABA 4 - GERENCIAR OPs
# =================================================================

with tab4:
    st.subheader("⚙️ Gerenciamento de OPs")
    
    df_ger = carregar_dados()
    
    if not df_ger.empty:
        df_programadas = df_ger[
            df_ger["status"].isin(["Pendente","Setup","Manutenção"])
        ].sort_values("inicio")
        
        if not df_programadas.empty:
            for _, prod in df_programadas.iterrows():
                with st.expander(
                    f"{prod['maquina']} | {prod['pedido']} | Início: {prod['inicio'].strftime('%d/%m %H:%M')}"
                ):
                    st.write("**Item:**", prod["item"])
                    st.write("**Quantidade:**", int(prod["qtd"]) if pd.notna(prod["qtd"]) else 0)
                    st.write("**Início:**", prod["inicio"].strftime('%d/%m/%Y %H:%M'))
                    st.write("**Fim:**", prod["fim"].strftime('%d/%m/%Y %H:%M'))
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(
                            "✅ Finalizar",
                            key=f"ok_{prod['id']}"
                        ):
                            finalizar_op(prod["id"])
                            st.success("OP finalizada!")
                            st.rerun()
                    
                    with col2:
                        if st.button(
                            "🗑️ Deletar",
                            key=f"del_{prod['id']}"
                        ):
                            deletar_op(prod["id"])
                            st.success("OP deletada!")
                            st.rerun()
        else:
            st.info("Nenhuma OP pendente encontrada")
    else:
        st.info("Nenhuma OP cadastrada")


# =================================================================
# ABA 5 - PRODUTOS
# =================================================================

with tab5:
    st.subheader("📋 Produtos")
    if not df_produtos.empty:
        st.dataframe(
            df_produtos,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Nenhum produto carregado do Google Sheets")


# =================================================================
# ABA 6 - CARGAS SOPRO
# =================================================================

with tab6:
    st.subheader("📊 Cargas Sopro")
    
    df_c = carregar_dados()
    
    if not df_c.empty:
        df_p = df_c[
            (df_c["status"] == "Pendente") &
            (df_c["qtd"] > 0)
        ]
        
        df_sopro = df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)]
        
        if not df_sopro.empty:
            total_cargas = df_sopro["qtd"].sum() / CARGA_UNIDADE
            
            st.metric(
                "Total Geral de Cargas Sopro",
                f"{total_cargas:.1f}"
            )
            
            st.dataframe(
                df_sopro[["maquina", "pedido", "qtd"]].sort_values("maquina"),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "maquina": "Máquina",
                    "pedido": "OP",
                    "qtd": "Quantidade"
                }
            )
        else:
            st.info("Nenhuma carga de sopro pendente")
    else:
        st.info("Nenhuma OP cadastrada")


# =================================================================
# RODAPÉ
# =================================================================

st.divider()
st.caption(
    "v7.2 | Industrial By William | PCP Serigrafia + Sopro | Supabase Edition"
)
