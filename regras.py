# -*- coding: utf-8 -*-
"""
REGRAS DE NEGÓCIO — Sistema Goularth de Torneios
===================================================
"""

import re
import datetime

CATEGORIA_FILHOTE = "FILHOTE"
CATEGORIA_ADULTO = "ADULTO"
CATEGORIA_MISTO = "MISTO"

CATEGORIAS_VALIDAS = (CATEGORIA_FILHOTE, CATEGORIA_ADULTO, CATEGORIA_MISTO)

MODALIDADE_FIBRA = "FIBRA"
MODALIDADE_CANTO_LIVRE = "CANTO_LIVRE"
MODALIDADES_VALIDAS = (MODALIDADE_FIBRA, MODALIDADE_CANTO_LIVRE)

FEDERACAO = "FOB"


class ErroValidacao(Exception):
    pass


# ================================================================
# CPF
# ================================================================
def validar_cpf_formato(cpf):
    if not cpf:
        raise ErroValidacao("CPF não informado.")
    apenas_digitos = re.sub(r"\D", "", str(cpf))
    if len(apenas_digitos) != 11:
        raise ErroValidacao(f"CPF '{cpf}' inválido — deve ter 11 dígitos.")
    return apenas_digitos


# ================================================================
# CATEGORIA AUTOMÁTICA PELA ANILHA
# ================================================================
def extrair_ano_anilha(codigo_ave):
    if not codigo_ave or not str(codigo_ave).strip():
        raise ErroValidacao("Código da ave não informado.")

    codigo = str(codigo_ave).strip()
    partes = codigo.split("-")
    
    if len(partes) >= 5:
        ultimo = partes[-1]
        if ultimo.isdigit() and len(ultimo) == 2:
            return 2000 + int(ultimo)
    
    candidatos = re.findall(r"20\d{2}", codigo)
    if candidatos:
        return int(candidatos[0])
    
    raise ErroValidacao(
        f"Não foi possível identificar o ano no código '{codigo}'."
    )


def calcular_categoria(codigo_ave, ano_referencia=None):
    if ano_referencia is None:
        ano_referencia = datetime.date.today().year

    ano_anilha = extrair_ano_anilha(codigo_ave)

    if ano_anilha > ano_referencia:
        raise ErroValidacao(
            f"O ano da anilha ({ano_anilha}) é maior que o ano atual ({ano_referencia})."
        )

    if ano_anilha in (ano_referencia, ano_referencia - 1):
        return CATEGORIA_FILHOTE
    return CATEGORIA_ADULTO


def verificar_categoria_passaro(codigo_ave, categoria_etapa, ano_referencia=None):
    """
    Verifica se o pássaro pode participar da etapa.
    - Se categoria for FILHOTE: só filhotes
    - Se categoria for ADULTO: só adultos
    - Se categoria for MISTO: qualquer um (filhote ou adulto)
    """
    categoria_passaro = calcular_categoria(codigo_ave, ano_referencia)
    
    if categoria_etapa == CATEGORIA_MISTO:
        return True
    
    return categoria_passaro == categoria_etapa


# ================================================================
# VALIDAÇÃO DE CÓDIGOS
# ================================================================
def validar_codigo_ave(codigo):
    if not codigo:
        raise ErroValidacao("Código da ave não informado.")
    
    partes = codigo.split("-")
    if len(partes) != 5:
        raise ErroValidacao(
            f"Formato inválido. Use: FOB-SIGLA-NUMSOCIO-NUMANILHA-ANO (ex: FOB-II-0889-0008-23)"
        )
    
    if partes[0] != FEDERACAO:
        raise ErroValidacao(f"Federação deve ser {FEDERACAO}")
    
    if not partes[1] or len(partes[1]) > 4:
        raise ErroValidacao("Sigla do criador inválida (máximo 4 letras).")
    
    if not partes[2] or not partes[2].isdigit():
        raise ErroValidacao("Número do sócio deve conter apenas dígitos.")
    
    if not partes[3] or not partes[3].isdigit():
        raise ErroValidacao("Número da anilha deve conter apenas dígitos.")
    
    if not partes[4] or not partes[4].isdigit() or len(partes[4]) != 2:
        raise ErroValidacao("Ano deve ter 2 dígitos (ex: 23 para 2023).")
    
    return True


def normalizar_modalidade(modalidade):
    modalidade_norm = str(modalidade).strip().upper().replace(" ", "_")
    if modalidade_norm not in MODALIDADES_VALIDAS:
        raise ErroValidacao(
            f"Modalidade '{modalidade}' inválida. Use Fibra ou Canto Livre."
        )
    return modalidade_norm


def normalizar_categoria(categoria):
    categoria_norm = str(categoria).strip().upper()
    if categoria_norm not in CATEGORIAS_VALIDAS:
        raise ErroValidacao(
            f"Categoria inválida. Use Filhote, Adulto ou Misto."
        )
    return categoria_norm


# ================================================================
# LIMITE POR CPF
# ================================================================
def validar_limite_cpf(quantidade_ja_inscrita, limite_por_cpf):
    if limite_por_cpf is None:
        return
    if quantidade_ja_inscrita >= limite_por_cpf:
        raise ErroValidacao(
            f"Limite de {limite_por_cpf} pássaro(s) por CPF nesta categoria já foi atingido."
        )
