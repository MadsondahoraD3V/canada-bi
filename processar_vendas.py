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
# 1. CONFIGURAÇÕES VISUAIS E CSS (CORPORATIVO)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* BLINDAGEM CONTRA MODO CLARO DO NAVEGADOR */
    .stApp, .stApp > header { background-color: #0f172a !important; }
    
    /* Forçar Barra Lateral Escura e Textos Claros */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    
    /* Consertar o Fundo Branco do Uploader no Chrome */
    [data-testid="stFileUploadDropzone"] { background-color: #1e293b !important; }
    
    /* Assinatura Flutuante Global */
    .assinatura-flutuante {
        position: fixed; bottom: 15px; left: 20px;
        background: rgba(15, 23, 42, 0.9); color: #94a3b8;
        padding: 8px 15px; border-radius: 20px; font-size: 11px;
        border: 1px solid #334155; z-index: 9999; backdrop-filter: blur(5px);
    }
    .assinatura-flutuante span { color: #38bdf8; font-weight: bold; }

    /* Total Flutuante no Topo */
    .floating-sum {
        position: fixed; top: 70px; right: 30px;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        color: white; padding: 15px 25px; border-radius: 8px; z-index: 1000;
        font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        text-align: center; border: 1px solid #3b82f6;
    }
    
    /* Cards de Categoria */
    .cat-card {
        background: #1e293b; border: 1px solid #334155;
        border-radius: 6px; padding: 15px; text-align: center; margin-top: 5px;
        transition: all 0.3s;
    }
    .cat-card:hover { border-color: #38bdf8; background: #0f172a; }

    /* Menu Lateral Futurista */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 6px;
        padding: 10px; margin-bottom: 8px; text-align: center; cursor: pointer;
        transition: all 0.3s ease; color: #cbd5e1 !important; font-weight: bold; width: 100%;
    }
    div[role="radiogroup"] > label:hover { 
        background: #0f172a !important; border-color: #38bdf8 !important; color: #38bdf8 !important; transform: translateX(5px);
    }
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    /* Customizando a área de Upload */
    [data-testid="stFileUploader"] {
        background-color: #1e293b !important; border-radius: 12px; padding: 15px;
        border: 1px solid #334155 !important;
    }
    
    /* Ocultando textos desnecessários do uploader nativo */
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

def garantir_mesa_limpa(usuario_atual):
    if "usuario_anterior" not in st.session_state:
        st.session_state.usuario_anterior = usuario_atual
    if st.session_state.usuario_anterior != usuario_atual:
        st.session_state.arquivo_carregado = None
        st.session_state.usuario_anterior = usuario_atual

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
    cores = {
        "Tabacaria": {"bg": "#334155", "glow": "rgba(51, 65, 85, 0.2)"},
        "Bebidas": {"bg": "#1e3a8a", "glow": "rgba(30, 58, 138, 0.2)"},
        "Bomboniere": {"bg": "#0f766e", "glow": "rgba(15, 118, 110, 0.2)"},
        "Remédios": {"bg": "#9a3412", "glow": "rgba(154, 52, 18, 0.2)"},
        "Mercearia": {"bg": "#0369a1", "glow": "rgba(3, 105, 161, 0.2)"}
    }
    colunas_html = ""
    for i, (cat, paleta) in enumerate(cores.items()):
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div class="cyber-card"><div class="card-title">{row["Nome"]}</div><div class="card-value">R$ {row["Valor"]:,.2f}</div></div>' for _, row in itens_cat.iterrows()])
        colunas_html += f"""
        <div class="coluna-categoria">
            <div class="accordion-header" style="background: {paleta['bg']}; box-shadow: 0 2px 10px {paleta['glow']};" onclick="toggleAccordion('content-{i}')">
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
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {{ --bg-main: #0f172a; --bg-panel: #1e293b; --bg-card: #0f172a; --text-main: #f8fafc; --text-muted: #94a3b8; --accent: #38bdf8; --success: #38bdf8; }}
            body {{ background-color: var(--bg-main); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; padding-bottom: 80px; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 10px; }}
            .neon-bar {{ background: linear-gradient(90deg, #1e293b, #1e3a8a); padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 30px; border: 1px solid #334155; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }}
            .neon-bar h3 {{ margin: 0; font-size: 12px; color: #cbd5e1; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; }}
            .neon-bar h1 {{ margin: 5px 0; font-size: 38px; font-weight: 800; color: white; }}
            .container-cols {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; align-items: flex-start; }}
            .coluna-categoria {{ flex: 1; min-width: 220px; max-width: 300px; display: flex; flex-direction: column; }}
            .accordion-header {{ padding: 12px 15px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid rgba(255,255,255,0.05); position: relative; z-index: 10; }}
            .cat-check {{ width: 16px; height: 16px; cursor: pointer; margin-right: 10px; }}
            .cat-title {{ font-size: 12px; font-weight: bold; color: white; letter-spacing: 0.5px; }}
            .cat-total {{ font-size: 13px; font-weight: bold; color: white; background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 4px; }}
            .accordion-content {{ max-height: 0px; overflow-y: auto; transition: max-height 0.4s; background-color: var(--bg-panel); border-radius: 0 0 6px 6px; margin-top: -3px; }}
            .accordion-content.show {{ max-height: 400px; border: 1px solid #334155; border-top: none; }}
            .content-inner {{ padding: 12px 8px; display: flex; flex-direction: column; gap: 6px; }}
            .cyber-card {{ background: var(--bg-card); padding: 10px; border-radius: 4px; border-left: 3px solid var(--accent); display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155; }}
            .card-title {{ font-size: 11px; color: #cbd5e1; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .card-value {{ font-size: 12px; font-weight: bold; color: var(--accent); }}
            .assinatura-html {{ position: fixed; bottom: 15px; left: 20px; background: rgba(15, 23, 42, 0.9); color: #94a3b8; padding: 8px 15px; border-radius: 20px; font-size: 11px; border: 1px solid #334155; z-index: 9999; }}
            .assinatura-html span {{ color: #38bdf8; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="neon-bar"><h3>CAIXA TOTAL SELECIONADO</h3><h1 id="display-total">R$ {total_geral:,.2f}</h1><p style="color:#94a3b8; font-size:11px; margin:0;">Período: {periodo}</p></div>
        <div class="container-cols">{colunas_html}</div>
        <div class="assinatura-html">Desenvolvido por <span>@madson_da_hora</span> / Analista de dados e Programador</div>
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

def processar_pdf(file):
    dados = []
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        txt_topo = (pdf.pages[0].extract_text() or "")
        match_d = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', txt_topo)
        periodo = f"{match_d.group(1)} a {match_d.group(2)}" if match_d else "DATA DESCONHECIDA"
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for linha in linhas:
                try:
                    valores = re.findall(r'\d+,\d{2}', linha)
                    if len(valores) >= 4:
                        ean_m = re.search(r'\b\d{8,14}\b', linha)
                        nome_m = re.search(r'(.+?)\s+(?:UN|KG)\s+\d+,\d{2}', linha)
                        n_bruto = nome_m.group(1).replace(ean_m.group() if ean_m else "", "").strip()
                        nome_limpo = limpar_nome_produto(n_bruto)
                        val = float(valores[-4].replace(',', '.'))
                        dados.append({"Nome": nome_limpo, "Cat": palpite_categoria(nome_limpo), "Valor": val})
                except: continue
    return dados, periodo

# ==========================================
# 4. SEGURANÇA E LOGIN
# ==========================================
credentials = {
    "usernames": {
        "madson": {"name": "Madson", "password": "084269"},
        "joacildo": {"name": "Joacildo", "password": "canada2026"},
        "danila": {"name": "Danila", "password": "canada2026"},
        "manoel": {"name": "Manoel", "password": "canada2026"}
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_v14", "auth_key_v14", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    user_logado = st.session_state['username']
    garantir_mesa_limpa(user_logado)
    config_usuarios = carregar_configuracoes()

    st.sidebar.markdown(f"<h3 style='color:#f8fafc; font-size:16px; margin-bottom: 20px;'>Usuário: {st.session_state['name']}</h3>", unsafe_allow_html=True)
    
    opcoes_menu = ["Painel Individual", "Gerar Multiplos Relatorios"]
    if user_logado == 'madson':
        opcoes_menu.extend(["Historico de Atividades", "Central de Acoes"])
    
    pagina = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    if user_logado != "madson":
        cota_atual = config_usuarios.get(user_logado, {}).get("quota", 0)
        validade = config_usuarios.get(user_logado, {}).get("trial_end", "N/A")
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Uploads Restantes: <b style='color:#38bdf8;'>{cota_atual}</b></p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Validade Trial: <b style='color:#38bdf8;'>{validade}</b></p>", unsafe_allow_html=True)

    authenticator.logout("Encerrar Sessao", "sidebar")

    if pagina == "Painel Individual":
        st.markdown("<h2 style='color:white; font-size:22px; margin-bottom: 30px;'>Análise Individual</h2>", unsafe_allow_html=True)
        pode_acessar, msg_erro = verificar_acesso(user_logado, config_usuarios, is_batch=False)
        
        if not pode_acessar:
            st.error(msg_erro)
        else:
            if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None

            if st.session_state.arquivo_carregado is None:
                st.markdown("<p style='color:#94a3b8; font-size:14px; text-align:center; margin-top:20px;'>Selecione um Novo Relatório para iniciar o processamento.</p>", unsafe_allow_html=True)
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

                c1, c2, c3 = st.columns([1, 2, 2])
                with c1:
                    if st.button("Remover Relatório"):
                        st.session_state.arquivo_carregado = None
                        st.rerun()
                with c2:
                    html_rel = gerar_html_interativo(df, per, total_bruto)
                    st.download_button(label="Salvar Relatorio", data=html_rel, file_name=f"BI_CANADA_{per.replace('/','-')}.html", mime="text/html")
                with c3:
                    st.download_button(label="Baixar PDF Original", data=file, file_name=file.name, mime="application/pdf")

                st.markdown(f"<p style='color:#94a3b8; font-size:13px; margin-top:20px;'>Período Analisado: <b style='color:white;'>{per}</b></p>", unsafe_allow_html=True)
                
                cats = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
                cols = st.columns(len(cats))
                selecionadas = []
                for i, c in enumerate(cats):
                    with cols[i]:
                        if st.checkbox(c, value=True, key=f"s_{c}"): selecionadas.append(c)
                        v = df[df['Cat'] == c]['Valor'].sum()
                        st.markdown(f'<div class="cat-card"><div style="color:#94a3b8; font-size:11px; font-weight:600; letter-spacing:0.5px; text-transform:uppercase;">{c}</div><div style="color:#38bdf8; font-size:16px; font-weight:bold; margin-top:5px;">{formatar_moeda(v)}</div></div>', unsafe_allow_html=True)
                
                soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum()
                st.markdown(f'<div class="floating-sum">TOTAL SELECIONADO<br>{formatar_moeda(soma_f)}</div>', unsafe_allow_html=True)

    elif pagina == "Gerar Multiplos Relatorios":
        st.markdown("<h2 style='color:white; font-size:22px;'>Processamento em Lote</h2>", unsafe_allow_html=True)
        pode_acessar, msg_erro = verificar_acesso(user_logado, config_usuarios, is_batch=True)
        if not pode_acessar: st.error(msg_erro)
        else:
            st.markdown("<p style='color:#94a3b8; font-size:14px; text-align:center;'>Selecione múltiplos relatórios para processamento simultâneo.</p>", unsafe_allow_html=True)
            batch_files = st.file_uploader("Selecionar Novos Relatórios", type="pdf", accept_multiple_files=True)
            if batch_files:
                for f in batch_files[:7]:
                    try:
                        dados, per = processar_pdf(f)
                        registrar_log(st.session_state['name'], f.name, per)
                        consumir_cota(user_logado, config_usuarios)
                    except: continue
                st.success("Arquivos processados e registrados.")

    elif pagina == "Historico de Atividades":
        st.markdown("<h2 style='color:white; font-size:22px;'>Histórico de Registros</h2>", unsafe_allow_html=True)
        if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE, sep=';').sort_index(ascending=False), use_container_width=True)

    elif pagina == "Central de Acoes":
        st.markdown("<h2 style='color:white; font-size:22px;'>Central de Gerenciamento</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8; font-size:13px;'>Gerencie acessos e cotas dos usuários corporativos.</p>", unsafe_allow_html=True)
        usuarios_comuns = [u for u in config_usuarios.keys() if u != "madson"]
        usr_selecionado = st.selectbox("Selecione o Usuário", usuarios_comuns)
        if usr_selecionado:
            dados_usr = config_usuarios[usr_selecionado]
            with st.form("form_admin"):
                st.markdown(f"<h4 style='color:#38bdf8;'>Permissões: {usr_selecionado.capitalize()}</h4>", unsafe_allow_html=True)
                novo_batch = st.checkbox("Habilitar 'Gerar Múltiplos Relatórios'", value=dados_usr["batch_allowed"])
                nova_cota = st.number_input("Cota Restante de Uploads", min_value=0, value=dados_usr["quota"], step=1)
                data_atual = datetime.strptime(dados_usr["trial_end"], "%Y-%m-%d").date()
                nova_data = st.date_input("Data de Expiração (Trial)", value=data_atual)
                if st.form_submit_button("Salvar Modificações"):
                    config_usuarios[usr_selecionado]["batch_allowed"] = novo_batch
                    config_usuarios[usr_selecionado]["quota"] = nova_cota
                    config_usuarios[usr_selecionado]["trial_end"] = nova_data.strftime("%Y-%m-%d")
                    salvar_configuracoes(config_usuarios)
                    st.success("Configurações atualizadas com sucesso.")

elif st.session_state.get("authentication_status") is False:
    st.error("Credenciais inválidas.")
elif st.session_state.get("authentication_status") is None:
    st.info("Insira suas credenciais para acessar o painel corporativo.")
