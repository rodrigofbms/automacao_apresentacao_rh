

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
import math
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
from absenteismo.geral.queries_absenteismo_geral import SCRIPTS_SQL 

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

paleta_cores = {'Faltas': '#D9381E', 'Atestados': '#F28E2B', 'Atrasos': "#DA9500"}

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
    pasta_graficos = DIRETORIO_RAIZ / "absenteismo" / "geral" / "graficos"
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    #Nome do arquivo de saída
    nome_arquivo_saida = pasta_graficos / f"donut_tipo_horas_absenteismo_por_mes_{mes_ano_filtro}.png"


    # Ler a consulta SQL dentro do dicionário SCRIPTS do arquivo queries_absenteismo_geral.py diretamente para um DataFrame do Pandas
    df = pd.read_sql(SCRIPTS_SQL["absenteismo_geral_por_mes"], conexao, params=[data_inicio_sql, data_fim_sql])

    # Verifica se a consulta retornou valores, se não ele retorna um aviso
    if df.empty:
       
       print(f"⚠️ Nenhum dado encontrado.")
       return
    
    else:

        print(f"✅ Sucesso! {len(df)} registros encontrados.")

        # Defina a lista com o nome exato das colunas que você deseja
        # ATENÇÃO: confira se o nome da coluna de Afastamento bate com o seu banco
        colunas_desejadas = ['TOTAL_HORAS_FALTAS', 'TOTAL_HORAS_ATRASOS', 'TOTAL_HORAS_ATESTADOS']

        # -----------------------------------------------------------------------------
        # LIMPEZA E PADRONIZAÇÃO DE COLUNAS
        # -----------------------------------------------------------------------------

        # Converte para timestamp em pandas
        df['MES_ANO'] = pd.to_datetime(df['MES_ANO'], format="%Y-%m")

        # Converte para o tipo numerico
        df['TOTAL_HORAS_FALTAS'] = pd.to_numeric(df['TOTAL_HORAS_FALTAS'], errors='coerce')
        df['TOTAL_HORAS_ATRASOS'] = pd.to_numeric(df['TOTAL_HORAS_ATRASOS'], errors='coerce')
        df['TOTAL_HORAS_ATESTADOS'] = pd.to_numeric(df['TOTAL_HORAS_ATESTADOS'], errors='coerce')

        #df_mes_desejado = df[df['MES_ANO'] == '2026-06']

        # 'Derreter' o DataFrame (Wide -> Long)
        df_longo = pd.melt(
            df,
            id_vars=['MES_ANO'],
            value_vars=colunas_desejadas,
            var_name='TIPO_HORAS',
            value_name='HORAS'
        )

        # Renomeando para ficar compreensível
        df_longo['TIPO_HORAS'] = df_longo['TIPO_HORAS'].map({
            'TOTAL_HORAS_FALTAS': 'Faltas',
            'TOTAL_HORAS_ATESTADOS': 'Atestados',
            'TOTAL_HORAS_ATRASOS': 'Atrasos'
        })

        # Agrupa para ter um valor único por categoria (o melt pode gerar 1 linha por regional/centro de custo)
        # A ordem aqui é a que aparecerá no gráfico, então definimos manualmente com reindex
        ordem_categorias = ['Faltas', 'Atestados', 'Atrasos']
        df_donut = (
            df_longo.groupby('TIPO_HORAS')['HORAS'].sum()
            .reindex(ordem_categorias) # O reindex só garante que a ordem das categorias seja sempre a mesma que você quer, e não a ordem alfabética que o groupby daria.
            .reset_index()
        )

        cores_ordenadas = [paleta_cores[tipo] for tipo in df_donut['TIPO_HORAS']]

        total_horas = df_donut['HORAS'].sum()

        sns.set_theme(style="white")
        fig, ax = plt.subplots(figsize=(11, 7))

        # --- GRÁFICO DE ROSCA (DONUT) ---
        # A variável wedges guarda cada "fatia" desenhada como um objeto — é isso que usamos no próximo passo pra saber onde cada fatia está.
        wedges, _ = ax.pie(
            df_donut['HORAS'],
            colors=cores_ordenadas,

            # startangle=90 faz a primeira fatia começar no topo (12h no relógio)
            startangle=90,

            # counterclock=False faz as fatias seguirem no sentido horário.
            counterclock=False,

            # diz "pinte só os últimos 38% desse raio, de fora pra dentro" — ou seja, deixa os 62% do meio vazios (branco).
            wedgeprops={'width': 0.38, 'edgecolor': 'white', 'linewidth': 3},
            radius=1.0
        )



        # Rótulo de percentual dentro de cada fatia (posicionado no meio do "anel")
        # O '_' é uma convenção do Python (não é sintaxe especial) que significa "esse valor eu recebo mas não vou usar". 
        # Como a gente nunca usa o índice numérico da linha — só quer os dados de dentro dela (row['TIPO_HORAS'], row['HORAS'])
        #  — a gente escreve '_' no lugar do nome pra deixar claro pra quem lê o código: "esse aqui pode ignorar".

        # EXPLICANDO A LÓGICA DO ZIP E DO ITERROWS:
        # 1. df_donut.iterrows() gera uma sequência de tuplas: (0, linha0), (1, linha1), (2, linha2)...
        # 2. wedges é uma lista de objetos: [fatia0, fatia1, fatia2...]
        # 3. zip(wedges, df_donut.iterrows()) casa item a item as duas sequências, gerando: (fatia0, (0, linha0)), (fatia1, (1, linha1)), (fatia2, (2, linha2))...

        # Repara: cada item do zip agora é uma tupla de 2 posições, mas a segunda posição é ela mesma outra tupla de 2 posições.

        # 4. Por isso no for, a variável tem essa "forma aninhada": for wedge, (_, row) in zip(...):
        # - wedge pega a primeira posição (a fatia do gráfico)
        # - (_, row) desempacota a segunda posição, que é a tupla (indice, linha) vinda do iterrows() — e aqui de novo a gente ignora o índice e só guarda row.

        # No fim das contas, o objetivo do zip é simples: "para a fatia 0 do gráfico, me dá também a linha 0 dos dados; 
        # para a fatia 1, a linha 1; e assim por diante" — porque precisamos saber, ao mesmo tempo, 
        # o ângulo da fatia (que vem de wedge) e o valor/nome da categoria (que vem de row) pra escrever o texto certo no lugar certo.
        for wedge, (_, row) in zip(wedges, df_donut.iterrows()):

            # Cada wedge sabe seu ângulo de início (theta1) e fim (theta2). Ex: a fatia "Faltas" pode ir de 90° a 265°.
            ang = (wedge.theta2 + wedge.theta1) / 2

            # raio_texto = 1 - 0.38/2 calcula a distância do centro até o meio do anel (não a borda de fora, nem a de dentro — o meio da faixa colorida). 
            # Como o anel vai de 0.62 até 1.0 (lembra do width=0.38?), o meio dele é 1 - 0.38/2 = 0.81
            raio_texto = 1 - 0.38 / 2  

            # cos(ang) e sin(ang) são só matemática de círculo: dado um ângulo e uma distância do centro, eles te dão as coordenadas x, y exatas daquele ponto. 
            # É a mesma lógica de "ponteiro de relógio apontando numa direção".
            x = raio_texto * math.cos(math.radians(ang))
            y = raio_texto * math.sin(math.radians(ang))
            pct = row['HORAS'] / total_horas * 100
            ax.text(x, y, formatar_numero(valor= pct, sufixo="%"), ha='center', va='center',
                    fontsize=13, weight='bold', color='white')

        # --- TEXTO CENTRAL COM O TOTAL ---
        # Como o miolo do gráfico ficou vazio (por causa do width=0.38), o ponto (0, 0) é literalmente o centro do círculo. 
        # Colocamos o número um pouquinho acima do centro (y=0.08) e a palavra "horas" um pouco abaixo (y=-0.12), pra ficarem empilhados visualmente.
        ax.text(0, 0.08, formatar_numero(valor= total_horas, sufixo="h"),
                ha='center', va='center', fontsize=26, weight='bold', color='#222222')
        ax.text(0, -0.12, "horas", ha='center', va='center', fontsize=18, weight='bold', color='#222222')

        ax.set(aspect="equal")
        ax.axis('off')

        # --- LEGENDA LATERAL CUSTOMIZADA ---
        # Posições verticais para cada item da legenda (em coordenadas do eixo, de cima pra baixo)
        y_inicial = 0.70
        espacamento = 0.18

        # Diferente do ax.text() (que usa coordenadas do gráfico, tipo -1 a 1), o fig.text() usa coordenadas da figura inteira, 
        # de 0 a 1 tanto na horizontal quanto na vertical (0,0 = canto inferior esquerdo; 1,1 = canto superior direito).

        # x=0.72 é fixo pra todos os itens — é a coluna onde o quadradinho colorido fica.

        # x=0.745 é a coluna do texto, um pouco à direita do quadrado.

        # O for percorre as 4 categorias e vai descendo (y = y_inicial - i * espacamento) — a cada categoria, desce um pouco mais na tela.

        # Dentro de cada categoria, tem 3 linhas de texto empilhadas (nome, valor, percentual), 
        # por isso o y + 0.045 e y - 0.045 — pra separar essas 3 linhas verticalmente sem se sobrepor.

        # O "█" é só um caractere de bloco cheio usado como se fosse um quadrado colorido — um "gambiarra" simples pra não precisar desenhar um retângulo de verdade.

        for i, (_, row) in enumerate(df_donut.iterrows()):
            y = y_inicial - i * espacamento
            cor = paleta_cores[row['TIPO_HORAS']]
            pct = row['HORAS'] / total_horas * 100
            pct_formatado = formatar_numero(valor= pct, prefixo="(" ,sufixo="%)")
            valor_formatado = formatar_numero(valor= row['HORAS'], sufixo=" Horas")

            # Barrinha colorida vertical (usando fig.add_axes seria mais preciso, aqui usamos anotação simples)
            fig.text(0.72, y, "█", fontsize=28, color=cor, va='center', ha='left')
            fig.text(0.755, y + 0.045, row['TIPO_HORAS'], fontsize=17,weight='bold', color='#333333', va='center', ha='left')
            fig.text(0.755, y, valor_formatado, fontsize=15, color='#111111', va='center', ha='left')
            fig.text(0.755, y - 0.045, pct_formatado, fontsize=15, color='#333333', va='center', ha='left')

        plt.subplots_adjust(left=0.02, right=0.70)

        # 2. Reserva espaço na margem inferior (bottom=0.15 eleva o gráfico e deixa 15% de espaço livre no rodapé)
        plt.subplots_adjust(bottom=0.15)

        # Coloca a logo e a marca d'água no gráfico, usando a função assinar_grafico() do arquivo assinatura_grafico.py
        # OBS: Sempre colocar depois do plt.tight_layout() e antes do plt.savefig(),
        # senão o tight_layout pode reorganizar e deslocar os elementos que você acabou de posicionar.
        assinar_grafico(plt.gcf())

        plt.savefig(nome_arquivo_saida, dpi=300, bbox_inches='tight')
        plt.close()
        #plt.show()


# ---------------------------------------------------------
# EXECUÇÃO INDIVIDUAL (STANDALONE/FALLBACK)
# ---------------------------------------------------------
if __name__ == "__main__":

    # Carrega as variáveis de ambiente do arquivo Scripts_python/.env
    load_dotenv(DIRETORIO_RAIZ / ".env")
  
  
    # Permite testar este script diretamente pelo terminal sem ser chamado para execução
    SQL_SERVER = os.environ["SQL_SERVER"]
    SQL_DATABASE = os.environ["SQL_DATABASE"]
    SQL_UID = os.environ["SQL_UID"]
    SQL_PASSWORD = os.environ["SQL_PASSWORD"]

    # Recebe argumentos via sys.argv se existirem
    args_inicio = sys.argv[1] if len(sys.argv) >= 4 else None
    args_fim = sys.argv[2] if len(sys.argv) >= 4 else None
    args_ano_inicio = sys.argv[3] if len(sys.argv) >= 4 else None

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
          data_inicio_ano_sql=args_ano_inicio,
        )
    finally:
      conexao_temp.close()