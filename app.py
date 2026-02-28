import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import io

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")

MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# ===============================
# BANCO DE DADOS
# ===============================
def conectar_banco():
    return sqlite3.connect("pcp.db", check_same_thread=False)

# Inicialização e Migração Automática
conn = conectar_banco()
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")

# Tenta adicionar a coluna cliente caso a tabela já exista sem ela
try:
    cursor.execute("ALTER TABLE produtos ADD COLUMN cliente TEXT")
except:
    pass
conn.commit()
conn.close()

# ===============================
# FUNÇÕES DE APOIO
# ===============================
def carregar_dados():
    with conectar_banco() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
    return df

def carregar_produtos():
    with conectar_banco() as c:
        df = pd.read_sql_query("SELECT * FROM produtos", c)
    return df

def obter_proximo_horario_livre(maquina_nome):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maquina_nome) & (df["status"] != "Concluído")]
        if not df_maq.empty:
            return df_maq["fim"].max()
    return agora

# ===============================
# INTERFACE PRINCIPAL
# ===============================
st.title("🏭 PCP William - Sistema de Controle")

aba1, aba2, aba3, aba4 = st.tabs(["➕ Adicionar Pedido", "📊 Gantt Industrial", "⚙️ Gerenciar", "📦 Cadastro de Produtos"])

# --- ABA 4: CADASTRO DE PRODUTOS ---
with aba4:
    st.subheader("📦 Cadastrar Novo Produto")
    c1, c2, c3 = st.columns([2, 3, 2])
    with c1: n_cod = st.text_input("Código do Produto", key="cad_cod")
    with c2: n_des = st.text_input("Descrição / Nome", key="cad_des")
    with c3: n_cli = st.text_input("Cliente Padrão", key="cad_cli")
    
    if st.button("Salvar no Catálogo", key="btn_save_prod"):
        if n_cod and n_des:
            try:
                with conectar_banco() as c:
                    c.execute("INSERT INTO produtos (codigo, descricao, cliente) VALUES (?, ?, ?)", (n_cod, n_des, n_cli))
                    c.commit()
                st.success(f"Produto {n_cod} cadastrado!")
                st.rerun()
            except: st.error("Erro: Código já cadastrado.")
        else: st.warning("Preencha Código e Descrição.")
    
    st.divider()
    df_p = carregar_produtos()
    st.dataframe(df_p, use_container_width=True)
    
    if not df_p.empty:
        p_del = st.selectbox("Produto para excluir", df_p['codigo'].tolist(), key="sel_del_p")
        if st.button("Excluir Produto Permanentemente"):
            with conectar_banco() as c:
                c.execute("DELETE FROM produtos WHERE codigo=?", (p_del,))
                c.commit()
            st.rerun()

# --- ABA 1: ADICIONAR PEDIDO ---
with aba1:
    st.subheader("➕ Programar Produção")
    df_prods = carregar_produtos()
    
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_sel = st.selectbox("Máquina", MAQUINAS, key="add_maq")
        sugestao = obter_proximo_horario_livre(maq_sel)
    
    with col_prod:
        if not df_prods.empty:
            lista_c = [""] + df_prods['codigo'].tolist()
            cod_sel = st.selectbox("Buscar Produto Cadastrado", lista_c, key="add_cod")
            if cod_sel != "":
                row = df_prods[df_prods['codigo'] == cod_sel].iloc[0]
                item_a, cli_a = row['descricao'], row['cliente']
            else: item_a, cli_a = "", ""
        else:
            st.warning("Cadastre produtos na aba ao lado primeiro!")
            item_a, cli_a, cod_sel = "", "", ""

    c1, c2, c3 = st.columns(3)
    with c1:
        ped_n = st.text_input("Número do Pedido", key="add_ped")
        item_n = st.text_input("Descrição do Item", value=item_a, key="add_item")
        cli_n = st.text_input("Cliente", value=cli_a, key="add_cli_final")
    with c2:
        qtd = st.number_input("Quantidade", min_value=1, value=2380)
        setup = st.number_input("Setup (minutos)", value=30)
    with c3:
        dt_in = st.date_input("Data de Início", sugestao.date())
        hr_in = st.time_input("Hora de Início", sugestao.time())

    if st.button("🚀 Confirmar e Lançar", use_container_width=True):
        if ped_n and item_n:
            inicio_dt = datetime.combine(dt_in, hr_in)
            fim_dt = inicio_dt + timedelta(hours=qtd/CADENCIA)
            # Nome que aparecerá no gráfico
            label = f"{cli_n} | {ped_n} ({item_n})"
            
            with conectar_banco() as c:
                c.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                          (maq_sel, label, item_n, inicio_dt.strftime('%Y-%m-%d %H:%M:%S'), fim_dt.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
                if setup > 0:
                    fim_setup = fim_dt + timedelta(minutes=setup)
                    c.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                              (maq_sel, f"SETUP - {label}", "Ajuste", fim_dt.strftime('%Y-%m-%d %H:%M:%S'), fim_setup.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
                c.commit()
            st.success("Lançado com sucesso!")
            st.rerun()

# --- ABA 2: GANTT INDUSTRIAL ---
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status",
            text="pedido", hover_data=["item"],
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"},
            category_orders={"maquina": MAQUINAS}
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_width=3, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Nenhum dado para exibir no gráfico.")

# --- ABA 3: GERENCIAR E EXPORTAR ---
with aba3:
    df_m = carregar_dados()
    if not df_m.empty:
        # Exportação
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_m.to_excel(writer, index=False)
        st.download_button("📥 Baixar Planilha Excel", output.getvalue(), "PCP_William.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        st.divider()
        # Lista de Ações
        for _, r in df_m.sort_values("inicio", ascending=False).iterrows():
            col1, col2, col3 = st.columns([5,1,1])
            col1.write(f"**{r['pedido']}** | {r['inicio'].strftime('%d/%m %H:%M')} ({r['status']})")
            if r['status'] != "Concluído":
                if col2.button("✔", key=f"ok_{r['id']}"):
                    with conectar_banco() as c:
                        c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                        c.commit()
                    st.rerun()
            if col3.button("🗑", key=f"del_{r['id']}"):
                with conectar_banco() as c:
                    c.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                    c.commit()
                st.rerun()
