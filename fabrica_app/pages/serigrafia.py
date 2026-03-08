# =================================================================
# ABA 1 - CRONOGRAMA SERIGRAFIA
# =================================================================

import streamlit as st
from config import MAQUINAS_SERIGRAFIA
from components import renderizar_setor

def mostrar_serigrafia():
    renderizar_setor(MAQUINAS_SERIGRAFIA)
