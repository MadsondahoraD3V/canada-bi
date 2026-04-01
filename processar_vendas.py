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
import time

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS (ENTERPRISE UX + ANTI-FORK)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* =========================================
       BLINDAGEM ANTI-FORK (OCULTA O TOPO)
       Isso remove o botão do GitHub, o Menu e o Deploy
       ========================================= */
    header { visibility: hidden !important; display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; display: none !important; }

    /* REMOVE ESPAÇO MORTO NO TOPO DO STREAMLIT */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    
    /* FUNDO RADIAL PREMIUM */
    .stApp { background: radial-gradient(circle at top, #0f172a 0%, #020617 100%) !important; }
    
    [data-testid="stSidebar"] { 
        background-color: rgba(2, 6, 23, 0.7) !important; 
        border-right: 1px solid rgba(255,255,255,0.05) !important; 
        backdrop-filter: blur(12px) !important;
    }
    
    /* TEXTOS PUROS E ELEGANTES */
    .stTextInput label p, .stPasswordInput label p, .stSelectbox label p, .stNumberInput label p, .stDateInput label p { 
        color: #e2e8f0 !important; font-weight: 600 !important; font-size: 13px !important; letter-spacing: 0.5px;
    }
    
    /* INPUTS SOFISTICADOS */
    .stTextInput input, .stPasswordInput input {
        background-color: rgba(15, 23, 42, 0.6) !important; color: #ffffff !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important;
    }
    .stTextInput input:focus, .stPasswordInput input:focus {
        border-color: #38bdf8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.2) !important;
    }
    
    /* UPLOADER ESTILO SAAS */
    [data-testid="stFileUploadDropzone"] { background-color: rgba(15, 23, 42, 0.4) !important; }
    [data-testid="stFileUploader"] {
        background-color: rgba(15, 23, 42, 0.4) !important; border-radius: 16px; padding: 20px;
        border: 1px dashed rgba(56, 189, 248, 0.4) !important; backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover { border-color: #38bdf8 !important; background-color: rgba(15, 23, 42, 0.8) !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
    small { display: none !important; }
    
    /* MENU LATERAL MAGNÉTICO */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.05) !important; 
        border-radius: 8px; padding: 10px 15px; margin-bottom: 8px; text-align: left; cursor: pointer;
        transition: all 0.3s ease; color: #94a3b8 !important; font-weight: 500; width: 100%; position: relative;
    }
    div[role="radiogroup"] > label:hover, div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) { 
        background: rgba(56, 189, 248, 0.1) !important; border-color: rgba(56, 189, 248, 0.3) !important; 
        color: #ffffff !important; transform: translateX(4px); box-shadow: -4px 0px 0px 0px #38bdf8;
    }
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    /* BOTÕES MENORES E DISCRETOS */
    .stButton > button, .stDownloadButton > button {
        padding: 4px 12px !important; font-size: 13px !important; font-weight: 600 !important; min-height: 35px !important; 
        border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important;
        background: rgba(15, 23, 42, 0.8) !important; color: #e2e8f0 !important; transition: all 0.3s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: rgba(56, 189, 248, 0.15) !important; border-color: #38bdf8 !important; color: #ffffff !important;
        transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    /* COMPACTAÇÃO EXTREMA DA COLUNA DE CATEGORIAS (QUASE COLADAS) */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stHorizontalBlock"] {
        gap: 0rem !important; align-items: center !important; margin-bottom: -18px !important;
    }
    
    /* BOTÕES DAS CATEGORIAS (FILTROS) */
    .botao-categoria button {
        background-color: transparent !important; border: none !important; color: #94a3b8 !important;
        justify-content: flex-start !important; padding: 0px 5px !important; font-weight: 700 !important;
        font-size: 12px !important; box-shadow: none !important; min-height: 20px !important;
        transition: all 0.3s ease !important;
    }
    .botao-categoria button:hover { color: #38bdf8 !important; transform: translateX(3px); }

    /* CHECKBOXES ESTILIZADOS */
    [data-testid="stCheckbox"] { padding-top: 5px !important; }

    /* SCROLLBAR MINIMALISTA */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(56,189,248,0.5); }

    /* ASSINATURA EM BADGE PREMIUM (INTOCÁVEL) */
    .assinatura-master {
        position: fixed; bottom: 20px; left: 20px; background: rgba(2, 6, 23, 0.6); color: #64748b;
        padding: 8px 16px; border-radius: 30px; font-size: 10px; border: 1px solid rgba(255,255,255,0.05); 
        z-index: 999999; backdrop-filter: blur(10px); pointer-events: none; white-space: nowrap;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-transform: uppercase; letter-spacing: 0.5px;
    }

    footer {visibility: hidden;}
    </style>
    
    <div class="assinatura-master">
        Desenvolvido por <span style="color: #e0e7ff; font-weight: bold;">@madson_da_hora</span>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE GERENCIAMENTO (JSON)
# ==========================================
CONFIG_FILE = "usuarios_config.json"
LOG_FILE = "log_atividades.csv"

CORES_CATEGORIAS = {
    "Tabacaria": {"bg": "rgba(30, 41, 59, 0.7)", "glow": "rgba(51, 65, 85, 0.4)", "border": "#475569"},
    "Bebidas": {"bg": "rgba(30, 58, 138, 0.6)", "glow": "rgba(37, 99, 235, 0.3)", "border": "#3b82f6"},
    "Bomboniere": {"bg": "rgba(13, 148, 136, 0.6)", "glow": "rgba(20, 184, 166, 0.3)", "border": "#14b8a6"},
    "Remédios": {"bg": "rgba(190, 18, 60, 0.6)", "glow": "rgba(225, 29, 72, 0.3)", "border": "#e11d48"},
    "Mercearia": {"bg": "rgba(3, 105, 161, 0.6)", "glow": "rgba(2, 132, 199, 0.3)", "border": "#0284c7"}
}

DEFAULT_CONFIG = {
    "madson": {"name": "Madson", "password": "084269", "batch_allowed": True, "quota": 999, "trial_end": "2099-12-31"},
    "joacildo": {"name": "Joacildo", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "danila": {"name": "Danila", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "manoel": {"name": "Manoel", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"}
}

def salvar_configuracoes(config_data):
    with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f)

def carregar_configuracoes():
    if not os.path.exists(CONFIG_FILE):
        salvar_configuracoes(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        dados_salvos = json.load(f)
    precisa_atualizar = False
    for usuario, config_padrao in DEFAULT_CONFIG.items():
        if usuario not in dados_salvos:
            dados_salvos[usuario] = config_padrao
            precisa_atualizar = True
        else:
            for chave, valor in config_padrao.items():
                if chave not in dados_salvos[usuario]:
                    dados_salvos[usuario][chave] = valor
                    precisa_atualizar = True
    if precisa_atualizar: salvar_configuracoes(dados_salvos)
    return dados_salvos

def consumir_cota(username, config_data):
    if username != "madson" and username in config_data:
        config_data[username]["quota"] -= 1
        salvar_configuracoes(config_data)

def garantir_mesa_limpa(usuario_atual):
    if "usuario_anterior" not in st.session_state:
        st.session_state.usuario_anterior = usuario_atual
    if st.session_state.usuario_anterior != usuario_atual:
        st.session_state.arquivo_carregado = None
        st.session_state.cat_expandida = None
        st.session_state.usuario_anterior = usuario_atual

# ==========================================
# 3. FUNÇÕES CORE (CONGELADAS - INTOCÁVEIS)
# ==========================================
def registrar_log(usuario, arquivo, periodo):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    novo_log = pd.DataFrame([{"Data/Hora": agora, "Usuário": usuario, "Arquivo": arquivo, "Período": periodo}])
    if not os.path.isfile(LOG_FILE): novo_log.to_csv(LOG_FILE, index=False, sep=';', encoding='utf-8-sig')
    else: novo_log.to_csv(LOG_FILE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) 
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome) 
    return nome.replace('.', '').replace('-', '').strip()[:22]

def palpite_categoria(nome):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn').upper()
    
    if any(k in txt for k in ["BATATA DOCE", "ITALAKINHO", "DOCE DE LEITE", "ERVADOCE", "ERVA DOCE"]): 
        return "Mercearia"
        
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY", "FUMO", "SEDA", "GUNDANG", "GUDANG"]): 
        return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL", "BUDWEISER", "ITAIPAVA", "YPIOCA"]): 
        return "Bebidas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE", "JUJUBA", "DADA", "PACOCA", "MOLEQUE", "BALA"]): 
        return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): 
        return "Remédios"
        
    return "Mercearia"

