def verificar_conflito(df, maquina, inicio_novo, fim_novo):

    if df.empty:
        return False

    df_maquina = df[
        (df["maquina"] == maquina)
        & (df["status"].isin(["Pendente","Setup","Manutenção"]))
    ]

    for _, row in df_maquina.iterrows():

        inicio_existente = row["inicio"]
        fim_existente = row["fim"]

        if (inicio_novo < fim_existente) and (fim_novo > inicio_existente):

            return True

    return False
