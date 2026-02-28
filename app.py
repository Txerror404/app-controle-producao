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

# Tabela de Produtos
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
# ABA 4 - CADASTRO DE PRODUTOS (CORRIGIDA)
# ===============================
with aba4:
    st.subheader("📦 Cadastrar Novo Produto")
    
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        novo_cod = st.text_input("Código do Produto (Ex: REF-100)", key="novo_codigo")
    with col2:
        nova_desc = st.text_input("Descrição/Nome do Produto", key="nova_descricao")
    with col3:
        novo_cli = st.text_input("Cliente", key="novo_cliente")
    
    if st.button("✅ Cadastrar Produto", key="btn_cadastrar_produto"):
        if novo_cod and nova_desc:
            try:
                # Verificar se o código já existe
                cursor.execute("SELECT codigo FROM produtos WHERE codigo = ?", (novo_cod,))
                if cursor.fetchone():
                    st.error("❌ Código já existe! Use um código diferente.")
                else:
                    cursor.execute("INSERT INTO produtos (codigo, descricao, cliente) VALUES (?, ?, ?)", 
                                   (novo_cod, nova_desc, novo_cli))
                    conn.commit()
                    st.success("✅ Produto cadastrado com sucesso!")
                    
                    # Limpar os campos usando session state
                    for key in ["novo_codigo", "nova_descricao", "novo_cliente"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erro inesperado: {str(e)}")
        else:
            st.warning("⚠️ Preencha pelo menos o código e a descrição do produto!")
    
    st.divider()
    
    st.subheader("📋 Produtos Cadastrados")
    df_p = carregar_produtos()
    
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
        
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            prod_del = st.selectbox("Selecionar produto para excluir", df_p['codigo'].tolist(), key="select_excluir_produto")
        with col_del2:
            if st.button("🗑️ Excluir Produto", key="btn_excluir_produto"):
                cursor.execute("DELETE FROM produtos WHERE codigo=?", (prod_del,))
                conn.commit()
                st.success(f"✅ Produto {prod_del} excluído com sucesso!")
                st.rerun()
    else:
        st.info("ℹ️ Nenhum produto cadastrado ainda.")

# ===============================
# ABA 1 - ADICIONAR PEDIDO
# ===============================
with aba1:
    st.subheader("➕ Novo Pedido de Produção")
    df_prods = carregar_produtos()
    
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_sel = st.selectbox("Máquina", MAQUINAS, key="sel_maquina")
        sugestao = obter_proximo_horario_livre(maq_sel)
    
    with col_prod:
        if not df_prods.empty:
            lista_codigos = [""] + df_prods['codigo'].tolist()
            cod_sel = st.selectbox("Buscar Produto Cadastrado", lista_codigos, key="sel_produto")
            
            if cod_sel and cod_sel != "":
                # Puxa descrição e cliente automaticamente
                produto_info = df_prods[df_prods['codigo'] == cod_sel].iloc[0]
                item_auto = produto_info['descricao']
                cliente_auto = produto_info['cliente'] if pd.notna(produto_info['cliente']) else ""
            else:
                item_auto = ""
                cliente_auto = ""
        else:
            st.warning("⚠️ Nenhum produto cadastrado. Cadastre produtos na aba 'Cadastro de Produtos'.")
            item_auto = ""
            cliente_auto = ""
            cod_sel = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        ped_in = st.text_input("Número do Pedido", placeholder="Ex: 5050", key="pedido_num")
        item_in = st.text_input("Descrição do Item", value=item_auto, key="item_desc")
        cliente_in = st.text_input("Cliente Vinculado", value=cliente_auto, key="cliente_nome")
    with col2:
        qtd = st.number_input("Quantidade", min_value=1, value=2380, key="qtd_prod")
        setup_in = st.number_input("Tempo de Setup (min)", min_value=0, value=30, key="setup_tempo")
    with col3:
        dt_in = st.date_input("Data de Início", sugestao.date(), key="data_inicio")
        hr_in = st.time_input("Hora de Início", sugestao.time(), key="hora_inicio")

    if st.button("🚀 Lançar Produção + Setup", key="btn_lancar"):
        if ped_in and item_in:
            ini_dt = datetime.combine(dt_in, hr_in)
            f_prod = ini_dt + timedelta(hours=qtd/CADENCIA)
            
            # Identificador inclui Cliente e Código para facilitar no Gantt
            identificador_pedido = f"{cliente_in} | {cod_sel} | Ped: {ped_in}"
            
            salvar_pedido_com_setup(maq_sel, identificador_pedido, item_in, ini_dt, f_prod, setup_in)
            st.success("✅ Produção agendada com sucesso!")
            st.rerun()
        else:
            st.error("❌ Preencha o número do pedido e a descrição do item!")

# ===============================
# ABA 2 - GANTT
# ===============================
with aba2:
    st.subheader("📊 Gráfico de Gantt - Programação da Produção")
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
            category_orders={"maquina": MAQUINAS},
            title="Linha vermelha = momento atual"
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.update_layout(showlegend=True, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Estatísticas rápidas
        col_est1, col_est2, col_est3 = st.columns(3)
        with col_est1:
            st.metric("Total de Pedidos", len(df))
        with col_est2:
            st.metric("Pendentes", len(df[df['status'] == 'Pendente']))
        with col_est3:
            st.metric("Concluídos", len(df[df['status'] == 'Concluído']))
    else:
        st.info("ℹ️ Nenhum pedido cadastrado ainda.")

# ===============================
# ABA 3 - GERENCIAR
# ===============================
with aba3:
    st.subheader("⚙️ Gerenciar Pedidos")
    df = carregar_dados()
    if not df.empty:
        df_ordenado = df.sort_values("inicio", ascending=False)
        
        for idx, row in df_ordenado.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
                
                # Formatação da data
                data_ini = row['inicio'].strftime('%d/%m %H:%M')
                data_fim = row['fim'].strftime('%H:%M')
                
                with col1:
                    if row['status'] == 'Setup':
                        st.write(f"🔧 **{row['pedido']}** | {data_ini} → {data_fim} ({row['status']})")
                    elif row['status'] == 'Concluído':
                        st.write(f"✅ ~~**{row['pedido']}**~~ | {data_ini} → {data_fim} (Concluído)")
                    else:
                        st.write(f"⏳ **{row['pedido']}** | {data_ini} → {data_fim} ({row['status']})")
                
                with col2:
                    if row["status"] != "Concluído" and row["status"] != "Setup":
                        if st.button("✅ OK", key=f"ok_{row['id']}_{idx}"):
                            cursor.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (row['id'],))
                            conn.commit()
                            st.rerun()
                
                with col3:
                    if st.button("🗑️ Apagar", key=f"del_{row['id']}_{idx}"):
                        cursor.execute("DELETE FROM agenda WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()
                
                with col4:
                    if row['status'] != 'Concluído' and row['status'] != 'Setup':
                        st.caption("Pendente")
                
                st.divider()
    else:
        st.info("ℹ️ Nenhum pedido cadastrado ainda.")

# ===============================
# RODAPÉ
# ===============================
st.divider()
st.caption("PCP William - Sistema de Controle de Produção v1.0")
