# config/pptx_mapping.py
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from config.settings import MES_ANO_EXTENSO, MES_ANO_UNDERLINE, MES_INICIO_ANO_UNDERLINE

def obter_mapa_titulos():
    return {
        0: {
            "placeholder_index": 10,
            "texto": MES_ANO_EXTENSO,
            "fonte_nome": "Roboto",
            "tamanho_pt": 28,
            "bold": True,
            "italic": True,
            "cor_rgb": RGBColor(255, 255, 255),
            "alinhamento": PP_ALIGN.CENTER,
            "uppercase": False
        },
        23: {
            "placeholder_index": 10,
            "texto": MES_ANO_EXTENSO,
            "fonte_nome": "Roboto",
            "tamanho_pt": 26,
            "bold": True,
            "italic": False,
            "cor_rgb": RGBColor(0, 85, 140),
            "alinhamento": PP_ALIGN.CENTER,
            "uppercase": True
        },
    }

# Dicionário mapeando palavras-chave do nome da imagem ao número do slide ou posição
# Ajuste os índices do slide conforme a posição real dentro do seu modelo PPTX (0 = slide 1, 1 = slide 2...)
def obter_mapa_imagens():
    return {
        # Slide 25
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 2
                f"absenteismo_por_mes_{MES_INICIO_ANO_UNDERLINE}-{MES_ANO_UNDERLINE}": {"slide_index": 24, "placeholder_index": 10},
        
                # Slide 26
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 2
                f"donut_tipo_horas_absenteismo_por_mes_{MES_ANO_UNDERLINE}": {"slide_index": 25, "placeholder_index": 10},
        
                # Slide 27
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 17
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 18
                f"cards_atrasos_por_mes_{MES_ANO_UNDERLINE}": {"slide_index": 26, "placeholder_index": 11},
        
                # Slide 27
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 17
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 18
                f"top_5_atrasos_absenteismo_por_centro_custo_{MES_ANO_UNDERLINE}": {"slide_index": 26, "placeholder_index": 10},
        
                # Slide 28
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 17
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 18
                f"cards_faltas_por_mes_{MES_ANO_UNDERLINE}": {"slide_index": 27, "placeholder_index": 11},
        
                # Slide 28
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 7
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 9
                f"top_5_faltas_absenteismo_por_centro_custo_{MES_ANO_UNDERLINE}": {"slide_index": 27, "placeholder_index": 10},
        
                # Slide 29
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 17
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 18
                f"cards_atestados_por_mes_{MES_ANO_UNDERLINE}": {"slide_index": 28, "placeholder_index": 11},
        
                # Slide 29
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 7
                # Placeholder idx: 11 | Nome: Espaço Reservado para Imagem 9
                f"top_5_atestados_absenteismo_por_centro_custo_{MES_ANO_UNDERLINE}": {"slide_index": 28, "placeholder_index": 10},
        
                # Slide 30
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 2
                f"custo_atestados_por_mes_{MES_INICIO_ANO_UNDERLINE}-{MES_ANO_UNDERLINE}": {"slide_index": 29, "placeholder_index": 10},
        
                # Slide 31
                # Placeholder idx: 10 | Nome: Espaço Reservado para Imagem 2
                f"custo_atestados_por_centro_custo_{MES_ANO_UNDERLINE}": {"slide_index": 30, "placeholder_index": 10},
    }


def obter_mapa_texto_ai():
    """Mapeamento do placeholder onde o texto gerado pela IA será injetado."""

    # Slide 31
    # Placeholder idx: 10
    return {
        "slide_index": 31,
        "placeholder_index": 10,
        "fonte_nome": "Arial",
        "tamanho_pt": 18,
        "alinhamento": PP_ALIGN.LEFT,
        "cor_rgb": RGBColor(50, 50, 50),
    }