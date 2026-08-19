# config/settings.py
import os
from pathlib import Path
from datetime import date
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E AMBIENTE
# ---------------------------------------------------------
# Path(__file__).resolve()        = caminho completo até enviar_email_mensal.py
# .parent                         = pasta raiz 'config/'
# .parent.parent                  = pasta raiz 'automacao-rh/'
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

ASSETS_DIR = BASE_DIR / "assets"

LOGS_DIR = BASE_DIR / "logs"

APRSENTACOES_DIR = BASE_DIR / "apresentacoes"

GRAFICOS_DIR = [
BASE_DIR / "absenteismo"  / "geral" / "graficos",
BASE_DIR / "absenteismo" / "faltas" / "graficos",
BASE_DIR / "absenteismo" / "atrasos" / "graficos",
BASE_DIR / "absenteismo" / "atestados" / "graficos"
]


# Configuração de Fuso Horário
os.environ["TZ"] = "America/Bahia"

# Cálculo de Datas
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

hoje = date.today()
primeiro_dia_ano = date(hoje.year, 1, 1)
primeiro_dia_mes_atual = hoje.replace(day=1)
ultimo_dia_mes_retrassado = primeiro_dia_mes_atual - relativedelta(days=1, months=1)
primeiro_dia_mes_retrassado = ultimo_dia_mes_retrassado.replace(day=1)

DATA_INICIO_ANO_SQL = primeiro_dia_ano.strftime("%Y-%m-%d")
MES_INICIO_ANO_UNDERLINE = primeiro_dia_ano.strftime("%Y_%m")

DATA_INICIO_SQL = primeiro_dia_mes_retrassado.strftime("%Y-%m-%d")
DATA_FIM_SQL = ultimo_dia_mes_retrassado.strftime("%Y-%m-%d")
MES_ANO_FILTRO = primeiro_dia_mes_retrassado.strftime("%Y-%m")
MES_ANO_UNDERLINE = primeiro_dia_mes_retrassado.strftime("%Y_%m")
MES_ANO_EXTENSO = f"{MESES_PT[primeiro_dia_mes_retrassado.month]}/{primeiro_dia_mes_retrassado.year}"

# Credenciais SMTP
SMTP_SERVER = os.environ["SMTP_SERVER"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
EMAIL_REMETENTE = os.environ["EMAIL_REMETENTE"]
SENHA_REMETENTE = os.environ["SENHA_REMETENTE"]
EMAIL_DESTINATARIO = os.environ["EMAIL_DESTINATARIO"]
EMAIL_TI = os.environ["EMAIL_TI"]

# Credenciais Banco de Dados
SQL_SERVER = os.environ["SQL_SERVER"]
SQL_DATABASE = os.environ["SQL_DATABASE"]
SQL_UID = os.environ["SQL_UID"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]

# Credenciais IA
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]