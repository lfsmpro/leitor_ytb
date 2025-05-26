"""
Aplicação Streamlit para análise de sentimentos de comentários do YouTube usando a API do Gemini.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv, find_dotenv

from youtube_extractor import YouTubeCommentExtractor
from sentiment_analyzer import GeminiSentimentAnalyzer

# Carregar variáveis de ambiente
dotenv_path = find_dotenv()
if not dotenv_path:
    # Se o arquivo .env não existir, cria um novo
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(dotenv_path):
        with open(dotenv_path, 'w') as f:
            f.write("# Chaves de API\n")
            f.write("YOUTUBE_API_KEY=\n")
            f.write("GEMINI_API_KEY=\n")

load_dotenv(dotenv_path)

# Configuração da página
st.set_page_config(
    page_title="Analisador de Comentários do YouTube",
    page_icon="🎬",
    layout="wide"
)

# Título e descrição
st.title("🎬 Analisador de Comentários do YouTube com Gemini")
st.markdown("""
Esta aplicação extrai comentários de vídeos do YouTube e os analisa usando a API do Gemini
para classificar o sentimento como positivo, negativo ou neutro.
""")

# Inicializar variáveis de estado da sessão se não existirem
if 'last_video_url' not in st.session_state:
    st.session_state.last_video_url = ""

# Sidebar para configurações
st.sidebar.title("Configurações")

# Opção para usar dados de exemplo
use_example_data = st.sidebar.checkbox("Usar dados de exemplo", value=False)

if not use_example_data:
    # Entrada das chaves de API
    st.sidebar.subheader("Chaves de API")

    # Obter chaves salvas
    youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    # Mostrar status das chaves
    if youtube_api_key:
        st.sidebar.success("✅ Chave de API do YouTube está configurada")
    else:
        st.sidebar.warning("⚠️ Chave de API do YouTube não configurada")

    if gemini_api_key:
        st.sidebar.success("✅ Chave de API do Gemini está configurada")
    else:
        st.sidebar.warning("⚠️ Chave de API do Gemini não configurada")

    # Informação sobre configuração das chaves
    if not youtube_api_key or not gemini_api_key:
        with st.sidebar.expander("ℹ️ Como configurar as chaves de API"):
            st.markdown("""
            **Para configurar as chaves de API:**

            1. Crie um arquivo `.env` na pasta da aplicação
            2. Adicione as seguintes linhas:
            ```
            YOUTUBE_API_KEY=sua_chave_youtube_aqui
            GEMINI_API_KEY=sua_chave_gemini_aqui
            ```
            3. Reinicie a aplicação

            **Como obter as chaves:**
            - **YouTube API**: [Google Cloud Console](https://console.cloud.google.com/)
            - **Gemini API**: [Google AI Studio](https://aistudio.google.com/)
            """)

    # Entrada da URL do vídeo
    st.sidebar.subheader("Configurações de Análise")
    video_url = st.sidebar.text_input("URL do vídeo do YouTube")

    # Verificar se a URL do vídeo mudou
    if video_url != st.session_state.last_video_url and video_url != "":
        # Se a URL mudou e não está vazia, limpar os dados anteriores
        if 'analyzed' in st.session_state:
            del st.session_state.analyzed
        if 'results' in st.session_state:
            del st.session_state.results
        if 'extraction_info' in st.session_state:
            del st.session_state.extraction_info

        # Atualizar a URL armazenada
        st.session_state.last_video_url = video_url

        # Mostrar mensagem informando que os dados foram limpos
        st.sidebar.success("Nova URL detectada. Dados do vídeo anterior foram limpos.")

    # Número de comentários
    max_comments = st.sidebar.slider("Número máximo de comentários", 10, 300, 30)

    # Filtro para tipo de comentários a serem extraídos
    st.sidebar.subheader("Filtro de Extração")
    comment_type_options = ["Todos os comentários", "Apenas comentários principais", "Apenas respostas"]
    comment_type_filter = st.sidebar.radio("Tipo de comentários a extrair:", comment_type_options)

    # Campo para prompt personalizado
    st.sidebar.subheader("Prompt Personalizado")

    # Opção para usar prompt personalizado
    use_custom_prompt = st.sidebar.checkbox("Usar prompt personalizado", value=False)

    custom_prompt = ""
    if use_custom_prompt:
        custom_prompt = st.sidebar.text_area(
            "Digite seu prompt personalizado:",
            placeholder="Ex: Analise este comentário considerando aspectos de toxicidade, ironia e contexto cultural brasileiro...",
            height=100,
            help="O prompt personalizado será usado para analisar os comentários. O sistema ainda retornará sentiment, score e explanation no formato padrão."
        )

        # Mostrar explicação sobre o prompt personalizado
        with st.sidebar.expander("ℹ️ Como usar o prompt personalizado"):
            st.markdown("""
            **Dicas para criar um bom prompt:**
            - Seja específico sobre o que você quer analisar
            - Mencione critérios específicos (ex: ironia, sarcasmo, contexto cultural)
            - O sistema sempre retornará: sentimento (positivo/negativo/neutro), pontuação (-1 a 1) e explicação
            - Exemplos de prompts:
              - "Analise considerando ironia e sarcasmo"
              - "Foque em aspectos de toxicidade e agressividade"
              - "Considere o contexto cultural brasileiro"
            """)
    else:
        custom_prompt = None
else:
    # Usar dados de exemplo
    youtube_api_key = "exemplo"
    gemini_api_key = "exemplo"
    video_url = "https://www.youtube.com/watch?v=exemplo"
    max_comments = 30
    use_custom_prompt = False  # Não usar prompt personalizado com dados de exemplo
    custom_prompt = None

    # Criar dados de exemplo
    @st.cache_data
    def get_example_data():
        data = {
            'author': ['Usuário 1', 'Usuário 2', 'Usuário 3', 'Usuário 4', 'Usuário 5'],
            'text': [
                'Adorei esse vídeo! Muito informativo e bem produzido.',
                'Não gostei do conteúdo, achei muito superficial.',
                'Interessante, mas poderia ter mais exemplos práticos.',
                'Péssimo vídeo, perda de tempo.',
                'Conteúdo excelente, já compartilhei com meus amigos!'
            ],
            'likes': [15, 2, 8, 1, 20],
            'published_at': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'],
            'sentiment': ['positivo', 'negativo', 'neutro', 'negativo', 'positivo'],
            'score': [0.8, -0.6, 0.1, -0.9, 0.9],
            'explanation': [
                'O comentário expressa entusiasmo e elogia a qualidade do vídeo.',
                'O comentário expressa insatisfação com o conteúdo do vídeo.',
                'O comentário reconhece aspectos positivos, mas também sugere melhorias.',
                'O comentário expressa forte insatisfação e frustração.',
                'O comentário expressa entusiasmo e indica que o usuário recomendou o conteúdo.'
            ]
        }
        return pd.DataFrame(data)

# Função para extrair e analisar comentários
def extract_and_analyze(custom_prompt=None):
    # Verificar se as chaves de API foram fornecidas
    if not youtube_api_key or not gemini_api_key:
        st.error("Por favor, forneça as chaves de API do YouTube e do Gemini.")
        return None

    if use_example_data:
        return get_example_data()

    if not video_url:
        st.error("Por favor, forneça a URL de um vídeo do YouTube.")
        return None

    # Extrair comentários
    with st.spinner("Extraindo comentários do YouTube..."):
        try:
            extractor = YouTubeCommentExtractor(youtube_api_key)
            video_id = extractor.extract_video_id(video_url)

            if not video_id:
                st.error("URL de vídeo inválida. Por favor, verifique e tente novamente.")
                return None

            # Obter detalhes do vídeo
            video_details = extractor.get_video_details(video_id)
            if video_details:
                st.subheader("Detalhes do Vídeo")
                st.write(f"**Título:** {video_details['title']}")
                st.write(f"**Canal:** {video_details['channel']}")
                st.write(f"**Visualizações:** {video_details['view_count']}")
                st.write(f"**Likes:** {video_details['like_count']}")
                st.write(f"**Total de comentários:** {video_details['comment_count']}")

            # Determinar o tipo de comentário a ser extraído com base no filtro
            extract_main = True
            extract_replies = True

            if comment_type_filter == "Apenas comentários principais":
                extract_main = True
                extract_replies = False
            elif comment_type_filter == "Apenas respostas":
                extract_main = False
                extract_replies = True

            comments_df, extraction_info = extractor.get_comments(
                video_url,
                max_comments=max_comments,
                extract_main=extract_main,
                extract_replies=extract_replies
            )

            # Armazenar informações de extração na sessão
            st.session_state.extraction_info = extraction_info

            # Mostrar mensagem de sucesso com detalhes
            st.success(f"Extraídos {len(comments_df)} comentários de {extraction_info['available']} disponíveis.")

            # Mostrar explicações sobre a extração, se houver
            if extraction_info['reasons']:
                with st.expander("Detalhes da extração de comentários", expanded=True):
                    for reason in extraction_info['reasons']:
                        st.info(reason)
        except Exception as e:
            st.error(f"Erro ao extrair comentários: {e}")
            return None

    # Analisar sentimentos
    with st.spinner("Analisando sentimentos com a API do Gemini..."):
        try:
            analyzer = GeminiSentimentAnalyzer(gemini_api_key)
            # Passar o prompt personalizado se fornecido
            results_df = analyzer.batch_analyze(comments_df, custom_prompt=custom_prompt)
            st.success("Análise de sentimentos concluída!")
            return results_df
        except Exception as e:
            st.error(f"Erro ao analisar sentimentos: {e}")
            return None

# Botões para controle da análise
col1, col2 = st.sidebar.columns(2)

# Botão para iniciar a análise
if col1.button("Iniciar Análise", use_container_width=True):
    results_df = extract_and_analyze(custom_prompt)

    if results_df is not None:
        # Armazenar os resultados na sessão
        st.session_state.results = results_df
        st.session_state.analyzed = True

        # Atualizar a URL armazenada para a URL atual
        st.session_state.last_video_url = video_url

# Botão para limpar dados manualmente
if col2.button("Limpar Dados", use_container_width=True):
    # Limpar todos os dados da sessão
    if 'analyzed' in st.session_state:
        del st.session_state.analyzed
    if 'results' in st.session_state:
        del st.session_state.results
    if 'extraction_info' in st.session_state:
        del st.session_state.extraction_info

    # Mostrar mensagem de confirmação
    st.sidebar.success("Dados limpos com sucesso!")

# Verificar se há resultados na sessão
if 'analyzed' in st.session_state and st.session_state.analyzed:
    results_df = st.session_state.results

    # Mostrar informações sobre prompt personalizado se usado
    if not use_example_data and use_custom_prompt and custom_prompt:
        st.info(f"🎯 **Análise realizada com prompt personalizado:** {custom_prompt[:100]}{'...' if len(custom_prompt) > 100 else ''}")

    # Exibir resultados
    st.subheader("Resultados da Análise")

    # Estatísticas gerais
    col1, col2, col3 = st.columns(3)

    with col1:
        total_positivos = len(results_df[results_df['sentiment'] == 'positivo'])
        st.metric("Comentários Positivos", total_positivos)

    with col2:
        total_neutros = len(results_df[results_df['sentiment'] == 'neutro'])
        st.metric("Comentários Neutros", total_neutros)

    with col3:
        total_negativos = len(results_df[results_df['sentiment'] == 'negativo'])
        st.metric("Comentários Negativos", total_negativos)

    # Gráfico de distribuição de sentimentos
    st.subheader("Distribuição de Sentimentos")

    # Contagem de sentimentos
    sentiment_counts = results_df['sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['Sentimento', 'Contagem']

    # Criar gráfico com Plotly
    fig = px.pie(
        sentiment_counts,
        values='Contagem',
        names='Sentimento',
        color='Sentimento',
        color_discrete_map={
            'positivo': '#4CAF50',
            'neutro': '#FFC107',
            'negativo': '#F44336',
            'erro': '#9E9E9E'
        },
        title='Distribuição de Sentimentos'
    )
    st.plotly_chart(fig)

    # Exibir tabela de comentários
    st.subheader("Tabela de Comentários")

    # Verificar se a coluna 'type' existe no DataFrame
    display_columns = ['author', 'text', 'sentiment', 'score', 'explanation']
    column_config = {
        'author': 'Autor',
        'text': 'Comentário',
        'sentiment': 'Sentimento',
        'score': st.column_config.NumberColumn(
            'Pontuação',
            format="%.2f"
        ),
        'explanation': 'Explicação'
    }

    # Adicionar coluna de tipo se existir
    filtered_df = results_df.copy()
    if 'type' in results_df.columns:
        display_columns.insert(1, 'type')
        column_config['type'] = 'Tipo'

        # Adicionar filtro para tipo de comentário
        st.subheader("Filtrar Comentários")

        # Obter valores únicos para o filtro
        tipos_comentarios = ['Todos'] + sorted(results_df['type'].unique().tolist())

        # Criar o filtro
        tipo_selecionado = st.selectbox("Filtrar por tipo de comentário:", tipos_comentarios)

        # Aplicar o filtro se não for "Todos"
        if tipo_selecionado != 'Todos':
            filtered_df = results_df[results_df['type'] == tipo_selecionado]
            st.write(f"Mostrando {len(filtered_df)} comentários do tipo '{tipo_selecionado}'")

    # Adicionar coluna de autor do comentário pai se existir
    if 'parent_author' in results_df.columns:
        display_columns.insert(2, 'parent_author')
        column_config['parent_author'] = 'Resposta para'

    # Adicionar filtro de sentimento
    if 'sentiment' in results_df.columns:
        col1, col2 = st.columns(2)
        with col1:
            sentimentos = ['Todos'] + sorted(results_df['sentiment'].unique().tolist())
            sentimento_selecionado = st.selectbox("Filtrar por sentimento:", sentimentos)
            if sentimento_selecionado != 'Todos':
                filtered_df = filtered_df[filtered_df['sentiment'] == sentimento_selecionado]

        with col2:
            # Adicionar campo de busca por texto
            texto_busca = st.text_input("Buscar no texto dos comentários:")
            if texto_busca:
                filtered_df = filtered_df[filtered_df['text'].str.contains(texto_busca, case=False, na=False)]

    # Mostrar contagem de resultados filtrados
    st.write(f"Exibindo {len(filtered_df)} de {len(results_df)} comentários")

    # Exibir a tabela filtrada
    st.dataframe(
        filtered_df[display_columns],
        column_config=column_config,
        hide_index=True
    )

    # Opção para baixar os resultados
    csv = results_df.to_csv(index=False)
    st.download_button(
        label="Baixar resultados como CSV",
        data=csv,
        file_name="analise_comentarios_youtube.csv",
        mime="text/csv"
    )

# Informações adicionais
st.sidebar.markdown("---")
st.sidebar.subheader("Sobre")
st.sidebar.info("""
Esta aplicação utiliza a API do YouTube para extrair comentários e a API do Gemini para análise de sentimentos.
Para usar, você precisa de chaves de API válidas para ambos os serviços.
""")

# Informações sobre o controle de taxa
st.sidebar.subheader("Limites de API")
st.sidebar.warning("""
**Controle de Taxa Implementado:**
- Máximo de 15 requisições por minuto para a API do Gemini
- A aplicação aguardará automaticamente quando necessário para respeitar este limite
- Isso evita erros de excesso de requisições e garante o funcionamento contínuo
""")

# Explicação sobre a escala de sentimento
st.sidebar.subheader("Escala de Sentimento")
st.sidebar.markdown("""
- **-1.0 a -0.3**: Sentimento negativo
- **-0.3 a 0.3**: Sentimento neutro
- **0.3 a 1.0**: Sentimento positivo
""")

# Informações sobre prompt personalizado
st.sidebar.subheader("Prompt Personalizado")
st.sidebar.info("""
**Nova funcionalidade!** 🎯

Agora você pode personalizar a análise de sentimentos fornecendo seu próprio prompt. Isso permite:

- Análises mais específicas (ex: detectar ironia, sarcasmo)
- Considerar contexto cultural brasileiro
- Focar em aspectos específicos como toxicidade
- Adaptar a análise para diferentes domínios

O sistema sempre retornará sentimento, pontuação e explicação no formato padrão.
""")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando Streamlit, API do YouTube e API do Gemini")
