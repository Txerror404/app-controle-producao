# =================================================================
# ESTILOS CSS DA INTERFACE
# =================================================================

import streamlit as st

def aplicar_estilos():
    st.markdown("""
    <style>
        /* Container principal */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
            background-color: #1A1E24;
        }
        
        /* Toolbar do Plotly */
        .modebar-container {
            top: 5px !important;
            right: 10px !important;
            opacity: 0.8 !important;
            background-color: #252A33 !important;
            border-radius: 8px !important;
            padding: 5px !important;
            border: 1px solid #3A404C !important;
        }
        .modebar-container:hover {
            opacity: 1 !important;
        }
        
        .modebar-btn {
            color: #E0E0E0 !important;
        }
        .modebar-btn:hover {
            color: #E63946 !important;
        }
        
        /* Estilo das abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
            padding: 0px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #252A33;
            border-radius: 6px;
            padding: 8px 20px;
            color: #E0E0E0;
            font-weight: 500;
            border: 1px solid #3A404C;
            transition: all 0.2s;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #2F3540;
            color: #FFFFFF;
            border-color: #E63946;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #E63946 !important;
            color: white !important;
            border-color: #E63946 !important;
        }
        
        /* Cards de métricas */
        div[data-testid="metric-container"] {
            background-color: #252A33;
            border: 1px solid #3A404C;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        
        div[data-testid="metric-container"] label {
            color: #A0A8B8 !important;
            font-size: 14px !important;
        }
        
        div[data-testid="metric-container"] div {
            color: #FFFFFF !important;
            font-size: 24px !important;
            font-weight: 600 !important;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #FFFFFF !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Divisores */
        hr {
            margin-top: 1rem !important;
            margin-bottom: 1rem !important;
            border-color: #3A404C !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #252A33;
            border-radius: 6px;
            border: 1px solid #3A404C;
            color: #FFFFFF !important;
        }
        
        .streamlit-expanderContent {
            background-color: #1A1E24;
            border: 1px solid #3A404C;
            border-top: none;
            border-radius: 0 0 6px 6px;
        }
        
        /* Inputs e selects */
        div[data-baseweb="select"] > div {
            background-color: #252A33 !important;
            border-color: #3A404C !important;
        }
        
        input, textarea, [data-baseweb="input"] input {
            background-color: #252A33 !important;
            border-color: #3A404C !important;
            color: #FFFFFF !important;
        }
        
        label {
            color: #A0A8B8 !important;
            font-weight: 500 !important;
        }
        
        /* Botões */
        .stButton button {
            background-color: #252A33;
            border: 1px solid #E63946;
            color: #E63946;
            border-radius: 6px;
            transition: all 0.2s;
            width: 100%;
            font-weight: 500;
        }
        
        .stButton button:hover {
            background-color: #E63946;
            color: white;
            border-color: #E63946;
        }
        
        /* Cards de status personalizados */
        .status-card-atrasada {
            background-color: rgba(230, 57, 70, 0.12);
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #E63946;
            margin-bottom: 10px;
            border: 1px solid #3A404C;
        }
        
        .status-card-execucao {
            background-color: rgba(243, 156, 18, 0.12);
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #F39C12;
            margin-bottom: 10px;
            border: 1px solid #3A404C;
        }
        
        .status-card-semop {
            background-color: rgba(149, 165, 166, 0.12);
            padding: 15px;
            border-radius: 10px;
            border-left: 6px solid #95A5A6;
            margin-bottom: 10px;
            text-align: center;
            border: 1px solid #3A404C;
        }
        
        /* Cabeçalho customizado */
        .custom-header {
            background-color: #252A33;
            padding: 8px 15px;
            border-radius: 8px;
            border-left: 8px solid #E63946;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #3A404C;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        .custom-header h2 {
            color: #FFFFFF !important;
            margin: 0;
            font-size: 20px;
        }
        
        .custom-header p {
            color: #A0A8B8 !important;
            margin: 2px 0 0 0;
            font-size: 12px;
        }
        
        .clock-box {
            text-align: center;
            border: 1px solid #E63946;
            padding: 2px 15px;
            border-radius: 5px;
            background-color: #1A1E24;
            min-width: 130px;
            box-shadow: 0 2px 8px rgba(230, 57, 70, 0.2);
        }
        
        .clock-time {
            color: #E63946;
            margin: 0;
            font-family: 'Courier New', monospace;
            font-size: 22px;
            font-weight: bold;
        }
        
        .clock-date {
            color: #A0A8B8;
            margin: -2px 0 2px 0;
            font-size: 12px;
            border-top: 1px dashed #E63946;
            padding-top: 2px;
        }
        
        /* Rodapé */
        .footer {
            text-align: center;
            color: #A0A8B8;
            font-size: 12px;
            padding: 20px 0 10px 0;
            border-top: 1px solid #3A404C;
            margin-top: 30px;
        }
        
        /* Texto em geral */
        p, li, .stMarkdown {
            color: #E0E0E0 !important;
        }
        
        /* Info boxes */
        .stAlert {
            background-color: #252A33 !important;
            border: 1px solid #3A404C !important;
            color: #E0E0E0 !important;
        }
        
        /* Dataframes */
        .dataframe {
            background-color: #252A33 !important;
            color: #E0E0E0 !important;
        }
        
        /* Popovers */
        div[data-testid="stPopover"] {
            background-color: #252A33;
            border: 1px solid #3A404C;
        }
        
        /* Selectbox dropdown */
        div[data-baseweb="popover"] {
            background-color: #252A33 !important;
            border: 1px solid #3A404C !important;
        }
        
        li[role="option"] {
            color: #E0E0E0 !important;
        }
        
        li[role="option"]:hover {
            background-color: #2F3540 !important;
        }
        
        /* Número de inputs */
        .stNumberInput input {
            background-color: #252A33 !important;
            color: #FFFFFF !important;
        }
        
        /* Date input e time input */
        .stDateInput input, .stTimeInput input {
            background-color: #252A33 !important;
            color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)
