1   import streamlit as st
2   import pandas as pd
3   import plotly.express as px
4   import sqlite3
5   from datetime import datetime, timedelta
6   import pytz
7   from streamlit_autorefresh import st_autorefresh
8   
9   # =================================================================
10  # 1. CONFIGURAÇÕES GERAIS E ESTILO (NÃO ALTERAR)
11  # =================================================================
12  st.set_page_config(page_title="PCP Industrial - SISTEMA COMPLETO", layout="wide")
13  st_autorefresh(interval=120000, key="pcp_refresh_global")
14  
15  ADMIN_EMAIL = "will@admin.com.br"
16  OPERACIONAL_EMAIL = "sarita@deco.com.br"
17  
18  MAQUINAS_SERIGRAFIA = ["maquina 13001", "maquina 13002", "maquina 13003", "maquina 13004"]
19  MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]  # 16 MÁQUINAS
20  TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO
21  
22  CADENCIA_PADRAO = 2380
23  CARGA_UNIDADE = 49504 
24  fuso_br = pytz.timezone("America/Sao_Paulo")
25  agora = datetime.now(fuso_br).replace(tzinfo=None)
26  
27  GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"
28  
29  st.markdown("""
30      <style>
31          .block-container {padding-top: 0.5rem;}
32          .modebar-container { top: 0 !important; }
33          .stTabs [data-baseweb="tab-list"] { gap: 10px; }
34          .stTabs [data-baseweb="tab"] { 
35              background-color: #1e1e1e; border-radius: 5px; padding: 5px 20px; color: white;
36          }
37          .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; }
38      </style>
39  """, unsafe_allow_html=True)
40  
41  # =================================================================
42  # 2. BANCO DE DADOS E CARREGAMENTO
43  # =================================================================
44  def conectar(): return sqlite3.connect("pcp.db", check_same_thread=False)
45  
46  with conectar() as conn:
47      conn.execute("""
48          CREATE TABLE IF NOT EXISTS agenda (
49              id INTEGER PRIMARY KEY AUTOINCREMENT, 
50              maquina TEXT, pedido TEXT, item TEXT, 
51              inicio TEXT, fim TEXT, status TEXT, 
52              qtd REAL, vinculo_id INTEGER
53          )
54      """)
55  
56  @st.cache_data(ttl=600)
57  def carregar_produtos_google():
58      try:
59          df = pd.read_csv(GOOGLE_SHEETS_URL)
60          df.columns = df.columns.str.strip()
61          df['id_item'] = df['ID_ITEM'].astype(str).str.strip()
62          df['descricao'] = df['DESCRIÇÃO_1'].astype(str).str.strip()
63          df['cliente'] = df['CLIENTE'].astype(str).str.strip()
64          df['qtd_carga'] = pd.to_numeric(df['QTD/CARGA'].astype(str).str.replace(',', '.'), errors='coerce').fillna(CARGA_UNIDADE)
65          return df.fillna('N/A')
66      except Exception as e:
67          return pd.DataFrame(columns=['id_item', 'descricao', 'cliente', 'qtd_carga'])
68  
69  def carregar_dados():
70      conn = conectar()
71      df = pd.read_sql_query("SELECT * FROM agenda", conn)
72      conn.close()
73      if not df.empty:
74          df["inicio"] = pd.to_datetime(df["inicio"])
75          df["fim"] = pd.to_datetime(df["fim"])
76          df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
77          df["rotulo_barra"] = df.apply(lambda r: "🔧 SETUP" if r['status'] == "Setup" else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}", axis=1)
78      return df
79  
80  def proximo_horario(maq):
81      df = carregar_dados()
82      if not df.empty:
83          df_maq = df[(df["maquina"] == maq) & (df["status"].isin(["Pendente", "Setup"]))]
84          if not df_maq.empty: return max(agora, df_maq["fim"].max())
85      return agora
86  
87  # =================================================================
88  # 3. SEGURANÇA E CABEÇALHO
89  # =================================================================
90  if "auth_ok" not in st.session_state: st.session_state.auth_ok = False
91  if not st.session_state.auth_ok:
92      st.markdown("<h1 style='text-align:center;'>🏭 PCP Industrial</h1>", unsafe_allow_html=True)
93      col1, col2, col3 = st.columns([1, 1.5, 1])
94      with col2:
95          email = st.text_input("E-mail autorizado:").lower().strip()
96          if st.button("Acessar Sistema", use_container_width=True):
97              if email in [ADMIN_EMAIL, OPERACIONAL_EMAIL]: 
98                  st.session_state.auth_ok = True; st.session_state.user_email = email; st.rerun()
99      st.stop()
100 
101 df_produtos = carregar_produtos_google()
102 
103 # CABEÇALHO
104 st.markdown(f"""
105     <div style="background-color: #1E1E1E; padding: 8px 15px; border-radius: 8px; border-left: 8px solid #FF4B4B; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
106         <div>
107             <h2 style="color: white; margin: 0; font-size: 20px; font-family: 'Segoe UI', sans-serif;">📊 PCP <span style="color: #FF4B4B;">|</span> CRONOGRAMA DE MÁQUINAS</h2>
108             <p style="color: #888; margin: 2px 0 0 0; font-size: 12px;">👤 Usuário: {st.session_state.user_email}</p>
109         </div>
110         <div style="text-align: center; border: 1px solid #FF4B4B; padding: 2px 15px; border-radius: 5px; background-color: #0E1117; min-width: 130px;">
111             <h3 style="color: #FF4B4B; margin: 0; font-family: 'Courier New', Courier, monospace; font-size: 22px; line-height: 1.2;">⏰ {agora.strftime('%H:%M:%S')}</h3>
112             <p style="color: #aaa; margin: -2px 0 2px 0; font-size: 12px; border-top: 1px dashed #FF4B4B; padding-top: 2px;">{agora.strftime('%d/%m/%Y')}</p>
113         </div>
114     </div>
115 """, unsafe_allow_html=True)
116 
117 # =================================================================
118 # 4. GRÁFICOS E STATUS
119 # =================================================================
120 def renderizar_setor(lista_maquinas, altura=500):
121     df_all = carregar_dados()
122     if df_all.empty:
123         st.info("Nenhuma OP agendada.")
124         return
125 
126     df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
127     if df_g.empty:
128         st.info("Sem dados para este setor.")
129         return
130 
131     df_g["status_cor"] = df_g["status"]
132     df_g.loc[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído"), "status_cor"] = "Executando"
133 
134     fig = px.timeline(
135         df_g, x_start="inicio", x_end="fim", y="maquina", color="status_cor", text="rotulo_barra",
136         category_orders={"maquina": lista_maquinas},
137         color_discrete_map={"Pendente": "#3498db", "Concluído": "#2ecc71", "Setup": "#7f7f7f", "Executando": "#ff7f0e"}
138     )
139 
140     fig.update_yaxes(autorange="reversed", title="", showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False)
141     fig.update_traces(textposition='inside', insidetextanchor='start', width=0.92)
142     
143     # RÉGUA COM DATA E HORA
144     fig.update_xaxes(
145         type='date', 
146         range=[agora - timedelta(hours=2), agora + timedelta(hours=36)], 
147         dtick=10800000, 
148         tickformat="%H:%M\n%d/%m",
149         gridcolor='rgba(255,255,255,0.1)',
150         showgrid=True,
151         tickangle=0,
152         tickfont=dict(size=11)
153     )
154     
155     # LINHA VERMELHA ESTICADA ATÉ O "AGORA"
156     fig.add_vline(
157         x=agora, 
158         line_dash="dash", 
159         line_color="red", 
160         line_width=1,
161         opacity=0.8,
162         yref="paper",
163         y0=1,
164         y1=-0.30
165     )
166     
167     # ANOTAÇÃO "AGORA"
168     fig.add_annotation(
169         x=agora, 
170         y=-0.30, 
171         text=f"AGORA: {agora.strftime('%H:%M')}", 
172         showarrow=False, 
173         xref="x", 
174         yref="paper", 
175         font=dict(color="red", size=13, family="Arial Black"), 
176         bgcolor="rgba(0,0,0,0.9)", 
177         bordercolor="red", 
178         borderpad=2
179     )
180 
181     fig.update_layout(height=altura, margin=dict(l=10, r=10, t=50, b=100), bargap=0.01, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
182     st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'displaylogo': False})
183 
184     # CARDS DE STATUS
185     st.markdown("### 📊 Status do Setor")
186     c1, c2, c3, c4 = st.columns(4)
187     atrasadas = df_g[(df_g["fim"] < agora) & (df_g["status"].isin(["Pendente", "Setup"]))].shape[0]
188     em_uso = df_g[(df_g["inicio"] <= agora) & (df_g["fim"] >= agora) & (df_g["status"] != "Concluído")]["maquina"].nunique()
189     total_setor = len(lista_maquinas)
190     
191     c1.metric("🚨 OPs Atrasadas", atrasadas)
192     c2.metric("⚙️ Máquinas em Uso", em_uso)
193     c3.metric("💤 Máquinas Livres", total_setor - em_uso)
194     c4.metric("📈 Taxa de Ocupação", f"{(em_uso/total_setor)*100:.1f}%")
195     st.divider()
196 
197 # =================================================================
198 # 5. ABAS E LÓGICA DE NEGÓCIO
199 # =================================================================
200 aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["➕ Lançar", "🎨 Serigrafia", "🍼 Sopro", "⚙️ Gerenciar", "📋 Produtos", "📈 Cargas"])
201 
202 with aba1:
203     with st.container(border=True):
204         st.subheader("➕ Novo Lançamento")
205         c1, c2 = st.columns(2)
206         with c1:
207             maq_sel = st.selectbox("🏭 Máquina destino", TODAS_MAQUINAS)
208             item_sel = st.selectbox("📌 Selecione o ID_ITEM", df_produtos['id_item'].tolist())
209             # BUSCA AUTOMÁTICA DE DESCRIÇÃO E CLIENTE
210             info_prod = df_produtos[df_produtos['id_item'] == item_sel].iloc[0] if not df_produtos.empty else {}
211             desc_auto = info_prod.get('descricao', 'N/A')
212             cli_auto = info_prod.get('cliente', 'N/A')
213             carga_auto = info_prod.get('qtd_carga', CARGA_UNIDADE)
214             
215             st.text_input("📝 Descrição do Produto", value=desc_auto, disabled=True)
216         
217         with c2:
218             op_num = st.text_input("🔢 Número da OP")
219             st.text_input("👥 Cliente", value=cli_auto, disabled=True)
220             qtd_lanc = st.number_input("📊 Quantidade Total", value=int(carga_auto))
221         
222         st.divider()
223         c3, c4, c5 = st.columns(3)
224         setup_min = c3.number_input("⏱️ Tempo de Setup (min)", value=30)
225         sugestao_h = proximo_horario(maq_sel)
226         data_ini = c4.date_input("📅 Data de Início", sugestao_h.date())
227         hora_ini = c5.time_input("⏰ Hora de Início", sugestao_h.time())
228         
229         if st.button("🚀 CONFIRMAR E AGENDAR", type="primary", use_container_width=True):
230             if op_num:
231                 inicio_dt = datetime.combine(data_ini, hora_ini)
232                 fim_dt = inicio_dt + timedelta(hours=qtd_lanc/CADENCIA_PADRAO)
233                 with conectar() as conn:
234                     cur = conn.cursor()
235                     cur.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd) VALUES (?,?,?,?,?,?,?)",
236                                (maq_sel, f"{cli_auto} | {op_num}", item_sel, inicio_dt.strftime('%Y-%m-%d %H:%M:%S'), fim_dt.strftime('%Y-%m-%d %H:%M:%S'), "Pendente", qtd_lanc))
237                     if setup_min > 0:
238                         conn.execute("INSERT INTO agenda (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id) VALUES (?,?,?,?,?,?,?,?)",
239                                     (maq_sel, f"SETUP {op_num}", "Ajuste", fim_dt.strftime('%Y-%m-%d %H:%M:%S'), (fim_dt + timedelta(minutes=setup_min)).strftime('%Y-%m-%d %H:%M:%S'), "Setup", 0, cur.lastrowid))
240                     conn.commit()
241                 st.success("Lançamento concluído com sucesso!"); st.rerun()
242 
243 with aba2: renderizar_setor(MAQUINAS_SERIGRAFIA, 450)
244 with aba3: renderizar_setor(MAQUINAS_SOPRO, 750)
245 
246 with aba4:
247     st.subheader("⚙️ Gerenciamento e Reprogramação")
248     df_ger = carregar_dados()
249     if not df_ger.empty:
250         is_admin = st.session_state.user_email == ADMIN_EMAIL
251         for _, prod in df_ger[df_ger["status"].isin(["Pendente", "Setup"])].sort_values("inicio").iterrows():
252             with st.expander(f"📌 {prod['maquina']} | {prod['pedido']}"):
253                 col1, col2, col3 = st.columns([2, 2, 1.2])
254                 
255                 # REPROGRAMAR
256                 if is_admin:
257                     n_data = col1.date_input("Nova Data", prod['inicio'].date(), key=f"d_{prod['id']}")
258                     n_hora = col2.time_input("Nova Hora", prod['inicio'].time(), key=f"t_{prod['id']}")
259                     if st.button("💾 Salvar Novo Horário", key=f"s_{prod['id']}"):
260                         novo_i = datetime.combine(n_data, n_hora)
261                         novo_f = novo_i + (prod['fim'] - prod['inicio'])
262                         with conectar() as c:
263                             c.execute("UPDATE agenda SET inicio=?, fim=? WHERE id=?", (novo_i.strftime('%Y-%m-%d %H:%M:%S'), novo_f.strftime('%Y-%m-%d %H:%M:%S'), prod['id']))
264                             c.commit()
265                         st.rerun()
266                 
267                 if col3.button("✅ Finalizar OP", key=f"ok_{prod['id']}", use_container_width=True):
268                     with conectar() as c: c.execute("UPDATE agenda SET status='Concluído' WHERE id=?", (prod['id'],)); c.commit()
269                     st.rerun()
270                 if col3.button("🗑️ Deletar", key=f"del_{prod['id']}", use_container_width=True):
271                     with conectar() as c: c.execute("DELETE FROM agenda WHERE id=? OR vinculo_id=?", (prod['id'], prod['id'])); c.commit()
272                     st.rerun()
273 
274 with aba5: st.dataframe(df_produtos, use_container_width=True)
275 
276 with aba6:
277     df_c = carregar_dados()
278     if not df_c.empty:
279         df_p = df_c[(df_c["status"] == "Pendente") & (df_c["qtd"] > 0)]
280         st.metric("Total Geral de Cargas Sopro", f"{df_p[df_p['maquina'].isin(MAQUINAS_SOPRO)]['qtd'].sum() / CARGA_UNIDADE:.1f}")
281         st.table(df_p[df_p["maquina"].isin(MAQUINAS_SOPRO)][["maquina", "pedido", "qtd"]])
282 
283 st.divider()
284 st.caption(f"v5.9 | PCP Industrial William | 16 Máquinas Sopro | Atualização em tempo real ativa")
