# services/ai_service.py
import os
import logging
from pathlib import Path
import base64
from openai import OpenAI
from config.settings import MES_ANO_EXTENSO

# A chave OPENAI_API_KEY deve estar no seu arquivo .env
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def gerar_analise_rh_texto(dados_resumo: dict) -> str:
    """
    Envia os dados consolidados do mês para a OpenAI e gera um parecer sintético.
    
    :param dados_resumo: Dicionário contendo os indicadores principais (KPIs, CCs, Custo).
    :return: Texto analítico formatado para uso no slide.
    """

    logging.info(f"🤖 Solicitando análise executiva de IA para {MES_ANO_EXTENSO}...")

    system_prompt = (
        "Você é um Especialista Senior em Peolpe Analytics e consultor executivo focado em Recursos Humanos. "
        "Sua tarefa é analisar os indicadores mensais de absenteísmo fornecidos "
        "e gerar um resumo executivo objetivo para a diretoria.\n\n"
        "Diretrizes de resposta:\n"
        "1. Escreva de 3 a 4 marcadores (bullet points) no máximo.\n"
        "2. Destaque os pontos mais críticos (maiores impactos financeiros ou setores atípicos).\n"
        "3. Mantenha um tom profissional, direto e sem introduções ou saudações.\n"
        "4. Não use marcadores complexos em Markdown, apenas hífens ('- ') para os tópicos."
    )

    user_prompt = f"""
    Análise do Fechamento de {MES_ANO_EXTENSO}:
    
    - Horas Totais de Absenteísmo: {dados_resumo.get('horas_totais', 'N/A')}h
    - Variação em relação ao mês anterior: {dados_resumo.get('variacao_percentual', 'N/A')}%
    - Principais Motivos: {dados_resumo.get('principais_motivos', 'N/A')}
    - Top 3 Centros de Custo mais impactados: {dados_resumo.get('top_centros_custo', 'N/A')}
    - Custo Total Estimado de Atestados: R$ {dados_resumo.get('custo_atestados', 'N/A')}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # ou "gpt-4o-mini" para menor custo/tempo de resposta
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Baixa variação para respostas mais consistentes
            max_tokens=400
        )

        analise_texto = response.choices[0].message.content.strip()
        logging.info("✅ Análise da IA gerada com sucesso.")
        return analise_texto

    except Exception as e:
        logging.error(f"❌ Erro ao consultar API da OpenAI: {e}")
        # Retorna um texto fallback para não quebrar o pipeline
        return (
            "- Análise automatizada indisponível temporariamente devido a uma falha na API.\n"
            "- Favor consultar os gráficos individuais nos próximos slides para detalhes."
        )



def codificar_imagem_base64(caminho_imagem: Path) -> str:
    """Lê um arquivo de imagem PNG local e converte para Base64."""
    with open(caminho_imagem, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def gerar_analise_rh_imagem(lista_caminhos_imagens: list) -> str:
    """
    Recebe uma lista com os caminhos dos gráficos gerados em PNG,
    codifica todos em Base64 e envia para o GPT-4o analisar visualmente.
    """
    if not lista_caminhos_imagens:
        logging.warning("⚠️ Nenhuma imagem fornecida para o serviço de visão.")
        return "- Nenhuma imagem disponível para análise executiva."
    
    else:

        # Prompt de instrução para análise multimodal
        prompt_texto = """
        Você é um Consultor Executivo Sênior de RH e especialista em People Analytics.

        Análise os gráficos em anexo contendo o painel de indicadores de RH (absenteísmo, custos com atestados, distribuição por centro de custo, faltas vs atestados vs atrasos, etc.).

        Instruções para o parecer executivo:
        1. Faça a leitura visual dos eixos, dados numéricos e tendências demonstradas nas imagens.
        2. Correlacione as causas e efeitos entre os diferentes gráficos (ex: conecte o aumento de absenteísmo aos setores e aos centro de custos e as suas possíveis causas evidenciadas nas imagens).
        3. Apresente de 3 a 4 pontos de atenção/alerta críticos para a diretoria.
        4. Finalize com 2 recomendações estratégicas acionáveis para o RH podendo ser melhorias a serem implementadas ou atitudes que pode ser tomadas agora.
        5. Responda em estilo executivo focado, utilizando marcadores (bullet points).
        6. Não use marcadores complexos em Markdown, apenas hífens ('- ') para os tópicos.
        6. Mantenha um tom profissional, direto e sem introduções ou saudações.
        """

        # Estrutura inicial da mensagem com a instrução de texto
        conteudo_multimodal = [
            {"type": "text", "text": prompt_texto}
        ]

        # Codifica e insere cada um dos 11 gráficos no payload da chamada
        for idx, caminho in enumerate(lista_caminhos_imagens, 1):
            path_img = Path(caminho)
            if path_img.exists():
                base64_img = codificar_imagem_base64(path_img)
                conteudo_multimodal.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_img}",
                        "detail": "high"  # Permite ao modelo ler rótulos, legendas e números com alta precisão
                    }
                })
                logging.info(f"📸 Grafico {idx} codificado para análise: {path_img.name}")
            else:
                logging.warning(f"⚠️ Imagem não encontrada no caminho: {path_img}")

        # Envio para o modelo GPT-4o
        try:
            client = OpenAI() # Assume OPENAI_API_KEY configurada no .env

            logging.info("🤖 Enviando painel de gráficos para análise multimodal do GPT-4o...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": conteudo_multimodal
                    }
                ],
                max_tokens=850,
                temperature=0.3
            )

            resposta_analise_ia = response.choices[0].message.content.strip()
            logging.info("✅ Análise executiva gerada com sucesso pela OpenAI Vision.")
            return resposta_analise_ia

        except Exception as e:
            logging.error(f"❌ Erro na chamada multimodal com a OpenAI: {e}")
            return "- Falha na análise visual dos gráficos."