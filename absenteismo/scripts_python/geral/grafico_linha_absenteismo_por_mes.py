

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
from geral.queries_absenteismo_geral import SCRIPTS_SQL 

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
    pasta_graficos = DIRETORIO_RAIZ / "geral" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)


    nome_arquivo_saida = pasta_graficos / f"absenteismo_por_mes_{mes_inicio_ano_filtro}-{mes_ano_filtro}.png"


    # Ler a consulta SQL dentro do arquivo scripts.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["absenteismo_geral_por_mes"], conexao, params=[data_inicio_ano_sql, data_fim_sql])

    if df.empty:
       
       print("⚠️ Nenhum dado encontrado.")
       return {}
    
    else:

        print(f"✅ Sucesso! {len(df)} registros encontrados.")

        # Defina a lista com o nome exato das colunas que você deseja
        colunas_desejadas = ['MES_ANO', 'TAXA_ABSENTEISMO_PERC']

        dados = df[colunas_desejadas].copy()

        # -----------------------------------------------------------------------------
        # LIMPEZA E PADRONIZAÇÃO DE COLUNAS
        # -----------------------------------------------------------------------------

        # Converte para timestamp em pandas
        dados['MES_ANO'] = pd.to_datetime(dados['MES_ANO'], format="%Y-%m")

        # Converte para o tipo numerico
        dados['TAXA_ABSENTEISMO_PERC'] = pd.to_numeric(dados['TAXA_ABSENTEISMO_PERC'], errors='coerce')

        # Configuração do Ambiente Gráfico
        # - (style="whitegrid"): Define o fundo do gráfico como branco com linhas de grande cinza claro
        # - figsize=(12, 6): Cria a figura (a janela onde o gráfico será desenhado) e define o seu tamanho em polegadas
        sns.set_theme(style="whitegrid")
        plt.figure(figsize=(14, 6))


        # Plotagem da Linha
        # - sns.lineplot(...): Comando do Seaborn para desenhar um gráfico de linha
        # - data=mensal_simples: Indica qual DataFrame contém os dados.
        # - x='MES_ANO': Define que o tempo (meses) ficará no eixo horizontal.
        # - y='TAXA_ABSENTEISMO_PERC': Define que a média calculada ficará no eixo vertical.
        # - marker='o': Adiciona um marcador circular em cada ponto correspondente a um mês.
        # - linewidth=2.5: Define a espessura da linha que conecta os pontos.
        # - color='#ff7f0e': Define a cor da linha usando um código hexadecimal (neste caso, laranja).
        sns.lineplot(data=dados, x='MES_ANO', y='TAXA_ABSENTEISMO_PERC',
                    marker='s', linewidth=1.5, color='#2563EB',
                        linestyle='-', label='Taxa de Absenteísmo')

        # Customização de Títulos e Eixos
        # - plt.title(...): Adiciona o título principal no topo do gráfico.
        # - fontsize=14: ajusta o tamanho da fonte.
        # - weight='bold': deixa o texto em negrito.
        # - pad=15: adiciona um espaçamento (margem) entre o título e o corpo do gráfico.
        # - plt.xlabel(...) e plt.ylabel(...): Definem os textos de legenda dos eixos X e Y, respectivamente, configurando o tamanho da fonte para 12.
        plt.title('Taxa de Absenteísmo por Mês', fontsize=14, pad=15, weight='bold')
        plt.xlabel('Ano/Mês', fontsize=12, labelpad=10)
        plt.ylabel('Absenteísmo (%)', fontsize=12, labelpad=10)


        sns.despine(left=True, bottom=True) # Remove bordas desnecessárias

        # 4. Adicionar os valores exatos em cima de cada ponto
        # - for i, row in mensal_simples.iterrows(): Passa por cada linha do DataFrame agregado. row representa os dados daquele mês específico.
        # - plt.annotate(...): Função que escreve um texto em uma coordenada específica do gráfico.
        # - f"{row['TAXA_ABSENTEISMO_PERC']:.2f}%": O texto que será escrito. O :.2f formata o número para mostrar exatamente duas casas decimais, seguido pelo símbolo %.
        # - (row['MES_ANO'], row['TAXA_ABSENTEISMO_PERC']): A coordenada exata do gráfico (X e Y) onde o marcador está localizado.
        # - textcoords="offset points", xytext=(0, 10): Diz ao código para não escrever o texto exatamente em cima do ponto
        #     (o que causaria sobreposição), mas sim deslocá-lo 10 pontos para cima (y=10).
        # - ha='center': Alinhamento horizontal centralizado, garantindo que o texto fique perfeitamente equilibrado acima do marcador.
        # - weight='bold', color='#ff7f0e': Coloca o texto em negrito e na mesma cor laranja da linha.
        # ":_" o formatador dos dois pontos é um formatador de número para colocar ponto nas casas das dezenas (1000000 fica 1.000.000)
        # e o underline deve essa separação por "_", ou seja, ao invés de usar o "." usa o "_", se não fosse usado iria ser usado o "." como padrão
        for i, row in dados.iterrows():
            plt.annotate(formatar_numero(valor= row['TAXA_ABSENTEISMO_PERC'], sufixo="%"),
                        (row['MES_ANO'], row['TAXA_ABSENTEISMO_PERC']),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', weight='bold', color='#000000')


        # - plt.tight_layout(): Ajusta automaticamente os elementos do gráfico (título, rótulos, eixos) para que nada fique cortado ou espremido nas bordas da imagem final.
        plt.tight_layout()

        # 2. Reserva espaço na margem inferior (bottom=0.20 eleva o gráfico e deixa 20% de espaço livre no rodapé)
        plt.subplots_adjust(bottom=0.20)

        # Coloca a logo e a marca d'água no gráfico, usando a função assinar_grafico() do arquivo assinatura_grafico.py
        # OBS: Sempre colocar depois do plt.tight_layout() e antes do plt.savefig(),
        # senão o tight_layout pode reorganizar e deslocar os elementos que você acabou de posicionar.
        assinar_grafico(plt.gcf())

        plt.savefig(nome_arquivo_saida, dpi=300)
        plt.close()


        """
        # -----------------------------------------------------------------------------
        # EXTRAÇÃO AUTOMÁTICA DOS KPIS PARA A IA
        # -----------------------------------------------------------------------------
        # Pega o último mês (mês atual de referência)
        taxa_mes_atual = float(dados.iloc[-1]['TAXA_ABSENTEISMO_PERC'])
        mes_atual_nome = MESES_PT[dados.iloc[-1]['MES_ANO'].month]

        # Verifica se há ao menos 2 meses no DataFrame para calcular a variação MoM
        if len(dados) >= 2:
            taxa_mes_anterior = float(dados.iloc[-2]['TAXA_ABSENTEISMO_PERC'])
            variacao_mom = round(taxa_mes_atual - taxa_mes_anterior, 2)
            sinal = "+" if variacao_mom > 0 else ""
            variacao_str = f"{sinal}{variacao_mom} p.p."
        else:
            taxa_mes_anterior = None
            variacao_str = "N/A"

        # Média do ano e pico de absenteísmo
        media_ano = round(float(dados['TAXA_ABSENTEISMO_PERC'].mean()), 2)
        pico_linha = dados.loc[dados['TAXA_ABSENTEISMO_PERC'].idxmax()]
        pico_mes = f"{MESES_PT[pico_linha['MES_ANO'].month]} ({pico_linha['TAXA_ABSENTEISMO_PERC']:.2f}%)"

        # Cria dicionário formatado com todo o histórico
        historico_mensal = {
            row['MES_ANO'].strftime("%Y-%m"): f"{row['TAXA_ABSENTEISMO_PERC']:.2f}%" 
            for _, row in dados.iterrows()
        }

        resumo_kpis = {
            "absenteismo_mes_atual": f"{taxa_mes_atual:.2f}%",
            "variacao_mes_anterior": variacao_str,
            "media_acumulada_ano": f"{media_ano:.2f}%",
            "pico_absenteismo_ano": pico_mes,
            "historico_evolucao_mensal": historico_mensal
        }

        return resumo_kpis
        """


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