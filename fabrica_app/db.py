import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "pcp.db"


# ===============================
# CONEXÃO
# ===============================
def conectar():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


# ===============================
# CRIAR TABELA
# ===============================
def criar_tabela():

    with conectar() as conn:

        conn.execute(
            """
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
            """
        )


# ===============================
# CARREGAR DADOS
# ===============================
def carregar_dados():

    conn = conectar()

    df = pd.read_sql_query("SELECT * FROM agenda", conn)

    conn.close()

    if not df.empty:

        df["inicio"] = pd.to_datetime(df["inicio"])
        df["fim"] = pd.to_datetime(df["fim"])
        df["qtd"] = pd.to_numeric(df["qtd"], errors="coerce").fillna(0)

        df["rotulo_barra"] = df.apply(
            lambda r: "🔧 SETUP"
            if r["status"] == "Setup"
            else f"📦 {r['pedido']}<br>QTD: {int(r['qtd'])}",
            axis=1,
        )

    return df


# ===============================
# INSERIR PRODUÇÃO
# ===============================
def inserir_producao(
    maquina,
    pedido,
    item,
    inicio,
    fim,
    qtd,
):

    with conectar() as conn:

        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                maquina,
                pedido,
                item,
                inicio,
                fim,
                "Pendente",
                qtd,
            ),
        )

        conn.commit()

        return cur.lastrowid


# ===============================
# INSERIR SETUP
# ===============================
def inserir_setup(
    maquina,
    pedido,
    inicio,
    fim,
    vinculo_id,
):

    with conectar() as conn:

        conn.execute(
            """
            INSERT INTO agenda
            (maquina, pedido, item, inicio, fim, status, qtd, vinculo_id)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                maquina,
                pedido,
                "Ajuste",
                inicio,
                fim,
                "Setup",
                0,
                vinculo_id,
            ),
        )

        conn.commit()


# ===============================
# FINALIZAR OP
# ===============================
def finalizar_op(op_id):

    with conectar() as conn:

        conn.execute(
            "UPDATE agenda SET status='Concluído' WHERE id=?",
            (op_id,),
        )

        conn.commit()


# ===============================
# DELETAR OP
# ===============================
def deletar_op(op_id):

    with conectar() as conn:

        conn.execute(
            "DELETE FROM agenda WHERE id=? OR vinculo_id=?",
            (op_id, op_id),
        )

        conn.commit()


# ===============================
# REPROGRAMAR
# ===============================
def atualizar_horario(op_id, inicio, fim):

    with conectar() as conn:

        conn.execute(
            "UPDATE agenda SET inicio=?, fim=? WHERE id=?",
            (inicio, fim, op_id),
        )

        conn.commit()
