from datetime import datetime

def verificar_conflito(df, maquina, inicio_novo, fim_novo):
    """
    Verifica se existe conflito de horário na mesma máquina.
    Retorna True se houver conflito.
    """

    if df.empty:
        return False

    df_maquina = df[
        (df["maquina"] == maquina) &
        (df["status"].isin(["Pendente", "Setup", "Manutenção"]))
    ]

    for _, row in df_maquina.iterrows():
        inicio_existente = row["inicio"]
        fim_existente = row["fim"]

        if (inicio_novo < fim_existente) and (fim_novo > inicio_existente):
            return True

    return False
