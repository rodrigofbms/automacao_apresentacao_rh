

import logging

# Oculta mensagens de nível INFO emitidas pelo Matplotlib e seus submódulos
logging.getLogger('matplotlib.category').setLevel(logging.WARNING)
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
# Imports dos Módulos Especializados
from config.settings import (
    BASE_DIR, DATA_INICIO_SQL, DATA_FIM_SQL, 
    DATA_INICIO_ANO_SQL, MES_ANO_EXTENSO
)

from database.connection import obter_conexao_sql
from services.cleanup_service import limpar_arquivos_antigos
from services.pptx_service import gerar_apresentacao_pptx, coletar_imagens_graficos
from services.email_service import enviar_email_com_graficos, enviar_email_status_ti
from services.ai_service import gerar_analise_rh_imagem

# ---------------------------------------------------------
# IMPORTAR AS FUNÇÕES DE GERAÇÃO DOS SEUS SCRIPTS
# ---------------------------------------------------------
from geral.grafico_linha_absenteismo_por_mes import gerar_grafico as geral_linha_absenteismo_por_mes
from geral.grafico_donut_horas_absenteismo import gerar_grafico as geral_donut_horas_absenteismo
from geral.grafico_barra_vertical_horas_absenteismo import gerar_grafico as geral_grafico_barra_vertical_horas_absenteismo

from faltas.grafico_barra_horizontal_por_centro_custo import gerar_grafico as faltas_barra_horizontal_por_centro_custo
from faltas.cards_por_mes import gerar_grafico as faltas_cards_por_mes

from atrasos.grafico_barra_horizontal_por_centro_custo import gerar_grafico as atrasos_grafico_barra_horziontal_por_centro_custo
#from atrasos.grafico_barra_horizontal_por_regional import gerar_grafico as atrasos_grafico_barra_horizontal_por_regional
from atrasos.cards_por_mes import gerar_grafico as atrasos_cards_por_mes

from atestados.cards_por_mes import gerar_grafico as atestados_cards_por_mes
from atestados.grafico_barra_horizontal_por_centro_custo import gerar_grafico as atestados_grafico_barra_horizontal_por_centro_custo
from atestados.grafico_barra_vertical_custo_atestados_por_centro_custo import gerar_grafico as atestados_grafico_barra_vertical_custo_atestados_por_centro_custo
from atestados.grafico_linha_custo_atestados_por_mes import gerar_grafico as atestados_grafico_linha_custo_atestados_por_mes

# Formatter customizado para o CONTEÚDO das linhas do log respeitar o fuso
class FormatterFusoHorario(logging.Formatter):

  def converter_horario(self, timestamp):
    return datetime.fromtimestamp(timestamp, tz=ZoneInfo('America/Bahia'))

  def formatTime(self, record, datefmt=None):
    dt = self.converter_horario(record.created)
    if datefmt:
      return dt.strftime(datefmt)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# Definindo o Fuso Local
fuso_bahia = ZoneInfo('America/Bahia')

# ---------------------------------------------------------
# CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE
# ---------------------------------------------------------

# Criação da pasta de logs se não existir
PASTA_LOGS = BASE_DIR / "logs"
PASTA_LOGS.mkdir(exist_ok=True)

arquivo_log_atual = PASTA_LOGS / f"execucao_{datetime.now(fuso_bahia).strftime('%Y_%m_%d_%H-%M')}.log"

# ---------------------------------------------------------
# CONFIGURAÇÃO GLOBAL DO SISTEMA DE LOGS
# ---------------------------------------------------------

# Aplicação das configurações do Logging
formatter = FormatterFusoHorario('%(asctime)s [%(levelname)s] %(message)s')

# Handler para gravar no Arquivo
file_handler = logging.FileHandler(arquivo_log_atual, encoding='utf-8')
file_handler.setFormatter(formatter)

# Handler para exibir no Terminal/Console
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Configura o Logger raiz
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.handlers = [file_handler, stream_handler]