def processar_pdf(file):
    dados = []
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        txt_topo = (pdf.pages[0].extract_text() or "")
        match_d = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', txt_topo)
        periodo = f"{match_d.group(1)} a {match_d.group(2)}" if match_d else "DATA DESCONHECIDA"
        for page in pdf.pages:
            texto_limpo = (page.extract_text() or "").replace('"', '').replace('\r', '')
            linhas = texto_limpo.split('\n')
            for linha in linhas:
                if "TOTAL" in linha.upper() or "PÁGINA" in linha.upper(): continue
                try:
                    valores = re.findall(r'\d+,\d{2}', linha)
                    if len(valores) >= 4:
                        ean_m = re.search(r'\b\d{7,14}\b', linha)
                        if not ean_m: continue
                        str_sem_ean = linha.replace(ean_m.group(), "").strip()
                        partes = re.split(r'\s*\b\d+,\d{2}\b', str_sem_ean)
                        n_bruto = partes[0].strip()
                        n_bruto = re.sub(r'\s+(UN|KG|CX|PCT|L|ML|G|KIT|M|DZ|BD|FD)\b$', '', n_bruto, flags=re.IGNORECASE).strip()
                        nome_limpo = limpar_nome_produto(n_bruto)
                        val = float(valores[-4].replace(',', '.'))
                        dados.append({"Nome": nome_limpo, "Cat": palpite_categoria(nome_limpo), "Valor": val})
                except Exception as e: continue
    return dados, periodo

