import pandas as pd
import streamlit as st

CARGA_UNIDADE = 49504
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT0S5BpJDZ0Wt9_g6UrNZbHK6Q7ekPwvKJC4lfAwFxs5E_ZJm-yfmAd2Uc51etjgCgs0l2kkuktVwIr/pub?gid=732189898&single=true&output=csv"


@st.cache_data(ttl=600)
def carregar_produtos_google():
    try:
        df = pd.read_csv(GOOGLE_SHEETS_URL)
        df.columns = df.columns.str.strip()
        df["id_item"] = df["ID_ITEM"].astype(str).str.strip()
        df["descricao"] = df["DESCRIÇÃO_1"].astype(str).str.strip()
        df["cliente"] = df["CLIENTE"].astype(str).str.strip()
        df["qtd_carga"] = pd.to_numeric(
            df["QTD/CARGA"].astype(str).str.replace(",", "."),
            errors="coerce"
        ).fillna(CARGA_UNIDADE)
        return df.fillna("N/A")
    except Exception:
        return pd.DataFrame(columns=["id_item", "descricao", "cliente", "qtd_carga"])
