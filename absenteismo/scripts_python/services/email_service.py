import logging
from pathlib import Path
from config.settings import (
    BASE_DIR, MES_ANO_EXTENSO, EMAIL_DESTINATARIO,
    EMAIL_REMETENTE, EMAIL_TI, SENHA_REMETENTE, SMTP_PORT, SMTP_SERVER
)
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DE DIRETÓRIOS E ARQUIVO DE LOG
# ---------------------------------------------------------
PASTA_LOGS = BASE_DIR / "logs"
PASTA_LOGS.mkdir(exist_ok=True)

arquivo_log = PASTA_LOGS / f"execucao_{datetime.now().strftime('%Y_%m_%d_%H-%M')}.log"

# ---------------------------------------------------------
# 5. CONSTRUÇÃO E ENVIO DO E-MAIL MULTI-IMAGEM
# ---------------------------------------------------------
def enviar_email_com_graficos(lista_imagens: list[Path], caminho_pptx: Path | None = None):

    if not lista_imagens and not caminho_pptx:
        raise FileNotFoundError(f"[ERRO] Nenhuma arquivo referente a {MES_ANO_EXTENSO} foi encontrada!")

        
    else:
        logging.info(f"Preparando e-mail com {len(lista_imagens)} gráfico(s) para {EMAIL_DESTINATARIO}...")

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f'📊 Apresentação e Gráficos de Absenteísmo para Apresentação - Fechamento {MES_ANO_EXTENSO}'
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO

        # Container 'related' permite exibir imagens inline no HTML (rodapé)
        msg_related = MIMEMultipart("related")
        msg.attach(msg_related)


        # Corpo do e-mail simples sem as imagens renderizadas
        lista_nomes_arquivos = "".join([f"<li><code>{img.name}</code></li>" for img in lista_imagens])
        str_pptx = f"<li><b>Apresentação PowerPoint:</b> <code>{caminho_pptx.name}</code></li>" if caminho_pptx else ""

        html_completo = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <h2>Apresentação, Gráficos e Análise detalhada pelo IA — Fechamento {MES_ANO_EXTENSO}</h2>
                <p>Bom dia, Priscila! Tudo bem?</p>
                <p>Segue em anexo a apresentação em Power Point com os gráficos atualizados sobre o absenteísmo referente ao mês de <b>{MES_ANO_EXTENSO}</b>.</p>
                <p>Os gráficos e a apresentação foram gerados com sucesso e estão dispostos em <b>anexo</b> neste e-mail, além do parecer feito pelo IA de acordo com os dados relativos ao mês analisado.</p>
                
                <p><b>Arquivos anexados ({len(lista_imagens)}):</b></p>
                <ul>
                    {str_pptx}
                    {lista_nomes_arquivos}
                </ul>
                
                <br>
                <p style="font-size: 14px; color: #777;">
                    E-mail automático criado por Rodrigo Maturino | Analista de Dados.
                </p>

                <table border="0" cellpadding="0" cellspacing="0" style="margin-top: 20px; font-family: Arial, sans-serif;">
                    <tr>
                        <td style="padding-bottom: 1px; vertical-align: middle;">
                            <img src="cid:assinatura_rodape" alt="Contato" style="display: block; max-height: 90px; height: auto;">
                        </td>
                    </tr>

                    <tr>
                        <td style="border-top: 1px; padding-top: 1px; vertical-align: middle;">
                            <img src="cid:logo_rodape" alt="Eletrodata Engenharia" style="display: block; max-height: 90px; height: auto;">
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

        msg_related.attach(MIMEText(html_completo, "html"))

        #msg.attach(MIMEText(html_completo, 'html'))

        # Anexar a Apresentação PPTX
        if caminho_pptx and caminho_pptx.exists():
            with open(caminho_pptx, 'rb') as f:
                part = MIMEApplication(f.read(), Name=caminho_pptx.name)
                part['Content-Disposition'] = f'attachment; filename="{caminho_pptx.name}"'
                msg.attach(part)

        # ---------------------------------------------------------
        #  ANEXAR AS IMAGENS DO RODAPÉ (INLINE VIA CID)
        # ---------------------------------------------------------
        PASTA_ASSETS = BASE_DIR.parent / "assets"
        caminho_contato = PASTA_ASSETS / "cabecalho_rodape.png"
        caminho_logo = PASTA_ASSETS / "logo_rodape.png"

        # Anexar as imagens dos gráficos
        if caminho_contato.exists():
            with open(caminho_contato, "rb") as f:
                img_contato = MIMEImage(f.read())
                img_contato.add_header("Content-ID", "<assinatura_rodape>")
                img_contato.add_header("Content-Disposition", "inline", filename= caminho_contato.name)
                msg_related.attach(img_contato)
        else:
            logging.warning(f"Imagem de contato não encontrada em: {caminho_contato}")


        if caminho_logo.exists():
            with open(caminho_logo, "rb") as f:
                img_logo = MIMEImage(f.read())
                img_logo.add_header("Content-ID", "<logo_rodape>")
                img_logo.add_header("Content-Disposition", "inline", filename=caminho_logo.name)
                msg_related.attach(img_logo)
        else:
            logging.warning(f"Imagem de logo não encontrada em: {caminho_logo}")


        # ---------------------------------------------------------
        #   ANEXAR OS GRÁFICOS COMO ATTACHMENT (ANEXOS) 
        # ---------------------------------------------------------
        for caminho_img in lista_imagens:
            with open(caminho_img, 'rb') as img_file:
                img_anexo = MIMEImage(img_file.read())
                
                # defina o header como 'attachment' e informar o nome do arquivo
                img_anexo.add_header('Content-Disposition', 'attachment', filename=caminho_img.name)
                
                msg.attach(img_anexo)

        # Conectar ao servidor SMTP e enviar
        # Usando 'smtplib.SMTP_SSL()' para conexão segura (porta 465) não é necessário iniciar TLS separadamente usando o comando 'starttls()', porém
        # se utilizar a porta 587 'smtplib.SMTP()', você precisará usar 'starttls()' para criptografar a conexão.
        try:
            _enviar_smtp(destinatario=EMAIL_DESTINATARIO, msg=msg)
            logging.info(f"✅ E-mail consolidado enviado com sucesso para {EMAIL_DESTINATARIO}!")
        except Exception as e:
            logging.error(f"❌ Erro ao enviar e-mail: {e}")
            raise e


