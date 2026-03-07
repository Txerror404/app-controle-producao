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
