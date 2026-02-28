import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import time
import io

# ===============================
# 1. CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")

# Lista de e-mails autorizados (ADICIONE OS E-MAILS AQUI)
EMAILS_AUTORIZADOS = [
    "william@seuemail.com", 
    "admin@empresa.com",
    "producao@empresa.com"
]

# ===============================
# 2. SISTEMA DE ACESSO (LOGIN)
# ===============================
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🔐 PCP William</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Acesso restrito ao pessoal autorizado.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            email_input = st.text_input("Digite seu e-mail para acessar:").lower().strip()
            if st.button("Liberar Acesso", use_container_width=True):
                if email_input in EMAILS_AUTORIZADOS:
                    st.session_state.auth_ok = True
                    st.rerun()
                else:
                    st.error("E-mail não autorizado. Fale com o William.")

# Se não estiver logado, para o código aqui e mostra a tela de login
if not st.session_state.auth_ok:
    tela_login()
    st.stop()

# ===============================
# 3. VARIÁVEIS E BANCO (PÓS-LOGIN)
# ===============================
# Auto-refresh estável
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.rerun()

MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

# Inicializar tabelas
with conectar() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")

# Sidebar com Logout
with st.sidebar:
    st.title("👤 Usuário Ativo")
    st.write("Acesso Liberado ✅")
    if st.button("Sair do Sistema"):
        st.session_state.auth_ok = False
        st.rerun()

# ===============================
# 4. FUNÇÕES DE DADOS
# ===============================
def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
    return df

def carregar_produtos():
    with conectar() as c:
        return pd.read_sql_query("SELECT * FROM produtos", c)

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[df["maquina"] == maq]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# ===============================
# 5. DASHBOARD PRINCIPAL
# ===============================
st.title("🏭 Dashboard de Produção")

df_m = carregar_dados()
if not df_m.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("🔵 Pendentes", len(df_m[df_m["status"] == "Pendente"]))
    executando = len(df_m[(df_m["inicio"] <= agora) & (df_m["fim"] >= agora) & (df_m["status"] != "Concluído")])
    c2.metric("🟠 Em Execução", executando)
    c3.metric("🟢 Concluídos", len(df_m[df_m["status"] == "Concluído"]))

st.divider()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Adicionar Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# ABA 4 - CATÁLOGO
with aba4:
    st.subheader("Cadastro de Produtos")
    with st.form("cad_prod", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        des = c2.text_input("Descrição")
        cli = c3.text_input("Cliente Padrão")
        if st.form_submit_button("Salvar Produto"):
            if cod and des:
                with conectar() as conn:
                    conn.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (cod, des, cli))
                st.success("Produto cadastrado!")
                st.rerun()
    st.dataframe(carregar_produtos(), use_container_width=True)

# ABA 1 - NOVO PEDIDO
with aba1:
    st.subheader("Programar Máquina")
    df_p = carregar_produtos()
    
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_s = st.selectbox("Máquina", MAQUINAS)
        sugestao = proximo_horario(maq_s)
    
    with col_prod:
        if not df_p.empty:
            lista_p = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            p_sel = st.selectbox("Buscar Produto", [""] + lista_p)
            item_auto = p_sel.split(" | ")[1] if p_sel else ""
            cli_auto = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
        else:
            st.warning("Cadastre produtos primeiro.")
            item_auto, cli_auto = "", ""

    with st.form("form_ped"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Nº Pedido")
        cli_n = c1.text_input("Cliente", value=cli_auto)
        qtd_n = c2.number_input("Quantidade", value=2380)
        set_n = c2.number_input("Setup (min)", value=30)
        
        c3, c4 = st.columns(2)
        dat_n = c3.date_input("Data Início", sugestao.date())
        hor_n = c4.time_input("Hora Início", sugestao.time())

        if st.form_submit_button("🚀 Confirmar Programação"):
            if ped_n and p_sel:
                ini_real = max(datetime.combine(dat_n, hor_n), proximo_horario(maq_s))
                fim_prod = ini_real + timedelta(hours=qtd_n/CADENCIA)
                label = f"{cli_n} | {ped_n} ({item_auto})"
                
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                (maq_s, label, item_auto, ini_real.strftime('%Y-%m-%d %H:%M:%S'), fim_prod.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
                    if set_n > 0:
                        fim_set = fim_prod + timedelta(minutes=set_n)
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                    (maq_s, f"SETUP - {label}", "Ajuste", fim_prod.strftime('%Y-%m-%d %H:%M:%S'), fim_set.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
                st.success("Agendado com sucesso!")
                st.rerun()

# ABA 2 - GANTT
with aba2:
    st.subheader("Gráfico de Produção")
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] == "Pendente"), "status_cor"] = "Executando"
        
        fig = px.timeline(df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="pedido",
                         category_orders={"maquina": MAQUINAS},
                         color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"})
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem pedidos.")

# ABA 3 - GERENCIAR
with aba3:
    st.subheader("Gestão de Pedidos")
    df_ger = carregar_dados()
    if not df_ger.empty:
        # Exportação Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_ger.to_excel(writer, index=False)
        st.download_button("📥 Baixar Backup Excel", buf.getvalue(), "PCP_William.xlsx", key="ex_btn")
        
        st.divider()
        for _, r in df_ger.sort_values("inicio", ascending=False).iterrows():
            with st.expander(f"{r['maquina']} | {r['pedido']} ({r['status']})"):
                c1, c2 = st.columns([4, 1])
                c1.write(f"Início: {r['inicio'].strftime('%d/%m %H:%M')} | Fim: {r['fim'].strftime('%d/%m %H:%M')}")
                if c2.button("🗑️ Excluir", key=f"del_{r['id']}"):
                    with conectar() as conn:
                        conn.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                    st.rerun()
                if r['status'] == "Pendente":
                    if c2.button("✅ Concluir", key=f"ok_{r['id']}"):
                        with conectar() as conn:
                            conn.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                        st.rerun()
