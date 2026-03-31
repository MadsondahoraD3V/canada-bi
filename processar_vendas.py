import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from decimal import Decimal
import time

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS
# ==========================================
st.set_page_config(page_title="Canadá BI - Pro", layout="wide")

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
# 2. FUNÇÕES CORE (LÓGICA REUTILIZÁVEL)
# ==========================================
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

def processar_pdf(file):
    """Lógica central de leitura de cada PDF."""
    dados = []
    with pdfplumber.open(file) as pdf:
        txt_topo = pdf.pages[0].extract_text() or ""
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
                        nome_limpo = limpar_nome_produto(nome_m.group(1).replace(ean_m.group() if ean_m else "", "").strip())
                        val = float(valores[-4].replace(',', '.'))
                        dados.append({"Nome": nome_limpo, "Cat": palpite_categoria(nome_limpo), "Valor": val, "Periodo": periodo})
                except: continue
    return dados, periodo

# ==========================================
# 3. SEGURANÇA (LOGIN)
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
name, auth_status, username = authenticator.login("Login", "main")

if auth_status:
    # --- MENU DE NAVEGAÇÃO ---
    st.sidebar.title(f"👤 {name}")
    pagina = st.sidebar.radio("Navegação", ["📊 Painel Individual", "🚀 Upload em Lote"])
    authenticator.logout("Sair", "sidebar")

    # ==========================================
    # PÁGINA 1: PAINEL INDIVIDUAL
    # ==========================================
    if pagina == "📊 Painel Individual":
        st.title("📊 Análise Individual")
        file = st.file_uploader("Arraste um PDF para análise detalhada", type="pdf", key="single")
        
        if file:
            dados, per = processar_pdf(file)
            df = pd.DataFrame(dados)
            
            st.info(f"📅 Período: {per}")
            
            # Soma Flutuante
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

    # ==========================================
    # PÁGINA 2: UPLOAD EM LOTE
    # ==========================================
    else:
        st.title("🚀 Processamento em Lote")
        st.write("Selecione até 7 arquivos para processamento simultâneo e geração de relatórios.")
        
        batch_files = st.file_uploader("Upload em Lote", type="pdf", accept_multiple_files=True, key="batch")
        
        if batch_files:
            if len(batch_files) > 7:
                st.error("⚠️ Máximo de 7 arquivos permitido.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.container()
                
                sucessos = 0
                erros = 0
                lista_resultados = []

                for i, f in enumerate(batch_files):
                    # Atualiza Barra de Progresso
                    percentual = (i + 1) / len(batch_files)
                    progress_bar.progress(percentual)
                    status_text.text(f"Processando: {f.name}...")
                    
                    try:
                        dados, per = processar_pdf(f)
                        if not dados: raise Exception("PDF sem dados compatíveis")
                        
                        total = sum(d['Valor'] for d in dados)
                        lista_resultados.append({"arquivo": f.name, "status": "✅ Sucesso", "periodo": per, "total": total})
                        sucessos += 1
                    except Exception as e:
                        lista_resultados.append({"arquivo": f.name, "status": "❌ Erro", "periodo": "---", "total": 0})
                        erros += 1
                    
                    time.sleep(0.5) # Apenas para visualização do progresso

                # Relatório Final
                st.divider()
                st.subheader("📝 Relatório de Processamento")
                
                col_s, col_e = st.columns(2)
                col_s.metric("Sucessos", sucessos)
                col_e.metric("Falhas", erros, delta_color="inverse")

                # Tabela de Detalhes
                resumo_df = pd.DataFrame(lista_resultados)
                st.table(resumo_df)
                
                if erros > 0:
                    st.warning(f"Atenção: {erros} arquivo(s) apresentaram problemas de leitura.")
                else:
                    st.balloons()
                    st.success("Todos os arquivos foram processados com perfeição!")

    st.markdown('<div class="footer">Canadá BI v6.0 | Dashboard & Batch System</div>', unsafe_allow_html=True)

elif auth_status is False:
    st.error("Login/Senha incorretos")
