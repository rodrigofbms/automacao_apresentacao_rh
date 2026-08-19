

import pandas as pd



# Função para formatar valores numéricos no padrão PT-BR
def formatar_numero(valor, prefixo="", sufixo=""):
    if pd.isna(valor) or valor is None:
        valor = 0.0
    valor_formatado = f"{float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"{prefixo}{valor_formatado}{sufixo}"