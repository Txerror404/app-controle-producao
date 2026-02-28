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

# URL da sua planilha publicada
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"

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

# ===============================
# FUNÇÃO PARA CARREGAR PRODUTOS DO GOOGLE SHEETS
# ===============================
@st.cache_data(ttl=300)  # Cache de 5 minutos
def carregar_produtos_google():
    """Carrega os produtos diretamente do Google Sheets"""
    try:
        # Baixar CSV da planilha publicada
        df = pd.read_csv(GOOGLE_SHEETS_URL, sep=',', encoding='utf-8')
        
        # Limpar nomes das colunas (remover espaços extras, mas manter underline)
        df.columns = df.columns.str.strip()
        
        # Debug: mostrar colunas encontradas (opcional, pode remover depois)
        # st.write("Colunas encontradas:", df.columns.tolist())
        
        # Garantir que ID_ITEM existe
        if 'ID_ITEM' not in df.columns:
            st.error("❌ Coluna 'ID_ITEM' não encontrada na planilha!")
            return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'descricao_completa', 'qtd_carga'])
        
        # Usar ID_ITEM como identificador principal
        df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
        
        # Descrição - usando DESCRIÇÃO_1 (com underline)
        if 'DESCRIÇÃO_1' in df.columns:
            df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
        else:
            # Tentar variações do nome
            desc_col = None
            for col in df.columns:
                if 'DESCRIÇÃO' in col.upper() or 'DESCRICAO' in col.upper():
                    desc_col = col
                    break
            if desc_col:
                df['descricao'] = df[desc_col].astype(str).str.strip()
            else:
                df['descricao'] = ''
        
        # Cliente - se não existir ou estiver vazio, preencher com "N/A"
        if 'CLIENTE' in df.columns:
            df['cliente'] = df['CLIENTE'].astype(str).str.strip()
            df['cliente'] = df['cliente'].apply(lambda x: x if x and x != 'nan' and x != '' else 'N/A')
        else:
            df['cliente'] = 'N/A'
        
        # Quantidade por carga
        if 'QTD/CARGA' in df.columns:
            # Converter para número, tratando vírgulas e pontos
            df['qtd_carga'] = pd.to_numeric(
                df['QTD/CARGA'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            ).fillna(CARGA_UNIDADE)
        else:
            df['qtd_carga'] = CARGA_UNIDADE
        
        # Máquina (se disponível)
        if 'MQ' in df.columns:
            df['maquina'] = df['MQ'].astype(str).str.strip()
        else:
            df['maquina'] = ''
        
        # Preencher valores nulos
        df = df.fillna('N/A')
        
        # Criar campo 'descricao_completa' para exibição nos selects
        df['descricao_completa'] = df.apply(
            lambda row: f"{row['id_item']} - {row['descricao']}", 
            axis=1
        )
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar planilha: {e}")
        # Retorna DataFrame vazio com as colunas necessárias
        return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'descricao_completa', 'qtd_carga'])

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
    df = carregar_dados()
    if not df.empty:
        df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
        if not df_maq.empty:
            return max(agora, df_maq["fim"].max())
    return agora

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
            else: st.error("E-mail não autorizado.")
    st.stop()

st.markdown(f"""
    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 20px;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-family: 'Segoe UI', sans-serif;">
            📊 CRONOGRAMA DE MÁQUINAS <span style="color: #FF4B4B;">|</span> PCP INDUSTRIAL
        </h1>
        <p style="color: #888; margin: 5px 0 0 0;">👤 {st.session_state.user_email}</p>
    </div>
    """, unsafe_allow_html=True)

aba1, aba2, aba3, aba4, aba5 = st.tabs(["➕ Lançar OP", "📊 Gantt Real-Time", "⚙️ Gerenciar", "📋 Produtos (Google)", "📈 Cargas"])

