import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import time # Importado para o relógio

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config(page_title="PCP William - Profissional", layout="wide")

# --- LÓGICA DO RELÓGIO (AUTO REFRESH) ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Atualiza a cada 30 segundos
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# ===============================
# BANCO SQLITE
# ===============================
def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

conn = conectar()
cursor = conn.cursor()

# Tabelas
cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")
conn.commit()

# ===============================
# FUNÇÕES DE LÓGICA
# ===============================
def carregar_dados():
    c = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda", c)
    c.close()
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
    return df

def carregar_produtos():
    c = conectar()
    df = pd.read_sql_query("SELECT * FROM produtos", c)
    c.close()
    return df

def obter_proximo_horario_livre(maquina_nome):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[df["maquina"] == maquina_nome]
        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)
    return agora

def salvar_pedido_com_setup(maquina, pedido, item, inicio_desejado, minutos_setup, qtd):
    # Garante que não comece antes do que a máquina está livre ou de agora
    horario_livre = max(inicio_desejado, obter_proximo_horario_livre(maquina))
    
    tempo_producao_horas = qtd / CADENCIA
    fim_producao = horario_livre + timedelta(hours=tempo_producao_horas)
    
    c = conectar()
    cur = c.cursor()
    # Inserir Produção
    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                (maquina, pedido, item, horario_livre.strftime('%Y-%m-%d %H:%M:%S'), fim_producao.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
    
    # Inserir Setup
    if minutos_setup > 0:
        fim_setup = fim_producao + timedelta(minutes=minutos_setup)
        cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                    (maquina, f"SETUP - {pedido}", "Ajuste", fim_producao.strftime('%Y-%m-%d %H:%M:%S'), fim_setup.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
    
    c.commit()
    c.close()
    return horario_livre, fim_producao

# ===============================
# INTERFACE
# ===============================
st.title("🏭 PCP William - Dashboard Industrial")

# Métricas de topo (Dashboard rápido)
df_resumo = carregar_dados()
if not df_resumo.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("🔵 Pendentes", len(df_resumo[df_resumo["status"] == "Pendente"]))
    executando = len(df_resumo[(df_resumo["inicio"] <= agora) & (df_resumo["fim"] >= agora) & (df_resumo["status"] != "Concluído")])
    c2.metric("🟠 Em Execução", executando)
    c3.metric("🟢 Concluídos", len(df_resumo[df_resumo["status"] == "Concluído"]))

aba1, aba2, aba3, aba4 = st.tabs(["➕ Adicionar Pedido", "📊 Gantt de Produção", "⚙️ Gerenciar", "📦 Cadastro de Produtos"])

# --- ABA 4: CADASTRO --- (Mantida a sua lógica)
with aba4:
    st.subheader("📦 Cadastrar Novo Produto")
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1: novo_cod = st.text_input("Código", key="n_cod")
    with col2: nova_desc = st.text_input("Descrição", key="n_desc")
    with col3: novo_cli = st.text_input("Cliente", key="n_cli")
    
    if st.button("✅ Cadastrar Produto"):
        if novo_cod and nova_desc:
            c = conectar(); cur = c.cursor()
            cur.execute("INSERT INTO produtos (codigo, descricao, cliente) VALUES (?, ?, ?)", (novo_cod, nova_desc, novo_cli))
            c.commit(); c.close()
            st.success("Produto salvo!")
            st.rerun()

    st.divider()
    df_p = carregar_produtos()
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)

# --- ABA 1: ADICIONAR PEDIDO --- (Com correção de sobreposição)
with aba1:
    st.subheader("➕ Novo Pedido")
    df_prods = carregar_produtos()
    
    col_m, col_p = st.columns(2)
    with col_m:
        maq_sel = st.selectbox("Máquina", MAQUINAS)
        sugestao = obter_proximo_horario_livre(maq_sel)
        st.write(f"🕒 Próximo horário livre: **{sugestao.strftime('%d/%m %H:%M')}**")

    with col_p:
        if not df_prods.empty:
            opcoes = [f"{r['codigo']} - {r['descricao']}" for _, r in df_prods.iterrows()]
            prod_sel = st.selectbox("Produto", [""] + opcoes)
            if prod_sel:
                cod = prod_sel.split(" - ")[0]
                info = df_prods[df_prods['codigo'] == cod].iloc[0]
                st.session_state.item_f = info['descricao']
                st.session_state.cli_f = info['cliente']
        else:
            st.warning("Cadastre produtos primeiro.")

    c1, c2 = st.columns(2)
    with c1:
        ped_n = st.text_input("Nº Pedido")
        cli_n = st.text_input("Cliente", value=st.session_state.get('cli_f', ""))
    with c2:
        qtd_n = st.number_input("Quantidade", value=2380)
        setup_n = st.number_input("Setup (min)", value=30)

    if st.button("🚀 Lançar Produção", type="primary"):
        if ped_n and prod_sel:
            item_n = prod_sel.split(" - ")[1]
            label = f"{cli_n} | {ped_n} ({item_n})"
            salvar_pedido_com_setup(maq_sel, label, item_n, sugestao, setup_n, qtd_n)
            st.success("Pedido agendado!")
            st.rerun()

# --- ABA 2: GANTT --- (Restaurado o Relógio Visual)
with aba2:
    st.subheader("📊 Gráfico de Gantt")
    df_g = carregar_dados()
    if not df_g.empty:
        # Lógica visual de "Executando"
        df_g["status_visual"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] == "Pendente"), "status_visual"] = "Executando"

        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_visual",
            text="pedido", category_orders={"maquina": MAQUINAS},
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
        fig.update_yaxes(autorange="reversed")
        
        # LINHA DO RELÓGIO
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.add_annotation(x=agora, y=1.05, yref="paper", text=f"AGORA: {agora.strftime('%H:%M')}", showarrow=False, font=dict(color="red"))
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")

# --- ABA 3: GERENCIAR ---
with aba3:
    st.subheader("⚙️ Gerenciar")
    df_ger = carregar_dados()
    if not df_ger.empty:
        for i, r in df_ger.sort_values("inicio", ascending=False).iterrows():
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{r['pedido']}** | {r['maquina']} | {r['inicio'].strftime('%d/%m %H:%M')}")
            if col2.button("🗑️", key=f"del_{r['id']}"):
                c = conectar(); cur = c.cursor()
                cur.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                c.commit(); c.close(); st.rerun()
