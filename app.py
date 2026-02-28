import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# ===============================
# 1. CONFIGURAÇÃO E ACESSO
# ===============================
st.set_page_config(page_title="PCP Industrial", layout="wide")
st_autorefresh(interval=30000, key="pcp_refresh_global")

ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = "sarita@deco.com.br"
MAQUINAS = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504 
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
if "user_email" not in st.session_state: st.session_state.user_email = ""

def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)

with conectar() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            maquina TEXT, 
            pedido TEXT, 
            item TEXT, 
            inicio TEXT, 
            fim TEXT, 
            status TEXT, 
            qtd REAL, 
            vinculo_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            codigo TEXT PRIMARY KEY, 
            descricao TEXT, 
            cliente TEXT
        )
    """)

def carregar_dados():
    with conectar() as c:
        df = pd.read_sql_query("SELECT * FROM agenda", c)
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}", 
            axis=1
        )
    return df

def proximo_horario(maq):
    """Retorna o próximo horário livre considerando TODOS os eventos (inclusive Setup)"""
    df = carregar_dados()
    if not df.empty:
        # Considera TODOS os eventos não concluídos (Pendente e Setup)
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

# --- LOGIN ---
if not st.session_state.auth_ok:
    st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        email = st.text_input("E-mail autorizado:").lower().strip()
        if st.button("Acessar Sistema", use_container_width=True):
            if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]: 
                st.session_state.auth_ok = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("E-mail não autorizado.")
    st.stop()

is_admin = st.session_state.user_email == ADMIN_EMAIL

# ===============================
# 2. TÍTULO PROFISSIONAL
# ===============================
st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-family: 'Segoe UI', sans-serif;">
            📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
        <p style="color: #888; margin: 5px 0 0 0;">👤 {st.session_state.user_email}</p>
    </div>
    """, unsafe_allow_html=True)

# ===============================
# 3. INTERFACE DE ABAS
# ===============================
aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançar OP", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📦 Catálogo", "📈 Cargas"])

