"""
Automação A3 — Gerador de Conteúdo de Aula com Escopo Curricular.

Gera o conteúdo didático de uma aula (explicações, exemplos, atividades) respeitando
estritamente o que é previsto para o ano escolar conforme BNCC e PCN.

Exemplo: "Potenciação no 6º ano" gera conteúdo apenas com números naturais e
propriedades básicas — sem expoentes negativos (que pertencem ao 8º ano).

Input:
  - topico      : tema/conteúdo desejado (ex. "Potenciação")
  - componente  : disciplina (ex. "Matemática")
  - ano_escolar : "6º ano do Ensino Fundamental"

Output:
  - escopo curricular (o que cabe nesse ano segundo BNCC/PCN)
  - conteúdo explicativo detalhado (teoria + exemplos + atividades)
  - o que NÃO trabalhar (evitar erros de progressão)
  - habilidades BNCC contempladas
"""

import re
import time
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate


def _strip_code_fences(text: str) -> str:
    """Remove blocos ```markdown``` ou ``` que LLMs às vezes inserem no output."""
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

from src.rag.vectorstore import similarity_search
from src.utils.helpers import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Mapeamento de escopo curricular por série — guia o LLM a respeitar
# a progressão vertical mesmo sem ter o livro didático no corpus.
# Baseado na BNCC e na sequência tradicional dos PCN.
# ---------------------------------------------------------------------------

