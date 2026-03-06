import sqlite3
import pandas as pd

DB_FILE = "pcp.db"

def conectar():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

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