# ===============================
# ABA 2 - GANTT (RÉGUA CORRIGIDA - DATA A CADA 9 HORAS)
# ===============================
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, 
            x_start="inicio", 
            x_end="fim", 
            y="maquina", 
            color="status_cor", 
            text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "qtd", "item"],
            color_discrete_map={
                "Pendente": "#3498db", 
                "Concluído": "#2ecc71", 
                "Setup": "#7f7f7f", 
                "Executando": "#ff7f0e"
            }
        )

        # CONFIGURAÇÃO DA RÉGUA - DATA a cada 9 horas
        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=2), agora + timedelta(hours=48)],
            dtick=32400000,  # 9 horas em milissegundos (9 * 60 * 60 * 1000)
            tickformatstops=[
                # Para intervalos menores que 9 horas, mostra apenas HORA
                dict(dtickrange=[None, 32400000], value="%H:%M"),
                # Para intervalos de 9 horas ou mais, mostra DATA + HORA
                dict(dtickrange=[32400001, None], value="%d/%m\n%H:%M")
            ],
            tickformat="%H:%M",  # Formato padrão para ticks individuais
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True,
            tickangle=0,  # Texto na horizontal
            tickfont=dict(size=11)
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        
        # LINHA VERMELHA DO MOMENTO ATUAL
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        # ANOTAÇÃO "AGORA"
        fig.add_annotation(
            x=agora, 
            y=1.08, 
            text=f"🔴 AGORA: {agora.strftime('%d/%m %H:%M')}", 
            showarrow=False, 
            yref="paper", 
            font=dict(color="#FF4B4B", size=14, family="Arial Black"),
            bgcolor="rgba(0,0,0,0.7)",
            bordercolor="#FF4B4B",
            borderwidth=1,
            borderpad=4
        )
        
        # CONFIGURAÇÃO DAS BARRAS
        fig.update_traces(
            textposition='inside', 
            insidetextanchor='start',
            width=0.85, 
            hovertemplate="<b>OP: %{customdata[0]}</b><br>Produto: %{customdata[2]}<br>Qtd: %{customdata[1]}<extra></extra>"
        )
        
        # LAYOUT GERAL
        fig.update_layout(
            height=550,
            bargap=0.1,
            margin=dict(l=10, r=10, t=90, b=10),
            legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
            hovermode="x unified",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # LEGENDA EXPLICATIVA
        st.caption("📅 **Régua:** Data aparece a cada 9 horas (15:00, 00:00, 09:00, 18:00...) | 🔴 Linha vermelha = momento atual")
        
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

# ===============================
# ABA 1 - LANÇAR OP
# ===============================
with aba1:
    with st.container(border=True):
        st.subheader("➕ Lançar Nova Ordem de Produção")
        df_p = pd.read_sql_query("SELECT * FROM produtos", conectar())
        
        col1, col2 = st.columns(2)
        with col1:
            maquina_sel = st.selectbox("🏭 Máquina", MAQUINAS, key="maq_lanc")
            
            if not df_p.empty:
                opcoes_prod = [f"{row['codigo']} - {row['descricao']}" for _, row in df_p.iterrows()]
                produto_sel = st.selectbox("📦 Produto", opcoes_prod, key="prod_lanc")
                codigo_prod = produto_sel.split(" - ")[0]
                
                # Buscar cliente automaticamente
                cliente_auto = df_p[df_p['codigo'] == codigo_prod]['cliente'].values[0]
            else:
                st.warning("⚠️ Cadastre produtos na aba Catálogo")
                produto_sel = None
                cliente_auto = ""
        
        with col2:
            op_num = st.text_input("🔢 Número da OP", key="op_lanc")
            cliente_in = st.text_input("👥 Cliente", value=cliente_auto, key="cli_lanc")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            qtd = st.number_input("📊 Quantidade", min_value=1, value=int(CARGA_UNIDADE), key="qtd_lanc")
        with col4:
            setup_min = st.number_input("⏱️ Setup (min)", min_value=0, value=30, key="setup_lanc")
        with col5:
            # Sugestão de horário
            sugestao = proximo_horario(maquina_sel)
            data_inicio = st.date_input("📅 Data Início", sugestao.date(), key="data_lanc")
            hora_inicio = st.time_input("⏰ Hora Início", sugestao.time(), key="hora_lanc")
        
        if st.button("🚀 LANÇAR PRODUÇÃO", type="primary", use_container_width=True):
            if not op_num:
                st.error("❌ Digite o número da OP!")
            elif not produto_sel:
                st.error("❌ Selecione um produto!")
            else:
                # Calcular horários
                inicio = datetime.combine(data_inicio, hora_inicio)
                fim_prod = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)
                
                with conectar() as conn:
                    cur = conn.cursor()
                    
                    # Inserir PRODUÇÃO
                    cur.execute("""
                        INSERT INTO agenda 
                        (maquina, pedido, item, inicio, fim, status, qtd) 
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        maquina_sel, 
                        f"{cliente_in} | OP:{op_num}", 
                        codigo_prod, 
                        inicio.strftime('%Y-%m-%d %H:%M:%S'), 
                        fim_prod.strftime('%Y-%m-%d %H:%M:%S'), 
                        "Pendente", 
                        qtd
                    ))
                    
                    producao_id = cur.lastrowid
                    
                    # Inserir SETUP (se houver)
                    if setup_min > 0:
                        fim_setup = fim_prod + timedelta(minutes=setup_min)
                        conn.execute("""
                            INSERT INTO agenda 
                            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) 
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (
                            maquina_sel, 
                            f"SETUP OP:{op_num}", 
                            "Ajuste/Troca", 
                            fim_prod.strftime('%Y-%m-%d %H:%M:%S'), 
                            fim_setup.strftime('%Y-%m-%d %H:%M:%S'), 
                            "Setup", 
                            0, 
                            producao_id
                        ))
                    
                    st.success(f"✅ OP {op_num} lançada com sucesso!")
                    st.balloons()
                    st.rerun()

