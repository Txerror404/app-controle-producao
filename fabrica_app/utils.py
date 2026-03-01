from datetime import datetime, timedelta


# ==============================
# CONVERTER DATA + HORA
# ==============================
def combinar_data_hora(data, hora):
    return datetime.combine(data, hora)


# ==============================
# CALCULAR DURAÇÃO EM HORAS
# ==============================
def calcular_duracao(inicio, fim):
    return round((fim - inicio).total_seconds() / 3600, 2)


# ==============================
# GERAR HORÁRIOS DINÂMICOS
# ==============================
def gerar_horarios(intervalo_min=30):
    horarios = []
    inicio = datetime.strptime("00:00", "%H:%M")
    fim = datetime.strptime("23:59", "%H:%M")

    atual = inicio
    while atual <= fim:
        horarios.append(atual.time())
        atual += timedelta(minutes=intervalo_min)

    return horarios


# ==============================
# VALIDAR CONFLITO DE MÁQUINA
# ==============================
def verificar_conflito(maquina, inicio, fim, eventos_existentes, id_evento=None):
    """
    Verifica se existe conflito de horário para a mesma máquina.
    Se id_evento for informado, ignora ele (caso de edição).
    """

    for evento in eventos_existentes:
        if evento["maquina"] != maquina:
            continue

        if id_evento and evento["id"] == id_evento:
            continue

        inicio_existente = datetime.fromisoformat(evento["inicio"])
        fim_existente = datetime.fromisoformat(evento["fim"])

        # Regra de conflito
        if inicio < fim_existente and fim > inicio_existente:
            return True

    return False


# ==============================
# CORES PARA GANTT
# ==============================
def cor_por_status(status):
    cores = {
        "Pendente": "#f1c40f",
        "Em Produção": "#3498db",
        "Finalizado": "#2ecc71",
        "Atrasado": "#e74c3c",
        "Cancelado": "#95a5a6"
    }
    return cores.get(status, "#7f8c8d")


# ==============================
# FORMATAR DATA BR
# ==============================
def formatar_data_br(dt):
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%d/%m/%Y %H:%M")
