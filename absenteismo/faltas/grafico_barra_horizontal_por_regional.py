
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import pyodbc as pyodbc
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# ---------------------------------------------------------
# CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE
# ---------------------------------------------------------

# Path(__file__).resolve()        = caminho completo até grafico_linha_absenteismo_por_mes.py
# .parent                         = pasta 'geral/'
# .parent.parent                  = pasta raiz 'Scripts_python/'
DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent.parent

# Adiciona a raiz do projeto ao caminho de busca do Python
if str(DIRETORIO_RAIZ) not in sys.path:
    sys.path.append(str(DIRETORIO_RAIZ))

# Para importar o arquivo com as queries
from absenteismo.faltas.queries_absenteismo_faltas import SCRIPTS_SQL 

# Para importar o arquivo que criar a assinatura e marca d'água no gráfico
from utils.assinatura_grafico import assinar_grafico 

# Para importar a função que converter os valores para o formato PT-BR com prefixo (R$ 1.000,00) e sufixo (1.000,00h)
from utils.formatar_numero import formatar_numero

# ---------------------------------------------------------
#  DICIONÁRIO DE TRADUÇÃO DE MESES PARA PORTUGUÊS
# ---------------------------------------------------------
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def gerar_grafico(conexao, data_inicio_sql=None, data_fim_sql=None, data_inicio_ano_sql=None):

    # ---------------------------------------------------------
    # RECEBIMENTO DAS DATAS COMO PARÂMETRO
    # ---------------------------------------------------------

    # Se as datas forem passadas via linha de comando pelo script orquestrador de enviar_email_mensal.py, elas vão ser usadas. 
    # Caso contrário, calcula o mês retrassado automaticamente.
    if data_inicio_sql and data_fim_sql:

        # Converte a string 'YYYY-MM-DD' que vem como parâmetro (data_inicio_sql) em objeto datetime para extrair mês e ano
        data_inicio_sql_obj = datetime.strptime(data_inicio_sql, "%Y-%m-%d")
        mes_ano_filtro = data_inicio_sql_obj.strftime("%Y_%m")  # Ex: '2026_06'
        mes_ano_extenso = f"{MESES_PT[data_inicio_sql_obj.month]}/{data_inicio_sql_obj.year}"  # Ex: 'Junho/2026'

    else:
        # FALLBACK: Se você rodar este script manualmente sem parâmetros, 
        # ele calcula automaticamente o mês retrassado
        hoje = date.today()
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_retrassado = primeiro_dia_mes_atual - relativedelta(days=1, months=1)
        primeiro_dia_mes_retrassado = ultimo_dia_mes_retrassado.replace(day=1)

        # Formatações para consulta SQL, filtros e nomes de arquivo
        data_inicio_sql = primeiro_dia_mes_retrassado.strftime("%Y-%m-%d") # Ex: '2026-06-01'
        data_fim_sql = ultimo_dia_mes_retrassado.strftime("%Y-%m-%d") # Ex: '2026-06-30'
        mes_ano_filtro = primeiro_dia_mes_retrassado.strftime("%Y_%m") # Ex: '2026_06'
        mes_ano_extenso = f"{MESES_PT[primeiro_dia_mes_retrassado.month]}/{primeiro_dia_mes_retrassado.year}" # Ex: 'Junho/2026'

    # Garantir que o diretório de saída existe
    pasta_graficos = DIRETORIO_RAIZ / "absenteismo" / "faltas" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    # Nome do arquivo de saída
    nome_arquivo_saida = pasta_graficos / f"faltas_absenteismo_por_regional_{mes_ano_filtro}.png"


    # Ler a consulta SQL dentro do dicionário SCRIPTS do arquivo queries_absenteismo_faltas.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["faltas_por_regional"], conexao, params=[data_inicio_sql, data_fim_sql])

    
    if df.empty:

        print(f"⚠️ Nenhum dado encontrado.")

    else:

        print(f"✅ Sucesso! {len(df)} registros encontrados.")


        # -----------------------------------------------------------------------------
        # PARÂMETROS DE FILTRO
        # -----------------------------------------------------------------------------
        #mes_desejado = '2026-06'

        colunas_desejadas = ['MES_ANO', 'REGIONAL', 'TOTAL_HORAS_FALTA_PONTO']

        paleta_cores = {'Faltas': '#D9381E', 'Atestados': '#F28E2B', 'Atrasos': '#EDC948', 'BancoHoras' :'#0EA5E9'}

        df_colunas_desejadas = df[colunas_desejadas].copy()

        # -----------------------------------------------------------------------------
        # LIMPEZA E PADRONIZAÇÃO DE COLUNAS
        # -----------------------------------------------------------------------------
        # Remove aspas extras ou espaços nos nomes das colunas
        df_colunas_desejadas.columns = df_colunas_desejadas.columns.str.replace('"', '').str.strip()

        # Converte para timestamp em pandas
        df_colunas_desejadas['MES_ANO'] = pd.to_datetime(df_colunas_desejadas['MES_ANO'], format="%Y-%m")

        # Converte para String
        df_colunas_desejadas['REGIONAL'] = df_colunas_desejadas['REGIONAL'].astype(str)

        # Converte para o tipo numerico
        df_colunas_desejadas['TOTAL_HORAS_FALTA_PONTO'] = pd.to_numeric(df_colunas_desejadas['TOTAL_HORAS_FALTA_PONTO'], errors='coerce')

        # -----------------------------------------------------------------------------
        # 2. Filtrar e Ordenar
        # -----------------------------------------------------------------------------
        
        #df_filtrado = df_colunas_desejadas[(df_colunas_desejadas['MES_ANO'] == mes_ano_extenso)].copy()

        # Ordena pelo maior volume de horas e seleciona os Top N
        df_ranking = df_colunas_desejadas.sort_values(by='TOTAL_HORAS_FALTA_PONTO', ascending=False)

        # -----------------------------------------------------------------------------
        # 3. Construção do Gráfico
        # -----------------------------------------------------------------------------
        sns.set_theme(style="whitegrid")
        plt.figure(figsize=(10, 5))

        COR_GRAFICO = paleta_cores['Faltas']  # Cor do Gráfico

        # Define o tipo do gráfico 'barplot' , os dados, os eixos X e Y e cor da barra/linha
        ax = sns.barplot(
            data=df_ranking,
            x='TOTAL_HORAS_FALTA_PONTO',
            y='REGIONAL',
            color=COR_GRAFICO
        )

        # Adiciona uma linha em x=0 para separar claramente positivos e negativos
        #ax.axvline(0, color='black', linewidth=1, linestyle='-')

        # Calcula o total geral (soma de todas as horas) para usar como base do percentual
        total_horas = df_colunas_desejadas['TOTAL_HORAS_FALTA_PONTO'].sum()

        # Adiciona o valor no topo de cada barra automaticamente
        for container in ax.containers:
            labels = []
            for v in container:
                largura = v.get_width() # Valor relativo a quatidade de horas da barra no horizontal
                percentual = (largura / total_horas) * 100 if total_horas > 0 else 0 # Percentual relativo ao total de horas da barra
                largura_formatado = formatar_numero(valor= largura, sufixo="h")
                percentual_formatado = formatar_numero(valor= percentual, prefixo="(", sufixo="%)")
                texto = f"{largura_formatado} {percentual_formatado}"
                labels.append(texto)
            ax.bar_label(container, labels=labels, padding=4, fontsize=10, weight='bold', color='#333333')


        # Adiciona rótulos de valores e ocorrências na ponta da barra
        #for container in ax.containers:
        #    labels = [
        #        f"{val:_.2f}h".replace('.', ',').replace('_', '.')
        #        for val in df_ranking['TOTAL_HORAS_FALTA_PONTO']
        #    ]
        #    ax.bar_label(container, labels=labels, padding=5, fontsize=9, weight='bold', color='#333333')

        # Estilização do Gráfico
        plt.title(f'Top 5 Faltas por Regional | Mês: {mes_ano_extenso}',
                fontsize=12, pad=15, weight='bold')
        plt.xlabel('Total de Horas', fontsize=10, labelpad=10)
        plt.ylabel('Regional', fontsize=10, labelpad=10)

        # Ajuste dos limites do Eixo X com base nos valores máximo e mínimo (margem visual para ambos os lados)
        min_val = df_ranking['TOTAL_HORAS_FALTA_PONTO'].min()
        max_val = df_ranking['TOTAL_HORAS_FALTA_PONTO'].max()

        # Define o limite considerando folga à esquerda e à direita para dar margem para os
        # valores positivos e negativos usando o if ternário
        limite_esq = min_val * 1.25 if min_val < 0 else 0
        limite_dir = max_val * 1.25 if max_val > 0 else 0

        plt.xlim(limite_esq, limite_dir)

        # Dica para dar margem visual à direita
        #limite_max = df_ranking['TOTAL_SALDO_ATUAL_BANCO'].max() * 1.3
        #plt.xlim(0, limite_max)

        sns.despine()
        plt.tight_layout()

        # Reserva espaço na margem inferior (bottom=0.20 eleva o gráfico e deixa 20% de espaço livre no rodapé)
        plt.subplots_adjust(bottom=0.20)

        # Coloca a logo e a marca d'água no gráfico, usando a função assinar_grafico() do arquivo assinatura_grafico.py
        # OBS: Sempre colocar depois do plt.tight_layout() e antes do plt.savefig(),
        # senão o tight_layout pode reorganizar e deslocar os elementos que você acabou de posicionar.
        assinar_grafico(plt.gcf())

        plt.savefig(nome_arquivo_saida, dpi=300)
        plt.close()
        #plt.show()


