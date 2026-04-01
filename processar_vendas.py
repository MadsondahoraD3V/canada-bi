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
    /* Fundo Escuro */
    .stApp { background-color: #020617; }
    
    /* Assinatura Flutuante */
    .assinatura-flutuante {
        position: fixed; bottom: 15px; right: 20px;
        background: rgba(15, 23, 42, 0.8); color: #38bdf8;
        padding: 8px 15px; border-radius: 20px; font-size: 11px; font-weight: bold;
        border: 1px solid #38bdf8; z-index: 9999; backdrop-filter: blur(5px);
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
    }

    /* Total Flutuante no Topo */
    .floating-sum {
        position: fixed; top: 70px; right: 30px;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white; padding: 15px 20px; border-radius: 12px; z-index: 1000;
        font-weight: 900; font-size: 18px; box-shadow: 0 10px 25px rgba(16,185,129,0.4);
        text-align: center; border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Cards de Categoria */
    .cat-card {
        background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 10px; padding: 10px; text-align: center; margin-top: 5px;
    }

    /* MENU LATERAL FUTURISTA (Escondendo as bolinhas do Radio) */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
        padding: 12px; margin-bottom: 8px; text-align: center; cursor: pointer;
        transition: all 0.3s ease; color: #94a3b8; font-weight: bold; width: 100%;
    }
    div[role="radiogroup"] > label:hover { 
        background: #1e293b; border-color: #38bdf8; color: #38bdf8; transform: translateX(5px);
    }
    /* Estilo para a opção selecionada */
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    /* Esconder footer padrão do Streamlit */
    footer {visibility: hidden;}
    </style>
    
    <!-- Injetando a Assinatura Flutuante no HTML do Streamlit -->
    <div class="assinatura-flutuante">Desenvolvido por @madson_da_hora / Analista de dados e Programador</div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE GERENCIAMENTO DE USUÁRIOS (JSON)
# ==========================================
CONFIG_FILE = "usuarios_config.json"
LOG_FILE = "log_atividades.csv"

# Configuração padrão caso o arquivo não exista
DEFAULT_CONFIG = {
    "joacildo": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "danila": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "manoel": {"batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"}
}

def carregar_configuracoes():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def salvar_configuracoes(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)

def verificar_acesso(username, config_data, is_batch=False):
    """Verifica se o usuário pode fazer a ação."""
    if username == "madson": return True, "" # Admin tem passe livre
    
    user_data = config_data.get(username)
    if not user_data: return False, "Usuário não configurado no sistema."
    
    # Verifica Data
    trial_end = datetime.strptime(user_data["trial_end"], "%Y-%m-%d").date()
    if date.today() > trial_end:
        return False, "Seu período de teste expirou. Contate o Administrador."
    
    # Verifica Cota
    if user_data["quota"] <= 0:
        return False, "Sua cota de uploads acabou. Contate o Administrador."
        
    # Verifica permissão de Lote
    if is_batch and not user_data["batch_allowed"]:
        return False, "Você não tem permissão para Gerar Múltiplos Relatórios."
        
    return True, ""

def consumir_cota(username, config_data):
    if username != "madson" and username in config_data:
        config_data[username]["quota"] -= 1
        salvar_configuracoes(config_data)

# ==========================================
# 3. FUNÇÕES CORE E GERADOR DE HTML COMPACTO
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
    """Gera o HTML Compacto 'Cyber' com colunas lado a lado e assinatura flutuante."""
    cores = {
        "Tabacaria": {"bg": "#ea580c", "glow": "rgba(234, 88, 12, 0.4)"},
        "Bebidas": {"bg": "#2563eb", "glow": "rgba(37, 99, 235, 0.4)"},
        "Bomboniere": {"bg": "#db2777", "glow": "rgba(219, 39, 119, 0.4)"},
        "Remédios": {"bg": "#059669", "glow": "rgba(5, 150, 105, 0.4)"},
        "Mercearia": {"bg": "#475569", "glow": "rgba(71, 85, 105, 0.4)"}
    }
    colunas_html = ""
    
    for i, (cat, paleta) in enumerate(cores.items()):
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div class="cyber-card"><div class="card-title">{row["Nome"]}</div><div class="card-value">R$ {row["Valor"]:,.2f}</div></div>' for _, row in itens_cat.iterrows()])

        colunas_html += f"""
        <div class="coluna-categoria">
            <div class="accordion-header" style="background: {paleta['bg']}; box-shadow: 0 0 15px {paleta['glow']};" onclick="toggleAccordion('content-{i}')">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onclick="event.stopPropagation();" onchange="recalcular()">
                    <span class="cat-title">{cat.upper()} ▼</span>
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
        <title>Canadá BI - Relatório</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
        <style>
            :root {{ --bg-main: #020617; --bg-panel: #0f172a; --bg-card: #1e293b; --text-main: #f8fafc; --text-muted: #94a3b8; --accent: #38bdf8; --success: #10b981; }}
            body {{ background-color: var(--bg-main); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; padding-bottom: 60px; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 10px; }}
            
            .neon-bar {{ background: linear-gradient(90deg, #020617, #0f172a, #064e3b); padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 30px; border: 1px solid #10b98144; box-shadow: 0 0 30px rgba(16, 185, 129, 0.15); }}
            .neon-bar h3 {{ margin: 0; font-size: 14px; color: var(--text-muted); letter-spacing: 2px; }}
            .neon-bar h1 {{ margin: 5px 0; font-size: 42px; font-weight: 900; color: var(--success); }}
            
            .container-cols {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; align-items: flex-start; }}
            .coluna-categoria {{ flex: 1; min-width: 220px; max-width: 300px; display: flex; flex-direction: column; }}
            
            .accordion-header {{ padding: 12px 15px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid rgba(255,255,255,0.1); position: relative; z-index: 10; }}
            .cat-check {{ width: 18px; height: 18px; cursor: pointer; margin-right: 10px; }}
            .cat-title {{ font-size: 13px; font-weight: 900; color: white; }}
            .cat-total {{ font-size: 14px; font-weight: 700; color: white; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px; }}
            
            .accordion-content {{ max-height: 0px; overflow-y: auto; transition: max-height 0.4s; background-color: var(--bg-panel); border-radius: 0 0 8px 8px; margin-top: -5px; }}
            .accordion-content.show {{ max-height: 400px; border: 1px solid #1e293b; border-top: none; }}
            .content-inner {{ padding: 15px 10px; display: flex; flex-direction: column; gap: 8px; }}
            
            .cyber-card {{ background: var(--bg-card); padding: 10px; border-radius: 6px; border-left: 3px solid var(--accent); display: flex; justify-content: space-between; align-items: center; }}
            .card-title {{ font-size: 11px; font-weight: 700; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .card-value {{ font-size: 12px; font-weight: 900; color: var(--success); }}

            /* Assinatura Flutuante no HTML gerado */
            .assinatura-html {{
                position: fixed; bottom: 10px; right: 10px;
                background: rgba(15, 23, 42, 0.9); color: #38bdf8;
                padding: 6px 12px; border-radius: 15px; font-size: 10px; font-weight: bold;
                border: 1px solid #38bdf8; z-index: 9999; box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
            }}
        </style>
    </head>
    <body>
        <div class="neon-bar">
            <h3>CAIXA TOTAL SELECIONADO</h3>
            <h1 id="display-total">R$ {total_geral:,.2f}</h1>
            <p style="color:#64748b; font-size:12px; margin:0;">Período: {periodo}</p>
        </div>
        
        <div class="container-cols">
            {colunas_html}
        </div>

        <div class="assinatura-html">Desenvolvido por @madson_da_hora / Analista de dados e Programador</div>

        <script>
            function toggleAccordion(id) {{
                document.getElementById(id).classList.toggle("show");
            }}
            function recalcular() {{
                let total = 0;
                document.querySelectorAll('.cat-check').forEach(check => {{
                    if (check.checked) total += parseFloat(check.getAttribute('data-valor'));
                }});
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

authenticator = stauth.Authenticate(credentials, "canada_bi_v11", "auth_key_v11", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    user_logado = st.session_state['username']
    config_usuarios = carregar_configuracoes()

    st.sidebar.title(f"Usuário: {st.session_state['name']}")
    
    # Montando o Menu sem emojis
    opcoes_menu = ["Painel Individual", "Gerar Multiplos Relatorios"]
    if user_logado == 'madson':
        opcoes_menu.append("Historico de Atividades")
        opcoes_menu.append("Central de Acoes")
    
    pagina = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    # Mostrar status da cota na sidebar
    if user_logado != "madson":
        cota_atual = config_usuarios.get(user_logado, {}).get("quota", 0)
        validade = config_usuarios.get(user_logado, {}).get("trial_end", "N/A")
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Uploads Restantes: <b style='color:#38bdf8;'>{cota_atual}</b></p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Validade: <b style='color:#38bdf8;'>{validade}</b></p>", unsafe_allow_html=True)

    authenticator.logout("Encerrar Sessao", "sidebar")

    # --- PÁGINA 1: PAINEL INDIVIDUAL ---
    if pagina == "Painel Individual":
        st.title("Análise Individual")
        
        pode_acessar, msg_erro = verificar_acesso(user_logado, config_usuarios, is_batch=False)
        
        if not pode_acessar:
            st.error(msg_erro)
        else:
            if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None

            if st.session_state.arquivo_carregado is None:
                file = st.file_uploader("Selecione um arquivo PDF", type="pdf", key="single")
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
                    if st.button("Remover Arquivo"):
                        st.session_state.arquivo_carregado = None
                        st.rerun()
                with c2:
                    html_rel = gerar_html_interativo(df, per, total_bruto)
                    st.download_button(label="Salvar Relatorio", data=html_rel, file_name=f"BI_CANADA_{per.replace('/','-')}.html", mime="text/html")
                with c3:
                    st.download_button(label="Baixar PDF Original", data=file, file_name=file.name, mime="application/pdf")

                st.info(f"Período: {per}")
                
                cats = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
                cols = st.columns(len(cats))
                selecionadas = []
                for i, c in enumerate(cats):
                    with cols[i]:
                        if st.checkbox(c, value=True, key=f"s_{c}"): selecionadas.append(c)
                        v = df[df['Cat'] == c]['Valor'].sum()
                        st.markdown(f'<div class="cat-card"><div style="color:#94a3b8; font-size:12px; font-weight:bold;">{c.upper()}</div><div style="color:white; font-size:16px; font-weight:bold;">{formatar_moeda(v)}</div></div>', unsafe_allow_html=True)
                
                soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum()
                st.markdown(f'<div class="floating-sum">SELECIONADO<br>{formatar_moeda(soma_f)}</div>', unsafe_allow_html=True)

    # --- PÁGINA 2: LOTE ---
    elif pagina == "Gerar Multiplos Relatorios":
        st.title("Processamento em Lote")
        
        pode_acessar, msg_erro = verificar_acesso(user_logado, config_usuarios, is_batch=True)
        
        if not pode_acessar:
            st.error(msg_erro)
        else:
            batch_files = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)
            if batch_files:
                for f in batch_files[:7]:
                    try:
                        dados, per = processar_pdf(f)
                        registrar_log(st.session_state['name'], f.name, per)
                        consumir_cota(user_logado, config_usuarios)
                    except: continue
                st.success("Arquivos processados e registrados.")

    # --- PÁGINA 3: HISTÓRICO ---
    elif pagina == "Historico de Atividades":
        st.title("Histórico de Registros")
        if os.path.exists(LOG_FILE):
            st.dataframe(pd.read_csv(LOG_FILE, sep=';').sort_index(ascending=False), use_container_width=True)

    # --- PÁGINA 4: CENTRAL DE AÇÕES (ADMIN) ---
    elif pagina == "Central de Acoes":
        st.title("Central de Gerenciamento")
        st.write("Gerencie acessos e cotas dos usuários do sistema.")
        
        usuarios_comuns = [u for u in config_usuarios.keys() if u != "madson"]
        usr_selecionado = st.selectbox("Selecione o Usuário", usuarios_comuns)
        
        if usr_selecionado:
            dados_usr = config_usuarios[usr_selecionado]
            
            with st.form("form_admin"):
                st.subheader(f"Editando: {usr_selecionado.capitalize()}")
                
                novo_batch = st.checkbox("Permitir 'Gerar Múltiplos Relatórios'?", value=dados_usr["batch_allowed"])
                nova_cota = st.number_input("Cota de Uploads Restantes", min_value=0, value=dados_usr["quota"], step=1)
                
                data_atual = datetime.strptime(dados_usr["trial_end"], "%Y-%m-%d").date()
                nova_data = st.date_input("Vencimento do Acesso (Trial)", value=data_atual)
                
                if st.form_submit_button("Salvar Alterações"):
                    config_usuarios[usr_selecionado]["batch_allowed"] = novo_batch
                    config_usuarios[usr_selecionado]["quota"] = nova_cota
                    config_usuarios[usr_selecionado]["trial_end"] = nova_data.strftime("%Y-%m-%d")
                    salvar_configuracoes(config_usuarios)
                    st.success(f"Configurações de {usr_selecionado} atualizadas com sucesso!")

elif st.session_state.get("authentication_status") is False:
    st.error("Credenciais inválidas.")
elif st.session_state.get("authentication_status") is None:
    st.info("Insira suas credenciais para acessar o painel corporativo.")
