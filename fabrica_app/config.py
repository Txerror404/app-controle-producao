# =================================================================
# CONFIGURAÇÕES DO SISTEMA
# =================================================================

import pytz
from datetime import datetime

# =================================================================
# BANCO DE DADOS
# =================================================================
DATABASE_URL = "postgresql://postgres.ogxrgnaedmcbaqgryosg:pcp2026supabase@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"

# =================================================================
# USUÁRIOS
# =================================================================
ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = ["sarita@will.com.br", "oneida@will.com.br"]

# =================================================================
# MÁQUINAS
# =================================================================
MAQUINAS_SERIGRAFIA = [
    "maquina 13001",
    "maquina 13002",
    "maquina 13003",
    "maquina 13004"
]

MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

# =================================================================
# PRODUÇÃO
# =================================================================
CADENCIA_PADRAO = 2380  # unidades por hora
CARGA_UNIDADE = 49504   # unidades por carga
SETUP_DURACAO = 30      # minutos

# =================================================================
# FUSO HORÁRIO - APENAS O FUSO, NÃO O HORÁRIO FIXO
# =================================================================
fuso_br = pytz.timezone("America/Sao_Paulo")

# NOTA: 'agora' NÃO é definido aqui globalmente
# Cada função deve calcular datetime.now(fuso_br).replace(tzinfo=None)
# Isso garante que o horário seja atualizado a cada execução

# =================================================================
# GOOGLE SHEETS
# =================================================================
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"
