import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(page_title="Canadá BI - Dashboard Web", layout="wide")

# Estilo CSS para fixar a assinatura no rodapé e ajustar fontes
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
# 2. FUNÇÕES DE INTELIGÊNCIA E FORMATAÇÃO
# ==========================================
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_moeda(valor):
    v_str = f"{valor:,.2f}"
    return v_str.replace(',', 'X').replace('.', ',').replace('X', '.')

def palpite_categoria(nome):
    txt = remover_acentos(str(nome)).strip()
    if "SEDA" in txt and any(p in txt for p in ["SHAMPOO", "COND", "CREME"]): return "Mercearia"
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "LANDUS", "TREVO", "ISQUEIRO", "ROTHMANS"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL"]): return "Bebidas Alcoólicas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO", "ESTOMAZIL"]): return "Remédios"
    return "Mercearia"

# ==========================================
# 3. SISTEMA DE LOGIN (NOVO FORMATO)
# ==========================================
credentials = {
    "usernames": {
        "madson": {
            "name": "Madson da Hora",
            "password": "admin123" # Você pode alterar sua senha aqui
        }
    }
}

# Inicializa o autenticador
authenticator = stauth.Authenticate(credentials, "canada_bi_cookie", "auth_key_2026", expiry_days=30)

# Renderiza o formulário de login
authenticator.login()

# ==========================================
# 4. ÁREA LOGADA - DASHBOARD
# ==========================================
if st.session_state["authentication_status"]:
    st.sidebar.title(f"👤 {st.session_state['name']}")
    authenticator.logout("Sair do Sistema", "sidebar")
    
    st.title("🇨🇦 Canadá BI - Gestão de Faturamento")
    st.markdown("---")

    # Upload do arquivo PDF
    uploaded_file = st.file_uploader("Selecione o relatório de venda detalhada (PDF)", type="pdf")

    if uploaded_file:
        dados_agrupados = {}
        periodo_venda = "Não identificado"
        
        with pdfplumber.open(uploaded_file) as pdf:
            # Tenta capturar a data na primeira página
            primeira_pag = pdf.pages[0].extract_text()
            match_data = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', primeira_pag or "")
            if match_data:
                periodo_venda = f"{match_data.group(1)} a {match_data.group(2)}"

            # Processamento de todas as páginas
            for page in pdf.pages:
                linhas = page.extract_text().split('\n')
                for linha in linhas:
                    try:
                        linha_limpa = linha.replace('|', ' ').strip()
                        ean_match = re.search(r'\b\d{8,14}\b', linha_limpa)
                        valores = re.findall(r'\d+,\d{2}', linha_limpa)
                        
                        if ean_match and len(valores) >= 4:
                            ean = ean_match.group()
                            # Extração do nome do produto
                            match_n = re.search(r'(.+?)\s+(?:UN|KG)\s+\d+,\d{2}', linha_limpa)
                            nome_bruto = match_n.group(1).replace(ean, '').strip() if match_n else "Produto"
                            
                            qtde = Decimal(valores[0].replace(',', '.'))
                            valor_venda = Decimal(valores[-4].replace(',', '.'))
                            categoria = palpite_categoria(nome_bruto)
                            
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

        # --- EXIBIÇÃO DE MÉTRICAS E GRÁFICOS ---
        st.success(f"✅ Relatório Processado: {periodo_venda}")
        
        # Preparando dados para gráficos
        df_completo = pd.DataFrame(list(dados_agrupados.values()))
        df_completo['ValorTotal'] = df_completo['ValorTotal'].apply(float)
        
        col_g1, col_g2 = st.columns([1, 2]) # Coluna do gráfico de pizza menor e barras maior
        
        with col_g1:
            st.subheader("Faturamento por Categoria")
            resumo_cat = df_completo.groupby('Categoria')['ValorTotal'].sum().reset_index()
            # O Streamlit pie_chart é simples, mas eficaz
            st.write("Distribuição %")
            st.divider()
            # Calculando o total para os indicadores
            total_geral = df_completo['ValorTotal'].sum()
            st.metric("FATURAMENTO TOTAL", formatar_moeda(total_geral))

        with col_g2:
            st.subheader("Top 10 Produtos (Maior Receita)")
            top_10 = df_completo.nlargest(10, 'ValorTotal')
            st.bar_chart(data=top_10, x="Nome", y="ValorTotal", color="#38bdf8")

        st.markdown("---")
        
        # --- COLUNAS ESTILO KANBAN ---
        ordem_cats = ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Remédios", "Mercearia"]
        colunas_kanban = st.columns(len(ordem_cats))

        for i, nome_c in enumerate(ordem_cats):
            with colunas_kanban[i]:
                itens_filtrados = df_completo[df_completo['Categoria'] == nome_c]
                soma_valor = itens_filtrados['ValorTotal'].sum()
                
                st.info(f"**{nome_c.upper()}**")
                st.subheader(formatar_moeda(soma_valor))
                
                with st.expander("Detalhes"):
                    for _, row in itens_filtrados.iterrows():
                        st.write(f"**{row['Nome']}**")
                        st.caption(f"{float(row['Qtde'])} un | {formatar_moeda(row['ValorTotal'])}")
                        st.write("---")

    # Rodapé fixo
    st.markdown(f'<div class="footer">Desenvolvido por <b>@Madson_da_hora</b> - Data Analyst e Dev / Todos os direitos Reservados</div>', unsafe_allow_html=True)

elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha inválidos. Tente novamente.")
elif st.session_state["authentication_status"] is None:
    st.warning("Por favor, faça login para acessar o sistema.")