CURRICULUM_SCOPE: dict[str, dict[str, str]] = {
    "Matemática": {
        "1º ano do Ensino Fundamental": (
            "Números naturais até 100; contagem, leitura e escrita de números; sequências numéricas; "
            "adição e subtração simples sem reagrupamento; figuras geométricas planas básicas; "
            "medidas de comprimento e tempo (noções); organização de dados em tabelas simples."
        ),
        "2º ano do Ensino Fundamental": (
            "Números naturais até 1000; sistema de numeração decimal; adição e subtração com reagrupamento; "
            "multiplicação como adição repetida (tabuada até 5); formas geométricas planas e espaciais; "
            "medidas de comprimento (m, cm), massa e capacidade (noções); gráficos de barras simples."
        ),
        "3º ano do Ensino Fundamental": (
            "Números naturais até 10000; multiplicação e divisão (tabuada completa); "
            "frações simples (metade, terça, quarta parte); perímetro de figuras; "
            "medidas de tempo (horas, minutos); leitura de tabelas e gráficos de barras."
        ),
        "4º ano do Ensino Fundamental": (
            "Números naturais até 1 000 000; operações com números naturais (todas as quatro); "
            "frações equivalentes e comparação; números decimais (décimos e centésimos); "
            "área de quadrado e retângulo; ângulos (reto, agudo, obtuso); gráficos de linhas."
        ),
        "5º ano do Ensino Fundamental": (
            "Operações com números decimais; porcentagem (noções básicas: 10%, 25%, 50%); "
            "frações e decimais; geometria: polígonos, áreas e perímetros; "
            "razão e proporção (introdução); tabelas e gráficos diversos."
        ),
        "6º ano do Ensino Fundamental": (
            "Números naturais e inteiros (positivos e negativos, reta numérica); "
            "potenciação como multiplicação repetida — base e expoente naturais (EF06MA07); "
            "propriedades da potenciação: produto e quociente de mesma base, potência de potência — "
            "APENAS com expoentes naturais (NÃO usar expoentes negativos nem fracionários); "
            "radiciação como operação inversa da potenciação (raiz quadrada e cúbica de perfeitos); "
            "múltiplos e divisores, MDC, MMC; razão e proporção; porcentagem; "
            "área de triângulo e paralelogramo; coordenadas cartesianas (1º quadrante)."
        ),
        "7º ano do Ensino Fundamental": (
            "Números racionais (frações e decimais); operações com racionais; "
            "expressões algébricas (variável, monômios, polinômios simples); equações do 1º grau; "
            "propriedades da potenciação com expoentes inteiros NEGATIVOS — introdução (EF07MA01/02); "
            "porcentagem e juros simples; geometria: escala, semelhança, ângulos de triângulo; "
            "circunferência e círculo (comprimento e área)."
        ),
        "8º ano do Ensino Fundamental": (
            "Potências com expoentes inteiros negativos e fracionários (relação com radiciação) (EF08MA02); "
            "notação científica; raízes não exatas e números irracionais; equações do 2º grau; "
            "sistemas de equações do 1º grau; teorema de Pitágoras; funções do 1º grau; "
            "probabilidade; estatística: média, mediana, moda."
        ),
        "9º ano do Ensino Fundamental": (
            "Progressões aritméticas e geométricas; função do 2º grau; trigonometria (sen, cos, tg) no triângulo retângulo; "
            "semelhança de triângulos; volume de sólidos; estatística: histogramas, desvio padrão (noções)."
        ),
        "1º ano do Ensino Médio": (
            "Conjuntos; funções (1º e 2º grau, modular, exponencial, logarítmica); progressões; "
            "trigonometria (círculo trigonométrico, identidades); matrizes e determinantes (introdução)."
        ),
        "2º ano do Ensino Médio": (
            "Trigonometria avançada; geometria analítica (reta, circunferência); "
            "matrizes, determinantes e sistemas lineares; polinômios; probabilidade e estatística."
        ),
        "3º ano do Ensino Médio": (
            "Revisão e aprofundamento de funções; geometria espacial (sólidos, volumes); "
            "análise combinatória; probabilidade; distribuições estatísticas; logaritmos avançados."
        ),
    },
    "Ciências": {
        "6º ano do Ensino Fundamental": (
            "Matéria e energia: propriedades, estados físicos e mudanças de estado; "
            "misturas e métodos de separação; célula como unidade da vida (EF06CI05): membrana, citoplasma, núcleo, "
            "organelas básicas — célula animal x vegetal, procariota x eucariota; "
            "classificação dos seres vivos (5 reinos ou domínios, de forma introdutória); "
            "ecossistemas: biomas brasileiros, cadeias alimentares."
        ),
        "7º ano do Ensino Fundamental": (
            "Seres vivos: vírus, bactérias, protistas, fungos; plantas (morfologia e fisiologia básica); "
            "animais invertebrados e vertebrados; interações ecológicas; "
            "solo, atmosfera, ciclos biogeoquímicos (água, carbono, nitrogênio)."
        ),
        "8º ano do Ensino Fundamental": (
            "Corpo humano: sistemas (digestório, respiratório, circulatório, nervoso, reprodutor, imunológico); "
            "doenças e saúde; hereditariedade e genética básica; evolução biológica (Darwin, evidências)."
        ),
        "9º ano do Ensino Fundamental": (
            "Química: átomo, tabela periódica, ligações químicas, funções inorgânicas, reações; "
            "Física: cinemática (velocidade, aceleração), dinâmica (Leis de Newton), energia e trabalho, "
            "ondas, eletricidade básica; universo e cosmologia."
        ),
        "1º ano do Ensino Médio": (
            "Biologia celular aprofundada; bioquímica (carboidratos, proteínas, lipídios, ácidos nucleicos); "
            "metabolismo energético; Química: estequiometria, soluções, termoquímica; "
            "Física: cinemática e dinâmica avançadas, leis de conservação."
        ),
    },
    "Língua Portuguesa": {
        "6º ano do Ensino Fundamental": (
            "Gêneros textuais: conto, crônica, notícia, artigo de opinião; "
            "leitura e interpretação de textos literários e não literários; "
            "produção textual: parágrafo, coesão e coerência; "
            "gramática: classes de palavras (substantivo, adjetivo, verbo, advérbio), "
            "frase, oração e período; pontuação básica; acentuação gráfica; ortografia."
        ),
        "7º ano do Ensino Fundamental": (
            "Gêneros: reportagem, entrevista, poema, texto dramático; "
            "produção: introdução, desenvolvimento e conclusão em dissertações; "
            "gramática: morfologia avançada, pronomes, preposições, conjunções; "
            "concordância nominal e verbal (básica); semântica: sinonímia, antonímia, polissemia."
        ),
        "8º ano do Ensino Fundamental": (
            "Gêneros argumentativos: editorial, carta argumentativa, debate; "
            "análise crítica de textos midiáticos; produção de dissertações argumentativas; "
            "gramática: regência, crase, concordância avançada; figuras de linguagem."
        ),
        "9º ano do Ensino Fundamental": (
            "Gêneros: redação dissertativo-argumentativa (preparação ENEM), artigo científico resumido; "
            "análise literária (estilos de época introdutórios: classicismo, romantismo, realismo); "
            "gramática: sintaxe do período composto, análise de orações subordinadas; variação linguística."
        ),
    },
    "História": {
        "6º ano do Ensino Fundamental": (
            "Introdução à história: fontes históricas, tempo e espaço; Pré-história; "
            "Antiguidade Oriental (Mesopotâmia, Egito, Pérsia, Fenícia, Hebreus); "
            "Grécia Antiga; Roma Antiga (República e Império)."
        ),
        "7º ano do Ensino Fundamental": (
            "Idade Média: feudalismo, Igreja Católica, Islamismo, Cruzadas; "
            "Renascimento, Reforma Protestante; Grandes Navegações; "
            "Colonização das Américas; Escravidão africana."
        ),
        "8º ano do Ensino Fundamental": (
            "Iluminismo e Revoluções (Francesa, Industrial, Americana, Haitiana); "
            "Brasil Colônia e Império; Independência do Brasil; "
            "Abolição da escravidão; Proclamação da República."
        ),
        "9º ano do Ensino Fundamental": (
            "Primeira e Segunda Guerras Mundiais; Revolução Russa; "
            "Brasil República (1889–1985): Era Vargas, Ditadura Militar, redemocratização; "
            "Guerra Fria; descolonização da África e Ásia; mundo contemporâneo."
        ),
    },
    "Geografia": {
        "6º ano do Ensino Fundamental": (
            "O sujeito e seu lugar no mundo; cartografia (orientação, coordenadas, escala, projeções); "
            "natureza e ambiente: litosfera (relevo, rochas), atmosfera (tempo e clima), "
            "hidrosfera (rios, oceanos, ciclo da água); impactos ambientais."
        ),
        "7º ano do Ensino Fundamental": (
            "Dinâmica econômica mundial: globalização, desigualdades; "
            "América Latina: paisagens naturais, organização política e econômica; "
            "Africa: diversidade, história e desafios atuais."
        ),
        "8º ano do Ensino Fundamental": (
            "Brasil: território, regiões, biomas; urbanização e industrialização; "
            "população brasileira: diversidade étnica e cultural, migrações; "
            "agropecuária e questão agrária; problemas ambientais brasileiros."
        ),
        "9º ano do Ensino Fundamental": (
            "Geopolítica mundial: blocos econômicos, conflitos regionais; "
            "energia (matrizes energéticas); questões ambientais globais (clima, desmatamento); "
            "tecnologia e sociedade: redes, cidades inteligentes."
        ),
    },
}

