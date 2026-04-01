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

# ==========================================
# 1. CONFIGURAÇÕES VISUAIS E CSS (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Canadá BI - Pro", layout="wide")

# (O CSS do Streamlit permanece o mesmo para manter a consistência do site)
st.markdown("<style>.stApp { background-color: #020617; }</style>", unsafe_allow_html=True)

# ==========================================
# 2. FUNÇÕES CORE E GERADOR DE HTML INTELIGENTE
# ==========================================
def gerar_html_interativo(df, periodo, total_geral):
    """Gera o HTML 'Cyber' com JavaScript para recálculo offline."""
    
    # Preparar dados para o JavaScript
    resumo_cat = df.groupby('Cat')['Valor'].sum().to_dict()
    top10 = df.nlargest(10, 'Valor')
    
    # Gerar os itens do Accordion com Checkboxes
    categorias_html = ""
    cores = {"Tabacaria": "#ea580c", "Bebidas": "#2563eb", "Bomboniere": "#db2777", "Remédios": "#059669", "Mercearia": "#475569"}
    
    for i, cat in enumerate(cores.keys()):
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        
        cards_html = ""
        for _, row in itens_cat.iterrows():
            cards_html += f"""
            <div class="card">
                <div class="card-title">{row['Nome']}</div>
                <div class="card-price">R$ {row['Valor']:,.2f}</div>
            </div>"""

        categorias_html += f"""
        <div class="accordion-item" id="secao-{cat}">
            <div class="accordion-header" style="background-color: {cores[cat]};">
                <div onclick="toggleAccordion('content-{i}')" style="flex-grow:1;">
                    <span class="acc-title">{cat.upper()} ▼</span>
                </div>
                <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onchange="recalcular()">
                <span class="acc-value" id="val-{cat}">R$ {valor_cat:,.2f}</span>
            </div>
            <div id="content-{i}" class="accordion-content">
                <div class="cards-grid">{cards_html}</div>
            </div>
        </div>"""

    # Template Final com a lógica JavaScript embutida
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório BI - Canadá</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{ --bg-main: #020617; --bg-panel: #0f172a; --bg-card: #1e293b; --text-main: #f8fafc; --accent: #38bdf8; --success: #10b981; }}
            body {{ background-color: var(--bg-main); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding-bottom: 80px; }}
            .header-cyber {{ background-color: #000; padding: 30px; text-align: center; border-bottom: 1px solid #334155; }}
            .total-destaque {{ color: var(--success); font-size: 2.5rem; font-weight: 900; }}
            .charts-container {{ display: flex; justify-content: center; gap: 15px; padding: 20px; }}
            .chart-box {{ background: var(--bg-panel); padding: 15px; border-radius: 8px; width: 48%; height: 350px; }}
            .accordion-header {{ padding: 10px 20px; display: flex; align-items: center; cursor: pointer; border-radius: 6px; margin-bottom: 5px; }}
            .cat-check {{ width: 25px; height: 25px; margin-right: 15px; cursor: pointer; }}
            .accordion-content {{ max-height: 0; overflow: hidden; transition: max-height 0.4s ease-out; background: #000; }}
            .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; padding: 15px; }}
            .card {{ background: var(--bg-card); padding: 10px; border-radius: 5px; border-left: 3px solid var(--accent); }}
            .card-price {{ color: var(--success); font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header-cyber">
            <h1>DASHBOARD CANADÁ BI</h1>
            <p>Período: <strong>{periodo}</strong></p>
            <div class="total-destaque" id="display-total">CAIXA TOTAL BRUTO: R$ {total_geral:,.2f}</div>
        </div>
        <div class="charts-container">
            <div class="chart-box"><canvas id="graficoPizza"></canvas></div>
            <div class="chart-box"><canvas id="graficoTop10"></canvas></div>
        </div>
        <div style="max-width: 1200px; margin: 0 auto;">{categorias_html}</div>

        <script>
            function toggleAccordion(id) {{
                var content = document.getElementById(id);
                content.style.maxHeight = content.style.maxHeight ? null : content.scrollHeight + "px";
            }}

            let resumo = {json.dumps(resumo_cat)};
            let chartPizza, chartBarra;

            function recalcular() {{
                let total = 0;
                let novosLabels = [];
                let novosValores = [];
                
                document.querySelectorAll('.cat-check').forEach(check => {{
                    let cat = check.getAttribute('data-cat');
                    let valor = parseFloat(check.getAttribute('data-valor'));
                    if (check.checked) {{
                        total += valor;
                        novosLabels.push(cat);
                        novosValores.push(valor);
                    }}
                }});

                document.getElementById('display-total').innerText = "CAIXA TOTAL BRUTO: R$ " + total.toLocaleString('pt-BR', {{minimumFractionDigits: 2}});
                
                // Atualiza os Gráficos
                chartPizza.data.labels = novosLabels;
                chartPizza.data.datasets[0].data = novosValores;
                chartPizza.update();
            }}

            // Inicialização dos Gráficos
            const ctxPizza = document.getElementById('graficoPizza').getContext('2d');
            chartPizza = new Chart(ctxPizza, {{
                type: 'doughnut',
                data: {{ 
                    labels: Object.keys(resumo), 
                    datasets: [{{ data: Object.values(resumo), backgroundColor: ["#ea580c", "#2563eb", "#db2777", "#059669", "#475569"] }}] 
                }},
                options: {{ maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{color: 'white'}} }} }} }}
            }});
        </script>
    </body>
    </html>
    """

# (Funções registrar_log, limpar_nome_produto, palpite_categoria permanecem iguais)

# ... [O resto do código de Login e Navegação continua o mesmo] ...

# Dentro da '📊 Painel Individual', mude o botão de download para:
# html_interativo = gerar_html_interativo(df, per, total_bruto)
# st.download_button(label="🌐 Baixar Dashboard Inteligente", data=html_interativo, file_name=f"BI_CANADA_{per}.html", mime="text/html")
