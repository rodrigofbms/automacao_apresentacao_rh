import logging
import pyodbc
from contextlib import contextmanager
from config.settings import SQL_SERVER, SQL_DATABASE, SQL_UID, SQL_PASSWORD

@contextmanager
def obter_conexao_sql():
    """
    Gerenciador de contexto para criar e fechar a conexão com o SQL Server.
    Garante o fechamento mesmo em caso de erro.
    """
    logging.info("--- Conectando ao SQL Server ---")

    # A partir da versão 18 do driver da Microsoft, a opção Encrypt vem ativada por padrão (Encrypt=yes). 
    # Se o servidor SQL não tiver um certificado SSL válido e confiável configurado, o driver corta a conexão TCP no meio da transação.
    # As vezes pode causar erro na conexão por conta disso
    
    string_conexao = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_UID};"
        f"PWD={SQL_PASSWORD};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
    )
    
    conexao = pyodbc.connect(string_conexao)
    try:
        yield conexao
    finally:
        conexao.close()
        logging.info("--- Conexão com SQL Server encerrada ---")