# Escopo genérico para anos/disciplinas não mapeados explicitamente
_DEFAULT_SCOPE = (
    "Siga rigorosamente a progressão curricular da BNCC e PCN para o ano escolar informado. "
    "Use apenas conceitos e complexidade adequados à série. "
    "Não antecipe conteúdos de anos superiores."
)

# ---------------------------------------------------------------------------
# Prompt principal
# ---------------------------------------------------------------------------

CONTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um professor especialista em didática do Ensino Básico brasileiro.
Sua tarefa é gerar o CONTEÚDO DIDÁTICO de uma aula, complementando o plano de aula com material
explicativo, exemplos e atividades práticas.

⚠️ REGRA FUNDAMENTAL — ESCOPO CURRICULAR:
O conteúdo deve respeitar ESTRITAMENTE o que é previsto para o ano escolar informado,
conforme a BNCC e o PCN. Abaixo está o escopo curricular oficial para este ano e disciplina:

{escopo_curricular}

📌 Isso significa:
- Use apenas os conceitos, operações e complexidade adequados ao ano informado.
- NÃO antecipe conteúdos de anos seguintes (mesmo que pareça natural).
- NÃO simplifique a ponto de cobrir conteúdos de anos anteriores (salvo revisão necessária).

Contexto dos documentos curriculares oficiais (BNCC/PCN):
{context}

