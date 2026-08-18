

"""
Módulo utilitário para assinar gráficos (Eletrodata / Rodrigo Maturino).

Como Usar:

    from assinatura_grafico import assinar_grafico

    ... (seu código do gráfico normalmente) ...

    plt.tight_layout()
    assinar_grafico(plt.gcf())
    plt.savefig(nome_arquivo_saida, dpi=300)
    plt.show()
    
"""

import matplotlib.image as mpimg
import os
from pathlib import Path

# Path(__file__).resolve()        = caminho completo até assinatura_grafico.py
# .parent                         = pasta 'utils/'
# .parent.parent                  = pasta raiz 'Scripts_python/'
# .parent.parent.parent                  = pasta raiz 'Absenteismo/'
_DIR_SCRIPTS_PYTHON = Path(__file__).resolve().parent.parent.parent 

# Cria um diretório da logo padrão (PNG com fundo transparente) que será usada como marca d'água nos gráficos
# com base no diretório raiz do projeto (Absenteismo/)
LOGO_PATH_PADRAO = os.path.join(
    _DIR_SCRIPTS_PYTHON, 'assets', 'LOGO_ELETRODATA_VERTICAL_FUNDO_TRANSPARENTE.png'
)

def assinar_grafico(
    fig,
    cor_letra="black",
    fontsize=10,
    alpha_texto=0.5,
    logo_path=LOGO_PATH_PADRAO,
    nome="Rodrigo Maturino",
    cargo="Analista de Dados",
    posicao_texto=(0.97, 0.01), # Posição do texto (X, Y) em fração da figura (0 a 1)
    posicao_logo=(0.87, 0.03, 0.12, 0.12)  # (x, y, largura, altura) em fração da figura
):
    """
    Adiciona uma marca d'água em texto e (opcionalmente) uma logo no rodapé
    da figura, usando coordenadas RELATIVAS À FIGURA INTEIRA (0 a 1),
    e não coordenadas de dados do eixo.

    Isso garante que a posição fique sempre igual, não importa a escala
    dos dados do gráfico (percentual, valores em milhares, datas, etc).

    Parâmetros
    ----------
    fig : matplotlib.figure.Figure
        A figura atual (use plt.gcf() se estiver usando a API do pyplot).
    logo_path : str, opcional
        Caminho da imagem da logo (PNG com fundo transparente).
        Se None, não desenha a logo.
    nome : str
        Nome que aparece na marca d'água.
    cargo : str
        Cargo/função que aparece na marca d'água.
    posicao_texto : tuple (x, y)
        Posição do texto em fração da figura (0 a 1).
        Padrão: canto inferior direito.
    posicao_logo : tuple (x, y, largura, altura)
        Posição/tamanho da logo em fração da figura (0 a 1).
    fontsize : int
        Tamanho da fonte da marca d'água.
    alpha_texto : float
        Transparência do texto (0 a 1).

    IMPORTANTE: chame esta função DEPOIS do plt.tight_layout() e
    ANTES do plt.savefig(), senão o tight_layout pode reorganizar
    e deslocar os elementos que você acabou de posicionar.
    """

    # fig.text() (e não plt.text()!) usa coordenadas de figura por padrão,
    # então a posição fica consistente em qualquer gráfico.
    fig.text(
        posicao_texto[0], posicao_texto[1],
        f"Criado por {nome} | {cargo}",
        fontsize=fontsize,
        color=cor_letra,
        alpha=alpha_texto,
        ha="right",
        va="bottom",
    )

    if logo_path:
        logo = mpimg.imread(logo_path)
        # fig.add_axes() também usa fração da figura (0 a 1) -- consistente
        logo_ax = fig.add_axes(posicao_logo)
        logo_ax.imshow(logo)
        logo_ax.axis("off")

    return fig