# ---------------------------------------------------------
# ENVIO DO E-MAIL DE AUDITORIA/LOGS (PARA A TI/VOCÊ)
# ---------------------------------------------------------
def enviar_email_status_ti(sucesso: bool, mensagem_erro="", arquivo_log: Path | None = None):
  
  """Envia um e-mail de notificação técnica com o arquivo de log anexado."""

  msg = MIMEMultipart()
  msg["From"] = EMAIL_REMETENTE
  msg["To"] = EMAIL_TI

  if sucesso:
    msg["Subject"] = (
        f"✅ [SUCESSO] Automação Absenteísmo - Fechamento {MES_ANO_EXTENSO}"
    )
    corpo = (
        f"Olá,\n\nA execução da automação do Relatório de Absenteísmo"
        f" ({MES_ANO_EXTENSO}) foi concluída com SUCESSO!\n\n"
        f"• Relatório entregue para: {EMAIL_DESTINATARIO}\n"
        f"• Horário de Conclusão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        "O arquivo de log completo da execução está em anexo."
    )
  else:
    msg["Subject"] = (
        f"❌ [FALHA] Automação Absenteísmo - Fechamento {MES_ANO_EXTENSO}"
    )
    corpo = (
        "Atenção,\n\nOcorreu um ERRO durante a execução da automação do"
        f" Relatório de Absenteísmo ({MES_ANO_EXTENSO}).\n\n"
        f"Mensagem de erro:\n{mensagem_erro}\n\n"
        "Consulte o arquivo de log em anexo para visualizar o traceback do"
        " erro."
    )

  msg.attach(MIMEText(corpo, "plain", "utf-8"))

  # Anexar arquivo .log
  if arquivo_log and arquivo_log.exists():
    with open(arquivo_log, "rb") as f:
      part = MIMEApplication(f.read(), Name=arquivo_log.name)
      part["Content-Disposition"] = f'attachment; filename="{arquivo_log.name}"'
      msg.attach(part)

  try:
    _enviar_smtp(destinatario= EMAIL_TI, msg=msg)
    logging.info(f"📧 E-mail de notificação técnica/log enviado com sucesso para {EMAIL_TI}.")
  except Exception as e:
    logging.error(f"📧❌ Falha ao enviar e-mail de notificação para a TI: {e}")



def _enviar_smtp(destinatario: str , msg: MIMEMultipart):
    """Função para gerenciar o socket SMTP com SSL."""
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            #server.starttls()  # Inicia a criptografia TLS
            server.login(EMAIL_REMETENTE, SENHA_REMETENTE)
            server.sendmail(EMAIL_REMETENTE, destinatario, msg.as_string())
            server.quit()
    except Exception as e:
        raise e