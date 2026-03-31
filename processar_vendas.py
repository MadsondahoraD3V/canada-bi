import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import json
import os
import unicodedata
from decimal import Decimal
from datetime import datetime

# --- CONFIGURAÇÕES INICIAIS ---
# Definimos o layout largo para aproveitar sua tela de 60'
st.set_page_config(page_title="Canadá BI - Web", layout="wide")

# --- FUNÇÕES DE AUXÍLIO (INTELIGÊNCIA) ---
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper()

def formatar_moeda(valor):
    v_str = f"{valor:,.2f}"
    return v_str.replace(',', 'X').replace('.', ',').replace('X', '.')

def palpite_categoria(nome):
    txt = remover_acentos(str(nome)).strip()
    if "SEDA" in txt and any(p in txt for p in ["SHAMPOO", "COND", "CREME"]): return "Mercearia"
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "LANDUS", "TREVO", "ISQUEIRO"]): return "Tabacaria"
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 "]): return "Bebidas Alcoólicas"
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE"]): return "Bomboniere"
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO"]): return "Remédios"
    return "Mercearia"

# --- SISTEMA DE LOGIN ---
credentials = {
    "usernames": {
        "madson": {
            "name": "Madson da Hora",
            "password": "admin123" # Altere aqui para sua senha de preferência
        }
    }
}

authenticator = stauth.Authenticate(credentials, "canada_cookie", "secret_key_123", expiry_days=30)

# O Streamlit renderiza a tela de login aqui
authenticator.login()

if st.session_state["authentication_status"]:
    # LOGIN COM SUCESSO - MOSTRAR DASHBOARD
    st.sidebar.write(f"👤 Usuário: {st.session_state['name']}")
    authenticator.logout("Sair", "sidebar")
    
    st.title("🇨🇦 Dashboard Canadá BI")
    st.subheader("Processamento de Vendas e Faturamento")

    # UPLOAD DO PDF
    uploaded_file = st.file_uploader("Arraste o relatório PDF aqui", type="pdf")

    if uploaded_file:
        dados_agrupados = {}
        periodo = "Não identificado"
        
        with pdfplumber.open(uploaded_file) as pdf:
            # Pegar o período na primeira página
            texto_topo = pdf.pages[0].extract_text()
            match_p = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', texto_topo or "")
            if match_p:
                periodo = f"{match_p.group(1)} a {match_p.group(2)}"
            
            # Processar todas as páginas
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                for line in text.split('\n'):
                    try:
                        linha = line.replace('|', ' ').strip()
                        ean_match = re.search(r'\b\d{8,14}\b', linha)
                        valores = re.findall(r'\d+,\d{2}', linha)
                        
                        if ean_match and len(valores) >= 4:
                            ean = ean_match.group()
                            # Nome do produto
                            match_nome = re.search(r'(.+?)\s+(?:UN|KG)\s+\d+,\d{2}', linha)
                            nome = match_nome.group(1).replace(ean, '').strip() if match_nome else "Produto Desconhecido"
                            
                            qtde = Decimal(valores[0].replace(',', '.'))
                            valor_bruto = Decimal(valores[-4].replace(',', '.'))
                            cat = palpite_categoria(nome)
                            
                            if ean in dados_agrupados:
                                dados_agrupados[ean]['Qtde'] += qtde
                                dados_agrupados[ean]['Valor'] += valor_bruto
                            else:
                                dados_agrupados[ean] = {"Nome": nome, "Cat": cat, "Qtde": qtde, "Valor": valor_bruto}
                    except: continue

        st.info(f"📅 Período identificado: {periodo}")

        # --- EXIBIÇÃO DOS RESULTADOS (VISUAL KANBAN) ---
        categorias = ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Remédios", "Mercearia"]
        colunas = st.columns(len(categorias))

        total_geral = Decimal("0.00")

        for idx, cat_nome in enumerate(categorias):
            with colunas[idx]:
                itens_da_cat = [v for v in dados_agrupados.values() if v['Cat'] == cat_nome]
                soma_cat = sum(item['Valor'] for item in itens_da_cat)
                total_geral += soma_cat
                
                st.markdown(f"### {cat_nome}")
                st.metric("Subtotal", formatar_moeda(soma_cat))
                
                with st.expander("Ver Itens"):
                    for item in itens_da_cat:
                        st.caption(f"**{item['Nome']}**")
                        st.write(f"{item['Qtde']} un | {formatar_moeda(item['Valor'])}")
                        st.write("---")

        # Rodapé com Valor Total
        st.divider()
        st.subheader(f"💰 CAIXA TOTAL BRUTO: {formatar_moeda(total_geral)}")

    # Assinatura Fixa
    st.write("")
    st.info("Desenvolvido por @Madson_da_hora - Analista de Dados e Programador / Todos os direitos Reservados")

elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha incorretos.")
elif st.session_state["authentication_status"] is None:
    st.warning("Aguardando login...")
