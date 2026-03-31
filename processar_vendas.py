import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DE USUÁRIOS (FORMATO NOVO) ---
# Organizamos os dados em um dicionário para a biblioteca entender
credentials = {
    "usernames": {
        "madson": {
            "name": "Madson da Hora",
            "password": "admin123" # A biblioteca vai tratar a segurança automaticamente
        }
    }
}

# Criamos o autenticador com o novo formato de dicionário
# 'canada_cookie' é o nome do cookie salvo no navegador
# 'abcdef' é a chave de criptografia (pode ser qualquer texto)
authenticator = stauth.Authenticate(
    credentials,
    "canada_cookie",
    "abcdef",
    expiry_days=30
)

# Renderiza a caixa de login
# O método agora retorna uma tupla com informações do login
login_data = authenticator.login()

# No Streamlit Cloud, verificamos o status assim:
if st.session_state["authentication_status"]:
    st.sidebar.write(f"Bem-vindo, {st.session_state['name']}")
    authenticator.logout("Sair", "sidebar")
    
    st.title("🇨🇦 CANADÁ BI - Dashboard Web")
    # ... Restante do seu código de processamento ...

elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha incorretos.")
elif st.session_state["authentication_status"] is None:
    st.warning("Por favor, insira suas credenciais.")
