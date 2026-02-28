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
# ABA 4 - CADASTRO DE PRODUTOS
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
                    
                    # Limpar os campos
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
# ABA 1 - ADICIONAR PEDIDO (CORRIGIDA)
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
            # Criar lista de opções com formato mais amigável
            opcoes_produto = []
            for _, row in df_prods.iterrows():
                cliente = row['cliente'] if pd.notna(row['cliente']) else "Sem cliente"
                opcao = f"{row['codigo']} - {row['descricao']} ({cliente})"
                opcoes_produto.append(opcao)
            
            opcoes_com_blank = [""] + opcoes_produto
            
            # Verificar se já existe um produto selecionado no session state
            indice_padrao = 0
            if 'ultimo_produto_selecionado' in st.session_state:
                ultimo = st.session_state['ultimo_produto_selecionado']
                if ultimo in opcoes_com_blank:
                    indice_padrao = opcoes_com_blank.index(ultimo)
            
            produto_selecionado = st.selectbox(
                "Buscar Produto Cadastrado", 
                opcoes_com_blank, 
                index=indice_padrao,
                key="sel_produto_completo"
            )
            
            # Se selecionou um produto, extrair as informações
            if produto_selecionado and produto_selecionado != "":
                # Salvar no session state
                st.session_state['ultimo_produto_selecionado'] = produto_selecionado
                
                # Extrair o código (parte antes do " - ")
                codigo_selecionado = produto_selecionado.split(" - ")[0]
                
                # Buscar as informações completas do produto
                produto_info = df_prods[df_prods['codigo'] == codigo_selecionado].iloc[0]
                item_auto = produto_info['descricao']
                cliente_auto = produto_info['cliente'] if pd.notna(produto_info['cliente']) else ""
                
                # Salvar no session state para persistir
                st.session_state['item_auto'] = item_auto
                st.session_state['cliente_auto'] = cliente_auto
                st.session_state['codigo_auto'] = codigo_selecionado
            else:
                # Se não selecionou nada, limpar o session state
                st.session_state['item_auto'] = ""
                st.session_state['cliente_auto'] = ""
                st.session_state['codigo_auto'] = ""
                if 'ultimo_produto_selecionado' in st.session_state:
                    del st.session_state['ultimo_produto_selecionado']
        else:
            st.warning("⚠️ Nenhum produto cadastrado. Cadastre produtos na aba 'Cadastro de Produtos'.")
            # Inicializar session state vazio
            st.session_state['item_auto'] = ""
            st.session_state['cliente_auto'] = ""
            st.session_state['codigo_auto'] = ""

    # Recuperar valores do session state (se existirem)
    item_padrao = st.session_state.get('item_auto', "")
    cliente_padrao = st.session_state.get('cliente_auto', "")
    codigo_padrao = st.session_state.get('codigo_auto', "")

    col1, col2, col3 = st.columns(3)
    with col1:
        ped_in = st.text_input("Número do Pedido", placeholder="Ex: 5050", key="pedido_num")
        
        # Mostrar o código do produto selecionado (readonly)
        if codigo_padrao:
            st.text_input("Código do Produto", value=codigo_padrao, disabled=True, key="codigo_readonly")
        else:
            st.text_input("Código do Produto", value="", disabled=True, key="codigo_readonly")
            
        item_in = st.text_input("Descrição do Item", value=item_padrao, key="item_desc")
        
    with col2:
        cliente_in = st.text_input("Cliente Vinculado", value=cliente_padrao, key="cliente_nome")
        qtd = st.number_input("Quantidade", min_value=1, value=2380, key="qtd_prod")
        
    with col3:
        setup_in = st.number_input("Tempo de Setup (min)", min_value=0, value=30, key="setup_tempo")
        dt_in = st.date_input("Data de Início", sugestao.date(), key="data_inicio")
        hr_in = st.time_input("Hora de Início", sugestao.time(), key="hora_inicio")

    if st.button("🚀 Lançar Produção + Setup", key="btn_lancar"):
        if ped_in and item_in:
            ini_dt = datetime.combine(dt_in, hr_in)
            f_prod = ini_dt + timedelta(hours=qtd/CADENCIA)
            
            # Identificador inclui Cliente e Código para facilitar no Gantt
            if codigo_padrao:
                identificador_pedido = f"{cliente_in} | {codigo_padrao} | Ped: {ped_in}"
            else:
                identificador_pedido = f"{cliente_in} | Ped: {ped_in}"
            
            salvar_pedido_com_setup(maq_sel, identificador_pedido, item_in, ini_dt, f_prod, setup_in)
            st.success("✅ Produção agendada com sucesso!")
            
            # Limpar seleção de produto após lançar
            for key in ['sel_produto_completo', 'item_auto', 'cliente_auto', 'codigo_auto', 'ultimo_produto_selecionado']:
                if key in st.session_state:
                    del st.session_state[key]
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