---

Estruture o conteúdo em Markdown com as seguintes seções OBRIGATÓRIAS:

## 📌 Habilidades BNCC Contempladas
Liste os códigos e descrições das habilidades deste ano que esta aula desenvolve.

## 🚫 O que NÃO trabalhar neste ano
Liste explicitamente os subtópicos que pertencem a anos superiores e devem ser evitados
(com a informação de em que ano aparecem).

## 📖 Conteúdo: Explicação para o Professor
Explicação completa do conteúdo para o professor dominar o tema.
Inclua: definições, conceitos-chave, contexto histórico/prático quando relevante.

## 🎓 Como Apresentar aos Alunos (Linguagem Didática)
Roteiro de como explicar o conteúdo em sala, usando linguagem adequada à faixa etária.
Inclua: analogias, perguntas disparadoras, exemplos concretos do cotidiano.

## 📝 Exemplos Resolvidos
Pelo menos 3 exemplos resolvidos passo a passo, do mais simples ao mais complexo,
respeitando o escopo do ano.

## ✏️ Atividades para os Alunos
5 a 8 exercícios graduados (fácil → médio → desafiador), todos dentro do escopo do ano.
Para cada atividade, indique o objetivo e a habilidade BNCC exercitada.

## 💡 Dicas Pedagógicas
Erros comuns dos alunos neste conteúdo e como o professor pode abordá-los.
Sugestões de materiais concretos, jogos ou recursos digitais adequados ao ano.
"""),
    ("human", """Tópico / Conteúdo: {topico}
Componente curricular: {componente}
Ano escolar: {ano}

Gere o conteúdo completo da aula respeitando o escopo curricular do ano informado."""),
])


def generate_class_content(
    topico: str,
    componente: str,
    ano_escolar: str,
) -> dict:
    """
    Gera o conteúdo didático de uma aula respeitando o escopo curricular do ano.

    Returns:
        dict com 'content' (markdown), 'escopo_usado', 'elapsed_seconds', 'success', 'sources'
    """
    start = time.time()

    # Obtém o escopo curricular para este ano/disciplina
    escopo = (
        CURRICULUM_SCOPE
        .get(componente, {})
        .get(ano_escolar, _DEFAULT_SCOPE)
    )

    # Busca contexto nos documentos curriculares
    query = f"{componente} {topico} {ano_escolar} habilidades BNCC PCN conteúdo"
    docs = similarity_search(query, k=8)
    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in docs
    ) or "Sem trechos encontrados no corpus. Use o escopo curricular acima como referência principal."

    llm = get_llm(temperature=0.3)
    chain = CONTENT_PROMPT | llm

    response = chain.invoke({
        "topico": topico,
        "componente": componente,
        "ano": ano_escolar,
        "escopo_curricular": escopo,
        "context": context,
    })
    content_text: str = _strip_code_fences(response.content)

    # Valida seções obrigatórias
    required = [
        "Habilidades BNCC",
        "O que NÃO trabalhar",
        "Conteúdo",
        "Exemplos Resolvidos",
        "Atividades",
    ]
    sections_ok = sum(1 for s in required if s in content_text)
    elapsed = round(time.time() - start, 2)
    success = sections_ok >= 4 and elapsed < 90

    logger.info(
        "content_generated",
        topico=topico,
        componente=componente,
        ano=ano_escolar,
        sections_ok=sections_ok,
        elapsed=elapsed,
        success=success,
    )

    return {
        "content": content_text,
        "escopo_usado": escopo,
        "elapsed_seconds": elapsed,
        "success": success,
        "sources": [
            {"content": d.page_content[:300], "metadata": d.metadata}
            for d in docs
        ],
    }
