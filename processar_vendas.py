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

# Injeção de CSS para o tema Dark e animações Hoover
st.markdown("""
    <style>
    /* Fundo principal e remoção de margens */
    .stApp { background-color: #020617; }
    .block-container { padding-top: 1rem; }

    /* Estilização dos Cards de Categoria (Efeito Glassmorphism) */
    .cat-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease; /* Transição suave */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Efeito Hoover: O card sobe e brilha ao passar o mouse */
    .cat-card:hover {
        transform: translateY(-8px);
        border-color: #38bdf8;
        box-shadow: 0 10px 20px rgba(56, 189, 248, 0.1);
        background: rgba(15, 23, 42, 0.9);
    }

    .cat-title { color: #94a3b8; font-size: 13px; letter-spacing: 1px; font-weight: 600; margin-bottom: 8px; }
    .cat-value { color: #10b981; font-size: 24px; font-weight: 900; text-shadow: 0 0 10px rgba(16, 185, 129, 0.2); }

    /* Estilo do Rodapé */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: rgba(0,0,0,0.8); color: #475569; text-align: center;
        padding: 8px; font-size: 12px; border-top: 1px solid #1e293b; backdrop-filter: blur(5px);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE INTELIGÊNCIA (REGEX E CATEGORIAS)
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
# 3. SEGURANÇA E ACESSO
# ==========================================
credentials = {"usernames": {"madson": {"name": "Madson da Hora", "password": "admin123"}}}
authenticator = stauth.Authenticate(credentials, "canada_bi_cookie", "auth_key_2026", expiry_days=30)
authenticator.login()

if st.session_state["authentication_status"]:
    with st.sidebar:
        st.markdown("### 👤 Usuário Ativo")
        st.info(st.session_state['name'])
        authenticator.logout("Encerrar Sessão", "sidebar")
    
    st.title("🇨🇦 CANADA BI | Corporate Intelligence")
    
    # Upload Minimalista
    uploaded_file = st.file_uploader("Upload PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file:
        dados_agrupados = {}
        periodo = "Identificando..."
        
        with pdfplumber.open(uploaded_file) as pdf:
            primeira_pag = pdf.pages[0].extract_text()
            match_d = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', primeira_pag or "")
            if match_d: periodo = f"{match_d.group(1)} a {match_d.group(2)}"

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
                            qtde = Decimal(valores[0].replace(',', '.'))
                            valor_total = Decimal(valores[-4].replace(',', '.'))
                            cat = palpite_categoria(nome_final)
                            if ean in dados_agrupados:
                                dados_agrupados[ean]['Qtde'] += qtde
                                dados_agrupados[ean]['Valor'] += valor_total
                            else:
                                dados_agrupados[ean] = {"Nome": nome_final, "Cat": cat, "Qtde": qtde, "Valor": valor_total}
                    except: continue

        df = pd.DataFrame(list(dados_agrupados.values()))
        df['Valor'] = df['Valor'].apply(float)

        st.markdown(f"📊 **Análise Consolidada:** {periodo}")

        # --- GRÁFICOS CORPORATIVOS ---
        col_g1, col_g2 = st.columns([1.3, 1])
        
        with col_g1:
            top10 = df.nlargest(10, 'Valor')
            fig_bar = px.bar(top10, x="Valor", y="Nome", orientation='h', 
                             title="TOP 10 PRODUTOS",
                             color_discrete_sequence=['#0ea5e9'])
            fig_bar.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            resumo_cat = df.groupby('Cat')['Valor'].sum().reset_index()
            fig_pie = px.pie(resumo_cat, values='Valor', names='Cat', hole=0.5,
                             title="DISTRIBUIÇÃO POR GRUPO")
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- KANBAN COM ANIMAÇÃO HOOVER ---
        st.write("### 📂 Categorias")
        cats = ["Tabacaria", "Bebidas", "Bomboniere", "Remédios", "Mercearia"]
        colunas = st.columns(len(cats))
        
        for i, c_nome in enumerate(cats):
            with colunas[i]:
                valor_cat = df[df['Cat'] == c_nome]['Valor'].sum()
                st.markdown(f"""
                    <div class="cat-card">
                        <div class="cat-title">{c_nome}</div>
                        <div class="cat-value">{formatar_moeda(valor_cat)}</div>
                    </div>
                """, unsafe_allow_html=True)
                with st.expander("Expandir Detalhes"):
                    itens_cat = df[df['Cat'] == c_nome]
                    for _, row in itens_cat.iterrows():
                        st.caption(f"{row['Nome']} | {formatar_moeda(row['Valor'])}")

        # --- TOTAL IMPACTANTE ---
        st.divider()
        total_final = df['Valor'].sum()
        st.markdown(f"""
            <div style="background: linear-gradient(90deg, #020617, #0ea5e9); padding: 20px; border-radius: 15px; text-align: center;">
                <h3 style="margin:0; color: #94a3b8; font-size: 16px;">VALOR TOTAL DO PERÍODO</h3>
                <h1 style="margin:0; color: white; font-size: 48px;">{formatar_moeda(total_final)}</h1>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="footer">Dashboard Executive v2.0 | Madson da Hora Analyst</div>', unsafe_allow_html=True)
