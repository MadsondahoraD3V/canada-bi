# --- ADICIONE ESTE BLOCO DENTRO DO LOOP DE CATEGORIAS NO SEU APP.PY ---

# Melhorando o visual das métricas com cores
total_geral_float = float(total_geral)

# Criando colunas para os gráficos no topo
st.divider()
col_graf1, col_graf2 = st.columns(2)

# Exemplo de como preparar dados para um gráfico de pizza
with col_graf1:
    st.subheader("Distribuição por Categoria")
    df_pizza = pd.DataFrame([
        {"Categoria": cat, "Valor": float(sum(item['Valor'] for item in dados_agrupados.values() if item['Cat'] == cat))}
        for cat in categorias
    ])
    st.write("Gráfico de Pizza:") 
    st.pie_chart(data=df_pizza, x="Categoria", y="Valor")

with col_graf2:
    st.subheader("Top 5 Produtos (Faturamento)")
    # Ordena produtos pelo valor total
    top_produtos = sorted(dados_agrupados.values(), key=lambda x: x['Valor'], reverse=True)[:5]
    df_barras = pd.DataFrame(top_produtos)
    st.bar_chart(data=df_barras, x="Nome", y="Valor")

# --- ASSINATURA COM DESIGN MELHORADO ---
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #000;
        color: #64748b;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #334155;
    }
    </style>
    <div class="footer">
        Desenvolvido por <b>@Madson_da_hora</b> - Analista de Dados e Programador / Todos os direitos Reservados
    </div>
    """,
    unsafe_allow_html=True
)
