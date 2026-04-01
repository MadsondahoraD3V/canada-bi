import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
from datetime import datetime
import os

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
# 2. FUNÇÕES CORE E EXPORTAÇÃO
# ==========================================
LOG_FILE = "log_atividades.csv"

def registrar_log(usuario, arquivo, periodo):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    novo_log = pd.DataFrame([{"Data/Hora": agora, "Usuário": usuario, "Arquivo": arquivo, "Período": periodo}])
    if not os.path.isfile(LOG_FILE):
        novo_log.to_csv(LOG_FILE, index=False, sep=';', encoding='utf-8-sig')
    else:
        novo_log.to_csv(LOG_FILE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')
    
    # NOTA BONITINHA (POP-UP)
    st.toast('✅ Registro de relatório salvo', icon='📄')

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def gerar_html_bonitao(dados_df, periodo, total_geral):
    itens_html = ""
    for _, row in dados_df.iterrows():
        itens_html += f"""
        <div style="background:#1e293b; padding:10px; border-radius:8px; margin-bottom:5px; border-left:4px solid #38bdf8;">
            <span style="color:#94a3b8; font-size:12px;">{row['Cat']}</span><br>
            <b style="color:white;">{row['Nome']}</b><br>
            <span style="color:#10b981; font-weight:bold;">{formatar_moeda(row['Valor'])}</span>
        </div>"""

    return f"""
    <div style="background-color:#020617; color:white; font-family:sans-serif; padding:30px;">
        <h1 style="color:#38bdf8; border-bottom:1px solid #334155;">Dashboards Canadá BI</h1>
        <p>Período das Vendas: <b>{periodo}</b></p>
        <h2 style="color:#10b981;">TOTAL DO PERÍODO: {formatar_moeda(total_geral)}</h2>
        <hr style="border:0; border-top:1px solid #334155;">
        <h3>Detalhamento de Itens:</h3>
        {itens_html}
        <p style="margin-top:40px; color:#475569; font-size:12px;">Gerado por @Madson_da_hora</p>
    </div>
    """

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
# 3. SEGURANÇA E NAVEGAÇÃO
# ==========================================
credentials = {
    "usernames": {
        "madson": {"name": "Madson", "password": "084269"},
        "joacildo": {"name": "Joacildo", "password": "canada2026"},
        "danila": {"name": "Danila", "password": "canada2026"},
        "manoel": {"name": "Manoel", "password": "canada2026"}
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_cookie_v7", "secret_key_v7", expiry_days=30)
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    st.sidebar.title(f"👤 {st.session_state['name']}")
    
    opcoes_menu = ["📊 Painel Individual", "🚀 Upload em Lote"]
    if st.session_state['username'] == 'madson':
        opcoes_menu.append("📜 Histórico")
    
    pagina = st.sidebar.radio("Navegação", opcoes_menu)
    authenticator.logout("Sair", "sidebar")

    # --- PÁGINA 1 ---
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
                html_rel = gerar_html_bonitao(df, per, total_bruto)
                st.download_button(label="🌐 Baixar Relatório HTML", data=html_rel, file_name=f"RELATORIO DE {per.replace('/', '-')}.html", mime="text/html")
            with c3:
                st.download_button(label="📥 Baixar PDF Original", data=file, file_name=file.name, mime="application/pdf")

            # Dashboard Cards e Soma Flutuante...
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

    # --- PÁGINA 2 ---
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

    # --- PÁGINA 3 ---
    elif pagina == "📜 Histórico":
        st.title("📜 Histórico de Auditoria")
        if os.path.exists(LOG_FILE):
            df_logs = pd.read_csv(LOG_FILE, sep=';')
            st.dataframe(df_logs.sort_index(ascending=False), use_container_width=True)

    st.markdown('<div class="footer">Canadá BI v7.5 | Madson da Hora Analyst</div>', unsafe_allow_html=True)

elif st.session_state.get("authentication_status") is False:
    st.error("Login ou Senha incorretos.")