# ---------------------------------------------------------
# EXECUÇÃO INDIVIDUAL (STANDALONE/FALLBACK)
# ---------------------------------------------------------
if __name__ == "__main__":

    load_dotenv(DIRETORIO_RAIZ / ".env")
  
  # Permite testar este script diretamente pelo terminal sem ser chamado para execução
    SQL_SERVER = os.environ["SQL_SERVER"]
    SQL_DATABASE = os.environ["SQL_DATABASE"]
    SQL_UID = os.environ["SQL_UID"]
    SQL_PASSWORD = os.environ["SQL_PASSWORD"]

    # Recebe argumentos via sys.argv se existirem
    args_inicio = sys.argv[1] if len(sys.argv) >= 4 else None
    args_fim = sys.argv[2] if len(sys.argv) >= 4 else None

    # Cria uma conexão temporária apenas para este teste
    conexao_temp = pyodbc.connect(
      f"DRIVER={{ODBC Driver 18 for SQL Server}};"
      f"SERVER={SQL_SERVER};"
      f"DATABASE={SQL_DATABASE};"
      f"UID={SQL_UID};"
      f"PWD={SQL_PASSWORD};"
      "TrustServerCertificate=yes;"
    )

    try:
      gerar_grafico(
        conexao=conexao_temp,
        data_inicio_sql=args_inicio,
        data_fim_sql=args_fim
        )
    finally:
        conexao_temp.close()