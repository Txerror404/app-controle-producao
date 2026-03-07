import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# IMPORTS INTERNOS DO PROJETO
from db import criar_tabela, carregar_dados
from sheets import carregar_produtos_google
from utils import verificar_conflito

# =================================================================
# INICIALIZAÇÃO DO BANCO
# =================================================================

criar_tabela()

# =================================================================
# CONFIGURAÇÕES
# =================================================================

st.set_page_config(page_title="PCP Industrial - SISTEMA COMPLETO", layout="wide")

st_autorefresh(interval=120000, key="pcp_refresh_global")

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

MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1,17)]

TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504

fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# =================================================================
# ESTILO
# =================================================================

st.markdown("""
<style>

.block-container {
padding-top:0.5rem;
}

.modebar-container {
top:0!important;
}

.stTabs [data-baseweb="tab-list"] {
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
# PRODUTOS GOOGLE
# =================================================================

if "df_produtos" not in st.session_state:

    with st.spinner("Sincronizando Google Sheets..."):

        st.session_state.df_produtos = carregar_produtos_google()

df_produtos = st.session_state.df_produtos

# =================================================================
# CABEÇALHO
# =================================================================

st.markdown(f"""
<div style="background:#1E1E1E;padding:8px 15px;border-radius:8px;border-left:8px solid #FF4B4B;margin-bottom:15px;display:flex;justify-content:space-between;align-items:center;">
<div>

<h2 style="color:white;margin:0;font-size:20px;">
📊 PCP <span style="color:#FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS
</h2>

<p style="color:#888;margin:2px 0 0 0;font-size:12px;">
👤 Usuário: {st.session_state.user_email}
</p>

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
# FUNÇÃO PROXIMO HORÁRIO
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
# GANTT
# =================================================================

def renderizar_setor(lista_maquinas,altura=500):

    df = carregar_dados()

    if df.empty:

        st.info("Nenhuma OP programada.")
        return

    df_g = df[df["maquina"].isin(lista_maquinas)].copy()

    fig = px.timeline(
        df_g,
        x_start="inicio",
        x_end="fim",
        y="maquina",
        color="status",
        text="rotulo_barra"
    )

    fig.update_yaxes(autorange="reversed")

    fig.update_layout(height=altura)

    st.plotly_chart(fig,use_container_width=True)

# =================================================================
# ABAS
# =================================================================

aba1,aba2,aba3,aba4,aba5,aba6 = st.tabs([
"➕ Lançar",
"🎨 Serigrafia",
"🍼 Sopro",
"⚙️ Gerenciar",
"📋 Produtos",
"📈 Cargas"
])

# =================================================================
# ABA LANÇAMENTO
# =================================================================

with aba1:

    st.subheader("➕ Novo Lançamento")

    df_prod = df_produtos.copy()

    maq_sel = st.selectbox("Máquina",TODAS_MAQUINAS)

    item_sel = st.selectbox("ID ITEM",df_prod["id_item"].tolist())

    descricao="N/A"
    cliente="N/A"
    carga=CARGA_UNIDADE

    if item_sel:

        prod=df_prod[df_prod["id_item"]==item_sel]

        if not prod.empty:

            prod=prod.iloc[0]

            descricao=prod["descricao"]
            cliente=prod["cliente"]
            carga=int(prod["qtd_carga"])

    st.text_input("Descrição",descricao,disabled=True)
    st.text_input("Cliente",cliente,disabled=True)

    op_num = st.text_input("Número OP")

    qtd = st.number_input("Quantidade",value=carga)

    sugestao = proximo_horario(maq_sel)

    data = st.date_input("Data",sugestao.date())
    hora = st.time_input("Hora",sugestao.time())

    if st.button("🚀 CONFIRMAR E AGENDAR",use_container_width=True):

        inicio = datetime.combine(data,hora)

        fim = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)

        eventos = carregar_dados()

        if verificar_conflito(eventos,maq_sel,inicio,fim):

            st.error("⚠️ Conflito de horário nesta máquina!")
            st.stop()

        with sqlite3.connect("pcp.db") as conn:

            conn.execute("""
            INSERT INTO agenda
            (maquina,pedido,item,inicio,fim,status,qtd)
            VALUES (?,?,?,?,?,?,?)
            """,(
            maq_sel,
            f"{cliente} | OP:{op_num}",
            item_sel,
            inicio.strftime("%Y-%m-%d %H:%M:%S"),
            fim.strftime("%Y-%m-%d %H:%M:%S"),
            "Pendente",
            qtd
            ))

            conn.commit()

        st.success("OP programada!")

        st.rerun()

# =================================================================
# ABA GANTT
# =================================================================

with aba2:

    renderizar_setor(MAQUINAS_SERIGRAFIA,450)

with aba3:

    renderizar_setor(MAQUINAS_SOPRO,700)

# =================================================================
# PRODUTOS
# =================================================================

with aba5:

    st.dataframe(df_produtos,use_container_width=True)

# =================================================================
# CARGAS
# =================================================================

with aba6:

    df=carregar_dados()

    if not df.empty:

        df_p=df[(df["status"]=="Pendente")&(df["qtd"]>0)]

        total=df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)]["qtd"].sum()

        st.metric(
        "Total Cargas Sopro",
        f"{total/CARGA_UNIDADE:.1f}"
        )

st.divider()

st.caption("PCP Industrial | William | Streamlit")
