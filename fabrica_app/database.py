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
        # Versão SEM as colunas de auditoria
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                maquina,
                pedido,
                item,
                inicio,
                fim,
                "Pendente",
                qtd
            )
        )
        
        producao_id = cur.fetchone()[0]
        
        # Inserir setup de 30 minutos antes
        setup_inicio = inicio - timedelta(minutes=SETUP_DURACAO)
        setup_fim = inicio
        
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                maquina,
                f"SETUP - {pedido}",
                "Setup",
                setup_inicio,
                setup_fim,
                "Setup",
                0,
                producao_id
            )
        )
        
        conn.commit()
        return producao_id
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir produção: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def inserir_setup(maquina, pedido, inicio, fim, vinculo, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                maquina,
                pedido,
                "Ajuste",
                inicio,
                fim,
                "Setup",
                0,
                vinculo
            )
        )
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao inserir setup: {e}")
    finally:
        cur.close()
        conn.close()

def finalizar_op(id_op):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agenda SET status='Concluído' WHERE id=%s",
        (id_op,)
    )
    conn.commit()
    cur.close()
    conn.close()

def deletar_op(id_op):
    conn = conectar()
    cur = conn.cursor()
    
    cur.execute(
        "DELETE FROM agenda WHERE id=%s OR vinculo_id=%s",
        (id_op, id_op)
    )
    
    conn.commit()
    cur.close()
    conn.close()

def reprogramar_op(id_op, novo_inicio, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id, maquina, inicio, fim, vinculo_id, status, qtd 
            FROM agenda 
            WHERE id = %s OR vinculo_id = %s
            ORDER BY inicio
        """, (id_op, id_op))
        
        registros = cur.fetchall()
        
        if not registros:
            return
        
        setup = None
        producao = None
        
        for reg in registros:
            if reg[5] == "Setup":
                setup = reg
            else:
                producao = reg
        
        if not producao:
            return
        
        producao_id, maquina, old_inicio, old_fim, vinculo_id, status, qtd = producao
        
        novo_fim = calcular_fim_op(novo_inicio, qtd)
        
        # Versão SEM alterado_por/alterado_em
        cur.execute(
            """
            UPDATE agenda 
            SET inicio = %s, fim = %s
            WHERE id = %s
            """,
            (novo_inicio, novo_fim, producao_id)
        )
        
        if setup:
            setup_id, _, setup_inicio, setup_fim, _, _, _ = setup
            novo_setup_inicio = novo_inicio - timedelta(minutes=SETUP_DURACAO)
            novo_setup_fim = novo_inicio
            
            cur.execute(
                """
                UPDATE agenda 
                SET inicio = %s, fim = %s
                WHERE id = %s
                """,
                (novo_setup_inicio, novo_setup_fim, setup_id)
            )
        
        cur.execute("""
            SELECT id, inicio, fim, vinculo_id, status, qtd
            FROM agenda
            WHERE maquina = %s 
                AND status IN ('Pendente', 'Setup')
                AND id != %s 
                AND (vinculo_id != %s OR vinculo_id IS NULL)
                AND inicio > %s
            ORDER BY inicio
        """, (maquina, producao_id, producao_id, old_fim))
        
        seguintes = cur.fetchall()
        
        current_end = novo_fim
        
        for seguinte in seguintes:
            seg_id, seg_inicio, seg_fim, seg_vinculo, seg_status, seg_qtd = seguinte
            
            if seg_status == "Setup":
                cur.execute("SELECT id, inicio FROM agenda WHERE vinculo_id = %s AND status = 'Pendente'", (seg_vinculo or seg_id,))
                prod_vinculada = cur.fetchone()
                
                if prod_vinculada:
                    prod_id, prod_inicio = prod_vinculada
                    novo_setup_inicio = current_end
                    novo_setup_fim = current_end + timedelta(minutes=SETUP_DURACAO)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_setup_inicio, novo_setup_fim, seg_id)
                    )
                    
                    novo_prod_inicio = novo_setup_fim
                    novo_prod_fim = calcular_fim_op(novo_prod_inicio, seg_qtd if seg_qtd > 0 else qtd)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_prod_inicio, novo_prod_fim, prod_id)
                    )
                    
                    current_end = novo_prod_fim
                else:
                    duracao = (seg_fim - seg_inicio).total_seconds() / 60
                    novo_setup_inicio = current_end
                    novo_setup_fim = current_end + timedelta(minutes=duracao)
                    
                    cur.execute(
                        "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                        (novo_setup_inicio, novo_setup_fim, seg_id)
                    )
                    
                    current_end = novo_setup_fim
            else:
                novo_seg_inicio = current_end
                novo_seg_fim = calcular_fim_op(novo_seg_inicio, seg_qtd)
                
                cur.execute(
                    "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                    (novo_seg_inicio, novo_seg_fim, seg_id)
                )
                
                current_end = novo_seg_fim
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao reprogramar: {e}")
    finally:
        cur.close()
        conn.close()