# ============================================================
# ABA 2 - GANTT + CARDS DE ACOMPANHAMENTO
# ============================================================
with aba2:
    df_g = carregar_dados()
    if not df_g.empty:
        df_g["status_cor"] = df_g["status"]
        df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
        
        fig = px.timeline(
            df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
            category_orders={"maquina": MAQUINAS},
            custom_data=["pedido", "qtd", "item"],
            color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
        )

        fig.update_xaxes(
            type='date',
            range=[agora - timedelta(hours=2), agora + timedelta(hours=48)],
            dtick=10800000, 
            tickformat="%d/%m\n%H:%M",
            gridcolor='rgba(255,255,255,0.1)',
            showgrid=True,
            tickangle=0,
            tickfont=dict(size=10)
        )
        
        fig.update_yaxes(autorange="reversed", title="")
        fig.add_vline(x=agora, line_dash="dash", line_color="red", line_width=2)
        
        fig.add_annotation(
            x=agora, y=1.15, 
            text=f"AGORA: {agora.strftime('%H:%M')}", 
            showarrow=False, yref="paper", 
            font=dict(color="red", size=18, family="Arial Black"),
            align="center"
        )
        
        fig.update_traces(textposition='inside', insidetextanchor='start', width=0.85)
        fig.update_layout(height=500, margin=dict(l=10, r=10, t=100, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # --- CARDS DE ACOMPANHAMENTO ---
        st.markdown("---")
        atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
        maqs_em_uso = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído")]["maquina"].unique()
        ociosas = [m for m in MAQUINAS if m not in maqs_em_uso]
        
        col_c1, col_c2, col_c3 = st.columns(3)
        col_c1.metric("🚨 OPs ATRASADAS", f"{atrasadas} itens")
        col_c2.metric("💤 MÁQUINAS OCIOSAS", f"{len(ociosas)}")
        if ociosas:
            col_c3.warning(f"Sem programação: {', '.join(ociosas)}")
        else:
            col_c3.success("✅ Todas as máquinas ocupadas")
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

# ===============================
# ABA 1 - LANÇAR OP (COM DESCRIÇÃO_1 CORRIGIDA)
# ===============================
with aba1:
    with st.container(border=True):
        st.subheader("➕ Lançar Nova Ordem de Produção")
        
        # Carregar produtos do Google Sheets
        with st.spinner("Carregando produtos da planilha..."):
            df_produtos = carregar_produtos_google()
        
        col1, col2 = st.columns(2)
        with col1:
            maquina_sel = st.selectbox("🏭 Máquina", MAQUINAS, key="maq_lanc")
            
            if not df_produtos.empty:
                # Lista de produtos para selectbox (mostrando ID_ITEM + descrição)
                opcoes_prod = df_produtos['descricao_completa'].tolist()
                produto_sel = st.selectbox("📦 Produto (ID_ITEM - DESCRIÇÃO_1)", opcoes_prod, key="prod_lanc")
                
                # Extrair ID_ITEM do produto selecionado (parte antes do " - ")
                id_item_sel = produto_sel.split(" - ")[0] if " - " in produto_sel else produto_sel
                
                # Buscar informações completas do produto pelo ID_ITEM
                produto_info = df_produtos[df_produtos['id_item'] == id_item_sel]
                if not produto_info.empty:
                    info = produto_info.iloc[0]
                    # Cliente vem da planilha ou "N/A"
                    cliente_auto = info.get('cliente', 'N/A')
                    qtd_carga_sugerida = info.get('qtd_carga', CARGA_UNIDADE)
                    
                    # Garantir que seja número
                    try:
                        qtd_carga_sugerida = float(qtd_carga_sugerida) if qtd_carga_sugerida else CARGA_UNIDADE
                    except:
                        qtd_carga_sugerida = CARGA_UNIDADE
                else:
                    cliente_auto = "N/A"
                    qtd_carga_sugerida = CARGA_UNIDADE
            else:
                st.error("❌ Não foi possível carregar produtos da planilha. Verifique a URL.")
                produto_sel = None
                id_item_sel = ""
                cliente_auto = "N/A"
                qtd_carga_sugerida = CARGA_UNIDADE
        
        with col2:
            op_num = st.text_input("🔢 Número da OP", key="op_lanc")
            cliente_in = st.text_input("👥 Cliente", value=cliente_auto, key="cli_lanc", disabled=True)  # Read-only
        
        col3, col4, col5 = st.columns(3)
        qtd = col3.number_input("📊 Quantidade", min_value=1, value=int(qtd_carga_sugerida), key="qtd_lanc")
        setup_min = col4.number_input("⏱️ Setup (min)", min_value=0, value=30, key="setup_lanc")
        sugestao = proximo_horario(maquina_sel)
        data_inicio = col5.date_input("📅 Data Início", sugestao.date(), key="data_lanc")
        hora_inicio = col5.time_input("⏰ Hora Início", sugestao.time(), key="hora_lanc")
        
        if st.button("🚀 LANÇAR PRODUÇÃO", type="primary", use_container_width=True):
            if op_num and produto_sel:
                inicio = datetime.combine(data_inicio, hora_inicio)
                fim_prod = inicio + timedelta(hours=qtd/CADENCIA_PADRAO)
                with conectar() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) 
                        VALUES (?,?,?,?,?,?,?)
                    """, (maquina_sel, f"{cliente_in} | OP:{op_num}", id_item_sel, 
                          inicio.strftime('%Y-%m-%d %H:%M:%S'), fim_prod.strftime('%Y-%m-%d %H:%M:%S'), 
                          "Pendente", qtd))
                    producao_id = cur.lastrowid
                    if setup_min > 0:
                        fim_setup = fim_prod + timedelta(minutes=setup_min)
                        conn.execute("""
                            INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) 
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (maquina_sel, f"SETUP OP:{op_num}", "Ajuste/Troca", 
                              fim_prod.strftime('%Y-%m-%d %H:%M:%S'), fim_setup.strftime('%Y-%m-%d %H:%M:%S'), 
                              "Setup", 0, producao_id))
                st.success(f"✅ OP {op_num} lançada!"); 
                st.rerun()
            else:
                if not op_num:
                    st.error("❌ Digite o número da OP!")
                elif not produto_sel:
                    st.error("❌ Selecione um produto!")