# ---------------------------------------------------------
# EXECUTAR OS SCRIPTS DE GRÁFICOS PRIMEIRO
# ---------------------------------------------------------
def executar_scripts_graficos(data_inicio_sql, data_fim_sql, data_inicio_ano_sql):
    """
    Roda todos os scripts de gráficos encontrados nas subpastas
    antes de buscar e enviar as imagens.
    """

    logging.info(f"--- Gerando gráficos para o período: {data_inicio_sql} até"f" {data_fim_sql} ---")
        
        # Lista de caminhos dos seus scripts de gráfico
        # Adicione ou ajuste conforme sua estrutura de pastas
    funcoes_graficos = [
        geral_linha_absenteismo_por_mes,
        geral_donut_horas_absenteismo,
        geral_grafico_barra_vertical_horas_absenteismo,
        faltas_barra_horizontal_por_centro_custo,
        faltas_cards_por_mes,
        atrasos_grafico_barra_horziontal_por_centro_custo,
        atrasos_cards_por_mes,
        atestados_grafico_barra_horizontal_por_centro_custo,
        atestados_grafico_barra_vertical_custo_atestados_por_centro_custo,
        atestados_grafico_linha_custo_atestados_por_mes,
        atestados_cards_por_mes,
        # função gerar_grafico() do script do gráfico",
    ]

    
        
    # Criar Conexão Única Com o Banco de Dados
    logging.info("--- Abrindo conexão única com SQL Server ---")

    with obter_conexao_sql() as conexao:
        try:
            for funcao in funcoes_graficos:
                logging.info(f"▶️  Executando o Gráfico: {funcao.__module__}")    
                funcao(conexao, data_inicio_sql, data_fim_sql, data_inicio_ano_sql)
                
            logging.info("--- Geração de gráficos concluída ---\n")
            logging.info("--- Conexão com SQL Server encerrada ---")
        except Exception as e:

            logging.error(f"❌ Erro durante a execução da função: {funcao.__module__}")
            logging.error(f"✉️ Mensagem de erro: {e}")
            logging.info("--- Conexão com SQL Server encerrada ---")
            raise e
            



# ---------------------------------------------------------
# FLUXO PRINCIPAL DE EXECUÇÃO (MÉTODO MAIN)
# ---------------------------------------------------------
if __name__ == "__main__":

    logging.info(f"🚀 Iniciando rotina do relatório mensal de absenteísmo para {MES_ANO_EXTENSO}...")

    # Executa a manutenção do diretório (Remove arquivos com +180 dias)
    lista_diretorios_arquivos =[
        BASE_DIR / "geral" / "graficos",
        BASE_DIR / "faltas" / "graficos",
        BASE_DIR / "atrasos" / "graficos",
        BASE_DIR / "atestados" / "graficos",
        BASE_DIR / "apresentacoes",
        BASE_DIR / "logs"
    ]
    limpar_arquivos_antigos(lista_diretorios_arquivos, dias_retencao=360)

    try:
       
        # Passo 1: Opcional - Rodar scripts para garantir que os gráficos existem
        # (Comente a linha abaixo se preferir rodar os scripts de gráficos manualmente)
        executar_scripts_graficos(DATA_INICIO_SQL, DATA_FIM_SQL, DATA_INICIO_ANO_SQL)

        # Passo 2: Coletar os arquivos de imagem em todas as subpastas
        imagens = coletar_imagens_graficos()
        logging.info(f"Imagens encontradas para {MES_ANO_EXTENSO}: {[img.name for img in imagens]}")

        # Passo 3. Gera a análise com a OpenAI
        texto_analise_ia = gerar_analise_rh_imagem(imagens)

        # Passo 4: Gerar arquivo em PowerPoint contendo as imagens
        arquivo_pptx = gerar_apresentacao_pptx(lista_imagens= imagens, texto_ia= texto_analise_ia)

        # Passo 5: Montar e enviar o e-mail único
        enviar_email_com_graficos(imagens, caminho_pptx=arquivo_pptx)


        # Passo 6: Notificar a TI sobre o Sucesso com o arquivo de log
        enviar_email_status_ti(sucesso=True, arquivo_log=arquivo_log_atual)

        logging.info("🎉 Pipeline executado e finalizado com SUCESSO!")

    except Exception as e:
        mensagem_erro = str(e)
        logging.critical(f"❌ Falha na execução do Pipeline: {mensagem_erro}", exc_info=True)
        # Passo 7: Em caso de falha, motifica a TI sobre a falha anexando o arquivo de log
        try:
            enviar_email_status_ti(sucesso=False, mensagem_erro=mensagem_erro, arquivo_log=arquivo_log_atual)
        except Exception as e:
            logging.error(f"❌ Falha secundária: Não foi possível enviar o e-mail de alerta para a TI: {mensagem_erro}")