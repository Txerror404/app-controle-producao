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
# TESTE DE CONEXÃO
# =================================================================

try:
    conn = conectar()
    conn.close()
except Exception as e:
    st.error(f"Falha na conexão com Supabase: {e}")
    st.stop()


# =================================================================
# CRIAÇÃO DA TABELA (CASO NÃO EXISTA)
# =================================================================

try:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id SERIAL PRIMARY KEY,
            maquina TEXT,
            pedido TEXT,
            item TEXT,
            inicio TIMESTAMP,
            fim TIMESTAMP,
            status TEXT,
            qtd NUMERIC,
            vinculo_id INTEGER,
            criado_por TEXT,
            criado_em TIMESTAMP,
            alterado_por TEXT,
            alterado_em TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
except Exception as e:
    st.error(f"Erro ao criar tabela: {e}")
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
SETUP_DURACAO = 30  # minutos

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
    except Exception:
        return pd.DataFrame(columns=['id_item','descricao','cliente','qtd_carga'])


# =================================================================
# CARREGAR DADOS DO BANCO
# =================================================================

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda ORDER BY inicio", conn)
    conn.close()
    
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        
        # Rótulo para as barras
        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1
        )
        
        # Identificar OPs em execução
        df["em_execucao"] = (df["inicio"] <= agora) & (df["fim"] >= agora) & (df["status"] == "Pendente")
        
        # Identificar OPs atrasadas
        df["atrasada"] = (df["fim"] < agora) & (df["status"] == "Pendente")
        
        # Cor da barra baseada no status
        df["cor_barra"] = "Pendente"
        df.loc[df["status"] == "Setup", "cor_barra"] = "Setup"
        df.loc[df["status"] == "Manutenção", "cor_barra"] = "Manutenção"
        df.loc[df["status"] == "Concluído", "cor_barra"] = "Concluído"
        df.loc[df["em_execucao"], "cor_barra"] = "Executando"
        df.loc[df["atrasada"], "cor_barra"] = "Atrasada"
        
        # Formatar datas para hover
        df["fim_formatado"] = df["fim"].dt.strftime('%d/%m %H:%M')
        df["ini_formatado"] = df["inicio"].dt.strftime('%d/%m %H:%M')
        
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
# CALCULAR FIM DA OP
# =================================================================

def calcular_fim_op(inicio, qtd):
    return inicio + timedelta(hours=qtd / CADENCIA_PADRAO)


# =================================================================
# INSERIR PRODUÇÃO
# =================================================================

def inserir_producao(maquina, pedido, item, inicio, fim, qtd, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Inserir a produção
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, criado_por, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                maquina,
                pedido,
                item,
                inicio,
                fim,
                "Pendente",
                qtd,
                usuario,
                agora
            )
        )
        
        producao_id = cur.fetchone()[0]
        
        # Inserir setup de 30 minutos antes
        setup_inicio = inicio - timedelta(minutes=SETUP_DURACAO)
        setup_fim = inicio
        
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id, criado_por, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                maquina,
                f"SETUP - {pedido}",
                "Setup",
                setup_inicio,
                setup_fim,
                "Setup",
                0,
                producao_id,
                usuario,
                agora
            )
        )
        
        conn.commit()
        return producao_id
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir produção: {e}")
        return None
    finally:
        cur.close()
        conn.close()


# =================================================================
# INSERIR SETUP MANUAL
# =================================================================

def inserir_setup(maquina, pedido, inicio, fim, vinculo, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id, criado_por, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                maquina,
                pedido,
                "Ajuste",
                inicio,
                fim,
                "Setup",
                0,
                vinculo,
                usuario,
                agora
            )
        )
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir setup: {e}")
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
# DELETAR OP (E SEU SETUP)
# =================================================================

def deletar_op(id_op):
    conn = conectar()
    cur = conn.cursor()
    
    # Deletar a OP e seu setup vinculado
    cur.execute(
        "DELETE FROM agenda WHERE id=%s OR vinculo_id=%s",
        (id_op, id_op)
    )
    
    conn.commit()
    cur.close()
    conn.close()


