import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
import plotly.express as px

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS FUTURISTA
# ==========================================
st.set_page_config(page_title="Canadá BI - Executive", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #020617; }
    
    /* Painel Flutuante de Soma */
    .floating-sum {
        position: fixed;
        top: 60px;
        right: 20px;
        background: rgba(16, 185, 129, 0.9);
        color: white;
        padding: 15px 25px;
        border-radius: 12px;
        z-index: 999;
        font-weight: 900;
        font-size: 20px;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        border: 1px solid #ffffff33;
    }

    /* Cards de Categoria com Animação */
    .cat-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .cat-card:hover {
        transform: translateY(-5px);
        border-color: #38bdf8;
        background: rgba(15, 23, 42, 0.9);
    }

    .cat-title { color: #94a3b8; font-size: 13px; font-weight: 600; text-transform: uppercase; }
    .cat-value { color: #10b981; font-size: 24px; font-weight: 900; }

    /* Estilo para Checkboxes de Seleção */
    .stCheckbox { margin-bottom: -15px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES DE SUPORTE
# ==========================================
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) 
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome) 
    return nome.replace('.', '').replace('-', '').strip()[:28]

def palpite_categoria(nome):
    txt = remover_acentos(nome)
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): return "Remédios"
    return "Mercearia"

# ==========================================
# 3. SEGURANÇA - MÚLTIPLOS USUÁRIOS
# ==========================================
credentials = {
    "usernames": {
        "madson": {"name": "Madson", "password": "084269"},
        "joacildo": {"name": "Joacildo", "password": "canada2026"},
        "danila": {"name": "Danila", "password": "canada2026"},
        "manoel": {"name": "Manoel", "password": "canada2026"}
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_cookie", "auth_key_2026", expiry_days=30)
name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        authenticator.logout("Sair", "sidebar")
    
    st.title("🇨🇦 CANADA BI | Executive Intelligence")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file:
        dados_agrupados = {}
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                linhas = (page.extract_text() or "").split('\n')
                for linha in linhas:
                    try:
                        linha_limpa = linha.replace('|', ' ').strip()
                        ean_match = re.search(r'\b\d{8,14}\b', linha_limpa)
                        valores = re.findall(r'\d+,\d{2}', linha_limpa)
                        if ean_match and len(valores) >= 4:
                            ean = ean_match.group()
                            match_n = re.search(r'(.+?)\s+(?:UN|KG)\s+\d+,\d{2}', linha_limpa)
                            nome_bruto = match_n.group(1).replace(ean, '').strip() if match_n else "PRODUTO"
                            nome_final = limpar_nome_produto(nome_bruto)
                            valor_total = Decimal(valores[-4].replace(',', '.'))
                            cat = palpite_categoria(nome_final)
                            if ean in dados_agrupados:
                                dados_agrupados[ean]['Valor'] += valor_total
                            else:
                                dados_agrupados[ean] = {"Nome": nome_final, "Cat": cat, "Valor": valor_total}
                    except: continue

        df = pd.DataFrame(list(dados_agrupados.values()))
        df['Valor'] = df['Valor'].apply(float)

        # --- LÓGICA DA SOMA FLUTUANTE ---
        if 'soma_selecionada' not in st.session_state:
            st.session_state.soma_selecionada = 0.0

        # --- INTERFACE DE CATEGORIAS (KANBAN) ---
        st.write("### 📂 Selecione as Categorias para somar")
        cats = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
        colunas = st.columns(len(cats))
        
        soma_temp = 0.0
        
        for i, c_nome in enumerate(cats):
            with colunas[i]:
                valor_cat = df[df['Cat'] == c_nome]['Valor'].sum()
                
                # Checkbox para controle da soma flutuante
                selecionado = st.checkbox(f"Somar {c_nome}", value=True, key=f"check_{c_nome}")
                if selecionado:
                    soma_temp += valor_cat

                st.markdown(f"""
                    <div class="cat-card">
                        <div class="cat-title">{c_nome}</div>
                        <div class="cat-value">{formatar_moeda(valor_cat)}</div>
                    </div>
                """, unsafe_allow_html=True)

        # Exibição do Valor Flutuante (CSS fixo)
        st.markdown(f"""
            <div class="floating-sum">
                SELECIONADO: {formatar_moeda(soma_temp)}
            </div>
        """, unsafe_allow_html=True)

        # --- GRÁFICOS ---
        st.divider()
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.plotly_chart(px.bar(df.nlargest(10, 'Valor'), x="Valor", y="Nome", orientation='h', title="TOP 10", color_discrete_sequence=['#0ea5e9']).update_layout(template="plotly_dark", height=350), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df.groupby('Cat')['Valor'].sum().reset_index(), values='Valor', names='Cat', hole=0.5, title="DISTRIBUIÇÃO").update_layout(template="plotly_dark", height=350), use_container_width=True)

    st.markdown('<div class="footer">Dashboard Executive v3.0 | Madson da Hora</div>', unsafe_allow_html=True)

elif authentication_status is False:
    st.error("Login ou Senha incorretos.")
