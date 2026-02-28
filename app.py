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

# Acesso liberado
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
    conn.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT, qtd REAL)")
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
    if st.button("Sair do Sistema"):
        st.session_state.auth_ok = False
        st.rerun()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Novo Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 2: GANTT ---
with aba2:
    st.subheader("Cronograma de Máquinas")
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        fig = px.timeline(df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="pedido",
                         category_orders={"maquina": MAQUINAS},
                         color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"})
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.add_annotation(x=agora, y=1.05, yref="paper", text=f"⏱️ AGORA: {agora.strftime('%H:%M')}", showarrow=False, font=dict(color="white", size=14), bgcolor="red", borderpad=4)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    cols_avisos = st.columns(len(MAQUINAS))
    for i, m in enumerate(MAQUINAS):
        df_m_p = df_g[(df_g["maquina"] == m) & (df_g["status"] != "Concluído")] if not df_g.empty else pd.DataFrame()
        if df_m_p.empty: cols_avisos[i].warning(f"⚠️ {m.upper()}\n\nSem carga.")
        elif not df_m_p[df_m_p["fim"] < agora].empty: cols_avisos[i].error(f"🚨 {m.upper()}\n\nEM ATRASO")
        else: cols_avisos[i].success(f"✅ {m.upper()}\n\nEm dia.")

# --- ABA 1: NOVO PEDIDO ---
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
            p_sel = st.selectbox("Produto", [""] + lista_p)
            item_a = p_sel.split(" | ")[1] if p_sel else ""; cli_a = df_p[df_p['codigo'] == p_sel.split(" | ")[0]]['cliente'].values[0] if p_sel else ""
        else: st.error("Cadastre produtos no Catálogo."); item_a, cli_a = "", ""

    with st.form("form_p"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Nº Pedido")
        cli_n = c1.text_input("Cliente", value=cli_a)
        qtd_n = c2.number_input("Quantidade", value=2380)
        set_n = c2.number_input("Setup (min)", value=30)
        c3, c4 = st.columns(2)
        dat_n = c3.date_input("Data", sugestao.date()); hor_n = c4.time_input("Hora", sugestao.time())
        if st.form_submit_button("Confirmar Lançamento"):
            if ped_n and p_sel:
                ini = datetime.combine(dat_n, hor_n)
                fim = ini + timedelta(hours=qtd_n/CADENCIA)
                with conectar() as conn:
                    conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                (maq_s, f"{cli_n} | {ped_n}", item_a, ini.strftime('%Y-%m-%d %H:%M:%S'), fim.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_n))
                    if set_n > 0:
                        fim_s = fim + timedelta(minutes=set_n)
                        conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
                                    (maq_s, f"SETUP - {ped_n}", "Ajuste", fim.strftime('%Y-%m-%d %H:%M:%S'), fim_s.strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0))
                st.success("Salvo!"); st.rerun()

# --- ABA 3: GERENCIAR (MELHORADA COM SUB-TABS) ---
with aba3:
    st.subheader("Painel de Gestão de Ordens")
    df_ger = carregar_dados()
    
    tab_pendentes, tab_concluidos = st.tabs(["⚡ Em Aberto / Atrasados", "✅ Histórico (Concluídos)"])

    with tab_pendentes:
        if not df_ger.empty:
            # Filtra apenas o que não foi concluído
            df_aberto = df_ger[df_ger["status"] != "Concluído"].sort_values("inicio")
            
            if df_aberto.empty:
                st.success("Tudo em dia! Nenhuma ordem pendente.")
            else:
                for _, r in df_aberto.iterrows():
                    # Lógica de cor para o cabeçalho (Vermelho se atrasado)
                    is_atrasado = r['fim'] < agora
                    prefixo = "🚨 ATRASADO -" if is_atrasado else "⏳"
                    
                    with st.expander(f"{prefixo} {r['maquina']} | {r['pedido']}"):
                        col_info, col_edit = st.columns([2, 2])
                        with col_info:
                            st.write(f"**Item:** {r['item']}")
                            st.write(f"**Início:** {r['inicio'].strftime('%d/%m %H:%M')}")
                            st.write(f"**Fim:** {r['fim'].strftime('%d/%m %H:%M')}")
                            
                            c1, c2 = st.columns(2)
                            if c1.button("✅ CONCLUIR", key=f"c{r['id']}", use_container_width=True):
                                with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                                st.rerun()
                            if c2.button("🗑️ EXCLUIR", key=f"d{r['id']}", use_container_width=True):
                                with conectar() as c: c.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                                st.rerun()

                        with col_edit:
                            st.markdown("🛠️ **Ajustar Planejamento**")
                            n_data = st.date_input("Nova Data", value=r['inicio'].date(), key=f"dt{r['id']}")
                            n_hora = st.time_input("Nova Hora", value=r['inicio'].time(), key=f"hr{r['id']}")
                            if st.button("💾 Atualizar Horário", key=f"up{r['id']}"):
                                n_ini = datetime.combine(n_data, n_hora)
                                n_fim = n_ini + (r['fim'] - r['inicio'])
                                with conectar() as c:
                                    c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (n_ini.strftime('%Y-%m-%d %H:%M:%S'), n_fim.strftime('%Y-%m-%d %H:%M:%S'), r['id']))
                                st.success("Horário atualizado!")
                                st.rerun()

    with tab_concluidos:
        if not df_ger.empty:
            df_concluido = df_ger[df_ger["status"] == "Concluído"].sort_values("fim", ascending=False)
            if df_concluido.empty:
                st.info("Nenhum pedido concluído ainda.")
            else:
                # Botão para exportar apenas o histórico
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer: df_concluido.to_excel(writer, index=False)
                st.download_button("📥 Baixar Histórico Excel", buf.getvalue(), "Historico_PCP.xlsx")
                
                for _, r in df_concluido.iterrows():
                    with st.expander(f"✅ {r['maquina']} | {r['pedido']} (Fim: {r['fim'].strftime('%d/%m %H:%M')})"):
                        st.write(f"**Item:** {r['item']}")
                        st.write(f"**Período:** {r['inicio'].strftime('%d/%m %H:%M')} até {r['fim'].strftime('%d/%m %H:%M')}")
                        if st.button("Reabrir Ordem", key=f"re{r['id']}"):
                            with conectar() as c: c.execute("UPDATE agenda SET status='Pendente' WHERE id=?", (r['id'],))
                            st.rerun()

# --- ABA 4: CATÁLOGO ---
with aba4:
    with st.form("f_prod"):
        c1, c2, c3 = st.columns(3); cod = c1.text_input("Código"); des = c2.text_input("Descrição"); cli = c3.text_input("Cliente Padrão")
        if st.form_submit_button("Cadastrar Produto"):
            with conectar() as c: c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (cod, des, cli))
            st.rerun()
    st.dataframe(carregar_produtos(), use_container_width=True)