# ===============================
# ABA 3 - GERENCIAR
# ===============================
with aba3:
    st.subheader("⚙️ Gerenciar Ordens de Produção")
    df_ger = carregar_dados()
    
    if not df_ger.empty:
        producoes = df_ger[df_ger["status"] == "Pendente"].sort_values("inicio")
        
        if producoes.empty:
            st.info("✅ Nenhuma produção pendente no momento.")
        else:
            for _, prod in producoes.iterrows():
                setup = df_ger[(df_ger["vinculo_id"] == prod["id"]) & (df_ger["status"] == "Setup")]
                
                with st.expander(f"📦 {prod['maquina']} | {prod['pedido']} - {prod['item']}"):
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    
                    with col_a:
                        st.write(f"**Período:** {prod['inicio'].strftime('%d/%m %H:%M')} às {prod['fim'].strftime('%H:%M')}")
                        st.write(f"**Quantidade:** {int(prod['qtd'])} unidades")
                        if not setup.empty:
                            s = setup.iloc[0]
                            st.write(f"🔧 **Setup:** {s['inicio'].strftime('%H:%M')} às {s['fim'].strftime('%H:%M')}")
                    
                    if col_b.button("✅ Concluir", key=f"conc_{prod['id']}"):
                        try:
                            with conectar() as conn:
                                conn.execute("UPDATE agenda SET status='Concluído' WHERE id=? OR vinculo_id=?", 
                                           (prod['id'], prod['id']))
                                conn.commit()
                            st.success(f"OP {prod['pedido']} concluída!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    
                    if col_c.button("🗑️ Apagar", key=f"del_{prod['id']}"):
                        try:
                            with conectar() as conn:
                                conn.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", 
                                           (prod['id'], prod['id']))
                                conn.commit()
                            st.success(f"OP {prod['pedido']} apagada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
    else:
        st.info("ℹ️ Nenhuma produção cadastrada.")

# ===============================
# ABA 4 - PRODUTOS (VISUALIZAÇÃO DA PLANILHA)
# ===============================
with aba4:
    st.subheader("📋 Produtos - Fonte: Google Sheets")
    
    with st.spinner("Carregando dados da planilha..."):
        df_prod = carregar_produtos_google()
    
    if not df_prod.empty:
        # Métricas rápidas
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total de Produtos", len(df_prod))
        col_m2.metric("Clientes", df_prod['cliente'].nunique() if 'cliente' in df_prod.columns else 0)
        col_m3.metric("Carga média", f"{df_prod['qtd_carga'].mean():.0f}")
        
        st.markdown("---")
        
        # Filtros
        with st.expander("🔍 Filtrar produtos", expanded=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                if 'cliente' in df_prod.columns:
                    clientes = ['Todos'] + sorted(df_prod['cliente'].unique().tolist())
                    filtro_cliente = st.selectbox("Filtrar por Cliente", clientes)
                else:
                    filtro_cliente = 'Todos'
            
            with col_f2:
                busca = st.text_input("Buscar por ID_ITEM ou descrição")
            
            # Aplicar filtros
            df_filtrado = df_prod.copy()
            if filtro_cliente != 'Todos' and 'cliente' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['cliente'] == filtro_cliente]
            
            if busca:
                df_filtrado = df_filtrado[
                    df_filtrado['id_item'].astype(str).str.contains(busca, case=False, na=False) |
                    df_filtrado['descricao'].astype(str).str.contains(busca, case=False, na=False)
                ]
        
        # Mostrar dados
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Informação de atualização
        st.caption(f"📅 Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (cache de 5 minutos)")
    else:
        st.error("❌ Não foi possível carregar os dados da planilha.")

# ===============================
# ABA 5 - CARGAS
# ===============================
with aba5:
    st.subheader(f"📈 Cargas por Máquina (Base: {CARGA_UNIDADE} unid/carga)")
    df_c = carregar_dados()
    if not df_c.empty:
        df_prod_c = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
        cols = st.columns(4)
        for i, maq in enumerate(MAQUINAS):
            total_qtd = df_prod_c[df_prod_c["maquina"] == maq]["qtd"].sum()
            cols[i].metric(label=f"🏭 {maq.upper()}", value=f"{total_qtd / CARGA_UNIDADE:.1f} cargas", delta=f"{int(total_qtd)} unid")
        with st.expander("📋 Detalhamento por OP"):
            for maq in MAQUINAS:
                st.write(f"**{maq}**")
                df_maq = df_prod_c[df_prod_c["maquina"] == maq]
                if not df_maq.empty:
                    for _, row in df_maq.iterrows(): 
                        st.write(f"  • {row['pedido']}: {int(row['qtd'])} unid")
                else: 
                    st.write("  • Nenhuma OP")

st.divider()
col_r1, col_r2, col_r3 = st.columns(3)
with col_r1:
    st.caption(f"🕒 Sistema atualizado: {agora.strftime('%d/%m/%Y %H:%M:%S')}")
with col_r3:
    st.caption("🏭 PCP Industrial v3.2 - DESCRIÇÃO_1 corrigida")
