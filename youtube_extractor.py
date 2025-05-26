"""
Módulo para extrair comentários do YouTube usando a API do YouTube.
"""

import re
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class YouTubeCommentExtractor:
    def __init__(self, api_key):
        """
        Inicializa o extrator de comentários do YouTube.

        Args:
            api_key (str): Chave de API do YouTube
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def extract_video_id(self, url):
        """
        Extrai o ID do vídeo a partir da URL.

        Args:
            url (str): URL do vídeo do YouTube

        Returns:
            str: ID do vídeo ou None se não for encontrado
        """
        # Padrões comuns de URL do YouTube
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/v\/)([\w-]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def get_video_details(self, video_id):
        """
        Obtém detalhes do vídeo como título, canal, etc.

        Args:
            video_id (str): ID do vídeo do YouTube

        Returns:
            dict: Detalhes do vídeo
        """
        try:
            response = self.youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            ).execute()

            if not response['items']:
                return None

            video_info = response['items'][0]
            snippet = video_info['snippet']
            statistics = video_info['statistics']

            return {
                'title': snippet['title'],
                'channel': snippet['channelTitle'],
                'published_at': snippet['publishedAt'],
                'view_count': statistics.get('viewCount', 0),
                'like_count': statistics.get('likeCount', 0),
                'comment_count': statistics.get('commentCount', 0)
            }
        except HttpError as e:
            print(f"Erro ao obter detalhes do vídeo: {e}")
            return None

    def get_comments(self, video_url, max_comments=100, extract_main=True, extract_replies=True):
        """
        Obtém comentários de um vídeo do YouTube.

        Args:
            video_url (str): URL do vídeo do YouTube
            max_comments (int): Número máximo de comentários a serem extraídos
            extract_main (bool): Se True, extrai comentários principais
            extract_replies (bool): Se True, extrai respostas aos comentários

        Returns:
            pd.DataFrame: DataFrame contendo os comentários
            dict: Informações adicionais sobre a extração
        """
        video_id = self.extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Não foi possível extrair o ID do vídeo da URL: {video_url}")

        comments = []
        next_page_token = None
        total_available = 0
        extraction_info = {
            "requested": max_comments,
            "extracted": 0,
            "available": 0,
            "reasons": []
        }

        print(f"Extraindo comentários do vídeo: {video_id}")

        try:
            # Primeiro, verificar quantos comentários o vídeo tem
            video_info = self.youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()

            if video_info['items']:
                stats = video_info['items'][0]['statistics']
                if 'commentCount' in stats:
                    total_available = int(stats['commentCount'])
                    extraction_info["available"] = total_available

                    if total_available == 0:
                        extraction_info["reasons"].append("O vídeo não tem comentários disponíveis.")
                        return pd.DataFrame(comments), extraction_info

                    if total_available < max_comments:
                        extraction_info["reasons"].append(f"O vídeo tem apenas {total_available} comentários disponíveis.")

            # Agora extrair os comentários
            page_count = 0
            empty_response = False

            # Adicionar informações sobre o filtro de tipo de comentário
            if not extract_main and extract_replies:
                extraction_info["reasons"].append("Configurado para extrair apenas respostas aos comentários.")
            elif extract_main and not extract_replies:
                extraction_info["reasons"].append("Configurado para extrair apenas comentários principais.")

            # Verificar se há algum tipo de comentário para extrair
            if not extract_main and not extract_replies:
                extraction_info["reasons"].append("Nenhum tipo de comentário selecionado para extração.")
                return pd.DataFrame(comments), extraction_info

            while len(comments) < max_comments:
                page_count += 1

                # Fazer a requisição para a API do YouTube com parâmetros adicionais
                # Usar textFormat=plainText para garantir que recebemos todos os comentários
                # Usar order=time para garantir que recebemos os comentários em ordem cronológica
                # Usar moderationStatus=published para tentar obter todos os comentários publicados
                try:
                    response = self.youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=min(100, max_comments - len(comments)),
                        pageToken=next_page_token,
                        textFormat='plainText',
                        order='time',
                        moderationStatus='published'
                    ).execute()
                except HttpError as e:
                    # Se falhar com parâmetros adicionais, tentar com parâmetros básicos
                    if 'moderationStatus' in str(e):
                        print("Parâmetro moderationStatus não suportado, usando configuração básica")
                        response = self.youtube.commentThreads().list(
                            part='snippet',
                            videoId=video_id,
                            maxResults=min(100, max_comments - len(comments)),
                            pageToken=next_page_token,
                            textFormat='plainText'
                        ).execute()
                    else:
                        raise

                # Verificar se a resposta contém itens
                if 'items' not in response or len(response['items']) == 0:
                    empty_response = True
                    extraction_info["reasons"].append("A API do YouTube retornou uma página vazia de comentários.")
                    break

                # Extrair os comentários da resposta
                for item in response['items']:
                    try:
                        # Extrair o comentário principal (se configurado para extrair comentários principais)
                        if extract_main:
                            comment = item['snippet']['topLevelComment']['snippet']

                            # Verificar se o comentário tem conteúdo válido
                            if 'textDisplay' not in comment or not comment['textDisplay'].strip():
                                continue

                            comments.append({
                                'author': comment.get('authorDisplayName', 'Anônimo'),
                                'text': comment['textDisplay'],
                                'likes': comment.get('likeCount', 0),
                                'published_at': comment.get('publishedAt', ''),
                                'type': 'principal'
                            })
                        else:
                            # Se não estamos extraindo comentários principais, apenas armazenar a referência
                            comment = item['snippet']['topLevelComment']['snippet']

                        # Verificar se há respostas a este comentário (se configurado para extrair respostas)
                        if extract_replies and item['snippet'].get('totalReplyCount', 0) > 0 and len(comments) < max_comments:
                            try:
                                # Obter as respostas ao comentário
                                replies = self.youtube.comments().list(
                                    part='snippet',
                                    parentId=item['id'],
                                    maxResults=min(100, max_comments - len(comments)),
                                    textFormat='plainText'
                                ).execute()

                                # Adicionar as respostas à lista de comentários
                                if 'items' in replies:
                                    for reply in replies['items']:
                                        try:
                                            reply_snippet = reply['snippet']

                                            # Verificar se a resposta tem conteúdo válido
                                            if 'textDisplay' not in reply_snippet or not reply_snippet['textDisplay'].strip():
                                                continue

                                            comments.append({
                                                'author': reply_snippet.get('authorDisplayName', 'Anônimo'),
                                                'text': reply_snippet['textDisplay'],
                                                'likes': reply_snippet.get('likeCount', 0),
                                                'published_at': reply_snippet.get('publishedAt', ''),
                                                'type': 'resposta',
                                                'parent_author': comment.get('authorDisplayName', 'Anônimo')
                                            })

                                            # Verificar se atingimos o limite de comentários
                                            if len(comments) >= max_comments:
                                                break
                                        except KeyError as e:
                                            print(f"Erro ao processar resposta: {e}")
                                            continue
                            except HttpError as e:
                                print(f"Erro ao obter respostas: {e}")
                    except KeyError as e:
                        print(f"Erro ao processar comentário: {e}")
                        continue

                # Verificar se há mais páginas de comentários
                next_page_token = response.get('nextPageToken')
                if not next_page_token or len(comments) >= max_comments:
                    break

                # Limite de segurança para evitar loops infinitos
                if page_count >= 10:  # Limitar a 10 páginas (até 1000 comentários)
                    extraction_info["reasons"].append("Limite de páginas atingido (10 páginas).")
                    break

            # Atualizar informações de extração
            extraction_info["extracted"] = len(comments)

            if len(comments) < max_comments and not empty_response and total_available > len(comments):
                extraction_info["reasons"].append(
                    "Alguns comentários podem ter sido filtrados pela API do YouTube (spam, removidos pelo autor, etc)."
                )

            # Se não conseguimos extrair todos os comentários, tentar uma abordagem alternativa
            if len(comments) < min(max_comments, total_available) and len(comments) < total_available:
                extraction_info["reasons"].append(
                    "Tentando método alternativo para extrair mais comentários..."
                )

                # Tentar uma abordagem diferente: usar a API de pesquisa para encontrar comentários
                try:
                    # Limpar a lista de comentários para evitar duplicatas
                    comment_ids = set([c.get('id', '') for c in comments])

                    # Tentar extrair comentários usando a API de pesquisa
                    search_response = self.youtube.search().list(
                        part="snippet",
                        channelId=video_info['items'][0]['snippet']['channelId'],
                        maxResults=min(50, max_comments - len(comments)),
                        order="relevance",
                        type="video",
                        videoId=video_id
                    ).execute()

                    if 'items' in search_response:
                        for item in search_response['items']:
                            try:
                                # Verificar se este é um comentário e não outro tipo de resultado
                                if item['id']['kind'] == 'youtube#comment':
                                    comment_id = item['id']['videoId']

                                    # Evitar duplicatas
                                    if comment_id in comment_ids:
                                        continue

                                    comment_ids.add(comment_id)

                                    comments.append({
                                        'author': item['snippet'].get('channelTitle', 'Anônimo'),
                                        'text': item['snippet'].get('description', ''),
                                        'likes': 0,  # Não disponível na API de pesquisa
                                        'published_at': item['snippet'].get('publishedAt', ''),
                                        'type': 'alternativo'
                                    })
                            except (KeyError, TypeError) as e:
                                print(f"Erro ao processar resultado de pesquisa: {e}")
                                continue
                except Exception as e:
                    print(f"Erro ao usar método alternativo: {e}")
                    extraction_info["reasons"].append(f"Método alternativo falhou: {str(e)}")

            # Atualizar o contador de comentários extraídos
            extraction_info["extracted"] = len(comments)

            # Se ainda não conseguimos extrair todos os comentários
            if len(comments) < min(max_comments, total_available):
                extraction_info["reasons"].append(
                    "Não foi possível extrair todos os comentários disponíveis. Isso pode ocorrer devido a limitações da API do YouTube ou porque alguns comentários estão ocultos/filtrados."
                )

                # Adicionar uma explicação mais detalhada
                extraction_info["reasons"].append(
                    "A API do YouTube tem limitações conhecidas na extração de comentários. Alguns comentários podem estar ocultos pelo autor do vídeo, marcados como spam, ou não disponíveis através da API pública."
                )

            # Criar o DataFrame com os comentários extraídos
            df = pd.DataFrame(comments)

            # Adicionar uma coluna para indicar se é um comentário principal ou uma resposta
            if 'type' not in df.columns and not df.empty:
                df['type'] = 'principal'

            return df, extraction_info
        except HttpError as e:
            print(f"Erro ao extrair comentários: {e}")
            extraction_info["reasons"].append(f"Erro na API do YouTube: {str(e)}")
            raise
