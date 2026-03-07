# =================================================================
# CONEXÃO E OPERAÇÕES COM BANCO DE DADOS
# =================================================================

import psycopg2
import streamlit as st
import pandas as pd
from config import DATABASE_URL, agora, SETUP_DURACAO, CADENCIA_PADRAO
from datetime import timedelta

def conectar():
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar no Supabase: {e}")
        st.stop()

def carregar_dados():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM agenda ORDER BY inicio", conn)
    conn.close()
    
    if not df.empty:
        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors='coerce').fillna(0)
        
        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP" if r['status'] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1
        )
        
        df["em_execucao"] = (df["inicio"] <= agora) & (df["fim"] >= agora) & (df["status"] == "Pendente")
        df["atrasada"] = (df["fim"] < agora) & (df["status"] == "Pendente")
        
        df["cor_barra"] = "Pendente"
        df.loc[df["status"] == "Setup", "cor_barra"] = "Setup"
        df.loc[df["status"] == "Manutenção", "cor_barra"] = "Manutenção"
        df.loc[df["status"] == "Concluído", "cor_barra"] = "Concluído"
        df.loc[df["em_execucao"], "cor_barra"] = "Executando"
        df.loc[df["atrasada"], "cor_barra"] = "Atrasada"
        
        df["fim_formatado"] = df["fim"].dt.strftime('%d/%m %H:%M')
        df["ini_formatado"] = df["inicio"].dt.strftime('%d/%m %H:%M')
        
    return df

def proximo_horario(maq):
    df = carregar_dados()
    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq) &
            (df["status"].isin(["Pendente","Setup","Manutenção"]))
        ]
        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)
    return agora

def calcular_fim_op(inicio, qtd):
    return inicio + timedelta(hours=qtd / CADENCIA_PADRAO)

def inserir_producao(maquina, pedido, item, inicio, fim, qtd, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, criado_por, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                maquina,
                pedido,
                item,
                inicio,
                fim,
                "Pendente",
                qtd,
                usuario,
                agora
            )
        )
        
        producao_id = cur.fetchone()[0]
        
        setup_inicio = inicio - timedelta(minutes=SETUP_DURACAO)
        setup_fim = inicio
        
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id, criado_por, criado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                maquina,
                f"SETUP - {pedido}",
                "Setup",
                setup_inicio,
                setup_fim,
                "Setup",
                0,
                producao_id,
                usuario,
                agora
            )
        )
        
        conn.commit
