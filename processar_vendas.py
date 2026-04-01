import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
from datetime import datetime, date
import os
import json

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS (SITE)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* Fundo Escuro Corporativo */
    .stApp { background-color: #020617; }
    
    /* Assinatura Flutuante Global */
    .assinatura-flutuante {
        position: fixed; bottom: 15px; right: 20px;
        background: rgba(15, 23, 42, 0.9); color: #94a3b8;
        padding: 8px 15px; border-radius: 20px; font-size: 11px;
        border: 1px solid #1e293b; z-index: 9999; backdrop-filter: blur(5px);
    }
    .assinatura-flutuante span { color: #0ea5e9; font-weight: bold; }

    /* Total Flutuante no Topo (Azul Corporativo) */
    .floating-sum {
        position: fixed; top: 70px; right: 30px;
        background: linear-gradient(135deg, #0f172a 0%, #0284c7 100%);
        color: white; padding: 15px 25px; border-radius: 30px; z-index: 1000;
        font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
        text-align: center; border: 1px solid #0284c7;
    }
    
    /* Cards de Categoria */
    .cat-card {
        background: rgba(15, 23, 42, 0.5); border: 1px solid #1e293b;
        border-radius: 8px; padding: 12px; text-align: center; margin-top: 5px;
        transition: all 0.3s;
    }
    .cat-card:hover { border-color: #0284c7; background: rgba(15, 23, 42, 0.8); }

    /* Estilização do Menu Lateral */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
        padding: 12px; margin-bottom: 8px; text-align: center; cursor: pointer;
        transition: all 0.3s ease; color: #94a3b8; font-weight: bold; width: 100%;
    }
    div[role="radiogroup"] > label:hover { 
        background: #1e293b; border-color: #0ea5e9; color: #0ea5e9; transform: translateX(5px);
    }
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    /* Customizando o botão de Upload do Streamlit para ficar redondo */
    [data-testid="stFileUploader"] section {
        border: 2px dashed #1e293b !important;
        border-radius: 15px !important;
        background-color: #0f172a !important;
        padding: 20px !important;
    }
    [data-testid="stFileUploader"] button {
        border-radius: 30px !important;
        background-color: transparent !important;
        border: 1px solid #0ea5e9 !important;
        color: #0ea5e9 !important;
        font-weight: bold !important;
        padding: 10px 25px !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background-color: #0ea5e9 !important;
        color: white !important;
    }
    
    /* Esconder elementos inúteis do uploader nativo */
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
    small { display: none !important; }

    footer {visibility: hidden;}
    </style>
    
    <div class="assinatura-flutuante">Desenvolvido por <span>@madson_da_hora</span> / Analista de dados e Programador</div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE GERENCIAMENTO (JSON) E SESSÃO
# ==========================================
CONFIG_FILE = "usuarios_config.json"
LOG_FILE = "log_atividades.csv"

DEFAULT_CONFIG = {
    "joacildo": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "danila": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "manoel": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"}
}

def carregar_configuracoes():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f: json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def salvar_configuracoes(config_data):
    with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f)

def verificar_acesso(username, config_data, is_batch=False):
    if username == "madson": return True, "" 
    user_data = config_data.get(username)
    if not user_data: return False, "Usuário não configurado no sistema."
    trial_end = datetime.strptime(user_data["trial_end"], "%Y-%m-%d").date()
    if date.today() > trial_end: return False, "Seu período de acesso expirou. Contate o Administrador."
    if user_data["quota"] <= 0: return False, "Sua cota de uploads atingiu o limite."
    if is_batch and not user_data["batch_allowed"]: return False, "Acesso restrito: Geração múltipla não permitida."
    return True, ""

def consumir_cota(username, config_data):
    if username != "madson" and username in config_data:
        config_data[username]["quota"] -= 1
        salvar_configuracoes(config_data)

def limpar_sessao_se_novo_usuario(username_atual):
    """Limpa o cache de arquivos se um usuário diferente logar, evitando vazamento de dados."""
    if "ultimo_usuario" not in st.session_state:
        st.session_state.ultimo_usuario = ""
        
    if st.session_state.ultimo_usuario != username_atual:
        st.session_state.arquivo_carregado = None
        st.session_state.ultimo_usuario = username_atual

# ==========================================
# 3. FUNÇÕES CORE E GERADOR DE HTML
# ==========================================
def registrar_log(usuario, arquivo, periodo):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    novo_log = pd.DataFrame([{"Data/Hora": agora, "Usuário": usuario, "Arquivo": arquivo, "Período": periodo}])
    if not os.path.isfile(LOG_FILE):
        novo_log.to_csv(LOG_FILE, index=False, sep=';', encoding='utf-8-sig')
    else:
        novo_log.to_csv(LOG_FILE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) 
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome) 
    return nome.replace('.', '').replace('-', '').strip()[:22]

def palpite_categoria(nome):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn').upper()
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): return "Remédios"
    return "Mercearia"

def gerar_html_interativo(df, periodo, total_geral):
    """Gera o HTML com paleta Azul Corporativo e Assinatura."""
    cores = {
        "Tabacaria": {"bg": "#ea580c", "glow": "rgba(234, 88, 12, 0.2)"},
        "Bebidas": {"bg": "#2563eb", "glow": "rgba(37, 99, 235, 0.2)"},
        "Bomboniere": {"bg": "#db2777", "glow": "rgba(219, 39, 119, 0.2)"},
        "Remédios": {"bg": "#059669", "glow": "rgba(5, 150, 105, 0.2)"},
        "Mercearia": {"bg": "#475569", "glow": "rgba(71, 85, 105, 0.2)"}
    }
    colunas_html = ""
    
    for i, (cat, paleta) in enumerate(cores.items()):
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div class="cyber-card"><div class="card-title">{row["Nome"]}</div><div class="card-value">R$ {row["Valor"]:,.2f}</div></div>' for _, row in itens_cat.iterrows()])

        colunas_html += f"""
        <div class="coluna-categoria">
            <div class="accordion-header" style="background: {paleta['bg']}; box-shadow: 0 0 10px {paleta['glow']};" onclick="toggleAccordion('content-{i}')">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onclick="event.stopPropagation();" onchange="recalcular()">
                    <span class="cat-title">{cat.upper()}</span>
                </div>
                <span class="cat-total">R$ {valor_cat:,.2f}</span>
            </div>
            <div id="content-{i}" class="accordion-content">
                <div class="content-inner">{cards_html}</div>
            </div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Canadá BI - Relatório Corporativo</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
        <style>
            :root {{ --bg-main: #020617; --bg-panel: #0f172a; --bg-card: #1e293b; --text-main: #f8fafc; --text-muted: #94a3b8; --accent: #0ea5e9; --success: #0284c7; }}
            body {{ background-color: var(--bg-main); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; padding-bottom: 80px; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius:
