import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS
# ==========================================
st.set_page_config(page_title="Canadá BI - Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #020617; }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #000000; color: #64748b; text-align: center;
        padding: 10px; font-size: 14px; border-top: 1px solid #1e293b; z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES DE LIMPEZA E INTELIGÊNCIA
# ==========================================
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def limpar_nome_produto(nome_bruto):
    """Isola o nome real do produto removendo códigos e datas."""
    # Remove códigos de 5 a 8 dígitos
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto)
    # Remove datas como 20-mar ou 20-mar-2026
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome)
    # Remove caracteres especiais e espaços sobrando
    nome = nome.replace('.', '').replace('-', '').strip()
    return nome if nome else "PRODUTO SEM NOME"

def palpite_categoria(nome):
    txt = remover_acentos(nome)
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY", "LANDUS"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL", "BEBIDA", "ICE"]): return "Bebidas Alcoólicas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE", "BALA", "PIPOCA"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO", "ESTOMAZIL", "REMEDIO"]): return "Remédios"
    return "Mercearia"

# ==========================================
# 3. LOGIN
# ==========================================
credentials = {
    "usernames": {
        "madson": {"name": "Madson da Hora", "password": "admin123"}
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_cookie", "auth_key_2026", expiry_days=30)
authenticator.login()

# ==========================================
# 4. DASHBOARD PRINCIPAL
# ==========================================
if st.session_state["authentication_status"]:
    st.sidebar.title(f"👤 {st.session_state['name']}")
    authenticator.logout("Sair", "sidebar")
    
    st.title("🇨🇦 Dashboard Canadá BI")
    uploaded_file = st.file_uploader("Upload do relatório PDF", type="pdf")

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

        # --- PROCESSAMENTO DE DADOS PARA GRÁFICOS ---
        df = pd.DataFrame(list(dados_agrupados.values()))
        df['Valor'] = df['Valor'].apply(float)

        st.info(f"📅 Período identificado: {periodo}")
        
        # --- ÁREA DE GRÁFICOS ---
        col_g1, col_g2 = st.columns([1, 1])
        
        with col_g1:
            st.subheader("Top 10 Produtos (R$)")
            top10 = df.nlargest(10, 'Valor')
            st.bar_chart(data=top10, x="Nome", y="Valor", color="#38bdf8")

        with col_g2:
            st.subheader("Faturamento por Categoria")
            # SOLUÇÃO DO ERRO: Agrupamos e definimos a Categoria como Índice
            resumo_cat = df.groupby('Cat')['Valor'].sum()
            st.pie_chart(resumo_cat)

        # --- PAINEL KANBAN (COLUNAS) ---
        st.divider()
        cats = ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Remédios", "Mercearia"]
        colunas = st.columns(len(cats))
        
        for i, c_nome in enumerate(cats):
            with colunas[i]:
                itens_cat = df[df['Cat'] == c_nome]
                total_cat = itens_cat['Valor'].sum()
                st.metric(c_nome.upper(), formatar_moeda(total_cat))
                
                with st.expander("Ver Detalhes"):
                    for _, row in itens_cat.iterrows():
                        st.caption(f"**{row['Nome']}**")
                        st.write(f"Qtde: {row['Qtde']} | {formatar_moeda(row['Valor'])}")
                        st.write("---")

        st.divider()
        st.header(f"💰 TOTAL GERAL BRUTO: {formatar_moeda(df['Valor'].sum())}")

    # Rodapé Profissional
    st.markdown('<div class="footer">Desenvolvido por <b>@Madson_da_hora</b> - Analista de Dados e Programador / Todos os direitos Reservados</div>', unsafe_allow_html=True)

elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha inválidos.")
