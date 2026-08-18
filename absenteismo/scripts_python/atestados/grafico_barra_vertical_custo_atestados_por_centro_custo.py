
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
    pasta_graficos = DIRETORIO_RAIZ / "atestados" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    #Nome do arquivo de saída
    nome_arquivo_saida = pasta_graficos / f"custo_atestados_por_centro_custo_{mes_ano_filtro}.png"


    # Ler a consulta SQL dentro do dicionário SCRIPTS do arquivo queries_absenteismo_geral.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["custo_atestados_por_centro_custo_e_mes"], conexao, params=[data_inicio_sql, data_fim_sql])

    if df.empty:
    
        print(f"⚠️ Nenhum dado encontrado.")
        return
    
    else:
        print(f"✅ Sucesso! {len(df)} registros encontrados.")


        # Defina a lista com o nome exato das colunas que você deseja
        colunas_desejadas = ['CENTRO_CUSTO','VALOR_TOTAL_ATESTADO_FOLHA_R$']

        # Definido o tipo do coluna para tipo string
        df['CENTRO_CUSTO'] = df['CENTRO_CUSTO'].astype(str).str.replace('"', '').str.strip()
        
        # Definido o tipo do coluna para tipo numerico
        df['VALOR_TOTAL_ATESTADO_FOLHA_R$'] = pd.to_numeric(df['VALOR_TOTAL_ATESTADO_FOLHA_R$'], errors='coerce')

        #df_mes_desejado = df[df['MES_ANO'] == '2026-06']

        # Abreviado os nomes dos centro de custo, pois ficam são longos e se sobrepõem no gráfico
        #df_mes_desejado['NOME_CENTRO_CUSTO_ABREVIADO'] = df_mes_desejado['NOME_CENTRO_CUSTO'].apply(abreviar_nome)

        # Seleciona os 10 maiores valores
        df_sorted = df.sort_values(by='VALOR_TOTAL_ATESTADO_FOLHA_R$', ascending=False).head(10)

        # Verifica se há duplicatas na coluna 'NOME_CENTRO_CUSTO_ABREVIADO' após a abreviação
        #print(df_sorted['NOME_CENTRO_CUSTO_ABREVIADO'].duplicated().sum())

        sns.set_theme(style="whitegrid")
        plt.figure(figsize=(14, 8))

        ax = sns.barplot(data=df_sorted,
                        x='CENTRO_CUSTO',
                            y='VALOR_TOTAL_ATESTADO_FOLHA_R$',
                            color=paleta_cores['Atestados'],
                                errorbar=None,
                                order=df_sorted['CENTRO_CUSTO'])  # Mantém a ordem dos centros de custo conforme o DataFrame ordenado

        # Estilização das linhas e bordas
        ax.grid(axis='y', linestyle='--', alpha=0.5) # Linhas de grade suaves apenas na horizontal
        ax.tick_params(colors='#444444', labelsize=11)

        # Calcula o total geral (soma de todas as horas) para usar como base do percentual
        total_horas = df_sorted['VALOR_TOTAL_ATESTADO_FOLHA_R$'].sum()

        # Adiciona o valor no topo de cada barra automaticamente
        for container in ax.containers:
            labels = []
            for v in container:
                altura = v.get_height() # Valor relativo a quatidade de horas da barra
                percentual = (altura / total_horas) * 100 if total_horas > 0 else 0 # Percentual relativo ao total de horas da barra
                altura_formatado = formatar_numero(valor= altura, sufixo= "h")
                percentual_formatado = formatar_numero(valor=percentual, prefixo="(", sufixo="%)")
                texto = f"{altura_formatado}\n{percentual_formatado}"
                labels.append(texto)
            ax.bar_label(container, labels=labels, padding=4, fontsize=10, weight='bold')


        plt.title('Custo dos Atestados | Mês: Junho/2026', fontsize=14, pad=15, weight='bold')
        plt.xlabel('Centro de Custo', fontsize=12, labelpad=10)
        plt.ylabel('Valor Total (R$)', fontsize=12, labelpad=10)

        # Rotacionando os nomes dos centros de custo em 90 graus para não se cruzarem
        plt.xticks(rotation=45, ha='right', fontsize=10)

        # Usamos enumerate para saber exatamente a posição (índice 0, 1, 2...) de cada barra no eixo Y
        #for index, row in enumerate(media_mensal_simples_centro_custo.itertuples()):

        # index indica a posição na linha horizontal (0, 1, 2...)
        # somamos 0.5 ao valor da taxa para o texto flutuar logo acima da barra
        # e colocando abaixo da barra e centralizando usando o 'index' no eixo Y
        #    plt.text(row.TAXA_ABSENTEISMO_PERC + 0.3, index, f"{row.TAXA_ABSENTEISMO_PERC:.2f}%",
        #             va='center', ha='left', weight='bold', color='#d95f02', fontsize=9)

        sns.despine(top=True, right=True, left=True) # Remove as bordas desnecessárias
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