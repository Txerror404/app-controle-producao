import sqlite3
from contextlib import contextmanager

DB_NAME = "pcp.db"


# ==============================
# CONEXÃO SEGURA
# ==============================
@contextmanager
def conectar():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ==============================
# CRIAR TABELAS + ÍNDICES
# ==============================
def criar_tabelas():
    with conectar() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op TEXT NOT NULL,
            cliente TEXT,
            produto TEXT,
            maquina TEXT NOT NULL,
            setor TEXT,
            inicio DATETIME NOT NULL,
            fim DATETIME NOT NULL,
            status TEXT DEFAULT 'Pendente',
            observacao TEXT,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Índices para performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maquina ON agenda(maquina)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inicio ON agenda(inicio)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON agenda(status)")
        conn.commit()


# ==============================
# INSERIR EVENTO
# ==============================
def inserir_evento(op, cliente, produto, maquina, setor, inicio, fim, status="Pendente", observacao=""):
    with conectar() as conn:
        conn.execute("""
        INSERT INTO agenda
        (op, cliente, produto, maquina, setor, inicio, fim, status, observacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (op, cliente, produto, maquina, setor, inicio, fim, status, observacao))
        conn.commit()


# ==============================
# ATUALIZAR EVENTO COMPLETO
# ==============================
def atualizar_evento(id_evento, op, cliente, produto, maquina, setor, inicio, fim, status, observacao):
    with conectar() as conn:
        conn.execute("""
        UPDATE agenda
        SET op=?, cliente=?, produto=?, maquina=?, setor=?,
            inicio=?, fim=?, status=?, observacao=?
        WHERE id=?
        """, (op, cliente, produto, maquina, setor,
              inicio, fim, status, observacao, id_evento))
        conn.commit()


# ==============================
# ATUALIZAR STATUS
# ==============================
def atualizar_status(id_evento, novo_status):
    with conectar() as conn:
        conn.execute("""
        UPDATE agenda
        SET status=?
        WHERE id=?
        """, (novo_status, id_evento))
        conn.commit()


# ==============================
# SOFT DELETE (INDUSTRIAL)
# ==============================
def soft_delete(id_evento):
    with conectar() as conn:
        conn.execute("""
        UPDATE agenda
        SET status='Cancelado'
        WHERE id=?
        """, (id_evento,))
        conn.commit()


# ==============================
# LISTAR EVENTOS ATIVOS
# ==============================
def listar_eventos():
    with conectar() as conn:
        eventos = conn.execute("""
        SELECT * FROM agenda
        WHERE status != 'Cancelado'
        ORDER BY inicio
        """).fetchall()
    return eventos


# ==============================
# BUSCAR POR ID
# ==============================
def buscar_evento_por_id(id_evento):
    with conectar() as conn:
        evento = conn.execute("""
        SELECT * FROM agenda
        WHERE id=?
        """, (id_evento,)).fetchone()
    return evento


# ==============================
# RESETAR FÁBRICA (CUIDADO)
# ==============================
def apagar_tudo():
    with conectar() as conn:
        conn.execute("DELETE FROM agenda")
        conn.commit()
