import psycopg2
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# CONFIGURAÇÃO DA PÁGINA

st.set_page_config(
    page_title="PCP Industrial - SISTEMA COMPLETO",
    layout="wide"
)

# CONEXÃO COM BANCO SUPABASE

DATABASE_URL = "postgresql://postgres.ogxrgnaedmcbaqgryosg:pcp2026supabase@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"


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

# TESTE DE CONEXÃO

try:
    conn = conectar()
    conn.close()
except Exception as e:
    st.error(f"Falha na conexão com Supabase: {e}")
    st.stop()

# CRIAÇÃO DA TABELA (CASO NÃO EXISTA)

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

# AUTO REFRESH

st_autorefresh(interval=120000, key="pcp_refresh_global")

# CONFIGURAÇÕES GERAIS

ADMIN_EMAIL = "will@admin.com.br"

OPERACIONAL_EMAIL = [
    "sarita@will.com.br",
    "oneida@will.com.br"
]

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

# FUSO HORÁRIO

fuso_br = pytz.timezone("America/Sao_Paulo")

agora = datetime.now(fuso_br).replace(tzinfo=None)

# GOOGLE SHEETS

GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"


# ESTILO DA INTERFACE

st.markdown("""
<style>

.block-container {
    padding-top: 0.5rem;
}

.modebar-container {
    top:0!important;
}

.stTabs [data-baseweb="tab-list"]{
    gap:10px;
}

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
# CARREGAR DADOS DO BANCO (SUPABASE)
# =================================================================

def carregar_dados():

    conn = conectar()

    df = pd.read_sql_query(
        "SELECT * FROM agenda",
        conn
    )

    conn.close()

    if not df.empty:

        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)

        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status']=="Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1
        )

    return df


# =================================================================
# PRÓXIMO HORÁRIO LIVRE DA MÁQUINA
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
# INSERIR PRODUÇÃO
# =================================================================

def inserir_producao(maquina,pedido,item,inicio,fim,qtd,usuario):

    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO agenda
        (maquina,pedido,item,inicio,fim,status,qtd,criado_por,criado_em)
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

    conn.commit()
    cur.close()
    conn.close()

    return producao_id


# =================================================================
# INSERIR SETUP
# =================================================================

def inserir_setup(maquina,pedido,inicio,fim,vinculo,usuario):

    conn = conectar()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO agenda
        (maquina,pedido,item,inicio,fim,status,qtd,vinculo_id,criado_por,criado_em)
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

    cur.execute(
        """
        UPDATE agenda
        SET inicio=%s,
            fim=%s,
            alterado_por=%s,
            alterado_em=%s
        WHERE id=%s
        """,
        (
            novo_inicio,
            novo_fim,
            usuario,
            agora,
            id_op
        )
    )

    conn.commit()
    cur.close()
    conn.close()
    # =================================================================
# LOGIN
# =================================================================

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:

    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)

    col1,col2,col3 = st.columns([1,1.5,1])

    with col2:

        email = st.text_input("E-mail autorizado:").lower().strip()

        if st.button("Acessar Sistema",use_container_width=True):

            if email in [ADMIN_EMAIL] + OPERACIONAL_EMAIL:

                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()

    st.stop()


# =================================================================
# CARREGAR PRODUTOS
# =================================================================

if 'df_produtos' not in st.session_state:

    with st.spinner("Sincronizando produtos..."):

        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos


# =================================================================
# CABEÇALHO
# =================================================================

st.markdown(f"""
<div style="background:#1E1E1E;padding:8px 15px;border-radius:8px;border-left:8px solid #FF4B4B;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;">
<div>

<h2 style="color:white;margin:0;font-size:20px;">📊 PCP | CRONOGRAMA</h2>
<p style="color:#888;margin:2px 0 0 0;font-size:12px;">👤 {st.session_state.user_email}</p>

</div>

<div style="text-align:center;border:1px solid #FF4B4B;padding:2px 15px;border-radius:5px;background:#0E1117;">
<h3 style="color:#FF4B4B;margin:0;font-family:'Courier New';font-size:22px;">
⏰ {agora.strftime('%H:%M:%S')}
</h3>
<p style="color:#aaa;margin:-2px 0 2px 0;font-size:12px;border-top:1px dashed #FF4B4B;padding-top:2px;">
{agora.strftime('%d/%m/%Y')}
</p>
</div>
</div>
""",unsafe_allow_html=True)


# =================================================================
# ABAS
# =================================================================

aba1, aba2, aba3, aba4 = st.tabs(["➕ Lançar OP","🎨 Serigrafia","🍼 Sopro","⚙️ Gerenciar"])


# =================================================================
# LANÇAMENTO
# =================================================================

with aba1:

    st.subheader("➕ Nova Ordem de Produção")

    c1,c2 = st.columns(2)

    with c1:

        maq_sel = st.selectbox("Máquina",TODAS_MAQUINAS)

        item_sel = st.selectbox(
            "Item",
            df_produtos["id_item"].tolist()
        )

        descricao = get_descricao_produto(item_sel)

        st.text_input("Descrição",value=descricao,disabled=True)

    with c2:

        op_num = st.text_input("Número OP")

        qtd_lanc = st.number_input("Quantidade",value=CARGA_UNIDADE)

    st.divider()

    sugestao = proximo_horario(maq_sel)

    c3,c4 = st.columns(2)

    data_ini = c3.date_input("Data início",sugestao.date())
    hora_ini = c4.time_input("Hora início",sugestao.time())

    minutos_setup = st.number_input("Tempo setup (min)",value=30)

    if st.button("🚀 AGENDAR",use_container_width=True):

        inicio_dt = datetime.combine(data_ini,hora_ini)

        fim_dt = inicio_dt + timedelta(hours=qtd_lanc/CADENCIA_PADRAO)

        producao_id = inserir_producao(
            maq_sel,
            f"OP:{op_num}",
            item_sel,
            inicio_dt,
            fim_dt,
            qtd_lanc,
            st.session_state.user_email
        )

        fim_setup = fim_dt + timedelta(minutes=minutos_setup)

        inserir_setup(
            maq_sel,
            f"SETUP {op_num}",
            fim_dt,
            fim_setup,
            producao_id,
            st.session_state.user_email
        )

        st.success("OP criada com sucesso")
        st.rerun()


# =================================================================
# FUNÇÃO GANTT
# =================================================================

def renderizar_setor(maquinas):

    df = carregar_dados()

    df = df[df["maquina"].isin(maquinas)]

    if df.empty:

        st.info("Sem programação")
        return

    fig = px.timeline(
        df,
        x_start="inicio",
        x_end="fim",
        y="maquina",
        color="status",
        text="rotulo_barra"
    )

    fig.update_yaxes(autorange="reversed")

    fig.add_vline(
        x=agora,
        line_dash="dash",
        line_color="red"
    )

    st.plotly_chart(fig,use_container_width=True)


# =================================================================
# SERIGRAFIA
# =================================================================

with aba2:

    renderizar_setor(MAQUINAS_SERIGRAFIA)


# =================================================================
# SOPRO
# =================================================================

with aba3:

    renderizar_setor(MAQUINAS_SOPRO)


# =================================================================
# GERENCIAR
# =================================================================

with aba4:

    df = carregar_dados()

    df = df[df["status"].isin(["Pendente","Setup","Manutenção"])]

    if df.empty:

        st.info("Nenhuma OP programada")
        st.stop()

    for _,prod in df.sort_values("inicio").iterrows():

        with st.expander(f"{prod['maquina']} | {prod['pedido']}"):

            st.write("Item:",prod["item"])
            st.write("Início:",prod["inicio"])
            st.write("Fim:",prod["fim"])

            col1,col2,col3 = st.columns(3)

            if col1.button("Finalizar",key=f"f{prod['id']}"):

                finalizar_op(prod["id"])
                st.rerun()

            if col2.button("Deletar",key=f"d{prod['id']}"):

                deletar_op(prod["id"])
                st.rerun()

            if col3.button("Reprogramar",key=f"r{prod['id']}"):

                novo_inicio = prod["inicio"] + timedelta(hours=1)

                novo_fim = prod["fim"] + timedelta(hours=1)

                reprogramar_op(
                    prod["id"],
                    novo_inicio,
                    novo_fim,
                    st.session_state.user_email
                )

                st.rerun()