# ==========================================
# 5. NOVO HTML EXPORTADO (COM NOME DO ARQUIVO)
# ==========================================
def gerar_html_interativo(df, periodo, total_geral, nome_arquivo):
    colunas_html = ""
    categorias_presentes = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
    for i, cat in enumerate(categorias_presentes):
        paleta = CORES_CATEGORIAS.get(cat, {"bg": "rgba(30, 41, 59, 0.7)", "glow": "rgba(51, 65, 85, 0.4)", "border": "#475569"})
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div class="cyber-card"><div class="card-title">{row["Nome"]}</div><div class="card-value">R$ {row["Valor"]:,.2f}</div></div>' for _, row in itens_cat.iterrows()])
        colunas_html += f"""
        <div class="coluna-categoria">
            <div class="accordion-header" style="background: {paleta['bg']}; box-shadow: 0 4px 15px {paleta['glow']}; border-color: {paleta['border']};" onclick="toggleAccordion('content-{i}')">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onclick="event.stopPropagation();" onchange="recalcular()">
                    <span class="cat-title">{cat.upper()}</span>
                </div>
                <span class="cat-total">R$ {valor_cat:,.2f}</span>
            </div>
            <div id="content-{i}" class="accordion-content"><div class="content-inner">{cards_html}</div></div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Canadá BI - Relatório Oficial</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap" rel="stylesheet">
        <style>
            :root {{ --bg-main: #020617; --text-main: #f8fafc; --accent: #38bdf8; }}
            body {{ background: radial-gradient(circle at top, #0f172a 0%, #020617 100%); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 30px; padding-bottom: 80px; min-height: 100vh; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 10px; }}
            .neon-bar {{ background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); padding: 30px; border-radius: 16px; text-align: center; margin-bottom: 40px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }}
            .neon-bar h3 {{ margin: 0; font-size: 13px; color: #94a3b8; letter-spacing: 2px; text-transform: uppercase; font-weight: 500; }}
            .neon-bar h1 {{ margin: 10px 0 0 0; font-size: 46px; font-weight: 900; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .container-cols {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; align-items: flex-start; }}
            .coluna-categoria {{ flex: 1; min-width: 240px; max-width: 320px; display: flex; flex-direction: column; }}
            .accordion-header {{ padding: 15px 20px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid; backdrop-filter: blur(8px); position: relative; z-index: 10; transition: transform 0.3s ease; }}
            .accordion-header:hover {{ transform: translateY(-2px); }}
            .cat-check {{ width: 18px; height: 18px; cursor: pointer; margin-right: 12px; accent-color: var(--accent); }}
            .cat-title {{ font-size: 13px; font-weight: 700; color: white; letter-spacing: 0.5px; }}
            .cat-total {{ font-size: 14px; font-weight: 700; color: white; background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 6px; }}
            .accordion-content {{ max-height: 0px; overflow-y: auto; transition: max-height 0.5s cubic-bezier(0.4, 0, 0.2, 1); background-color: rgba(2, 6, 23, 0.6); border-radius: 0 0 12px 12px; margin-top: -6px; backdrop-filter: blur(10px); }}
            .accordion-content.show {{ max-height: 450px; border: 1px solid rgba(255,255,255,0.05); border-top: none; }}
            .content-inner {{ padding: 15px 10px; display: flex; flex-direction: column; gap: 8px; }}
            .cyber-card {{ background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px; border-left: 3px solid rgba(255,255,255,0.2); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.02); transition: all 0.2s; }}
            .cyber-card:hover {{ background: rgba(255,255,255,0.05); border-left-color: var(--accent); transform: translateX(2px); }}
            .card-title {{ font-size: 12px; color: #e2e8f0; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .card-value {{ font-size: 13px; font-weight: 700; color: #ffffff; }}
            .assinatura-html {{ position: fixed; bottom: 20px; left: 20px; background: rgba(2, 6, 23, 0.8); color: #64748b; padding: 10px 20px; border-radius: 30px; font-size: 11px; border: 1px solid rgba(255,255,255,0.05); z-index: 9999; backdrop-filter: blur(12px); box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-transform: uppercase; letter-spacing: 0.5px; }}
            .assinatura-html span {{ color: #e0e7ff; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="neon-bar">
            <h3>Caixa Total Selecionado</h3>
            <h1 id="display-total">R$ {total_geral:,.2f}</h1>
            <p style="color:#64748b; font-size:12px; margin-top:8px; margin-bottom:0px;">Período Auditado: {periodo}</p>
            <p style="color:#475569; font-size:10px; margin-top:2px;">Arquivo Origem: {nome_arquivo}</p>
        </div>
        <div class="container-cols">{colunas_html}</div>
        <div class="assinatura-html">Desenvolvido por <span>@madson_da_hora</span></div>
        <script>
            function toggleAccordion(id) {{ document.getElementById(id).classList.toggle("show"); }}
            function recalcular() {{
                let total = 0;
                document.querySelectorAll('.cat-check').forEach(check => {{ if (check.checked) total += parseFloat(check.getAttribute('data-valor')); }});
                document.getElementById('display-total').innerText = "R$ " + total.toLocaleString('pt-BR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
            }}
        </script>
    </body>
    </html>"""

