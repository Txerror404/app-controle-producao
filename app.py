import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import io
from streamlit_autorefresh import st_autorefresh

# ===============================
# 1. CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")

# ATUALIZAÇÃO AUTOMÁTICA: 30 segundos
st_autorefresh(interval=30000, key="pcp_refresh")

# Acesso liberado conforme solicitado
EMAILS_AUTORIZADOS = ["will@admin.com.br"]

# ===============================
# 2. SISTEMA DE ACESSO (LOGIN)
# ===============================
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🔐 PCP William</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            email_input = st.text_input("E-mail autorizado:").lower().strip()
            if st.button("Liberar Acesso", use_container_width=True):
                if email_input in EMAILS_AUTORIZADOS:
                    st.session_state.auth_ok = True
                    st.rerun()
                else:
                    st.error("E-mail não autorizado.")

if not st.session_state.auth_ok:
    tela_login()
    st.stop()

# ===============================
# 3. VARIÁVEIS E BANCO
# ===============================
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")

# ===============================
# 4. FUNÇÕES DE APOIO
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
        df_maq = df[(df["maquina"] == maq) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# ===============================
# 5. INTERFACE PRINCIPAL
# ===============================
st.title("🏭 Gestão de Produção Industrial")

with st.sidebar:
    st.title("👤 Usuário Ativo")
    st.write(f"Hora Local: **{agora.strftime('%H:%M:%S')}**")
    st.info("Atualização: 30s")
    if st.button("Sair do Sistema"):
        st.session_state.auth_ok = False
        st.rerun()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Novo Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 2: GANTT (COM ALERTA DE ATRASO) ---
with aba2:
    st.subheader("Cronograma de Máquinas")
    df_g = carregar_dados()
    
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        # Marca como 'Executando' o que está no horário atual e não foi concluído
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="pedido",
            category_orders={"maquina": MAQUINAS},
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
    else:
        fig = px.timeline(pd.DataFrame([{"maquina": m, "inicio": agora, "fim": agora} for m in MAQUINAS]), 
                          x_start="inicio", x_end="fim", y="maquina", category_orders={"maquina": MAQUINAS})
        fig.update_traces(visible=False)

    fig.update_yaxes(autorange="reversed", title="Máquinas")
    fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
    
    fig.add_annotation(
        x=agora, y=1.05, yref="paper",
        text=f"⏱️ AGORA: {agora.strftime('%H:%M')}",
        showarrow=False, font=dict(color="white", size=14),
        bgcolor="red", borderpad=4
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- LÓGICA DE AVISOS COM DETECÇÃO DE ATRASO ---
    st.markdown("---")
    cols_avisos = st.columns(len(MAQUINAS))
    
    for i, m in enumerate(MAQUINAS):
        # Filtra o que deveria estar acontecendo ou pendente para essa máquina
        df_maq_pendente = df_g[(df_g["maquina"] == m) & (df_g["status"] != "Concluído")] if not df_g.empty else pd.DataFrame()
        
        if df_maq_pendente.empty:
            cols_avisos[i].warning(f"⚠️ {m.upper()}\n\nSem carga programada.")
        else:
            # Verifica se alguma tarefa não concluída já deveria ter terminado
            # Se o 'agora' passou do 'fim' de qualquer tarefa não concluída, marca atraso
            atrasados = df_maq_pendente[df_maq_pendente["fim"] < agora]
            
            if not atrasados.empty:
                cols_avisos[i].error(f"🚨 {m.upper()}\n\nPRODUÇÃO EM ATRASO")
            else:
                cols_avisos[i].success(f"✅ {m.upper()}\n\nOperação em dia.")

# --- ABA 1: NOVO PEDIDO ---
with aba1:
    st.subheader("Programar Máquina")
    df_p = carregar_produtos()
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_s = st.selectbox("Máquina", MAQUINAS)
        sugestao = proximo_horario(maq_s)
        st.info(f"Sugerido: {sugestao.strftime('%d/%m %H:%M')}")
    
    with col_prod:
        if not df_p.empty:
            lista_p = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            p_sel = st.selectbox("Produto", [""] + lista_p)
            item_a = p_sel.split(" | ")[1] if p_sel else ""
            cli_a = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
        else:
            st.error("Cadastre produtos no Catálogo.")
            item_a, cli_a = "", ""

    with st.form("form_p"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Nº Pedido")
        cli_n = c1.text_input("Cliente", value=cli_a)
        qtd_n = c2.number_input("Quantidade", value=2380)
        set_n = c2.number_input("Setup (min)", value=30)
        c3, c4 = st.columns(2)
        dat_n = c3.date_input("Data", sugestao.date())
        hor_n = c4.time_input("Hora", sugestao.time())

        if st.form_submit_button("Confirmar Lançamento"):
            if ped_n and p_sel:
                ini = max(datetime.combine(dat_n, hor_n), proximo_horario(maq_s))
                fim = ini + timedelta(hours=qtd_n/CADENCIA)
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                (maq_s, f"{cli_n} | {ped_n}", item_a, ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
                    if set_n > 0:
                        fim_s = fim + timedelta(minutes=set_n)
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                    (maq_s, f"SETUP - {ped_n}", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), fim_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
                st.success("Salvo!"); st.rerun()

# --- ABA 3: GERENCIAR ---
with aba3:
    st.subheader("Gerenciar Ordem de Produção")
    df_ger = carregar_dados()
    if not df_ger.empty:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_ger.to_excel(writer, index=False)
        st.download_button("📥 Exportar Backup Excel", buf.getvalue(), "PCP_William.xlsx")
        
        for _, r in df_ger.sort_values("inicio", ascending=False).iterrows():
            cor_status = "🔴" if r['status'] != 'Concluído' and r['fim'] < agora else "⚪"
            with st.expander(f"{cor_status} {r['maquina']} - {r['pedido']}"):
                c1, c2 = st.columns([4, 1])
                c1.write(f"Início: {r['inicio']} | Fim: {r['fim']}")
                if c2.button("Excluir", key=f"d{r['id']}"):
                    with conectar() as c: c.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                    st.rerun()
                if r['status'] != 'Concluído' and c2.button("Concluir", key=f"c{r['id']}"):
                    with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                    st.rerun()

# --- ABA 4: CATÁLOGO ---
with aba4:
    with st.form("f_prod"):
        c1, c2, c3 = st.columns(3)
        cod = c1.text_input("Código")
        des = c2.text_input("Descrição")
        cli = c3.text_input("Cliente Padrão")
        if st.form_submit_button("Cadastrar Produto"):
            with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (cod, des, cli))
            st.rerun()
    st.dataframe(carregar_produtos(), use_container_width=True)
