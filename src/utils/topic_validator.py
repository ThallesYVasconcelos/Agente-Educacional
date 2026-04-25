"""
Validação de consistência entre tema e disciplina selecionada.

Estratégia dupla:
  A) Verificação rápida por palavras-chave (local, sem LLM)
     → Detecta inconsistências óbvias imediatamente
  B) Detecção automática via LLM
     → Sugere a disciplina correta com base no tema digitado
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# A) Mapa de palavras-chave por disciplina
# Chave: nome da disciplina (igual ao selectbox)
# Valor: termos que PERTENCEM a essa disciplina
# ---------------------------------------------------------------------------

_KEYWORDS: dict[str, list[str]] = {
    "Ciências": [
        "célula", "celula", "membrana", "núcleo", "nucleo", "citoplasma", "organela",
        "mitocôndria", "mitocondria", "cloroplasto", "vacúolo", "vacuolo",
        "fotossíntese", "fotossintese", "respiração celular", "respiracao celular",
        "dna", "rna", "genética", "genetica", "cromossomo", "evolução", "evolucao",
        "ecossistema", "cadeia alimentar", "bioma", "habitat", "espécie", "especie",
        "vertebrado", "invertebrado", "mamífero", "mamifero", "réptil", "reptil",
        "anfíbio", "anfibio", "bactéria", "bacteria", "vírus", "virus", "fungo",
        "planta", "raiz", "caule", "folha", "flor", "semente", "fruto",
        "átomo", "atomo", "molécula", "molecula", "elemento químico", "elemento quimico",
        "tabela periódica", "tabela periodica", "ligação química", "ligacao quimica",
        "reação química", "reacao quimica", "ácido", "acido", "base", "sal",
        "força", "forca", "energia", "trabalho", "velocidade", "aceleração", "aceleracao",
        "onda", "luz", "eletricidade", "magnetismo", "circuito elétrico", "circuito eletrico",
        "mudança de estado", "mudanca de estado", "mistura", "solução", "solucao",
        "solo", "atmosfera", "clima", "temperatura", "pressão", "pressao",
        "sistema solar", "planeta", "estrela", "universo", "galáxia", "galaxia",
        "corpo humano", "sistema digestório", "sistema digestorio", "sistema respiratório",
        "sistema respiratorio", "sistema circulatório", "sistema circulatorio",
        "sistema nervoso", "sistema imunológico", "sistema imunologico",
    ],
    "Matemática": [
        "potenciação", "potenciacao", "potência", "potencia", "expoente", "base",
        "radiciação", "radicacao", "raiz quadrada", "raiz cúbica", "raiz cubica",
        "fração", "fracao", "decimal", "porcentagem", "razão", "razao", "proporção", "proporcao",
        "equação", "equacao", "inequação", "inequacao", "função", "funcao",
        "geometria", "triângulo", "triangulo", "quadrado", "retângulo", "retangulo",
        "círculo", "circulo", "circunferência", "circunferencia", "área", "area",
        "perímetro", "perimetro", "volume", "ângulo", "angulo",
        "adição", "adicao", "subtração", "subtracao", "multiplicação", "multiplicacao",
        "divisão", "divisao", "tabuada", "mdc", "mmc", "múltiplos", "multiplos",
        "divisores", "números inteiros", "numeros inteiros", "número natural", "numero natural",
        "número racional", "numero racional", "número irracional", "numero irracional",
        "álgebra", "algebra", "variável", "variavel", "polinômio", "polinomio",
        "monômio", "monomio", "sistema linear", "matrizes", "determinante",
        "probabilidade", "estatística", "estatistica", "média", "media", "mediana", "moda",
        "progressão aritmética", "progressao aritmetica", "progressão geométrica", "progressao geometrica",
        "trigonometria", "seno", "cosseno", "tangente", "pitágoras", "pitagoras",
        "plano cartesiano", "coordenadas", "gráfico", "grafico",
    ],
    "História": [
        "revolução", "revolucao", "guerra", "império", "imperio", "república", "republica",
        "escravidão", "escravidao", "colonização", "colonizacao", "independência", "independencia",
        "feudalismo", "renascimento", "iluminismo", "absolutismo", "democracia",
        "grécia", "grecia", "roma", "egito", "mesopotâmia", "mesopotamia",
        "idade média", "idade media", "cruzadas", "reforma protestante",
        "grandes navegações", "grandes navegacoes", "era vargas", "ditadura",
        "getúlio vargas", "getulio vargas", "proclamação da república", "proclamacao da republica",
        "abolição", "abolicao", "lei áurea", "lei aurea", "pedro i", "pedro ii",
        "pré-história", "pre-historia", "paleolítico", "paleolitico", "neolítico", "neolitico",
        "civilização", "civilizacao", "faraó", "farao", "pirâmide", "piramide",
        "segunda guerra", "primeira guerra", "guerra fria", "nazismo", "fascismo",
        "holocausto", "imperialismo", "descolonização", "descolonizacao",
    ],
    "Geografia": [
        "cartografia", "mapa", "escala", "coordenadas geográficas", "coordenadas geograficas",
        "latitude", "longitude", "meridiano", "paralelo", "projeção", "projecao",
        "relevo", "montanha", "planalto", "planície", "planicie", "depressão", "depressao",
        "bacia hidrográfica", "bacia hidrografica", "rio", "lago", "oceano", "mar",
        "bioma", "cerrado", "amazônia", "amazonia", "caatinga", "pantanal", "mata atlântica",
        "clima", "tempo", "temperatura", "precipitação", "precipitacao",
        "globalização", "globalizacao", "urbanização", "urbanizacao",
        "densidade demográfica", "densidade demografica", "migração", "migracao",
        "recursos naturais", "desmatamento", "erosão", "erosao", "sustentabilidade",
        "região", "regiao", "território", "territorio", "fronteira", "estado", "município", "municipio",
        "pib", "idh", "desigualdade", "pobreza", "desenvolvimento",
    ],
    "Língua Portuguesa": [
        "texto", "redação", "redacao", "dissertação", "dissertacao", "narração", "narracao",
        "descrição", "descricao", "argumentação", "argumentacao", "crônica", "cronica",
        "conto", "poema", "poesia", "romance", "fábula", "fabula", "notícia", "noticia",
        "gênero textual", "genero textual", "gênero discursivo", "genero discursivo",
        "ortografia", "gramática", "gramatica", "sintaxe", "morfologia",
        "substantivo", "adjetivo", "verbo", "advérbio", "adverbio", "pronome",
        "preposição", "preposicao", "conjunção", "conjuncao", "artigo",
        "sujeito", "predicado", "oração", "oracao", "período", "periodo",
        "concordância", "concordancia", "regência", "regencia", "crase",
        "pontuação", "pontuacao", "acentuação", "acentuacao",
        "leitura", "interpretação de texto", "interpretacao de texto",
        "alfabetização", "alfabetizacao", "letramento", "fonema", "sílaba", "silaba",
        "variação linguística", "variacao linguistica", "dialeto",
        "literatura", "autor", "obra literária", "obra literaria",
    ],
    "Arte": [
        "pintura", "escultura", "desenho", "arte", "artista", "obra de arte",
        "música", "musica", "ritmo", "melodia", "harmonia", "instrumento musical",
        "teatro", "drama", "dança", "danca", "coreografia",
        "fotografia", "cinema", "audiovisual", "animação", "animacao",
        "arte rupestre", "renascimento artístico", "renascimento artistico",
        "impressionismo", "modernismo", "vanguarda", "arte abstrata",
        "artesanato", "folclore", "cultura popular",
    ],
    "Educação Física": [
        "esporte", "futebol", "basquete", "vôlei", "volei", "natação", "natacao",
        "atletismo", "ginástica", "ginastica", "handebol", "tênis", "tenis",
        "regra", "tática", "tatica", "técnica esportiva", "tecnica esportiva",
        "saúde", "saude", "qualidade de vida", "sedentarismo", "obesidade",
        "exercício físico", "exercicio fisico", "atividade física", "atividade fisica",
        "postura", "coordenação motora", "coordenacao motora", "flexibilidade",
        "resistência", "resistencia", "força muscular", "forca muscular",
        "jogo", "brincadeira", "recreação", "recreacao", "lazer",
    ],
    "Língua Estrangeira": [
        "inglês", "ingles", "english", "espanhol", "spanish", "francês", "frances",
        "vocabulário", "vocabulario", "grammar", "gramática inglesa", "gramatica inglesa",
        "listening", "speaking", "reading", "writing", "pronúncia", "pronuncia",
        "phrasal verb", "idiom", "expressão idiomática", "expressao idiomatica",
        "present simple", "past simple", "future", "present perfect",
    ],
    "Ensino Religioso": [
        "religião", "religiao", "fé", "fe", "crença", "crenca", "espiritualidade",
        "sagrado", "profano", "divindade", "oração", "oracao", "ritual",
        "hinduísmo", "hinduismo", "budismo", "islamismo", "judaísmo", "judaismo",
        "cristianismo", "catolicismo", "protestantismo", "umbanda", "candomblé", "candomble",
        "ética", "etica", "valores", "tolerância", "tolerancia", "diversidade religiosa",
    ],
}


def _normalize(text: str) -> str:
    return text.lower().strip()


# ---------------------------------------------------------------------------
# A) Verificação rápida por palavras-chave
# ---------------------------------------------------------------------------

def check_topic_discipline(topic: str, disciplina: str) -> dict:
    """
    Verifica se o tema informado é consistente com a disciplina selecionada.

    Returns:
        {
            "ok": bool,                    # True = parece consistente
            "detected": str | None,        # Disciplina detectada pelas palavras-chave
            "confidence": "high"|"low",
            "message": str,                # Mensagem para exibir ao professor
        }
    """
    topic_norm = _normalize(topic)

    # Conta hits por disciplina
    hits: dict[str, int] = {}
    for disc, keywords in _KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in topic_norm)
        if count > 0:
            hits[disc] = count

    if not hits:
        # Nenhuma palavra-chave reconhecida — não temos como avaliar
        return {
            "ok": True,
            "detected": None,
            "confidence": "low",
            "message": "",
        }

    best_disc = max(hits, key=lambda d: hits[d])
    best_score = hits[best_disc]

    if best_disc == disciplina:
        return {
            "ok": True,
            "detected": best_disc,
            "confidence": "high",
            "message": "",
        }

    # Inconsistência detectada
    return {
        "ok": False,
        "detected": best_disc,
        "confidence": "high" if best_score >= 2 else "low",
        "message": (
            f"O tema **\"{topic}\"** parece ser de **{best_disc}**, "
            f"mas você selecionou **{disciplina}**."
        ),
    }


# ---------------------------------------------------------------------------
# B) Detecção automática via LLM
# ---------------------------------------------------------------------------

def detect_discipline_with_llm(topic: str, ano: str) -> dict:
    """
    Usa o LLM para identificar a disciplina mais adequada para o tema e ano.

    Returns:
        {
            "disciplina": str,       # Disciplina sugerida pelo LLM
            "justificativa": str,    # Explicação curta
            "habilidades": list[str] # Códigos BNCC sugeridos (opcional)
        }
    """
    import json
    from langchain_core.prompts import ChatPromptTemplate
    from src.utils.helpers import get_llm

    COMPONENTES = [
        "Língua Portuguesa", "Matemática", "Ciências", "História",
        "Geografia", "Arte", "Educação Física", "Língua Estrangeira", "Ensino Religioso",
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""Você é um especialista em currículo da Educação Básica brasileira.
Dado um tema/tópico de aula e um ano escolar, identifique:
1. Qual componente curricular esse tema pertence (escolha UMA das opções)
2. Uma justificativa curta (1 frase)
3. Os códigos de habilidades BNCC mais relevantes para esse tema/ano (até 3)

Componentes possíveis: {', '.join(COMPONENTES)}

Responda APENAS com JSON:
{{
  "disciplina": "nome do componente",
  "justificativa": "porque pertence a essa disciplina",
  "habilidades": ["EF0XXX00", ...]
}}
"""),
        ("human", "Tema: {topic}\nAno escolar: {ano}"),
    ])

    llm = get_llm(temperature=0)
    chain = prompt | llm

    try:
        result = chain.invoke({"topic": topic, "ano": ano})
        raw = result.content.strip()
        # Remove possíveis blocos de código
        raw = re.sub(r"```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```", "", raw).strip()
        data = json.loads(raw)
        return {
            "disciplina": data.get("disciplina", ""),
            "justificativa": data.get("justificativa", ""),
            "habilidades": data.get("habilidades", []),
        }
    except Exception:
        return {"disciplina": "", "justificativa": "", "habilidades": []}