# ==========================================
# 4. SEGURANÇA E LOGIN DINÂMICO
# ==========================================
config_usuarios = carregar_configuracoes()

credentials_dict = {"usernames": {}}
for u, data in config_usuarios.items():
    credentials_dict["usernames"][u] = {"name": data["name"], "password": data["password"]}

authenticator = stauth.Authenticate(credentials_dict, "canada_bi_v26", "auth_key_v26", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    user_logado = st.session_state['username']
    garantir_mesa_limpa(user_logado)

    if 'cat_expandida' not in st.session_state:
        st.session_state.cat_expandida = None

    st.sidebar.markdown(f"<h3 style='color:#ffffff; font-size:18px; font-weight:700; margin-bottom: 25px;'>Olá, {st.session_state['name']}</h3>", unsafe_allow_html=True)
    
    # EFEITO ESMAECIDO E TOOLTIP PARA USUÁRIOS COMUNS
    css_bloqueio = ""
    if user_logado != 'madson':
        css_bloqueio += """
        div[role="radiogroup"] > label:nth-child(3),
        div[role="radiogroup"] > label:nth-child(4) {
            opacity: 0.3 !important; filter: grayscale(100%) !important; cursor: not-allowed !important; pointer-events: auto !important;
        }
        div[role="radiogroup"] > label:nth-child(3):hover::after,
        div[role="radiogroup"] > label:nth-child(4):hover::after {
            content: "Recurso Premium. Contate o Administrador.";
            position: absolute; top: 100%; left: 0%; width: 100%; background: #e11d48; color: white;
            padding: 5px 0; border-radius: 6px; font-size: 10px; text-align: center; z-index: 99999; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        """
        if not config_usuarios.get(user_logado, {}).get("batch_allowed", False):
            css_bloqueio += """
            div[role="radiogroup"] > label:nth-child(2) {
                opacity: 0.3 !important; filter: grayscale(100%) !important; cursor: not-allowed !important; pointer-events: auto !important;
            }
            div[role="radiogroup"] > label:nth-child(2):hover::after {
                content: "Sua assinatura não contempla múltiplas gerações.";
                position: absolute; top: 100%; left: 0%; width: 100%; background: #e11d48; color: white;
                padding: 5px 0; border-radius: 6px; font-size: 10px; text-align: center; z-index: 99999; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            """
    st.markdown(f"<style>{css_bloqueio}</style>", unsafe_allow_html=True)

    opcoes_menu = ["Análise de Relatório", "Gerar Multiplos Relatorios", "Historico de Atividades", "Central de Permissões"]
    pagina = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    if user_logado != "madson":
        cota_atual = config_usuarios.get(user_logado, {}).get("quota", 0)
        validade = config_usuarios.get(user_logado, {}).get("trial_end", "N/A")
        st.sidebar.markdown(f"<div style='background:rgba(255,255,255,0.02); padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.05);'><p style='color:#94a3b8; font-size:11px; margin:0;'>Uploads Restantes: <b style='color:#38bdf8; font-size:13px;'>{cota_atual}</b></p><p style='color:#94a3b8; font-size:11px; margin:5px 0 0 0;'>Validade: <b style='color:#38bdf8; font-size:13px;'>{validade}</b></p></div>", unsafe_allow_html=True)

    authenticator.logout("Encerrar Sessão", "sidebar")

    # --- PÁGINA 1: ANÁLISE DE RELATÓRIO ---
    if pagina == "Análise de Relatório":
        
        trial_end = datetime.strptime(config_usuarios[user_logado]["trial_end"], "%Y-%m-%d").date()
        if date.today() > trial_end or (config_usuarios[user_logado]["quota"] <= 0 and user_logado != "madson"):
            st.error("Acesso Expirado ou Sem Cotas. Contate o Administrador.")
        else:
            if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None

            if st.session_state.arquivo_carregado is None:
                st.markdown("<h2 style='color:#ffffff; font-size:26px; font-weight:800; margin-top:-10px; letter-spacing:-0.5px;'>Análise de Relatório</h2>", unsafe_allow_html=True)
                file = st.file_uploader("Selecionar Novo Relatório", type="pdf", key="single")
                if file:
                    st.session_state.arquivo_carregado = file
                    dados, per = processar_pdf(file)
                    registrar_log(st.session_state['name'], file.name, per)
                    consumir_cota(user_logado, config_usuarios)
                    st.rerun()
            else:
                file = st.session_state.arquivo_carregado
                dados, per = processar_pdf(file)
                df = pd.DataFrame(dados)
                total_bruto = df['Valor'].sum()

                col_topo1, col_topo2, col_topo3 = st.columns([5, 2.5, 2.5])
                with col_topo1:
                    st.markdown("<h2 style='color:#ffffff; font-size:26px; font-weight:800; margin-top:-10px; margin-bottom:0px; letter-spacing:-0.5px;'>Análise de Relatório</h2>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#64748b; font-size:12px; margin-top:5px; margin-bottom:0px; text-transform:uppercase; letter-spacing:1px;'>Período Auditado: <b style='color:#38bdf8;'>{per}</b></p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#475569; font-size:10px; margin-top:0px; margin-bottom:0px;'>Arquivo origem: <i>{file.name}</i></p>", unsafe_allow_html=True)
                with col_topo2:
                    st.markdown("<div style='margin-top:0px;'>", unsafe_allow_html=True)
                    html_rel = gerar_html_interativo(df, per, total_bruto, file.name)
                    nome_arquivo_html = f"RELATORIO DE {per.replace('/', '-').replace(' a ', '_a_')}.html"
                    st.download_button(label="📥 Salvar Relatório Atual", data=html_rel, file_name=nome_arquivo_html, mime="text/html", use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col_topo3:
                    st.markdown("<div style='margin-top:0px;'>", unsafe_allow_html=True)
                    if st.button("🔄 Novo Upload", use_container_width=True):
                        st.session_state.arquivo_carregado = None
                        st.session_state.cat_expandida = None
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin-top:15px; margin-bottom:20px;'>", unsafe_allow_html=True)
                
                col_filtros, col_total, col_detalhes = st.columns([2.5, 3.5, 5], gap="large")
                selecionadas = []
                categorias_pdf = sorted(df['Cat'].unique())
                
                with col_filtros:
                    st.markdown("<h4 style='color:#94a3b8; font-size:11px; margin-bottom:15px; text-transform:uppercase; letter-spacing:1px;'>Categorias</h4>", unsafe_allow_html=True)
                    for cat in categorias_pdf:
                        v = df[df['Cat'] == cat]['Valor'].sum() if not df.empty else 0
                        c_chk, c_btn, c_val = st.columns([1, 5, 4])
                        with c_chk:
                            if st.checkbox("", value=True, key=f"chk_{cat}"): selecionadas.append(cat)
                        with c_btn:
                            st.markdown('<div class="botao-categoria">', unsafe_allow_html=True)
                            if st.button(cat, key=f"btn_{cat}", use_container_width=True): st.session_state.cat_expandida = cat
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c_val:
                            st.markdown(f"<div style='padding-top:4px; color:#ffffff; font-weight:700; font-size:13px; text-align:right;'>{formatar_moeda(v)}</div>", unsafe_allow_html=True)

                with col_total:
                    st.markdown("<h4 style='color:#94a3b8; font-size:11px; margin-bottom:15px; text-transform:uppercase; letter-spacing:1px;'>Resumo Financeiro</h4>", unsafe_allow_html=True)
                    soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum() if not df.empty else 0
                    
                    st.markdown(f'''
                    <style>
                    .caixa-bruto {{ background: rgba(30, 58, 138, 0.15); backdrop-filter: blur(10px); padding: 30px 20px; border-radius: 16px; text-align: center; border: 1px solid rgba(59, 130, 246, 0.3); box-shadow: 0 10px 30px -10px rgba(37, 99, 235, 0.2); transition: all 0.3s ease; }}
                    .caixa-bruto:hover {{ transform: translateY(-3px); box-shadow: 0 15px 30px -10px rgba(37, 99, 235, 0.4); border-color: #38bdf8; }}
                    </style>
                    <div class="caixa-bruto">
                        <p style="margin:0; color:#94a3b8; font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;">Caixa Total Bruto</p>
                        <h1 style="margin:10px 0 0 0; font-size:32px; font-weight:900; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{formatar_moeda(soma_f)}</h1>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_detalhes:
                    st.markdown("<h4 style='color:#94a3b8; font-size:11px; margin-bottom:15px; text-transform:uppercase; letter-spacing:1px;'>Detalhamento do Relatório</h4>", unsafe_allow_html=True)
                    if st.session_state.cat_expandida:
                        cat_atual = st.session_state.cat_expandida
                        itens = df[df['Cat'] == cat_atual]
                        
                        st.markdown("""
                        <style>
                        .detalhe-panel { background:rgba(15, 23, 42, 0.6); backdrop-filter: blur(8px); padding:15px; border-radius:12px; border:1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease; }
                        .detalhe-panel:hover { box-shadow: 0 10px 20px rgba(0,0,0,0.2); border-left: 2px solid #38bdf8; }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        html_itens = f"<div class='detalhe-panel'>"
                        html_itens += f"<h5 style='color:#e2e8f0; margin:0 0 12px 0; font-size:13px; font-weight:700; letter-spacing:0.5px;'>{cat_atual.upper()}</h5>"
                        html_itens += "<div style='max-height: 400px; overflow-y: auto; padding-right:8px;'>"
                        for _, row in itens.iterrows():
                            html_itens += f"<div style='display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding:8px 0; transition: background 0.2s;' onmouseover=\"this.style.background='rgba(255,255,255,0.02)'\" onmouseout=\"this.style.background='transparent'\"><span style='color:#cbd5e1; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%; font-weight:500;'>{row['Nome']}</span><span style='color:#ffffff; font-size:12px; font-weight:700;'>R$ {row['Valor']:,.2f}</span></div>"
                        html_itens += "</div></div>"
                        st.markdown(html_itens, unsafe_allow_html=True)
                    else:
                        st.markdown("""<div style="background:rgba(15, 23, 42, 0.4); padding:20px; border-radius:12px; text-align:center; border: 1px dashed rgba(255,255,255,0.1);"><p style="color:#64748b; font-size:12px; font-weight:500; margin:0;">Selecione uma categoria ao lado para inspecionar os itens.</p></div>""", unsafe_allow_html=True)

    elif pagina == "Gerar Multiplos Relatorios":
        if not config_usuarios[user_logado]["batch_allowed"] and user_logado != "madson":
            pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:26px; font-weight:800; letter-spacing:-0.5px; margin-top:-10px;'>Processamento em Lote</h2>", unsafe_allow_html=True)
            batch_files = st.file_uploader("Selecionar Novos Relatórios", type="pdf", accept_multiple_files=True)
            if batch_files:
                for f in batch_files[:7]:
                    try:
                        dados, per = processar_pdf(f)
                        registrar_log(st.session_state['name'], f.name, per)
                        consumir_cota(user_logado, config_usuarios)
                    except: continue
                st.success("Arquivos processados com sucesso.")

    elif pagina == "Historico de Atividades":
        if user_logado != "madson":
            pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:26px; font-weight:800; letter-spacing:-0.5px; margin-top:-10px;'>Histórico de Auditoria</h2>", unsafe_allow_html=True)
            if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE, sep=';').sort_index(ascending=False), use_container_width=True)

    elif pagina == "Central de Permissões":
        if user_logado != "madson":
            pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:26px; font-weight:800; margin-bottom: 20px; letter-spacing:-0.5px; margin-top:-10px;'>Central de Permissões</h2>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2, gap="large")
            
            with c1:
                st.markdown("<div style='background:rgba(15, 23, 42, 0.6); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color:#38bdf8; font-size:14px; text-transform:uppercase; margin-bottom:15px;'>Editar Acesso Existente</h4>", unsafe_allow_html=True)
                usuarios_comuns = [u for u in config_usuarios.keys() if u != "madson"]
                usr_selecionado = st.selectbox("Selecione o Cliente", usuarios_comuns)
                
                if usr_selecionado:
                    dados_usr = config_usuarios[usr_selecionado]
                    with st.form("form_admin"):
                        nova_senha = st.text_input("Senha do Cliente", value=dados_usr["password"])
                        novo_batch = st.checkbox("Liberar Múltiplos Relatórios", value=dados_usr["batch_allowed"])
                        nova_cota = st.number_input("Cota de Uploads", min_value=0, value=dados_usr["quota"], step=1)
                        data_atual = datetime.strptime(dados_usr["trial_end"], "%Y-%m-%d").date()
                        nova_data = st.date_input("Vencimento do Plano", value=data_atual)
                        
                        if st.form_submit_button("Atualizar Cliente"):
                            config_usuarios[usr_selecionado]["password"] = nova_senha
                            config_usuarios[usr_selecionado]["batch_allowed"] = novo_batch
                            config_usuarios[usr_selecionado]["quota"] = nova_cota
                            config_usuarios[usr_selecionado]["trial_end"] = nova_data.strftime("%Y-%m-%d")
                            salvar_configuracoes(config_usuarios)
                            st.success("Dados atualizados instantaneamente!")
                st.markdown("</div>", unsafe_allow_html=True)
            
            with c2:
                st.markdown("<div style='background:rgba(15, 23, 42, 0.6); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color:#10b981; font-size:14px; text-transform:uppercase; margin-bottom:15px;'>Criar Novo Cliente</h4>", unsafe_allow_html=True)
                with st.form("form_novo_usuario"):
                    novo_login = st.text_input("Login (Sem espaços, ex: joao123)")
                    novo_nome = st.text_input("Nome da Empresa/Cliente")
                    nova_senha_criacao = st.text_input("Definir Senha Inicial", type="password")
                    
                    if st.form_submit_button("Adicionar ao Sistema"):
                        if novo_login and novo_nome and nova_senha_criacao:
                            novo_login_formatado = novo_login.lower().strip().replace(" ", "")
                            if novo_login_formatado in config_usuarios:
                                st.error("Login indisponível.")
                            else:
                                config_usuarios[novo_login_formatado] = {
                                    "name": novo_nome,
                                    "password": nova_senha_criacao,
                                    "batch_allowed": False,
                                    "quota": 15,
                                    "trial_end": "2026-12-31"
                                }
                                salvar_configuracoes(config_usuarios)
                                st.success(f"Cliente '{novo_nome}' pronto para acesso!")
                                time.sleep(1.5)
                                st.rerun()
                        else:
                            st.warning("Preencha todos os campos obrigatórios.")
                st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.get("authentication_status") is False:
    st.error("Credenciais inválidas. Verifique seu login e senha.")
elif st.session_state.get("authentication_status") is None:
    st.info("Plataforma Restrita. Insira suas credenciais para prosseguir.")
