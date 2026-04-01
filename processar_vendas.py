import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
from datetime import datetime
import os
import json
import plotly.express as px

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS
# ==========================================
st.set_page_config(page_title="Canadá BI - Admin Edition", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #020617; }
    .floating-sum {
        position: fixed; top: 70px; right: 30px;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white; padding: 20px; border-radius: 15px; z-index: 1000;
        font-weight: 900; font-size: 22px; box-shadow: 0 10px 25px rgba(16,185,129,0.4);
        text-align: center; border: 1px solid rgba(255,255,255,0.2);
    }
    .cat-card {
        background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px; padding: 15px; text-align: center; margin-top: 10px;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: rgba(0,0,0,0.9); color: #475569; text-align: center;
        padding: 8px; font-size: 11px; border-top: 1px solid #1e293b;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES CORE E GERADOR DE HTML
# ==========================================
LOG_FILE = "log_atividades.csv"

def registrar_log(usuario, arquivo, periodo):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    novo_log = pd.DataFrame([{"Data/Hora": agora, "Usuário": usuario, "Arquivo": arquivo, "Período": periodo}])
    if not os.path.isfile(LOG_FILE):
        novo_log.to_csv(LOG_FILE, index=False, sep=';', encoding='utf-8-sig')
    else:
        novo_log.to_csv(LOG_FILE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
    st.toast('✅ Registro de relatório salvo', icon='📄')

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) 
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome) 
    return nome.replace('.', '').replace('-', '').strip()[:25]

def palpite_categoria(nome):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn').upper()
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): return "Remédios"
    return "Mercearia"

def gerar_html_interativo(df, periodo, total_geral):
    """Gera o HTML com CSS futurista e JavaScript para recálculo offline."""
    resumo_cat = df.groupby('Cat')['Valor'].sum().to_dict()
    categorias_html = ""
    cores = {"Tabacaria": "#ea580c", "Bebidas": "#2563eb", "Bomboniere": "#db2777", "Remédios": "#059669", "Mercearia": "#475569"}
    
    for i, (cat, cor) in enumerate(cores.items()):
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div style="background:#1e293b;padding:10px;border-radius:5px;border-left:3px solid #38bdf8;margin:5px;">{row["Nome"]}<br><b style="color:#10b981;">R$ {row["Valor"]:,.2f}</b></div>' for _, row in itens_cat.iterrows()])

        categorias_html += f"""
        <div style="margin-bottom:10px; border-radius:8px; overflow:hidden; border:1px solid #334155;">
            <div style="background:{cor}; padding:15px; display:flex; align-items:center; justify-content:space-between;">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onchange="recalcular()" style="width:20px;height:20px;margin-right:15px;">
                    <b style="color:white; font-size:16px;">{cat.upper()}</b>
                </div>
                <span style="color:white; font-weight:bold;">R$ {valor_cat:,.2f}</span>
            </div>
            <div style="background:#000; padding:10px; display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:5px;">
                {cards_html}
            </div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Canadá BI - Relatório</title>
        <style>
            body {{ background:#020617; color:white; font-family:sans-serif; padding:20px; }}
            .total-box {{ background:linear-gradient(90deg, #020617, #10b981); padding:20px; border-radius:15px; text-align:center; margin-bottom:30px; }}
        </style>
    </head>
    <body>
        <div class="total-box">
            <h3 style="margin:0;opacity:0.8;">CAIXA TOTAL SELECIONADO</h3>
            <h1 id="display-total" style="margin:0;font-size:48px;">R$ {total_geral:,.2f}</h1>
            <p>Período: {periodo}</p>
        </div>
        {categorias_html}
        <script>
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
# 3. SEGURANÇA E LOGIN
# ==========================================
credentials = {
    "usernames": {
        "madson": {"name": "Madson", "password": "084269"},
        "joacildo": {"name": "Joacildo", "password": "canada2026"},
        "danila": {"name": "Danila", "password": "canada2026"},
        "manoel": {"name": "Manoel", "password": "canada2026"}
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_cookie_v8", "secret_key_v8", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    st.sidebar.title(f"👤 {st.session_state['name']}")
    
    opcoes_menu = ["📊 Painel Individual", "🚀 Upload em Lote"]
    if st.session_state['username'] == 'madson':
        opcoes_menu.append("📜 Histórico")
    
    pagina = st.sidebar.radio("Navegação", opcoes_menu)
    authenticator.logout("Sair", "sidebar")

    if pagina == "📊 Painel Individual":
        st.title("📊 Análise Individual")
        if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None

        if st.session_state.arquivo_carregado is None:
            file = st.file_uploader("Arraste um PDF", type="pdf", key="single")
            if file:
                st.session_state.arquivo_carregado = file
                dados, per = processar_pdf(file)
                registrar_log(st.session_state['name'], file.name, per)
                st.rerun()
        else:
            file = st.session_state.arquivo_carregado
            dados, per = processar_pdf(file)
            df = pd.DataFrame(dados)
            total_bruto = df['Valor'].sum()

            c1, c2, c3 = st.columns([1, 2, 2])
            with c1:
                if st.button("🗑️ Remover"):
                    st.session_state.arquivo_carregado = None
                    st.rerun()
            with c2:
                html_rel = gerar_html_interativo(df, per, total_bruto)
                st.download_button(label="🌐 Baixar Dashboard Inteligente", data=html_rel, file_name=f"BI_CANADA_{per.replace('/','-')}.html", mime="text/html")
            with c3:
                st.download_button(label="📥 Baixar PDF Original", data=file, file_name=file.name, mime="application/pdf")

            st.info(f"📅 Período: {per}")
            
            cats = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
            cols = st.columns(len(cats))
            selecionadas = []
            for i, c in enumerate(cats):
                with cols[i]:
                    if st.checkbox(c, value=True, key=f"s_{c}"): selecionadas.append(c)
                    v = df[df['Cat'] == c]['Valor'].sum()
                    st.markdown(f'<div class="cat-card"><div class="cat-title">{c}</div><div class="cat-value">{formatar_moeda(v)}</div></div>', unsafe_allow_html=True)
            
            soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum()
            st.markdown(f'<div class="floating-sum">SELECIONADO<br>{formatar_moeda(soma_f)}</div>', unsafe_allow_html=True)

    elif pagina == "🚀 Upload em Lote":
        st.title("🚀 Processamento em Lote")
        batch_files = st.file_uploader("Upload em Lote (Máx 7)", type="pdf", accept_multiple_files=True)
        if batch_files:
            if len(batch_files) > 7: st.error("Máximo 7.")
            else:
                for f in batch_files:
                    try:
                        dados, per = processar_pdf(f)
                        registrar_log(st.session_state['name'], f.name, per)
                    except: continue
                st.success("Arquivos processados e logs registrados!")

    elif pagina == "📜 Histórico":
        st.title("📜 Histórico de Auditoria")
        if os.path.exists(LOG_FILE):
            df_logs = pd.read_csv(LOG_FILE, sep=';')
            st.dataframe(df_logs.sort_index(ascending=False), use_container_width=True)

    st.markdown('<div class="footer">Canadá BI v8.0 | Madson da Hora Analyst</div>', unsafe_allow_html=True)

elif st.session_state.get("authentication_status") is False:
    st.error("Login ou Senha incorretos.")
elif st.session_state.get("authentication_status") is None:
    st.warning("Por favor, insira suas credenciais.")
