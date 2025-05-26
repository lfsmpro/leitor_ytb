"""
Módulo para analisar sentimentos de comentários usando a API do Gemini.
"""

import google.generativeai as genai
import json
import time
import streamlit as st
from datetime import datetime, timedelta
from collections import deque

class GeminiSentimentAnalyzer:
    def __init__(self, api_key):
        """
        Inicializa o analisador de sentimentos usando a API do Gemini.

        Args:
            api_key (str): Chave de API do Gemini
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # Controle de taxa: 15 requisições por minuto (4 segundos por requisição)
        self.rate_limit = 15  # requisições por minuto
        self.request_interval = 60 / self.rate_limit  # segundos entre requisições
        self.request_timestamps = deque(maxlen=self.rate_limit)  # armazena timestamps das últimas requisições

    def analyze_sentiment(self, text, custom_prompt=None):
        """
        Analisa o sentimento de um texto.

        Args:
            text (str): Texto a ser analisado
            custom_prompt (str, optional): Prompt personalizado para análise

        Returns:
            dict: Resultado da análise de sentimento
        """
        # Aplicar controle de taxa
        self._apply_rate_limiting()

        if custom_prompt:
            # Usar prompt personalizado, mas garantir que o formato JSON seja mantido
            prompt = f"""
            {custom_prompt}

            IMPORTANTE: Independente da análise solicitada, retorne SEMPRE um objeto JSON válido com as seguintes chaves, sem nenhum texto adicional:
            - sentiment: "positivo", "negativo" ou "neutro"
            - score: um número entre -1 e 1 (sem aspas)
            - explanation: uma breve explicação da classificação baseada na sua análise

            Formato exato esperado:
            {{
              "sentiment": "positivo|negativo|neutro",
              "score": 0.0,
              "explanation": "Sua explicação aqui"
            }}

            Comentário: "{text}"
            """
        else:
            # Usar prompt padrão
            prompt = f"""
            Analise o sentimento do seguinte comentário e classifique-o como positivo, negativo ou neutro.
            Além disso, forneça uma pontuação de sentimento entre -1 (muito negativo) e 1 (muito positivo).

            IMPORTANTE: Retorne APENAS um objeto JSON válido com as seguintes chaves, sem nenhum texto adicional:
            - sentiment: "positivo", "negativo" ou "neutro"
            - score: um número entre -1 e 1 (sem aspas)
            - explanation: uma breve explicação da classificação

            Formato exato esperado:
            {{
              "sentiment": "positivo|negativo|neutro",
              "score": 0.0,
              "explanation": "Sua explicação aqui"
            }}

            Comentário: "{text}"
            """

        try:
            # Registrar timestamp da requisição
            self.request_timestamps.append(datetime.now())

            response = self.model.generate_content(prompt)
            # Extrair o JSON da resposta
            json_str = response.text.strip()

            # Remover possíveis marcadores de código
            json_str = json_str.replace('```json', '').replace('```', '').strip()

            # Tentar analisar o JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                print(f"Erro ao decodificar JSON: {json_err}")
                print(f"Texto recebido: {json_str}")

                # Tentar corrigir problemas comuns de formatação JSON
                # 1. Tentar extrair apenas a parte que parece JSON
                import re
                json_pattern = r'\{.*\}'
                match = re.search(json_pattern, json_str, re.DOTALL)

                if match:
                    try:
                        corrected_json = match.group(0)
                        result = json.loads(corrected_json)
                        print("JSON corrigido com sucesso usando expressão regular")
                    except:
                        # 2. Fazer uma análise manual para extrair os campos
                        sentiment_match = re.search(r'"sentiment"\s*:\s*"([^"]+)"', json_str)
                        score_match = re.search(r'"score"\s*:\s*([-+]?\d*\.\d+|\d+)', json_str)
                        explanation_match = re.search(r'"explanation"\s*:\s*"([^"]+)"', json_str)

                        sentiment = sentiment_match.group(1) if sentiment_match else "neutro"
                        score = float(score_match.group(1)) if score_match else 0.0
                        explanation = explanation_match.group(1) if explanation_match else "Não foi possível extrair explicação"

                        result = {
                            "sentiment": sentiment,
                            "score": score,
                            "explanation": explanation
                        }
                        print("JSON reconstruído manualmente a partir do texto")
                else:
                    # Se não conseguir extrair, fazer uma análise básica do texto
                    if "positivo" in json_str.lower():
                        sentiment = "positivo"
                        score = 0.7
                    elif "negativo" in json_str.lower():
                        sentiment = "negativo"
                        score = -0.7
                    else:
                        sentiment = "neutro"
                        score = 0.0

                    result = {
                        "sentiment": sentiment,
                        "score": score,
                        "explanation": "Análise baseada em texto não estruturado devido a erro de formatação JSON"
                    }
                    print("Análise baseada em texto não estruturado")

            # Verificar se o resultado tem os campos esperados
            if not all(k in result for k in ["sentiment", "score", "explanation"]):
                missing = [k for k in ["sentiment", "score", "explanation"] if k not in result]
                print(f"Campos ausentes no resultado: {missing}")

                # Adicionar campos ausentes com valores padrão
                if "sentiment" not in result:
                    result["sentiment"] = "neutro"
                if "score" not in result:
                    result["score"] = 0.0
                if "explanation" not in result:
                    result["explanation"] = "Não foi fornecida explicação"

            # Normalizar o campo sentiment para garantir consistência
            if result["sentiment"].lower() in ["positivo", "positive"]:
                result["sentiment"] = "positivo"
            elif result["sentiment"].lower() in ["negativo", "negative"]:
                result["sentiment"] = "negativo"
            else:
                result["sentiment"] = "neutro"

            return result

        except Exception as e:
            print(f"Erro ao analisar sentimento: {e}")
            return {
                "sentiment": "erro",
                "score": 0,
                "explanation": f"Erro na análise: {str(e)}"
            }

    def _apply_rate_limiting(self):
        """
        Aplica controle de taxa para respeitar o limite de 15 requisições por minuto.
        Aguarda se necessário para não exceder o limite.
        """
        if not self.request_timestamps:
            return

        # Verificar se já atingimos o limite de requisições por minuto
        now = datetime.now()
        oldest_allowed_timestamp = now - timedelta(minutes=1)

        # Remover timestamps mais antigos que 1 minuto
        while self.request_timestamps and self.request_timestamps[0] < oldest_allowed_timestamp:
            self.request_timestamps.popleft()

        # Se já atingimos o limite, aguardar
        if len(self.request_timestamps) >= self.rate_limit:
            # Calcular tempo de espera necessário
            oldest_timestamp = self.request_timestamps[0]
            wait_time = (oldest_timestamp + timedelta(minutes=1) - now).total_seconds()

            if wait_time > 0:
                # Mostrar mensagem de espera no Streamlit se disponível
                try:
                    with st.spinner(f"Aguardando {wait_time:.1f} segundos para respeitar o limite de requisições..."):
                        time.sleep(wait_time)
                except:
                    # Fallback se não estiver em contexto Streamlit
                    print(f"Aguardando {wait_time:.1f} segundos para respeitar o limite de requisições...")
                    time.sleep(wait_time)

    def batch_analyze(self, comments_df, text_column='text', batch_size=10, custom_prompt=None):
        """
        Analisa o sentimento de múltiplos comentários em lotes.

        Args:
            comments_df (pd.DataFrame): DataFrame com os comentários
            text_column (str): Nome da coluna que contém o texto dos comentários
            batch_size (int): Tamanho do lote para processamento
            custom_prompt (str, optional): Prompt personalizado para análise

        Returns:
            pd.DataFrame: DataFrame original com colunas adicionais para os resultados da análise
        """
        results = []
        total = len(comments_df)

        # Informar sobre o controle de taxa
        st.info(f"Aplicando controle de taxa: máximo de {self.rate_limit} requisições por minuto para respeitar os limites da API do Gemini.")

        # Criar barra de progresso
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(0, total, batch_size):
            batch = comments_df.iloc[i:min(i+batch_size, total)]
            batch_results = []

            for j, (_, row) in enumerate(batch.iterrows()):
                text = row[text_column]
                current_index = i + j

                # Atualizar status
                status_text.text(f"Processando comentário {current_index + 1}/{total}...")

                # Analisar sentimento (com controle de taxa integrado)
                result = self.analyze_sentiment(text, custom_prompt)
                batch_results.append(result)

                # Atualizar barra de progresso
                progress = (current_index + 1) / total
                progress_bar.progress(progress)

            results.extend(batch_results)
            status_text.text(f"Processados {min(i+batch_size, total)}/{total} comentários")

        # Adicionar resultados ao DataFrame
        comments_df['sentiment'] = [r.get('sentiment', 'erro') for r in results]
        comments_df['score'] = [r.get('score', 0) for r in results]
        comments_df['explanation'] = [r.get('explanation', '') for r in results]

        # Limpar status temporário
        status_text.empty()

        return comments_df
