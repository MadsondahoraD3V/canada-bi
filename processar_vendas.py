import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS (INTERFACE)
# ==========================================
st.set_page_config(page_title="Canadá BI - Dashboard Web", layout="wide")

# CSS para manter a identidade visual (Fundo escuro e Rodapé fixo)
st.markdown("""
    <style>
    .main { background-color: #020617; }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #000000;
        color: #64748b;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #1e293b;
        z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE INTELIGÊNCIA (CATEGORIZAÇÃO)
# ==========================================
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_moeda(valor):
    v_str = f"{valor:,.2f}"
    return v_str.replace(',', 'X').replace('.', ',').replace('X', '.')

def palpite_categoria(nome):
    txt = remover_acentos(str(nome)).strip()
    # Categorização idêntica à do projeto desktop
    if "SEDA" in txt and any(p in txt for p in ["SHAMPOO", "COND", "CREME"]): return "Mercearia"
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "LANDUS", "TREVO", "ISQUEIRO", "ROTHMANS"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas Alcoólicas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO", "ESTOMAZIL"]): return "Remédios"
    return "Mercearia"

# ==========================================
# 3. SISTEMA DE LOGIN
# ==========================================
credentials = {
    "usernames": {
        "madson": {
            "name": "Madson da Hora",
            "password": "admin123" # Altere sua senha aqui se desejar
        }
    }
}

authenticator = stauth.Authenticate(credentials, "canada_bi_cookie", "auth_key_2026", expiry_days=30)
authenticator.login()

# ==========================================
# 4. EXECUÇÃO DO DASHBOARD (PÓS-LOGIN)
# ==========================================
if st.session_state["authentication_status"]:
    st.sidebar.title(f"👤 {st.session_state['name']}")
    authenticator.logout("Sair do Sistema", "sidebar")
    
    st.title("🇨🇦 Dashboard Canadá BI")
    st.markdown("---")

    # Upload do arquivo (Substitui o botão de selecionar pasta do Windows)
    uploaded_file = st.file_uploader("Arraste o relatório de venda detalhada (PDF) aqui", type="pdf")

    if uploaded_file:
        dados_agrupados = {}
        periodo_venda = "Não identificado"
        
        with pdfplumber.open(uploaded_file) as pdf:
            # Captura da data do período
            primeira_pag = pdf.pages[0].extract_text()
            match_data = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', primeira_pag or "")
            if match_data:
                periodo_venda = f"{match_data.group(1)} a {match_data.group(2)}"

            # Extração de dados por linha
            for page in pdf.pages:
                linhas = page.extract_text().split('\n')
                for linha in linhas:
                    try:
                        linha_limpa = linha.replace('|', ' ').strip()
                        ean_match = re.search(r'\b\d{8,14}\b', linha_limpa)
                        valores = re.findall(r'\d+,\d{2}', linha_limpa)
                        
                        if ean_match and len(valores) >= 4:
                            ean = ean_match.group()
                            match_n = re.search(r'(.+?)\s+(?:UN|KG)\s+\d+,\d{2}', linha_limpa)
                            nome_bruto = match_n.group(1).replace(ean, '').strip() if match_n else "Produto"
                            
                            qtde = Decimal(valores[0].replace(',', '.'))
                            valor_venda = Decimal(valores[-4].replace(',', '.'))
                            categoria = palpite_categoria(nome_bruto)
                            
                            # Agrupamento de itens idênticos
                            if ean in dados_agrupados:
                                dados_agrupados[ean]['Qtde'] += qtde
                                dados_agrupados[ean]['ValorTotal'] += valor_venda
                            else:
                                dados_agrupados[ean] = {
                                    "Nome": nome_bruto,
                                    "Categoria": categoria,
                                    "Qtde": qtde,
                                    "ValorTotal": valor_venda
                                }
                    except: continue

        # --- EXIBIÇÃO DOS RESULTADOS ---
        st.success(f"📅 Período identificado: {periodo_venda}")
        
        # Criação das colunas idênticas ao painel anterior
        ordem_cats = ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Remédios", "Mercearia"]
        colunas_kanban = st.columns(len(ordem_cats))

        total_geral = Decimal("0.00")

        for i, nome_c in enumerate(ordem_cats):
            with colunas_kanban[i]:
                # Filtra os itens da categoria atual
                itens_cat = [v for v in dados_agrupados.values() if v['Categoria'] == nome_c]
                soma_valor = sum(item['ValorTotal'] for item in itens_cat)
                total_geral += soma_valor
                
                # Cabeçalho da Coluna
                st.info(f"**{nome_c.upper()}**")
                st.subheader(formatar_moeda(soma_valor))
                
                # Lista de itens (Versão compacta)
                with st.expander("Ver Itens"):
                    for item in itens_cat:
                        st.markdown(f"**{item['Nome']}**")
                        st.caption(f"{float(item['Qtde'])} un | {formatar_moeda(item['ValorTotal'])}")
                        st.write("---")

        # --- GRÁFICOS DE APOIO ---
        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        
        df_completo = pd.DataFrame(list(dados_agrupados.values()))
        df_completo['ValorTotal'] = df_completo['ValorTotal'].apply(float)

        with col_graf1:
            st.write("### Top 10 Produtos")
            top_10 = df_completo.nlargest(10, 'ValorTotal')
            st.bar_chart(data=top_10, x="Nome", y="ValorTotal", color="#38bdf8")

        with col_graf2:
            st.write("### Faturamento por Grupo")
            resumo_cat = df_completo.groupby('Categoria')['ValorTotal'].sum()
            st.pie_chart(resumo_cat)

        # Grande Total Final
        st.divider()
        st.header(f"💰 CAIXA TOTAL BRUTO: {formatar_moeda(total_geral)}")

    # Rodapé fixo com sua assinatura
    st.markdown(f'<div class="footer">Desenvolvido por <b>@Madson_da_hora</b> - Data Analyst e Programador / Todos os direitos Reservados</div>', unsafe_allow_html=True)

elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha inválidos.")
elif st.session_state["authentication_status"] is None:
    st.warning("Por favor, faça login para acessar o sistema.")
