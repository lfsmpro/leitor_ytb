import streamlit as st

st.title("🎬 Teste de Deploy - Analisador de Comentários")
st.write("Se você está vendo esta mensagem, o deploy básico funcionou!")

# Teste de imports
try:
    import pandas as pd
    st.success("✅ Pandas importado com sucesso")
except ImportError as e:
    st.error(f"❌ Erro ao importar Pandas: {e}")

try:
    import plotly.express as px
    st.success("✅ Plotly importado com sucesso")
except ImportError as e:
    st.error(f"❌ Erro ao importar Plotly: {e}")

try:
    import google.generativeai as genai
    st.success("✅ Google Generative AI importado com sucesso")
except ImportError as e:
    st.error(f"❌ Erro ao importar Google Generative AI: {e}")

try:
    from googleapiclient.discovery import build
    st.success("✅ Google API Client importado com sucesso")
except ImportError as e:
    st.error(f"❌ Erro ao importar Google API Client: {e}")

try:
    from dotenv import load_dotenv
    st.success("✅ Python-dotenv importado com sucesso")
except ImportError as e:
    st.error(f"❌ Erro ao importar Python-dotenv: {e}")

st.markdown("---")
st.write("**Próximo passo:** Se todos os imports funcionaram, o problema não são as dependências.")