# ===============================
# ABA 3 - GERENCIAR
# ===============================
with aba3:
    st.subheader("⚙️ Gerenciar Ordens de Produção")
    df_ger = carregar_dados()
    
    if not df_ger.empty:
        # Separar produções e seus setups
        producoes = df_ger[df_ger["status"] == "Pendente"].sort_values("inicio")
        
        for _, prod in producoes.iterrows():
            # Buscar setup vinculado
            setup = df_ger[(df_ger["vinculo_id"] == prod["id"]) & (df_ger["status"] == "Setup")]
            
            with st.expander(f"📦 {prod['maquina']} | {prod['pedido']} - {prod['item']}"):
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    st.write(f"**Período:** {prod['inicio'].strftime('%d/%m %H:%M')} às {prod['fim'].strftime('%H:%M')}")
                    st.write(f"**Quantidade:** {int(prod['qtd'])} unidades")
                    
                    if not setup.empty:
                        s = setup.iloc[0]
                        st.write(f"🔧 **Setup:** {s['inicio'].strftime('%H:%M')} às {s['fim'].strftime('%H:%M')}")
                
                with col_b:
                    if st.button("✅ Concluir", key=f"conc_{prod['id']}"):
                        with conectar() as c:
                            # Concluir produção
                            c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (prod['id'],))
                            # Concluir setup vinculado se existir
                            if not setup.empty:
                                c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (setup.iloc[0]['id'],))
                        st.rerun()
                
                with col_c:
                    if st.button("🗑️ Apagar", key=f"del_{prod['id']}"):
                        with conectar() as c:
                            # Apagar produção e setup vinculado
                            c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (prod['id'], prod['id']))
                        st.rerun()
    else:
        st.info("ℹ️ Nenhuma produção pendente.")

# ===============================
# ABA 4 - CATÁLOGO DE PRODUTOS
# ===============================
with aba4:
    st.subheader("📦 Catálogo de Produtos")
    
    with st.expander("➕ Cadastrar Novo Produto", expanded=True):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            novo_cod = st.text_input("Código do Produto", key="novo_cod")
        with col_c2:
            nova_desc = st.text_input("Descrição", key="nova_desc")
        with col_c3:
            novo_cli = st.text_input("Cliente", key="novo_cli")
        
        if st.button("✅ Cadastrar Produto", key="btn_cad_prod"):
            if novo_cod and nova_desc:
                with conectar() as conn:
                    try:
                        conn.execute(
                            "INSERT INTO produtos (codigo, descricao, cliente) VALUES (?, ?, ?)",
                            (novo_cod, nova_desc, novo_cli)
                        )
                        st.success(f"✅ Produto {novo_cod} cadastrado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Código já existe!")
            else:
                st.warning("⚠️ Código e descrição são obrigatórios!")
    
    # Lista de produtos
    df_prod = pd.read_sql_query("SELECT * FROM produtos ORDER BY codigo", conectar())
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True)
        
        # Excluir produto
        with st.expander("🗑️ Excluir Produto"):
            prod_del = st.selectbox("Selecionar produto", df_prod['codigo'].tolist())
            if st.button("Excluir", type="secondary"):
                with conectar() as c:
                    c.execute("DELETE FROM produtos WHERE codigo=?", (prod_del,))
                st.rerun()
    else:
        st.info("ℹ️ Nenhum produto cadastrado.")

# ===============================
# ABA 5 - CARGAS
# ===============================
with aba5:
    st.subheader(f"📈 Cargas por Máquina (Base: {CARGA_UNIDADE} unid/carga)")
    df_c = carregar_dados()
    
    if not df_c.empty:
        # Filtrar apenas produções pendentes (excluir setups)
        df_prod = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        
        cols = st.columns(4)
        for i, maq in enumerate(MAQUINAS):
            total_qtd = df_prod[df_prod["maquina"] == maq]["qtd"].sum()
            cargas = total_qtd / CARGA_UNIDADE
            
            with cols[i]:
                st.metric(
                    label=f"🏭 {maq.upper()}",
                    value=f"{cargas:.1f} cargas",
                    delta=f"{int(total_qtd)} unid"
                )
        
        # Detalhamento por máquina
        with st.expander("📋 Detalhamento por OP"):
            for maq in MAQUINAS:
                st.write(f"**{maq}**")
                df_maq = df_prod[df_prod["maquina"] == maq]
                if not df_maq.empty:
                    for _, row in df_maq.iterrows():
                        st.write(f"  • {row['pedido']}: {int(row['qtd'])} unid")
                else:
                    st.write("  • Nenhuma OP")
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

# ===============================
# RODAPÉ
# ===============================
st.divider()
col_r1, col_r2, col_r3 = st.columns(3)
with col_r1:
    st.caption(f"🕒 Última atualização: {agora.strftime('%d/%m/%Y %H:%M:%S')}")
with col_r3:
    st.caption("🏭 PCP Industrial v2.0 - Régua 9h")
