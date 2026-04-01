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
# 1. CONFIGURAÇÕES VISUAIS E CSS (CORPORATIVO)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* Fundo Escuro Corporativo */
    .stApp, .stApp > header { background-color: #0f172a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b !important; }
    
    /* Textos dos formulários legíveis */
    .stTextInput label p, .stPasswordInput label p { color: #f8fafc !important; font-weight: 600 !important; }
    
    /* Upload limpo e arredondado */
    [data-testid="stFileUploadDropzone"] { background-color: #1e293b !important; }
    [data-testid="stFileUploader"] {
        background-color: #1e293b !important; border-radius: 12px; padding: 15px;
        border: 1px dashed #334155 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
    small { display: none !important; }
    
    /* Menu Lateral Futurista */
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 6px;
        padding: 10px; margin-bottom: 8px; text-align: center; cursor: pointer;
        transition: all 0.3s ease; color: #cbd5e1 !important; font-weight: bold; width: 100%;
        position: relative;
    }
    div[role="radiogroup"] > label:hover { background: #0f172a !important; border-color: #0ea5e9 !important; color: #0ea5e9 !important; transform: translateX(5px); }
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    /* BOTÕES MENORES E DISCRETOS */
    .stButton > button, .stDownloadButton > button {
        padding: 2px 10px !important; font-size: 12px !important; min-height: 30px !important; border-radius: 6px !important;
    }

    /* COMPACTAÇÃO DA COLUNA DE CATEGORIAS */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stHorizontalBlock"] {
        gap: 0.1rem !important; align-items: center !important; margin-bottom: -15px !important;
    }
    .botao-categoria button {
        background-color: transparent !important; border: 1px solid #334155 !important; color: #cbd5e1 !important;
        justify-content: flex-start !important; padding: 2px 8px !important; font-weight: normal !important;
        font-size: 11px !important; box-shadow: none !important; border-radius: 4px !important; min-height: 22px !important;
    }
    .botao-categoria button:hover { border-color: #0ea5e9 !important; color: #0ea5e9 !important; background-color: rgba(14, 165, 233, 0.1) !important; }

    /* Scrollbar minimalista */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }

    /* Assinatura global invencível e à esquerda */
    .assinatura-master {
        position: fixed; bottom: 15px; left: 15px; background: rgba(15, 23, 42, 0.95); color: #94a3b8;
        padding: 8px 15px; border-radius: 20px; font-size: 10px; border: 1px solid #334155; 
        z-index: 999999; backdrop-filter: blur(5px); pointer-events: none; white-space: nowrap;
    }

    footer {visibility: hidden;}
    </style>
    
    <div class="assinatura-master">
        Desenvolvido por <span style="color: #38bdf8; font-weight: bold;">@madson_da_hora</span> / Analista e Programador
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. SISTEMA DE GERENCIAMENTO (JSON) E MIGRAÇÃO
# ==========================================
CONFIG_FILE = "usuarios_config.json"
LOG_FILE = "log_atividades.csv"

# Molde padrão de configurações com todas as chaves exigidas
DEFAULT_CONFIG = {
    "madson": {"name": "Madson", "password": "084269", "batch_allowed": True, "quota": 999, "trial_end": "2099-12-31"},
    "joacildo": {"name": "Joacildo", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "danila": {"name": "Danila", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"},
    "manoel": {"name": "Manoel", "password": "canada2026", "batch_allowed": False, "quota": 10, "trial_end": "2026-12-31"}
}

def salvar_configuracoes(config_data):
    """Salva os dados no arquivo JSON."""
    with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f)

def carregar_configuracoes():
    """Lê as configurações e repara dados ausentes (Migração)."""
    # 1. Se o arquivo não existe, cria um novo a partir do molde.
    if not os.path.exists(CONFIG_FILE):
        salvar_configuracoes(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    # 2. Se o arquivo existe, lê os dados.
    with open(CONFIG_FILE, 'r') as f:
        dados_salvos = json.load(f)
        
    # 3. MIGRACÃO AUTOMÁTICA: Compara os dados salvos com o molde padrão.
    # Isso resolve o KeyError se o arquivo velho não tiver as senhas (password e name).
    precisa_atualizar = False
    for usuario, config_padrao in DEFAULT_CONFIG.items():
        # Se um novo usuário foi adicionado ao molde, adicionamos ao arquivo
        if usuario not in dados_salvos:
            dados_salvos[usuario] = config_padrao
            precisa_atualizar = True
        else:
            # Se faltar chaves (como 'password' ou 'name') num usuário existente, nós as injetamos
            for chave, valor in config_padrao.items():
                if chave not in dados_salvos[usuario]:
                    dados_salvos[usuario][chave] = valor
                    precisa_atualizar = True
                    
    # Salva o arquivo corrigido se houve alguma injeção de dados
    if precisa_atualizar:
        salvar_configuracoes(dados_salvos)
        
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
# 3. FUNÇÕES CORE E GERADOR DE HTML
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
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): return "Remédios"
    return "Mercearia"

def gerar_html_interativo(df, periodo, total_geral):
    cores = { "Tabacaria": {"bg": "#334155", "glow": "rgba(51, 65, 85, 0.2)"}, "Bebidas": {"bg": "#1e3a8a", "glow": "rgba(30, 58, 138, 0.2)"}, "Bomboniere": {"bg": "#0f766e", "glow": "rgba(15, 118, 110, 0.2)"}, "Remédios": {"bg": "#9a3412", "glow": "rgba(154, 52, 18, 0.2)"}, "Mercearia": {"bg": "#0369a1", "glow": "rgba(3, 105, 161, 0.2)"} }
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

# ==========================================
# 4. SEGURANÇA E LOGIN DINÂMICO
# ==========================================
# Carrega os dados migrados com segurança
config_usuarios = carregar_configuracoes()

credentials_dict = {"usernames": {}}
for u, data in config_usuarios.items():
    # Isso impede o KeyError, pois carregar_configuracoes agora garante que essas chaves existem!
    credentials_dict["usernames"][u] = {"name": data["name"], "password": data["password"]}

authenticator = stauth.Authenticate(credentials_dict, "canada_bi_v19", "auth_key_v19", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    user_logado = st.session_state['username']
    garantir_mesa_limpa(user_logado)

    if 'cat_expandida' not in st.session_state:
        st.session_state.cat_expandida = None

    st.sidebar.markdown(f"<h3 style='color:#f8fafc; font-size:16px; margin-bottom: 20px;'>Usuário: {st.session_state['name']}</h3>", unsafe_allow_html=True)
    
    # Efeito Visual de Paywall nos menus restritos
    if user_logado != 'madson':
        st.markdown("""
        <style>
        div[role="radiogroup"] > label:nth-child(3):hover::after,
        div[role="radiogroup"] > label:nth-child(4):hover::after {
            content: "Sem permissão para essa função, requer mudança de plano.";
            position: absolute; left: 102%; top: 5px; background: #ef4444; color: white;
            padding: 5px 10px; border-radius: 4px; font-size: 11px; white-space: nowrap; z-index: 99999;
        }
        </style>
        """, unsafe_allow_html=True)

    opcoes_menu = ["Análise de Relatório", "Gerar Multiplos Relatorios", "Historico de Atividades", "Central de Permissões"]
    pagina = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    if user_logado != "madson":
        cota_atual = config_usuarios.get(user_logado, {}).get("quota", 0)
        validade = config_usuarios.get(user_logado, {}).get("trial_end", "N/A")
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Uploads Restantes: <b style='color:#0ea5e9;'>{cota_atual}</b></p>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p style='color:#94a3b8; font-size:12px;'>Validade Trial: <b style='color:#0ea5e9;'>{validade}</b></p>", unsafe_allow_html=True)

    authenticator.logout("Encerrar Sessao", "sidebar")

    # --- PÁGINAS DO SISTEMA ---
    if pagina == "Análise de Relatório":
        st.markdown("<h2 style='color:white; font-size:22px; margin-bottom: 5px;'>Análise de Relatório</h2>", unsafe_allow_html=True)
        trial_end = datetime.strptime(config_usuarios[user_logado]["trial_end"], "%Y-%m-%d").date()
        
        if date.today() > trial_end or config_usuarios[user_logado]["quota"] <= 0 and user_logado != "madson":
            st.error("Acesso Expirado ou Sem Cotas. Contate o Administrador.")
        else:
            if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None

            if st.session_state.arquivo_carregado is None:
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

                col_botoes, col_vazia = st.columns([2, 8])
                with col_botoes:
                    html_rel = gerar_html_interativo(df, per, total_bruto)
                    st.download_button(label="📥 Salvar Relatório HTML", data=html_rel, file_name=f"BI_CANADA_{per.replace('/','-')}.html", mime="text/html", use_container_width=True)
                    if st.button("🗑️ Remover Relatório", use_container_width=True):
                        st.session_state.arquivo_carregado = None
                        st.session_state.cat_expandida = None
                        st.rerun()

                st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin-top:10px; border-bottom: 1px solid #1e293b; padding-bottom:10px;'>Período Analisado: <b style='color:white;'>{per}</b></p>", unsafe_allow_html=True)
                
                col_filtros, col_total, col_detalhes = st.columns([3, 3, 4], gap="large")
                selecionadas = []
                categorias = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
                
                with col_filtros:
                    st.markdown("<h4 style='color:#94a3b8; font-size:12px; margin-bottom:10px; text-transform:uppercase;'>Categorias</h4>", unsafe_allow_html=True)
                    for cat in categorias:
                        v = df[df['Cat'] == cat]['Valor'].sum()
                        c_chk, c_btn, c_val = st.columns([1, 5, 3])
                        with c_chk:
                            if st.checkbox("", value=True, key=f"chk_{cat}"): selecionadas.append(cat)
                        with c_btn:
                            st.markdown('<div class="botao-categoria">', unsafe_allow_html=True)
                            if st.button(cat.upper(), key=f"btn_{cat}", use_container_width=True): st.session_state.cat_expandida = cat
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c_val:
                            st.markdown(f"<div style='padding-top:2px; color:#0ea5e9; font-weight:bold; font-size:12px;'>{formatar_moeda(v)}</div>", unsafe_allow_html=True)

                with col_total:
                    st.markdown("<h4 style='color:#94a3b8; font-size:12px; margin-bottom:10px; text-transform:uppercase;'>Resumo Financeiro</h4>", unsafe_allow_html=True)
                    soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum()
                    st.markdown(f'''
                    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #3b82f6;">
                        <p style="margin:0; color:#cbd5e1; font-size:11px; font-weight:bold; letter-spacing:1px;">CAIXA TOTAL BRUTO</p>
                        <h1 style="margin:5px 0 0 0; color:white; font-size:24px; font-weight:900;">{formatar_moeda(soma_f)}</h1>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_detalhes:
                    st.markdown("<h4 style='color:#94a3b8; font-size:12px; margin-bottom:10px; text-transform:uppercase;'>Detalhamento (Miniatura)</h4>", unsafe_allow_html=True)
                    if st.session_state.cat_expandida:
                        cat_atual = st.session_state.cat_expandida
                        itens = df[df['Cat'] == cat_atual]
                        html_itens = f"<div style='background:#1e293b; padding:10px; border-radius:6px; border-left:2px solid #0ea5e9; border-top:1px solid #334155; border-right:1px solid #334155; border-bottom:1px solid #334155;'>"
                        html_itens += f"<h5 style='color:white; margin:0 0 8px 0; font-size:11px; letter-spacing:1px;'>{cat_atual.upper()}</h5>"
                        html_itens += "<div style='max-height: 250px; overflow-y: auto; padding-right:5px;'>"
                        for _, row in itens.iterrows():
                            html_itens += f"<div style='display:flex; justify-content:space-between; border-bottom:1px solid #334155; padding:4px 0;'><span style='color:#cbd5e1; font-size:10px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;'>{row['Nome']}</span><span style='color:#0ea5e9; font-size:10px; font-weight:bold;'>R$ {row['Valor']:,.2f}</span></div>"
                        html_itens += "</div></div>"
                        st.markdown(html_itens, unsafe_allow_html=True)
                    else:
                        st.markdown("""<div style="background:#1e293b; padding:15px; border-radius:6px; text-align:center; border: 1px dashed #334155;"><p style="color:#94a3b8; font-size:11px; margin:0;">👈 Clique na categoria para inspecionar</p></div>""", unsafe_allow_html=True)

    elif pagina == "Gerar Multiplos Relatorios":
        if not config_usuarios[user_logado]["batch_allowed"] and user_logado != "madson":
            st.toast("🔒 Sem permissão para essa função, requer mudança de plano.")
            st.warning("Acesso Restrito: Sua assinatura não contempla múltiplas gerações.")
        else:
            st.markdown("<h2 style='color:white; font-size:22px;'>Processamento em Lote</h2>", unsafe_allow_html=True)
            batch_files = st.file_uploader("Selecionar Novos Relatórios", type="pdf", accept_multiple_files=True)
            if batch_files:
                for f in batch_files[:7]:
                    try:
                        dados, per = processar_pdf(f)
                        registrar_log(st.session_state['name'], f.name, per)
                        consumir_cota(user_logado, config_usuarios)
                    except: continue
                st.success("Arquivos processados.")

    elif pagina == "Historico de Atividades":
        if user_logado != "madson":
            st.toast("🔒 Sem permissão para essa função, requer mudança de plano.")
            st.warning("Acesso Restrito ao Administrador.")
        else:
            st.markdown("<h2 style='color:white; font-size:22px;'>Histórico de Registros</h2>", unsafe_allow_html=True)
            if os.path.exists(LOG_FILE): st.dataframe(pd.read_csv(LOG_FILE, sep=';').sort_index(ascending=False), use_container_width=True)

    elif pagina == "Central de Permissões":
        if user_logado != "madson":
            st.toast("🔒 Sem permissão para essa função, requer mudança de plano.")
            st.warning("Acesso Restrito ao Administrador.")
        else:
            st.markdown("<h2 style='color:white; font-size:22px;'>Central de Permissões</h2>", unsafe_allow_html=True)
            usuarios_comuns = [u for u in config_usuarios.keys() if u != "madson"]
            usr_selecionado = st.selectbox("Selecione o Usuário para Editar", usuarios_comuns)
            
            if usr_selecionado:
                dados_usr = config_usuarios[usr_selecionado]
                with st.form("form_admin"):
                    st.markdown(f"<h4 style='color:#38bdf8; font-size:16px;'>Editando: {usr_selecionado.capitalize()}</h4>", unsafe_allow_html=True)
                    nova_senha = st.text_input("Senha de Acesso do Usuário", value=dados_usr["password"])
                    novo_batch = st.checkbox("Habilitar 'Gerar Múltiplos Relatórios'", value=dados_usr["batch_allowed"])
                    nova_cota = st.number_input("Cota Restante de Uploads", min_value=0, value=dados_usr["quota"], step=1)
                    data_atual = datetime.strptime(dados_usr["trial_end"], "%Y-%m-%d").date()
                    nova_data = st.date_input("Data de Expiração (Trial)", value=data_atual)
                    
                    if st.form_submit_button("Salvar Modificações"):
                        config_usuarios[usr_selecionado]["password"] = nova_senha
                        config_usuarios[usr_selecionado]["batch_allowed"] = novo_batch
                        config_usuarios[usr_selecionado]["quota"] = nova_cota
                        config_usuarios[usr_selecionado]["trial_end"] = nova_data.strftime("%Y-%m-%d")
                        salvar_configuracoes(config_usuarios)
                        st.success("Permissões e Senha atualizadas! A nova senha já está valendo.")

elif st.session_state.get("authentication_status") is False:
    st.error("Credenciais inválidas.")
elif st.session_state.get("authentication_status") is None:
    st.info("Insira suas credenciais para acessar o painel corporativo.")
