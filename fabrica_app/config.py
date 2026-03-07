# =================================================================
# CONFIGURAÇÕES DO SISTEMA
# =================================================================

import pytz
from datetime import datetime

# Banco de dados
DATABASE_URL = "postgresql://postgres.ogxrgnaedmcbaqgryosg:pcp2026supabase@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require"

# Usuários
ADMIN_EMAIL = "will@admin.com.br"
OPERACIONAL_EMAIL = ["sarita@will.com.br", "oneida@will.com.br"]

# Máquinas
MAQUINAS_SERIGRAFIA = [
    "maquina 13001",
    "maquina 13002",
    "maquina 13003",
    "maquina 13004"
]

MAQUINAS_SOPRO = [f"Sopro {i:02d}" for i in range(1, 17)]
TODAS_MAQUINAS = MAQUINAS_SERIGRAFIA + MAQUINAS_SOPRO

# Produção
CADENCIA_PADRAO = 2380
CARGA_UNIDADE = 49504
SETUP_DURACAO = 30  # minutos

# Fuso horário
fuso_br = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(fuso_br).replace(tzinfo=None)

# Google Sheets
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"
