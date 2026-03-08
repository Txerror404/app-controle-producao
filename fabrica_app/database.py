# =================================================================
# CONEXÃO E OPERAÇÕES COM BANCO DE DADOS
# =================================================================

import psycopg2
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from config import DATABASE_URL, SETUP_DURACAO, CADENCIA_PADRAO

# Fuso Brasil para usar nas funções
fuso_br = pytz.timezone("America/Sao_Paulo")

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
        
        # Calcular horário atual a cada execução
        agora = datetime.now(fuso_br).replace(tzinfo=None)
        
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
    agora = datetime.now(fuso_br).replace(tzinfo=None)
    
    if not df.empty:
        df_maq = df[
            (df["maquina"] == maq) &
            (df["status"].isin(["Pendente","Setup","Manutenção"]))
        ]
        if not df_maq.empty:
            ultimo_fim = df_maq["fim"].max()
            return max(agora, ultimo_fim)
    return agora

# =================================================================
# CALCULAR FIM DA OP - CORRIGIDO (com conversão Decimal para float)
# =================================================================
def calcular_fim_op(inicio, qtd):
    # Garantir que qtd seja float (resolve problema de Decimal do PostgreSQL)
    try:
        qtd_float = float(qtd)
    except:
        qtd_float = 0
    return inicio + timedelta(hours=qtd_float / CADENCIA_PADRAO)

# =================================================================
# INSERIR PRODUÇÃO - CORRIGIDO (SEM criado_por E criado_em)
# =================================================================
def inserir_producao(maquina, pedido, item, inicio, fim, qtd, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # ATENÇÃO: Esta query NÃO usa criado_por e criado_em
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

# =================================================================
# INSERIR SETUP MANUAL - CORRIGIDO (SEM criado_por E criado_em)
# =================================================================
def inserir_setup(maquina, pedido, inicio, fim, vinculo, usuario):
    conn = conectar()
    cur = conn.cursor()
    
    try:
        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

# =================================================================
# FINALIZAR OP
# =================================================================
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

# =================================================================
# DELETAR OP (E SEU SETUP)
# =================================================================
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

# =================================================================
# REPROGRAMAR OP - CORRIGIDO (com conversão Decimal para float)
# =================================================================
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
        
        # =================================================================
        # CORREÇÃO: Converter Decimal para float
        # =================================================================
        try:
            # Tenta converter para float (funciona com Decimal e outros tipos)
            qtd_float = float(qtd)
        except:
            qtd_float = 0
        
        novo_fim = calcular_fim_op(novo_inicio, qtd_float)
        
        # ATENÇÃO: Esta query NÃO usa alterado_por e alterado_em
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
        
        # Buscar OPs seguintes e recalcular
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
            
            # =================================================================
            # CORREÇÃO: Converter Decimal para float também aqui
            # =================================================================
            try:
                seg_qtd_float = float(seg_qtd)
            except:
                seg_qtd_float = 0
            
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
                    novo_prod_fim = calcular_fim_op(novo_prod_inicio, seg_qtd_float if seg_qtd_float > 0 else qtd_float)
                    
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
                novo_seg_fim = calcular_fim_op(novo_seg_inicio, seg_qtd_float)
                
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
        # =================================================================
# REPROGRAMAR OPs ATRASADAS EM CASCATA
# =================================================================
def reprogramar_ops_atrasadas():
    """
    Identifica OPs atrasadas e reprograma todas as OPs seguintes
    em suas respectivas máquinas (planejamento cascata)
    """
    conn = conectar()
    cur = conn.cursor()
    
    try:
        # Buscar horário atual sem timezone
        agora = datetime.now(pytz.timezone("America/Sao_Paulo")).replace(tzinfo=None)
        
        # =================================================================
        # PASSO 1: Identificar OPs de PRODUÇÃO atrasadas (fim < agora)
        # =================================================================
        cur.execute("""
            SELECT id, maquina, inicio, fim, qtd, vinculo_id
            FROM agenda
            WHERE status = 'Pendente' 
                AND fim < %s
                AND (item != 'Setup' OR item IS NULL)
            ORDER BY maquina, inicio
        """, (agora,))
        
        ops_atrasadas = cur.fetchall()
        
        if not ops_atrasadas:
            # Não há OPs atrasadas
            conn.commit()
            return
        
        # Agrupar por máquina para processar cada máquina separadamente
        maquinas_ops = {}
        for op in ops_atrasadas:
            op_id, maquina, old_inicio, old_fim, qtd, vinculo_id = op
            if maquina not in maquinas_ops:
                maquinas_ops[maquina] = []
            maquinas_ops[maquina].append(op)
        
        # =================================================================
        # PASSO 2: Para cada máquina, reprocessar todas as OPs
        # =================================================================
        for maquina, ops_maq in maquinas_ops.items():
            # Buscar TODAS as OPs desta máquina (incluindo as não atrasadas)
            cur.execute("""
                SELECT id, inicio, fim, status, qtd, vinculo_id, item
                FROM agenda
                WHERE maquina = %s 
                    AND status IN ('Pendente', 'Setup')
                ORDER BY inicio
            """, (maquina,))
            
            todas_ops_maquina = cur.fetchall()
            
            if not todas_ops_maquina:
                continue
            
            # =================================================================
            # PASSO 3: Reconstruir a sequência completa a partir do horário atual
            # =================================================================
            novo_sequencia = []
            current_time = agora
            
            for op in todas_ops_maquina:
                op_id, old_inicio, old_fim, status, qtd, vinculo_id, item = op
                
                if status == "Setup":
                    # Setup deve vir antes da produção vinculada
                    # Vamos pular setups aqui, eles serão recriados junto com as produções
                    continue
                
                # É uma produção
                try:
                    qtd_float = float(qtd) if qtd else 0
                except:
                    qtd_float = 0
                
                # Calcular novo fim baseado no horário atual
                novo_fim_prod = calcular_fim_op(current_time, qtd_float)
                
                # Atualizar a produção
                cur.execute(
                    """
                    UPDATE agenda 
                    SET inicio = %s, fim = %s
                    WHERE id = %s
                    """,
                    (current_time, novo_fim_prod, op_id)
                )
                
                # Atualizar o setup vinculado (se existir)
                if vinculo_id:
                    # Buscar o setup vinculado
                    cur.execute(
                        "SELECT id FROM agenda WHERE vinculo_id = %s AND status = 'Setup'",
                        (op_id,)
                    )
                    setup = cur.fetchone()
                    
                    if setup:
                        setup_id = setup[0]
                        setup_inicio = current_time - timedelta(minutes=SETUP_DURACAO)
                        setup_fim = current_time
                        
                        cur.execute(
                            "UPDATE agenda SET inicio = %s, fim = %s WHERE id = %s",
                            (setup_inicio, setup_fim, setup_id)
                        )
                
                # Avançar o tempo para a próxima OP
                current_time = novo_fim_prod
            
            # =================================================================
            # PASSO 4: Log da reprogramação (opcional)
            # =================================================================
            st.info(f"🔄 Máquina {maquina}: {len(ops_maq)} OPs atrasadas reprogramadas em cascata")
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Erro ao reprogramar OPs atrasadas: {e}")
    finally:
        cur.close()
        conn.close()
        
