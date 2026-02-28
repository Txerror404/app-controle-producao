import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config(page_title="PCP William - Profissional", layout="wide")

MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# ===============================
# BANCO SQLITE
# ===============================
conn = sqlite3.connect("pcp.db", check_same_thread=False)
cursor = conn.cursor()

# Tabela de Agenda
cursor.execute("""
CREATE TABLE IF NOT EXISTS agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maquina TEXT,
    pedido TEXT,
    item TEXT,
    inicio TEXT,
    fim TEXT,
    status TEXT
)
""")

# Tabela de Produtos (ATUALIZADA COM CLIENTE)
cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    codigo TEXT PRIMARY KEY,
    descricao TEXT,
    cliente TEXT
)
""")
conn.commit()

# ===============================
# FUNÇÕES
# ===============================
def carregar_dados():
    df = pd.read_sql_query("SELECT * FROM agenda", conn)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
    return df

def carregar_produtos():
    return pd.read_sql_query("SELECT * FROM produtos", conn)

def obter_proximo_horario_livre(maquina_nome):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maquina_nome) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return df_maq["fim"].max()
    return agora

def salvar_pedido_com_setup(maquina, pedido, item, inicio, fim_prod, minutos_setup):
    cursor.execute("""
        INSERT INTO agenda (maquina, pedido, item, inicio, fim, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (maquina, pedido, item, inicio.strftime('%Y-%m-%d %H:%M:%S'), fim_prod.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
    
    if minutos_setup > 0:
        fim_setup = fim_prod + timedelta(minutes=minutos_setup)
        cursor.execute("""
            INSERT INTO agenda (maquina, pedido, item, inicio, fim, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (maquina, f"SETUP - {pedido}", "Limpeza/Ajuste", fim_prod.strftime('%Y-%m-%d %H:%M:%S'), fim_setup.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
    conn.commit()

# ===============================
# INTERFACE
# ===============================
st.title("📊 PCP William - Sistema Integrado")

aba1, aba2, aba3, aba4 = st.tabs(["➕ Adicionar Pedido", "📊 Gantt de Produção", "⚙️ Gerenciar", "📦 Cadastro de Produtos"])

# ===============================
# ABA 4 - CADASTRO DE PRODUTOS
# ===============================
with aba4:
    st.subheader("Cadastrar Novo Produto")
    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        novo_cod = st.text_input("Código do Produto (Ex: REF-100)")
    with c2:
        nova_desc = st.text_input("Descrição/Nome do Produto")
    with c3:
        novo_cli = st.text_input("Cliente")
    
    if st.button("Cadastrar Produto"):
        if novo_cod and nova_desc:
            try:
                cursor.execute("INSERT INTO produtos (codigo, descricao, cliente) VALUES (?, ?, ?)", 
                               (novo_cod, nova_desc, novo_cli))
                conn.commit()
                st.success("Produto cadastrado com sucesso!")
                st.rerun()
            except:
                st.error("Erro: Verifique se o código já existe ou se há campos vazios.")
    
    st.divider()
    st.subheader("Produtos Cadastrados")
    df_p = carregar_produtos()
    st.dataframe(df_p, use_container_width=True)
    
    if not df_p.empty:
        prod_del = st.selectbox("Selecionar produto para excluir", df_p['codigo'].tolist())
        if st.button("Excluir Produto"):
            cursor.execute("DELETE FROM produtos WHERE codigo=?", (prod_del,))
            conn.commit()
            st.rerun()

# ===============================
# ABA 1 - ADICIONAR PEDIDO
# ===============================
with aba1:
    st.subheader("Novo Pedido")
    df_prods = carregar_produtos()
    
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_sel = st.selectbox("Máquina", MAQUINAS)
        sugestao = obter_proximo_horario_livre(maq_sel)
    
    with col_prod:
        if not df_prods.empty:
            lista_codigos = [""] + df_prods['codigo'].tolist()
            cod_sel = st.selectbox("Buscar Produto Cadastrado", lista_codigos)
            
            if cod_sel != "":
                # Puxa descrição e cliente automaticamente
                item_auto = df_prods[df_prods['codigo'] == cod_sel]['descricao'].values[0]
                cliente_auto = df_prods[df_prods['codigo'] == cod_sel]['cliente'].values[0]
            else:
                item_auto = ""
                cliente_auto = ""
        else:
            st.warning("Nenhum produto cadastrado.")
            item_auto = ""
            cliente_auto = ""
            cod_sel = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        ped_in = st.text_input("Número do Pedido", placeholder="Ex: 5050")
        item_in = st.text_input("Descrição do Item", value=item_auto)
        cliente_in = st.text_input("Cliente Vinculado", value=cliente_auto)
    with col2:
        qtd = st.number_input("Quantidade", min_value=1, value=2380)
        setup_in = st.number_input("Tempo de Setup (min)", min_value=0, value=30)
    with col3:
        dt_in = st.date_input("Início", sugestao.date())
        hr_in = st.time_input("Hora", sugestao.time())

    if st.button("Lançar Produção + Setup"):
        if ped_in and item_in:
            ini_dt = datetime.combine(dt_in, hr_in)
            f_prod = ini_dt + timedelta(hours=qtd/CADENCIA)
            
            # Identificador inclui Cliente e Código para facilitar no Gantt
            identificador_pedido = f"{cliente_in} | {cod_sel} | Ped: {ped_in}"
            
            salvar_pedido_com_setup(maq_sel, identificador_pedido, item_in, ini_dt, f_prod, setup_in)
            st.success("Produção agendada! ✅")
            st.rerun()
        else:
            st.error("Preencha os campos obrigatórios!")

# ===============================
# ABA 2 - GANTT
# ===============================
with aba2:
    df = carregar_dados()
    if not df.empty:
        fig = px.timeline(
            df, x_start="inicio", x_end="fim", y="maquina",
            color="status", text="pedido",
            color_discrete_map={
                "Pendente": "#1f77b4", 
                "Concluído": "#2ecc71",
                "Setup": "#7f7f7f"
            },
            category_orders={"maquina": MAQUINAS}
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

# ===============================
# ABA 3 - GERENCIAR
# ===============================
with aba3:
    df = carregar_dados()
    if not df.empty:
        for _, row in df.sort_values("inicio", ascending=False).iterrows():
            c1, c2, c3 = st.columns([5,1,1])
            c1.write(f"**{row['pedido']}** | {row['inicio'].strftime('%d/%m %H:%M')} -> {row['fim'].strftime('%H:%M')} ({row['status']})")
            if row["status"] != "Concluído":
                if c2.button("OK", key=f"ok{row['id']}"):
                    cursor.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
            if c3.button("Apagar", key=f"del{row['id']}"):
                cursor.execute("DELETE FROM agenda WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
