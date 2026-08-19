import logging
from pathlib import Path
from datetime import datetime,timedelta
from typing import Union


def limpar_arquivos_antigos(diretorios: Union[Path, list[Path]], dias_retencao: int = 180):
    """
    Deleta arquivos de gráficos e logs (.png, .jpg, .log) no diretório especificado que forem
    mais antigos do que a quantidade de dias informada (padrão: 180 dias / 6 meses).
    """
    
    # Se for passado apenas um Path individual, converte em lista para padronizar
    if isinstance(diretorios, Path):
        diretorios = [diretorios]

    data_limite = datetime.now() - timedelta(days=dias_retencao)
    arquivos_removidos = 0
    logging.info(f"🧹 Iniciando limpeza de arquivos automática (anteriores a {data_limite.strftime('%d/%m/%Y')})...")

    for pasta in diretorios:
        if not pasta.exists():

            logging.warning(f"⚠️ Diretório dos arquivos não encontrado para limpeza: {pasta}")
        
        else:
            
            # Percorre todos os arquivos de imagem no diretório
            for arquivo in pasta.glob("*.*"):
                if arquivo.is_file() and arquivo.suffix.lower() in [".png", ".jpg", ".jpeg", ".log", ".pptx"]:

                    # Obtém a data da última modificação do arquivo
                    data_modificacao = datetime.fromtimestamp(arquivo.stat().st_mtime)

                    if data_modificacao < data_limite:
                        try:
                            arquivo.unlink()
                            arquivos_removidos += 1
                            logging.info(f"🗑️ Arquivo removido: {arquivo.name} (Criado em: {data_modificacao.strftime('%d/%m/%Y')})")
                            
                        except Exception as e:
                            logging.error(f"Erro ao tentar deletar o arquivo {arquivo.name}: {e}")

            logging.info(f"✅ Limpeza concluída: {arquivos_removidos} arquivo(s) removido(s) no total.")