
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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
from faltas.queries_absenteismo_faltas import SCRIPTS_SQL 

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

paleta_cores = {'Faltas': "#D8002F", 'Atestados': '#F28E2B', 'Atrasos': '#EDC948', 'BancoHoras' :'#0EA5E9'}

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


    # Ler a consulta SQL dentro do dicionário SCRIPTS do arquivo queries_absenteismo_faltas.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["faltas_por_mes"], conexao, params=[data_inicio_sql, data_fim_sql])

    # Garantir que o diretório de saída existe
    pasta_graficos = DIRETORIO_RAIZ / "faltas" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    # Nome do arquivo de saída
    nome_arquivo_saida = pasta_graficos / f"cards_faltas_por_mes_2026_06.png"

    # Verificar
    if df.empty:

        print(f"⚠️ Nenhum dado encontrado.")

        return
    
    else:

        print(f"✅ Sucesso! {len(df)} registros encontrados.")

        # Extrai a primeira linha retornada da query
        row = df.iloc[0]

        # Mapeamento dos campos vindos do SQL
        total_horas = row.get("TOTAL_HORAS_FALTA_PONTO", 0)
        custo_estimado = row.get("CUSTO_ESTIMADO_FALTAS_R$", 0)
        horas_descontadas = row.get("TOTAL_HORAS_DESCONTADAS_FOLHA", 0)
        valor_descontado = row.get("VALOR_DESCONTADO_FOLHA_R$", 0)
        mes_ano = str(row.get("MES_ANO", "Mês"))

        # Configuração da figura do Matplotlib
        fig, ax = plt.subplots(figsize=(16, 5), dpi=300)
        fig.patch.set_facecolor("#F4F4F400")  # Cor de fundo
        ax.set_facecolor('#F4F4F4')
        ax.axis('off')

        # Estrutura dos cards: (x, y, largura, altura, título, valor, cor_de_fundo)
        cards = [
            # --- Linha Superior (2 Cards em destaque) ---
            {
                'rect': (0.10, 0.52, 0.38, 0.40),
                'titulo': 'Total de Horas \n de Falta do Ponto',
                'valor': formatar_numero(valor= total_horas,prefixo= "",sufixo= "h"),
                'cor': paleta_cores['Faltas']
            },
            {
                'rect': (0.52, 0.52, 0.38, 0.40),
                'titulo': 'Custo Estimado das Faltas \n (Valor da Hora x Faltas)',
                'valor': formatar_numero(valor= custo_estimado,prefixo=  "R$ ",sufixo= ""),
                'cor': paleta_cores['Faltas']
            },
            # --- Linha Inferior (2 Cards complementares) ---
            {
                'rect': (0.10, 0.08, 0.38, 0.38),
                'titulo': 'Total de Horas Descontadas \n na Folha',
                'valor': formatar_numero(valor= horas_descontadas,prefixo= "",sufixo= "h"),
                'cor': paleta_cores['Faltas']
            },
            {
                'rect': (0.52, 0.08, 0.38, 0.38),
                'titulo': 'Valor Descontado em Folha',
                'valor': formatar_numero(valor= valor_descontado,prefixo= "R$ ",sufixo= ""),
                'cor': paleta_cores['Faltas']
            },
        ]

        for card in cards:
            x, y, w, h = card['rect']

            # Desenha o bloco/card com borda branca refinada
            rect = patches.FancyBboxPatch(
                (x, y), w, h,
                boxstyle="square,pad=0.0",
                facecolor=card['cor'],
                edgecolor='white',
                linewidth=2,
                transform=ax.transAxes
            )
            ax.add_patch(rect)

            # Desenha o título do Card
            ax.text(
                x + w / 2, y + h * 0.70,
                card['titulo'],
                color='white',
                fontsize=16,
                fontweight='normal',
                ha='center',
                va='center',
                transform=ax.transAxes
            )

            # Desenha o valor numérico em destaque
            ax.text(
                x + w / 2, y + h * 0.30,
                card['valor'],
                color='white',
                fontsize=16,
                fontweight='bold',
                ha='center',
                va='center',
                transform=ax.transAxes
            )

        plt.tight_layout()
        assinar_grafico(plt.gcf(), fontsize=12)
        plt.savefig(nome_arquivo_saida, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f"Imagem de cards gerada com sucesso: {nome_arquivo_saida}")



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