# =================================================================
# REPROGRAMAR OP (E EMPURRAR AS SEGUINTES)
# =================================================================

def reprogramar_op(id_op, novo_inicio, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Buscar a OP atual e seu setup
        cur.execute("""
            SELECT id, maquina, inicio, fim, vinculo_id, status, qtd 
            FROM agenda 
            WHERE id = %s OR vinculo_id = %s
            ORDER BY inicio
        """, (id_op, id_op))
        
        registros = cur.fetchall()
        
        if not registros:
            return
        
        # Separar setup e produção
        setup = None
        producao = None
        
        for reg in registros:
            if reg[5] == "Setup":  # status
                setup = reg
            else:
                producao = reg
        
        if not producao:
            return
        
        # Calcular novos horários
        producao_id, maquina, old_inicio, old_fim, vinculo_id, status, qtd = producao
        
        # Novo fim baseado na quantidade
        novo_fim = calcular_fim_op(novo_inicio, qtd)
        
        # Atualizar a produção
        cur.execute(
            """
            UPDATE agenda 
            SET inicio = %s, fim = %s, alterado_por = %s, alterado_em = %s
            WHERE id = %s
            """,
            (novo_inicio, novo_fim, usuario, agora, producao_id)
        )
        
        # Se tiver setup, atualizar também
        if setup:
            setup_id, _, setup_inicio, setup_fim, _, _, _ = setup
            novo_setup_inicio = novo_inicio - timedelta(minutes=SETUP_DURACAO)
            novo_setup_fim = novo_inicio
            
            cur.execute(
                """
                UPDATE agenda 
                SET inicio = %s, fim = %s, alterado_por = %s, alterado_em = %s
                WHERE id = %s
                """,
                (novo_setup_inicio, novo_setup_fim, usuario, agora, setup_id)
            )
        
        # Buscar todas as OPs seguintes na mesma máquina
        cur.execute("""
            SELECT id, inicio, fim, vinculo_id, status, qtd
            FROM agenda
            WHERE maquina = %s 
                AND status IN ('Pendente', 'Setup')
                AND id != %s 
                AND (vinculo_id != %s OR vinculo_id IS NULL)
                AND inicio > %s
            ORDER BY inicio
        """, (maquina, producao_id, producao_id, old_fim))
        
        seguintes = cur.fetchall()
        
        # Recalcular horários das OPs seguintes
        current_end = novo_fim
        
        for seguinte in seguintes:
            seg_id, seg_inicio, seg_fim, seg_vinculo, seg_status, seg_qtd = seguinte
            
            # Calcular novo início (após a OP anterior)
            if seg_status == "Setup":
                # Setup deve começar antes da produção
                # Encontrar a produção vinculada
                cur.execute("SELECT id, inicio FROM agenda WHERE vinculo_id = %s AND status = 'Pendente'", (seg_vinculo or seg_id,))
                prod_vinculada = cur.fetchone()
                
                if prod_vinculada:
                    prod_id, prod_inicio = prod_vinculada
                    novo_setup_inicio = current_end
                    novo_setup_fim = current_end + timedelta(minutes=SETUP_DURACAO)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_setup_inicio, novo_setup_fim, seg_id)
                    )
                    
                    # Atualizar produção vinculada
                    novo_prod_inicio = novo_setup_fim
                    novo_prod_fim = calcular_fim_op(novo_prod_inicio, seg_qtd if seg_qtd > 0 else qtd)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_prod_inicio, novo_prod_fim, prod_id)
                    )
                    
                    current_end = novo_prod_fim
                else:
                    # Setup sem produção (raro)
                    duracao = (seg_fim - seg_inicio).total_seconds() / 60
                    novo_setup_inicio = current_end
                    novo_setup_fim = current_end + timedelta(minutes=duracao)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_setup_inicio, novo_setup_fim, seg_id)
                    )
                    
                    current_end = novo_setup_fim
            else:
                # É uma produção
                novo_seg_inicio = current_end
                novo_seg_fim = calcular_fim_op(novo_seg_inicio, seg_qtd)
                
                cur.execute(
                    "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                    (novo_seg_inicio, novo_seg_fim, seg_id)
                )
                
                current_end = novo_seg_fim
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao reprogramar: {e}")
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
            "Setup": "#7f7f7f",  # Cinza para setup
            "Executando": "#ff7f0e",  # Laranja para em execução
            "Atrasada": "#FF4B4B",  # Vermelho para atrasada
            "Manutenção": "#9b59b6"
        },
        custom_data=[
            "pedido",
            "item",
            "qtd",
            "ini_formatado",
            "fim_formatado",
            "status"
        ]
    )
    
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>📦 OP: %{customdata[0]}</b>",
            "🔧 <b>Item:</b> %{customdata[1]}",
            "📊 <b>Quantidade:</b> %{customdata[2]:,.0f} unidades",
            "⏱️ <b>Início programado:</b> %{customdata[3]}",
            "⏱️ <b>Término programado:</b> %{customdata[4]}",
            "⚙️ <b>Status:</b> %{customdata[5]}",
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
    
    # Linha vertical para o momento atual
    fig.add_vline(
        x=agora.timestamp() * 1000,
        line_width=2,
        line_dash="dash",
        line_color="white",
        opacity=0.5
    )
    
    st.plotly_chart(fig, use_container_width=True, height=altura)
    
    # OPs atrasadas
    ops_atrasadas = df_g[df_g["atrasada"]]
    
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
    
    # OPs em execução
    ops_execucao = df_g[df_g["em_execucao"]]
    
    if not ops_execucao.empty:
        st.markdown("#### ⚙️ OPs EM EXECUÇÃO")
        for i in range(0, len(ops_execucao), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ops_execucao):
                    op = ops_execucao.iloc[i + j]
                    descricao_produto = get_descricao_produto(op['item'])
                    with cols[j]:
                        st.markdown(f"""
                        <div style="background-color:#ff7f0e20;
                        padding:15px;
                        border-radius:10px;
                        border-left:5px solid #ff7f0e">
                        <p style="color:#ff7f0e;font-weight:bold">
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
                        Término previsto: {op['fim'].strftime('%d/%m %H:%M')}
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
    em_uso_count = ops_execucao["maquina"].nunique() if not ops_execucao.empty else 0
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
                value=int(carga_sugerida),
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
        
        if st.button("🚀 CONFIRMAR E AGENDAR (com setup automático de 30min)", key="btn_confirmar"):
            if op_num and item_sel:
                inicio_dt = datetime.combine(data_ini, hora_ini)
                fim_dt = calcular_fim_op(inicio_dt, qtd_lanc)
                
                resultado = inserir_producao(
                    maq_sel,
                    f"{cliente_texto} | OP:{op_num}",
                    item_sel,
                    inicio_dt,
                    fim_dt,
                    qtd_lanc,
                    st.session_state.user_email
                )
                
                if resultado:
                    st.success("✅ OP lançada com sucesso! Setup de 30 minutos agendado automaticamente.")
                    st.balloons()
                    st.rerun()
            else:
                st.error("Preencha OP e Item")


# =================================================================
# ABA 4 - GERENCIAR OPs (COM EDIÇÃO E REPROGRAMAÇÃO)
# =================================================================

with tab4:
    st.subheader("⚙️ Gerenciamento de OPs")
    st.markdown("Aqui você pode finalizar, deletar ou reprogramar OPs. Ao reprogramar, todas as OPs seguintes são ajustadas automaticamente.")
    
    df_ger = carregar_dados()
    
    if not df_ger.empty:
        # Mostrar apenas OPs pendentes e setups
        df_programadas = df_ger[
            df_ger["status"].isin(["Pendente", "Setup"])
        ].sort_values(["maquina", "inicio"])
        
        if df_programadas.empty:
            st.info("Nenhuma OP pendente encontrada")
        else:
            # Agrupar por máquina
            for maquina in sorted(df_programadas["maquina"].unique()):
                with st.expander(f"🏭 {maquina}", expanded=False):
                    df_maq = df_programadas[df_programadas["maquina"] == maquina]
                    
                    for _, prod in df_maq.iterrows():
                        # Pular setups na exibição principal (serão mostrados junto com a OP)
                        if prod["status"] == "Setup" and prod["vinculo_id"]:
                            continue
                            
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 2])
                        
                        with col1:
                            st.write(f"**{prod['pedido']}**")
                            if prod["status"] == "Setup":
                                st.caption("🔧 SETUP")
                            else:
                                desc = get_descricao_produto(prod['item'])
                                st.caption(f"Item: {prod['item']} - {desc[:30]}...")
                        
                        with col2:
                            st.write(f"Início: {prod['inicio'].strftime('%d/%m %H:%M')}")
                            st.write(f"Fim: {prod['fim'].strftime('%d/%m %H:%M')}")
                        
                        with col3:
                            if prod["status"] != "Setup":
                                st.metric("QTD", f"{int(prod['qtd']):,}")
                            else:
                                st.write("Setup")
                        
                        with col4:
                            if prod["status"] == "Pendente":
                                if prod["em_execucao"]:
                                    st.markdown("🟠 **Executando**")
                                elif prod["atrasada"]:
                                    st.markdown("🔴 **Atrasada**")
                                else:
                                    st.markdown("🔵 **Pendente**")
                            else:
                                st.markdown("⚪ **Setup**")
                        
                        with col5:
                            if prod["status"] == "Pendente":
                                # Botão de finalizar
                                if st.button("✅ Finalizar", key=f"fin_{prod['id']}"):
                                    finalizar_op(prod["id"])
                                    st.success("OP finalizada!")
                                    st.rerun()
                                
                                # Botão de reprogramar
                                with st.popover("📅 Reprogramar"):
                                    st.markdown(f"**Reprogramar {prod['pedido']}**")
                                    
                                    nova_data = st.date_input(
                                        "Nova data",
                                        value=prod['inicio'].date(),
                                        key=f"data_{prod['id']}"
                                    )
                                    
                                    nova_hora = st.time_input(
                                        "Nova hora",
                                        value=prod['inicio'].time(),
                                        key=f"hora_{prod['id']}"
                                    )
                                    
                                    if st.button("Confirmar reprogramação", key=f"conf_{prod['id']}"):
                                        novo_inicio = datetime.combine(nova_data, nova_hora)
                                        reprogramar_op(prod["id"], novo_inicio, st.session_state.user_email)
                                        st.success("OP reprogramada! OPs seguintes ajustadas.")
                                        st.rerun()
                            
                            # Botão de deletar (para todos)
                            if st.button("🗑️ Deletar", key=f"del_{prod['id']}"):
                                deletar_op(prod["id"])
                                st.success("OP e setup deletados!")
                                st.rerun()
                        
                        st.divider()
    else:
        st.info("Nenhuma OP cadastrada")


# =================================================================
# ABA 5 - PRODUTOS
# =================================================================

with tab5:
    st.subheader("📋 Produtos")
    st.dataframe(
        df_produtos,
        use_container_width=True,
        hide_index=True
    )


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
            
            # Tabela por máquina
            st.subheader("Distribuição por Máquina")
            for maquina in MAQUINAS_SOPRO:
                df_maq = df_sopro[df_sopro["maquina"] == maquina]
                if not df_maq.empty:
                    cargas_maq = df_maq["qtd"].sum() / CARGA_UNIDADE
                    with st.expander(f"{maquina} - {cargas_maq:.1f} cargas"):
                        st.dataframe(
                            df_maq[["pedido", "qtd"]],
                            use_container_width=True,
                            hide_index=True
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
    "v7.3 | Industrial By William | PCP Serigrafia + Sopro | Setup automático 30min | Reprogramação em cascata"
)
