# =================================================================
# ABA 2 - CRONOGRAMA SOPRO
# =================================================================

import streamlit as st
from config import MAQUINAS_SOPRO
from components import renderizar_setor

def mostrar_sopro():
    renderizar_setor(MAQUINAS_SOPRO)
