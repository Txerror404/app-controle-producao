import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
import time
import io

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(page_title="PCP William - Industrial", layout="wide")

# Lógica de Auto-Refresh estável (60 segundos)
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 60:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Variáveis Globais
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA = 2380
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# ===============================
# BANCO DE DADOS
# ===============================
def conectar():
    return sqlite3.connect("pcp.db", check_same_thread=False)

# Inicialização
conn = conectar()
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY AUTOINCREMENT, maquina TEXT, pedido TEXT, item TEXT, inicio TEXT, fim TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS produtos (codigo TEXT PRIMARY KEY, descricao TEXT, cliente TEXT)")
conn.commit()
conn.close()

# ===============================
# FUNÇÕES DE APOIO
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
        df = pd.read_sql_query("SELECT * FROM produtos", c)
    return df

def obter_proximo_horario_livre(maquina_nome):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[df["maquina"] == maquina_nome]
        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)
    return agora

# ===============================
# INTERFACE
# ===============================
st.title("🏭 PCP William - Sistema Industrial")

# Dashboard de Métricas
df_m = carregar_dados()
if not df_m.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔵 Pendentes", len(df_m[df_m["status"] == "Pendente"]))
    c2.metric("🟠 Em Execução", len(df_m[(df_m["inicio"] <= agora) & (df_m["fim"] >= agora) & (df_m["status"] != "Concluído")]))
    c3.metric("🟢 Concluídos", len(df_m[df_m["status"] == "Concluído"]))
    c4.metric("🕒 Atualização", agora.strftime("%H:%M"))

st.divider()

aba1, aba2, aba3, aba4 = st.tabs(["➕ Novo Pedido", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo"])

# --- ABA 4: CATÁLOGO ---
with aba4:
    st.subheader("Cadastro de Produtos")
    with st.form("form_prod", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        c_cod = col1.text_input("Código")
        c_des = col2.text_input("Descrição")
        c_cli = col3.text_input("Cliente Padrão")
        if st.form_submit_button("Salvar Produto"):
            if c_cod and c_des:
                with conectar() as c:
                    c.execute("INSERT OR REPLACE INTO produtos VALUES (?,?,?)", (c_cod, c_des, c_cli))
                    c.commit()
                st.success("Produto salvo!")
                st.rerun()

    df_p = carregar_produtos()
    st.dataframe(df_p, use_container_width=True)

# --- ABA 1: NOVO PEDIDO ---
with aba1:
    st.subheader("Programar Máquina")
    df_p = carregar_produtos()
    
    col_maq, col_prod = st.columns(2)
    with col_maq:
        maq_s = st.selectbox("Máquina", MAQUINAS, key="sel_maq")
        sugestao = obter_proximo_horario_livre(maq_s)
        st.info(f"Horário sugerido: {sugestao.strftime('%d/%m %H:%M')}")

    with col_prod:
        if not df_p.empty:
            lista_p = [f"{r['codigo']} | {r['descricao']}" for _, r in df_p.iterrows()]
            prod_s = st.selectbox("Produto", [""] + lista_p, key="sel_p")
            item_val = prod_s.split(" | ")[1] if prod_s else ""
            cli_val = df_p[df_p['codigo'] == prod_s.split(" | ")[0]]['cliente'].values[0] if prod_s else ""
        else:
            st.warning("Cadastre produtos na aba Catálogo.")
            item_val, cli_val = "", ""

    with st.form("form_pedido"):
        c1, c2 = st.columns(2)
        ped_n = c1.text_input("Pedido Nº")
        cli_n = c1.text_input("Cliente", value=cli_val)
        qtd_n = c2.number_input("Quantidade", value=2380)
        set_n = c2.number_input("Setup (min)", value=30)
        
        c3, c4 = st.columns(2)
        dat_n = c3.date_input("Início em", sugestao.date())
        hor_n = c4.time_input("Hora", sugestao.time())

        if st.form_submit_button("🚀 Lançar na Produção"):
            if ped_n and prod_s:
                ini_dt = datetime.combine(dat_n, hor_n)
                # Garante que não encavale
                ini_real = max(ini_dt, obter_proximo_horario_livre(maq_s))
                fim_dt = ini_real + timedelta(hours=qtd_n/CADENCIA)
                
                label = f"{cli_n} | {ped_n} ({item_val})"
                
                with conectar() as c:
                    cur = c.cursor()
                    cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                (maq_s, label, item_val, ini_real.strftime('%Y-%m-%d %H:%M:%S'), fim_dt.strftime('%Y-%m-%d %H:%M:%S'), "Pendente"))
                    if set_n > 0:
                        fim_set = fim_dt + timedelta(minutes=set_n)
                        cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status) VALUES (?,?,?,?,?,?)",
                                    (maq_s, f"SETUP - {label}", "Ajuste", fim_dt.strftime('%Y-%m-%d %H:%M:%S'), fim_set.strftime('%Y-%m-%d %H:%M:%S'), "Setup"))
                    c.commit()
                st.success("Agendado!")
                st.rerun()

# --- ABA 2: GANTT ---
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        # Status visual dinâmico
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] == "Pendente"), "status_cor"] = "Executando"

        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor",
            text="pedido", category_orders={"maquina": MAQUINAS},
            color_discrete_map={"Pendente": "#1f77b4", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        fig.add_annotation(x=agora, y=1.02, yref="paper", text="AGORA", showarrow=False, font=dict(color="red", size=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum pedido para mostrar.")

# --- ABA 3: GERENCIAR ---
with aba3:
    df_ger = carregar_dados()
    if not df_ger.empty:
        # Botão de Exportar
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_ger.to_excel(writer, index=False)
        st.download_button("📥 Exportar para Excel", output.getvalue(), "PCP_William.xlsx", key="btn_excel")
        
        st.divider()
        for _, r in df_ger.sort_values("inicio", ascending=False).iterrows():
            with st.expander(f"{r['maquina']} | {r['pedido']}"):
                c1, c2 = st.columns([4, 1])
                c1.write(f"Início: {r['inicio']} | Fim: {r['fim']}")
                if c2.button("Apagar", key=f"del_{r['id']}"):
                    with conectar() as c:
                        c.execute("DELETE FROM agenda WHERE id=?", (r['id'],))
                        c.commit()
                    st.rerun()
                if r['status'] == "Pendente":
                    if c2.button("OK", key=f"ok_{r['id']}"):
                        with conectar() as c:
                            c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (r['id'],))
                            c.commit()
                        st.rerun()
