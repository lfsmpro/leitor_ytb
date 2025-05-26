# Analisador de Comentários do YouTube com Gemini

Esta aplicação extrai comentários de vídeos do YouTube e os analisa usando a API gratuita do Gemini para classificar o sentimento como positivo, negativo ou neutro.

## Funcionalidades

- Extração de comentários de vídeos do YouTube usando a API do YouTube
- Análise de sentimento usando a API gratuita do Gemini
- Visualização interativa dos resultados com Streamlit
- Exportação dos resultados para CSV

## Requisitos

- Python 3.7+
- Chave de API do YouTube (Google Cloud Platform)
- Chave de API do Gemini (Google AI Studio)
- Bibliotecas Python listadas em `requirements.txt`

## Instalação

1. Clone o repositório ou baixe os arquivos

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as chaves de API:
   - Renomeie o arquivo `.env.example` para `.env`
   - Adicione suas chaves de API no arquivo `.env`

## Uso

1. Execute a aplicação Streamlit:
```bash
streamlit run app.py
```

2. Acesse a interface web no navegador (geralmente em http://localhost:8501)
3. Insira sua chave de API do YouTube e do Gemini (ou use as chaves configuradas no arquivo .env)
4. Insira a URL do vídeo do YouTube que deseja analisar
5. Defina o número máximo de comentários a serem analisados
6. Clique em "Iniciar Análise"
7. Explore os resultados interativos e baixe os dados analisados

## Obtenção das Chaves de API

### Chave de API do YouTube
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative a API do YouTube Data v3
4. Crie uma chave de API e copie-a

### Chave de API do Gemini
1. Acesse o [Google AI Studio](https://aistudio.google.com/)
2. Faça login com sua conta Google
3. Vá para a seção "API Keys"
4. Crie uma nova chave de API e copie-a

## Estrutura do Projeto

- `app.py`: Aplicação principal com interface Streamlit
- `youtube_extractor.py`: Classe para extrair comentários do YouTube
- `sentiment_analyzer.py`: Classe para analisar sentimentos com Gemini
- `requirements.txt`: Lista de dependências
- `.env`: Arquivo para armazenar chaves de API

## Limitações

- A API do YouTube tem cotas de uso diário
- A API gratuita do Gemini tem limites de uso
- O processamento de grandes volumes de comentários pode ser lento

## Licença

Este projeto é distribuído sob a licença MIT.
