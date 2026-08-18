

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
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
DIRETORIO_RAIZ = Path(__file__).resolve().parent.parent

# Adiciona a raiz do projeto ao caminho de busca do Python
if str(DIRETORIO_RAIZ) not in sys.path:
    sys.path.append(str(DIRETORIO_RAIZ))

# Para importar o arquivo com as queries
from atestados.queries_absenteismo_atestados import SCRIPTS_SQL 

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

paleta_cores = {'Faltas': '#D9381E', 'Atestados': '#F28E2B', 'Atrasos': "#DA9500", 'BancoHoras' :'#0EA5E9'}


def gerar_grafico(conexao,
    data_inicio_sql=None,
    data_fim_sql=None,
    data_inicio_ano_sql=None):

    # ---------------------------------------------------------
    # RECEBIMENTO DAS DATAS COMO PARÂMETRO
    # ---------------------------------------------------------

    # Se as datas forem passadas via linha de comando pelo script orquestrador de enviar_email_mensal.py, elas vão ser usadas. 
    # Caso contrário, calcula o mês retrassado automaticamente.
    if data_inicio_sql and data_fim_sql and data_inicio_ano_sql:

        # Converte a string 'YYYY-MM-DD' que vem como parâmetro (data_inicio_sql) em objeto datetime para extrair mês e ano
        data_inicio_sql_obj = datetime.strptime(data_inicio_sql, "%Y-%m-%d")
        mes_ano_filtro = data_inicio_sql_obj.strftime("%Y_%m")  # Ex: '2026_06'
        mes_ano_extenso = f"{MESES_PT[data_inicio_sql_obj.month]}/{data_inicio_sql_obj.year}"  # Ex: 'Junho/2026'

        # Converte a string 'YYYY-MM-DD' que vem como parâmetro (data_inicio_ano_sql) em objeto datetime para extrair mês e ano
        data_inicio_ano_sql_obj = datetime.strptime(data_inicio_ano_sql, "%Y-%m-%d")
        mes_inicio_ano_filtro = data_inicio_ano_sql_obj.strftime("%Y_%m") # Ex: '2026_01'
    else:
        # FALLBACK: Se você rodar este script manualmente sem parâmetros, 
        # ele calcula automaticamente o mês retrassado
        ano = date.today().year
        primeiro_dia_ano_atual = date(ano, 1, 1)
        hoje = date.today()
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_retrassado = primeiro_dia_mes_atual - relativedelta(days=1, months=1)
        primeiro_dia_mes_retrassado = ultimo_dia_mes_retrassado.replace(day=1)

        # Formatações para consulta SQL, filtros e nomes de arquivo
        data_inicio_ano_sql = primeiro_dia_ano_atual.strftime("%Y-%m-%d") # Ex: '2026-01-01'
        data_inicio_sql = primeiro_dia_mes_retrassado.strftime("%Y-%m-%d") # Ex: '2026-06-01'
        data_fim_sql = ultimo_dia_mes_retrassado.strftime("%Y-%m-%d") # Ex: '2026-06-30'
        mes_inicio_ano_filtro = primeiro_dia_ano_atual.strftime("%Y_%m") # Ex: '2026_01'
        mes_ano_filtro = primeiro_dia_mes_retrassado.strftime("%Y_%m") # Ex: '2026_06'
        mes_ano_extenso = f"{MESES_PT[primeiro_dia_mes_retrassado.month]}/{primeiro_dia_mes_retrassado.year}" # Ex: 'Junho/2026'

    # Garantir que o diretório de saída existe
    pasta_graficos = DIRETORIO_RAIZ / "atestados" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    #Nome do arquivo de saída
    nome_arquivo_saida = pasta_graficos / f"custo_atestados_por_mes_{mes_inicio_ano_filtro}-{mes_ano_filtro}.png"


    # 3. Ler a consulta SQL dentro do arquivo scripts.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["custo_atestados_por_mes"], conexao, params=[data_inicio_ano_sql, data_fim_sql])

    if df.empty:

        print(f"⚠️ Nenhum dado encontrado.")
        return
    
    else:
        print(f"✅ Sucesso! {len(df)} registros encontrados.")
        
        # 1. Defina a lista com o nome exato das colunas que você deseja
        colunas_desejadas = ['MES_ANO', 'VALOR_TOTAL_ATESTADO_FOLHA_R$']

        dados = df[colunas_desejadas].copy()

        # Converte para timestamp em pandas
        dados['MES_ANO'] = pd.to_datetime(dados['MES_ANO'], format="%Y-%m")

        # Converte para o tipo numerico
        dados['VALOR_TOTAL_ATESTADO_FOLHA_R$'] = pd.to_numeric(dados['VALOR_TOTAL_ATESTADO_FOLHA_R$'], errors='coerce')

        # Listar o nome de todas as colunas disponíveis no arquivo
        #print(dados.columns.tolist())

        # Agrupar por média simples
        # - Groupby(): Agrupa todas as linhas da tabela que possuem o mesmo valor da coluna 'MES_ANO'
        # - mean(): Calcula a média aritmética simples da coluna 'VALOR_TOTAL_ATESTADO_FOLHA_R$'
        # - reset_index(): Como o agrupamento transforma a coluna MES_ANO no "índice" da tabela,
        #     o reset_index() traz essa coluna de volta como uma coluna comum.
        #     O resultado é um novo DataFrame (mensal_simples) com apenas duas colunas: MES_ANO e VALOR_TOTAL_ATESTADO_FOLHA_R$.
        #media_mensal_simples = dados.groupby('MES_ANO')['VALOR_TOTAL_ATESTADO_FOLHA_R$'].mean().reset_index()


        # Configuração do Ambiente Gráfico
        # - (style="whitegrid"): Define o fundo do gráfico como branco com linhas de grande cinza claro
        # - figsize=(12, 6): Cria a figura (a janela onde o gráfico será desenhado) e define o seu tamanho em polegadas
        sns.set_theme(style="whitegrid")
        fig, ax = plt.subplots(figsize=(16, 6))

        x = dados['MES_ANO']
        y = dados['VALOR_TOTAL_ATESTADO_FOLHA_R$']


        # Estilização das linhas de fundo relativo aos valores do eixo Y (vertical)
        ax.grid(axis='y', linestyle='--', alpha=0.5)

        # Estilização das linhas de fundo relativo aos valores do eixo X (horizontal)
        ax.grid(axis='x', linestyle='-', alpha=0.5)

        # 2. Área preenchida abaixo da linha, na cor padrão dos atestados
        ax.fill_between(x, y, color=paleta_cores['Atestados'], alpha=0.25, zorder=1)


        # Plotagem da Linha Principal
        # - sns.lineplot(...): Comando do Seaborn para desenhar um gráfico de linha
        # - data=mensal_simples: Indica qual DataFrame contém os dados.
        # - x='MES_ANO': Define que o tempo (meses) ficará no eixo horizontal.
        # - y='VALOR_TOTAL_ATESTADO_FOLHA_R$': Define que a média calculada ficará no eixo vertical.
        # - marker='o': Adiciona um marcador circular em cada ponto correspondente a um mês.
        # - linewidth=2.5: Define a espessura da linha que conecta os pontos.
        # - color='#ff7f0e': Define a cor da linha usando um código hexadecimal (neste caso, laranja).
        sns.lineplot(data=dados, x='MES_ANO', y='VALOR_TOTAL_ATESTADO_FOLHA_R$',
                    marker='s', markersize=7, linewidth=2.5, color=paleta_cores['Atestados'], zorder=3,
                        ax=ax, linestyle='-', label='Custo dos Atestados')


        # 4. Identificar o mês de maior custo, para destacar
        idx_pico = y.idxmax()
        x_pico = dados.loc[idx_pico, 'MES_ANO']
        y_pico = dados.loc[idx_pico, 'VALOR_TOTAL_ATESTADO_FOLHA_R$']

        # Halo (efeito de destaque) atrás do ponto de pico
        ax.scatter(x_pico, y_pico, s=500, color=paleta_cores['Atestados'], alpha=0.25, zorder=4)


        # Ponto de pico em destaque, maior que os demais
        ax.scatter(x_pico, y_pico, s=140, color=paleta_cores['Atestados'], edgecolor='white', linewidth=2, zorder=5)
        

        # Customização de Títulos e Eixos
        ax.set_title('Custo dos Atestados por Mês', fontsize=14, pad=25, weight='bold')
        ax.set_xlabel('Ano/Mês', fontsize=12, labelpad=10)
        ax.set_ylabel('Custo (R$)', fontsize=12, labelpad=10)


        # Eixo Y formatado em R$ (padrão brasileiro: milhar com ponto, decimal com vírgula)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, pos: formatar_numero(valor= valor, prefixo="R$ ")))

        # espaço extra no topo para o rótulo do pico não colidir com o título
        ax.set_ylim(0, y.max() * 1.18)  


        sns.despine(left=True, bottom=True) # Remove bordas desnecessárias

        # 5. Adicionar os valores exatos em cima de cada ponto
        for i, row in dados.iterrows():
            valor_formatado = formatar_numero(valor= row['VALOR_TOTAL_ATESTADO_FOLHA_R$'], prefixo="R$ ")
            eh_pico = (i == idx_pico)
            ax.annotate(
                valor_formatado,
                (row['MES_ANO'], row['VALOR_TOTAL_ATESTADO_FOLHA_R$']),
                textcoords="offset points",
                xytext=(0, 22 if eh_pico else 10),
                ha='center',
                weight='bold',
                fontsize=15 if eh_pico else 10,
                color=paleta_cores['Atestados'] if eh_pico else '#000000',
            )
        
        ax.legend_.remove() if ax.legend_ else None
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
    args_inicio_ano = sys.argv[3] if len(sys.argv) >= 4 else None
    
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
        data_fim_sql=args_fim,
        data_inicio_ano_sql=args_inicio_ano
        )
    finally:
        conexao_temp.close()