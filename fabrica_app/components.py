# =================================================================
# COMPONENTES VISUAIS REUTILIZÁVEIS
# =================================================================

import streamlit as st
import plotly.express as px
from datetime import timedelta
from config import agora
from database import carregar_dados
from utils import get_descricao_produto

def renderizar_cabecalho(email_usuario):
    st.markdown(f"""
    <div class="custom-header">
        <div>
            <h2 style="margin:0;font-size:20px;color:#FFFFFF;">
                📊 PCP <span style="color:#E63946;">|</span> CRONOGRAMA DE MÁQUINAS
            </h2>
            <p style="color:#A0A8B8;margin:2px 0 0 0;font-size:12px;">
                👤 Usuário: {email_usuario}
            </p>
        </div>
        <div class="clock-box">
            <h3 class="clock-time">⏰ {agora.strftime('%H:%M:%S')}</h3>
            <p class="clock-date">{agora.strftime('%d/%m/%Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def renderizar_rodape():
    st.markdown("""
    <div class="footer">
        v7.3 | Industrial By William | PCP Serigrafia + Sopro | Setup automático 30min | Reprogramação em cascata
    </div>
    """, unsafe_allow_html=True)

def renderizar_setor(lista_maquinas, altura=500):
    df_all = carregar_dados()
    
    if df_all.empty:
        st.info("Nenhuma OP agendada.")
        return
    
    df_g = df_all[df_all["maquina"].isin(lista_maquinas)].copy()
    
    if df_g.empty:
        st.info("Sem dados para este setor.")
        return
    
    setor_nome = "SERIGRAFIA" if "maquina" in lista_maquinas[0] else "SOPRO"
    st.markdown(f"### 🏭 Setor {setor_nome}")
    
    fig = px.timeline(
        df_g,
        x_start="inicio",
        x_end="fim",
        y="maquina",
        color="cor_barra",
        text="rotulo_barra",
        category_orders={"maquina": lista_maquinas},
        color_discrete_map={
            "Pendente": "#3498DB",
            "Concluído": "#27AE60",
            "Setup": "#95A5A6",
            "Executando": "#F39C12",
            "Atrasada": "#E63946",
            "Manutenção": "#8E44AD"
        },
        custom_data=[
            "pedido",
            "item",
            "qtd",
            "ini_formatado",
            "fim_formatado",
            "status"
        ],
        height=altura
    )
    
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b style='font-size:14px;color:#2C3E50;'>📦 OP: %{customdata[0]}</b>",
            "<span style='color:#2C3E50;'>🔧 <b>Item:</b> %{customdata[1]}</span>",
            "<span style='color:#2C3E50;'>📊 <b>Quantidade:</b> %{customdata[2]:,.0f} unidades</span>",
            "<span style='color:#2C3E50;'>⏱️ <b>Início:</b> %{customdata[3]}</span>",
            "<span style='color:#2C3E50;'>⏱️ <b>Término:</b> %{customdata[4]}</span>",
            "<span style='color:#2C3E50;'>⚙️ <b>Status:</b> %{customdata[5]}</span>",
            "<span style='color:#2C3E50;'>⚙️ <b>Cadência:</b> 2.380 unid/hora</span>",
            "<extra></extra>"
        ]),
        textposition='inside',
        insidetextanchor='start',
        width=0.95,
        marker=dict(line=dict(width=1, color='#1A1E24')),
        opacity=0.9,
        selector=dict(type='bar'),
        textfont=dict(color='white', size=11, family='Arial')
    )
    
    fig.update_yaxes(
        autorange="reversed",
        title="",
        showgrid=True,
        gridcolor='#3A404C',
        zeroline=False,
        tickfont=dict(size=12, color='#E0E0E0'),
        tickangle=0
    )
    
    fig.update_xaxes(
        type='date',
        range=[
            agora - timedelta(hours=2),
            agora + timedelta(hours=36)
        ],
        dtick=10800000,
        tickformat="%H:%M\n%d/%m",
        gridcolor='#3A404C',
        showgrid=True,
        tickangle=0,
        tickfont=dict(size=11, color='#E0E0E0'),
        title=""
    )
    
    fig.add_vline(
        x=agora.timestamp() * 1000,
        line_width=3,
        line_dash="dash",
        line_color="#E63946",
        opacity=0.8,
        annotation_text="AGORA",
        annotation_position="top",
        annotation_font_size=12,
        annotation_font_color="#E63946"
    )
    
    fig.update_layout(
        plot_bgcolor='#1A1E24',
        paper_bgcolor='#1A1E24',
        font=dict(color='#E0E0E0'),
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(
            bgcolor='#252A33',
            bordercolor='#3A404C',
            font=dict(color='#E0E0E0')
        ),
        hoverlabel=dict(
            bgcolor='#252A33',
            font_size=13,
            font_family='Arial',
            font_color='#FFFFFF'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'scrollZoom': True,
        'modeBarButtonsToAdd': ['zoom', 'pan', 'select', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale'],
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    })
    
    # OPs atrasadas
    ops_atrasadas = df_g[df_g["atrasada"]]
    
    if not ops_atrasadas.empty:
        st.markdown("#### 🚨 OPs ATRASADAS")
        cols = st.columns(min(3, len(ops_atrasadas)))
        for i, (idx, op) in enumerate(ops_atrasadas.iterrows()):
            if i >= 3: break
            descricao_produto = get_descricao_produto(op['item'])
            with cols[i % 3]:
                st.markdown(f"""
                <div class="status-card-atrasada">
                    <p style="color:#E63946;font-weight:bold;margin:0 0 10px 0;font-size:16px;">
                        🏭 {op['maquina']}
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>Item:</b> {op['item']}
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>Descrição:</b> {descricao_produto[:50]}...
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>QTD:</b> {int(op['qtd']):,}
                    </p>
                    <p style="color:#A0A8B8;margin:10px 0 0 0;font-size:12px;">
                        ⏱️ Deveria terminar: {op['fim'].strftime('%d/%m %H:%M')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        st.divider()
    
    # OPs em execução
    ops_execucao = df_g[df_g["em_execucao"]]
    
    if not ops_execucao.empty:
        st.markdown("#### ⚙️ OPs EM EXECUÇÃO")
        cols = st.columns(min(3, len(ops_execucao)))
        for i, (idx, op) in enumerate(ops_execucao.iterrows()):
            if i >= 3: break
            descricao_produto = get_descricao_produto(op['item'])
            with cols[i % 3]:
                st.markdown(f"""
                <div class="status-card-execucao">
                    <p style="color:#F39C12;font-weight:bold;margin:0 0 10px 0;font-size:16px;">
                        🏭 {op['maquina']}
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>Item:</b> {op['item']}
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>Descrição:</b> {descricao_produto[:50]}...
                    </p>
                    <p style="color:#E0E0E0;margin:5px 0;font-size:14px;">
                        <b>QTD:</b> {int(op['qtd']):,}
                    </p>
                    <p style="color:#A0A8B8;margin:10px 0 0 0;font-size:12px;">
                        ⏱️ Término previsto: {op['fim'].strftime('%d/%m %H:%M')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
        st.divider()
    
    # Máquinas sem programação
    maquinas_com_op = df_g[df_g["status"] == "Pendente"]["maquina"].unique()
    maquinas_sem_programacao = [
        m for m in lista_maquinas if m not in maquinas_com_op
    ]
    
    if maquinas_sem_programacao:
        st.markdown("#### 💤 Máquinas sem Programação")
        cols = st.columns(4)
        for i, maq in enumerate(maquinas_sem_programacao[:4]):
            with cols[i]:
                st.markdown(f"""
                <div class="status-card-semop">
                    <p style="color:#95A5A6;font-weight:bold;margin:0;font-size:16px;">
                        🏭 {maq}
                    </p>
                    <p style="color:#A0A8B8;margin:5px 0 0 0;font-size:14px;">
                        Sem OP
                    </p>
                </div>
                """, unsafe_allow_html=True)
        st.divider()
    
    # Métricas
    st.markdown("#### 📊 Métricas Gerais")
    c1, c2, c3, c4 = st.columns(4)
    
    atrasadas_count = len(ops_atrasadas)
    em_uso_count = ops_execucao["maquina"].nunique() if not ops_execucao.empty else 0
    total_setor = len(lista_maquinas)
    total_ops = df_g[df_g["status"] == "Pendente"].shape[0]
    
    with c1:
        st.metric("🚨 OPs Atrasadas", atrasadas_count, delta=None)
    with c2:
        st.metric("⚙️ OPs em Execução", em_uso_count)
    with c3:
        st.metric("📦 Total OPs Pendentes", total_ops)
    with c4:
        if total_setor > 0:
            ocup = (em_uso_count / total_setor) * 100
            st.metric("📈 Taxa de Ocupação", f"{ocup:.1f}%")
        else:
            st.metric("📈 Taxa de Ocupação", "0%")
    
    st.divider()
