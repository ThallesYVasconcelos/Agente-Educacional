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


def _fix_latex(text: str) -> str:
    """
    Converte notação LaTeX residual em texto legível.
    Mesmo com instruções explícitas, o LLM às vezes insiste em usar LaTeX.
    """
    # Remove delimitadores LaTeX inline: \( ... \) e $ ... $
    text = re.sub(r"\\\((.+?)\\\)", lambda m: _latex_to_text(m.group(1)), text)
    text = re.sub(r"\$(.+?)\$", lambda m: _latex_to_text(m.group(1)), text)
    # Remove delimitadores LaTeX em bloco: \[ ... \]
    text = re.sub(r"\\\[(.+?)\\\]", lambda m: _latex_to_text(m.group(1)), text, flags=re.DOTALL)
    return text


def _latex_to_text(expr: str) -> str:
    """Converte expressão LaTeX simples em texto legível."""
    expr = expr.strip()
    # Operadores
    expr = expr.replace(r"\times", "×")
    expr = expr.replace(r"\div", "÷")
    expr = expr.replace(r"\cdot", "×")
    expr = expr.replace(r"\neq", "≠")
    expr = expr.replace(r"\leq", "≤")
    expr = expr.replace(r"\geq", "≥")
    expr = expr.replace(r"\pm", "±")
    expr = expr.replace(r"\sqrt", "√")
    expr = expr.replace(r"\frac", "/")
    # Sobrescritos comuns para potências
    sup_map = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
               "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
               "n": "ⁿ", "m": "ᵐ"}
    # a^{n} → aⁿ  ou  a^n → aⁿ
    def replace_pow(m: re.Match) -> str:
        base = m.group(1)
        exp = m.group(2).strip("{}")
        sup = "".join(sup_map.get(c, c) for c in exp)
        return f"{base}{sup}"
    expr = re.sub(r"([a-zA-Z0-9])\^\{?([^}^\s]+)\}?", replace_pow, expr)
    # Remove chaves restantes
    expr = expr.replace("{", "").replace("}", "")
    # Remove barras invertidas soltas
    expr = re.sub(r"\\([a-zA-Z]+)", r"\1", expr)
    return expr

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
    # =========================================================================
    # MATEMÁTICA
    # =========================================================================
    "Matemática": {
        # ── Anos Iniciais ──────────────────────────────────────────────────
        "1º ano do Ensino Fundamental": (
            "Números naturais de 0 a 99: leitura, escrita, ordenação e comparação (EF01MA01/02); "
            "sequências numéricas de 1 em 1, 2 em 2, 5 em 5 e 10 em 10; "
            "adição e subtração com resultados até 20, sem reagrupamento (EF01MA06/07); "
            "noção de dobro e metade com objetos concretos; "
            "figuras geométricas planas (quadrado, retângulo, triângulo, círculo) — reconhecimento; "
            "medidas de comprimento e tempo: noções (mais longo, mais curto; antes, depois, ontem, hoje); "
            "organização de dados em tabelas e listas simples. "
            "NÃO trabalhar: reagrupamento, multiplicação, divisão, frações ou decimais."
        ),
        "2º ano do Ensino Fundamental": (
            "Números naturais até 1000: leitura, escrita, composição e decomposição (EF02MA01); "
            "adição e subtração com reagrupamento (EF02MA07); "
            "multiplicação como adição repetida — tabuada de 2, 3, 4 e 5 (EF02MA08); "
            "metade e dobro; noção de quarta parte com objetos concretos; "
            "figuras geométricas planas e espaciais: reconhecimento e características básicas; "
            "medidas: comprimento (m, cm), massa (kg, g) e capacidade (l) — noções práticas; "
            "gráficos de barras simples: leitura e construção. "
            "NÃO trabalhar: tabuada completa, divisão formal, frações escritas, decimais."
        ),
        "3º ano do Ensino Fundamental": (
            "Números naturais até 99 999: leitura, escrita e valor posicional (EF03MA01); "
            "adição e subtração com reagrupamento; multiplicação (tabuada completa até 9×9) (EF03MA08); "
            "divisão exata como operação inversa da multiplicação (EF03MA09); "
            "frações como parte de um todo: metade, terça, quarta e quinta parte — representação concreta; "
            "perímetro de figuras planas por contagem ou adição dos lados; "
            "medidas de tempo: horas e minutos; calendário; "
            "leitura de tabelas e gráficos de barras. "
            "NÃO trabalhar: números decimais, porcentagem, potenciação, frações equivalentes formais."
        ),
        "4º ano do Ensino Fundamental": (
            "Números naturais até 1 000 000: leitura, escrita, comparação e ordenação (EF04MA01); "
            "as quatro operações com números naturais (incluindo divisão com resto) (EF04MA08/09); "
            "frações equivalentes e simplificação básica; comparação de frações de mesmo denominador; "
            "números decimais: décimos e centésimos — leitura, escrita e representação na reta (EF04MA10); "
            "área de quadrado e retângulo por contagem de quadradinhos ou fórmula simples; "
            "ângulos: reto, agudo e obtuso — identificação; "
            "gráficos de linhas: leitura e interpretação. "
            "NÃO trabalhar: operações com decimais, porcentagem, potenciação, equações."
        ),
        "5º ano do Ensino Fundamental": (
            "Números naturais e decimais: as quatro operações com decimais (EF05MA07/08); "
            "frações: equivalência, comparação, adição e subtração de frações de mesmo denominador (EF05MA04/05); "
            "porcentagem: noções básicas de 10%, 25%, 50% e 100% associadas a frações (EF05MA06) — "
            "NÃO trabalhar porcentagem com regra de três; "
            "razão e proporção: introdução (EF05MA09); "
            "geometria: polígonos regulares, área e perímetro de retângulos e triângulos; "
            "volume: noção de cubo (contagem de cubinhos); "
            "dados: tabelas de dupla entrada, gráficos de barras e pictogramas. "
            "NÃO trabalhar: potenciação, radiciação, equações, números negativos."
        ),
        # ── Anos Finais ────────────────────────────────────────────────────
        "6º ano do Ensino Fundamental": (
            "Números inteiros (positivos, negativos e zero): representação na reta numérica, "
            "comparação e ordenação (EF06MA01); operações com inteiros: adição e subtração (EF06MA03); "
            "múltiplos, divisores, MDC e MMC (EF06MA05/06); "
            "potenciação como multiplicação repetida, base e expoente naturais (EF06MA07) — "
            "APENAS expoentes naturais; propriedades: produto/quociente de mesma base, potência de potência; "
            "NÃO trabalhar expoentes negativos, fracionários nem radiciação (são do 7º e 8º anos); "
            "razão, proporção e porcentagem sem regra de três formal (EF06MA08/09); "
            "área de triângulo e paralelogramo; volume do paralelepípedo (EF06MA21/22); "
            "coordenadas cartesianas nos 4 quadrantes (EF06MA20)."
        ),
        "7º ano do Ensino Fundamental": (
            "Números racionais: frações e decimais, representação na reta numérica (EF07MA01); "
            "operações com racionais: adição, subtração, multiplicação e divisão (EF07MA02/03); "
            "potenciação com expoentes inteiros NEGATIVOS — introdução conceitual (EF07MA02); "
            "radiciação introdutória: raiz quadrada e cúbica de perfeitos (EF07MA02) — "
            "ex.: √25 = 5, ³√27 = 3 — APENAS quadrados e cubos perfeitos; "
            "NÃO trabalhar raízes de não-perfeitos, expoentes fracionários (8º ano); "
            "expressões algébricas: variável, monômios, polinômios simples (EF07MA13); "
            "equações do 1º grau com uma incógnita (EF07MA14); "
            "porcentagem e juros simples (EF07MA11); proporcionalidade direta e inversa; "
            "geometria: escala, semelhança de figuras, ângulos de triângulo (EF07MA20/21); "
            "circunferência e círculo: comprimento e área (EF07MA22)."
        ),
        "8º ano do Ensino Fundamental": (
            "Potências com expoentes inteiros negativos e fracionários (EF08MA02); "
            "notação científica (EF08MA02); "
            "números irracionais: √2, √3 — noção e localização na reta (EF08MA01); "
            "radiciação de não-perfeitos (aproximação); "
            "equações do 1º grau com duas variáveis; sistemas de equações do 1º grau (EF08MA15); "
            "equação do 2º grau: conceito e resolução por fórmula de Bhaskara (EF08MA16); "
            "funções do 1º grau: definição, gráfico, crescimento e decrescimento (EF08MA17); "
            "teorema de Pitágoras: enunciado, verificação e aplicações (EF08MA12); "
            "probabilidade: espaço amostral, eventos (EF08MA18); "
            "estatística: média aritmética, mediana e moda (EF08MA19)."
        ),
        "9º ano do Ensino Fundamental": (
            "Funções: revisão do 1º grau; função do 2º grau: gráfico (parábola), raízes, vértice (EF09MA06); "
            "progressões aritméticas e geométricas: termo geral e soma (EF09MA07); "
            "trigonometria no triângulo retângulo: seno, cosseno e tangente (EF09MA08); "
            "semelhança de triângulos e relações métricas (EF09MA11); "
            "geometria espacial: volume de prismas, pirâmides, cilindros, cones e esferas (EF09MA19); "
            "análise combinatória: arranjo, combinação e permutação (noções) (EF09MA21); "
            "estatística: gráficos de setor, histogramas, desvio padrão (noções) (EF09MA22)."
        ),
        # ── Ensino Médio ───────────────────────────────────────────────────
        "1º ano do Ensino Médio": (
            "Conjuntos numéricos: N, Z, Q, I, R — operações e propriedades; "
            "funções: conceito, domínio, imagem; função do 1º grau (revisão e aprofundamento); "
            "função do 2º grau: forma canônica, discriminante, gráfico; "
            "função modular: gráfico e equações; "
            "função exponencial: propriedades e gráfico; "
            "progressões aritméticas e geométricas (revisão e aplicações financeiras); "
            "trigonometria: círculo trigonométrico, funções sen, cos e tg, identidades básicas."
        ),
        "2º ano do Ensino Médio": (
            "Função logarítmica: definição, propriedades, equações e inequações logarítmicas; "
            "trigonometria avançada: lei dos senos, lei dos cossenos; "
            "geometria analítica: ponto, reta (equação, coeficiente angular, paralelismo, perpendicularismo), "
            "circunferência; "
            "matrizes: operações, determinantes (Sarrus e Laplace); "
            "sistemas lineares: Cramer e escalonamento; "
            "polinômios: operações, raízes, teorema do resto; "
            "probabilidade: eventos, P(A∪B), probabilidade condicional; "
            "estatística: distribuições de frequência, medidas de dispersão."
        ),
        "3º ano do Ensino Médio": (
            "Revisão e integração de funções (preparação ENEM/vestibulares); "
            "geometria espacial: prismas, pirâmides, cilindros, cones, esferas — áreas e volumes; "
            "análise combinatória: permutações, arranjos, combinações (aprofundamento); "
            "probabilidade: binomial (noções); distribuições estatísticas; "
            "logaritmos: aplicações (juros compostos, escala logarítmica); "
            "matemática financeira: juros simples e compostos, amortizações (noções); "
            "revisão geral de geometria analítica e trigonometria."
        ),
    },
    # =========================================================================
    # CIÊNCIAS (Ensino Fundamental — a disciplina se divide em Biologia,
    # Física e Química no Ensino Médio)
    # =========================================================================
    "Ciências": {
        # ── Anos Iniciais ──────────────────────────────────────────────────
        "1º ano do Ensino Fundamental": (
            "O corpo humano: partes do corpo, sentidos (visão, audição, olfato, paladar, tato) (EF01CI01); "
            "saúde e higiene pessoal: hábitos de higiene, prevenção de doenças (EF01CI02); "
            "materiais e suas propriedades: textura, cor, forma, peso — objetos do cotidiano (EF01CI04); "
            "seres vivos e não vivos: animais, plantas e objetos — diferenciação básica (EF01CI05); "
            "dia e noite: observação do céu, sol e lua (EF01CI07)."
        ),
        "2º ano do Ensino Fundamental": (
            "Seres vivos: animais (características, alimentação, locomoção) e plantas (partes: raiz, caule, folha, flor, fruto) (EF02CI04/05); "
            "ciclos de vida: nascimento, crescimento, reprodução, morte (EF02CI05); "
            "materiais e transformações: sólido, líquido e gasoso — mudanças simples (EF02CI01); "
            "meio ambiente: cuidados com a natureza, reciclagem, redução do lixo (EF02CI09); "
            "água: importância, usos e preservação (EF02CI02)."
        ),
        "3º ano do Ensino Fundamental": (
            "Produção de som e luz: fontes sonoras e luminosas; propagação e sombras (EF03CI01/02); "
            "saúde: alimentação saudável, grupos alimentares, roda dos alimentos (EF03CI06); "
            "solo: composição, erosão, importância para seres vivos (EF03CI08); "
            "animais: características morfológicas e comportamentais; adaptações ao ambiente (EF03CI04); "
            "transformações na natureza: cadeias alimentares simples (EF03CI07)."
        ),
        "4º ano do Ensino Fundamental": (
            "Ciclo da água: evaporação, condensação, precipitação; importância para os seres vivos (EF04CI08); "
            "microrganismos: vírus e bactérias — conceito básico, doenças comuns e prevenção (EF04CI07); "
            "sistema digestório: órgãos principais e função da digestão (EF04CI04); "
            "plantas: fotossíntese (conceito básico), respiração e reprodução das plantas (EF04CI03); "
            "preservação ambiental: poluição do ar, água e solo; ações humanas e impactos (EF04CI10)."
        ),
        "5º ano do Ensino Fundamental": (
            "Sistema solar: planetas, satélites, estrelas, cometas; movimentos de rotação e translação (EF05CI10/11); "
            "eletricidade: circuitos simples, condutores e isolantes (EF05CI01); "
            "transformações de energia: elétrica, luminosa, sonora, química, térmica (noções) (EF05CI02); "
            "ecossistemas brasileiros: florestas, cerrado, caatinga — biodiversidade e ameaças (EF05CI09); "
            "reprodução humana: puberdade, mudanças no corpo, higiene (EF05CI06/07). "
            "NÃO trabalhar: célula (6º ano), química detalhada, física formal."
        ),
        # ── Anos Finais ────────────────────────────────────────────────────
        "6º ano do Ensino Fundamental": (
            "Matéria e energia: propriedades da matéria, estados físicos (sólido, líquido, gasoso) e "
            "mudanças de estado (fusão, solidificação, vaporização, condensação, sublimação) (EF06CI01/02); "
            "misturas: homogêneas e heterogêneas; métodos de separação (filtração, decantação, destilação) (EF06CI03); "
            "célula como unidade da vida (EF06CI05): membrana plasmática, citoplasma, núcleo, organelas básicas; "
            "célula animal x vegetal; procariota x eucariota; "
            "classificação dos seres vivos: 5 reinos — introdução (EF06CI06); "
            "ecossistemas: biomas brasileiros (Amazônia, Cerrado, Mata Atlântica, Caatinga, Pampa, Pantanal), "
            "cadeias e teias alimentares (EF06CI07/08). "
            "NÃO trabalhar: genética, química aprofundada, física formal."
        ),
        "7º ano do Ensino Fundamental": (
            "Seres vivos — diversidade: vírus (estrutura, reprodução, doenças); "
            "bactérias (procariotos, importância e doenças); protistas e fungos (EF07CI01/02); "
            "plantas: morfologia (raiz, caule, folha, flor, fruto, semente), fotossíntese e respiração celular, "
            "reprodução sexuada e assexuada (EF07CI04/05); "
            "animais: invertebrados (poríferos, cnidários, platelmintos, nematelmintos, anelídeos, "
            "moluscos, artrópodes, equinodermos) e vertebrados (peixes, anfíbios, répteis, aves, mamíferos) (EF07CI06); "
            "ecologia: interações ecológicas (predatismo, parasitismo, mutualismo, comensalismo) (EF07CI07); "
            "solo e recursos hídricos: composição, erosão, poluição; "
            "ciclos biogeoquímicos: água, carbono, nitrogênio (EF07CI08)."
        ),
        "8º ano do Ensino Fundamental": (
            "Corpo humano — sistemas: digestório, respiratório, circulatório, excretor (EF08CI01/02/03/04); "
            "sistema nervoso e endócrino: coordenação e regulação (EF08CI06); "
            "sistema reprodutor: reprodução humana, gravidez, DST/IST, métodos contraceptivos (EF08CI07/08); "
            "imunologia: sistema imunológico, vacinas e soros (EF08CI05); "
            "hereditariedade e genética: DNA, cromossomos, herança genética (dominância, recessividade), "
            "heredograma básico (EF08CI09); "
            "evolução biológica: Darwin, seleção natural, evidências (EF08CI10); "
            "doenças sexualmente transmissíveis e saúde pública."
        ),
        "9º ano do Ensino Fundamental": (
            "Química: átomo (próton, nêutron, elétron), número atômico e de massa; tabela periódica (EF09CI01); "
            "ligações químicas: iônica, covalente e metálica (EF09CI02); "
            "funções inorgânicas: ácidos, bases, sais e óxidos (EF09CI03); "
            "reações químicas: tipos, balanceamento, velocidade e equilíbrio (noções) (EF09CI04); "
            "Física: cinemática — velocidade média, aceleração, MRU e MRUV (EF09CI05); "
            "dinâmica — 3 Leis de Newton; força, massa e aceleração (EF09CI06); "
            "energia: trabalho, potência, energia cinética e potencial, conservação (EF09CI07); "
            "ondas: características, som e luz; eletricidade: tensão, corrente, resistência (EF09CI08); "
            "universo: galáxias, estrelas, sistema solar, origem do universo (Big Bang) (EF09CI14)."
        ),
    },
    # =========================================================================
    # LÍNGUA PORTUGUESA
    # =========================================================================
    "Língua Portuguesa": {
        # ── Anos Iniciais ──────────────────────────────────────────────────
        "1º ano do Ensino Fundamental": (
            "Alfabetização: correspondência grafema-fonema, sílabas simples (EF01LP01/02); "
            "leitura de palavras e frases curtas; reconhecimento de letras maiúsculas e minúsculas; "
            "escrita do próprio nome; cópia e ditado de palavras simples; "
            "oralidade: escuta ativa, recontar histórias ouvidas; "
            "gêneros: parlendas, cantigas, histórias curtas — reconhecimento. "
            "NÃO trabalhar: análise gramatical, classes de palavras, pontuação formal."
        ),
        "2º ano do Ensino Fundamental": (
            "Consolidação da alfabetização: leitura e escrita de frases e textos curtos (EF02LP01/02); "
            "sílabas complexas: dígrafos (ch, lh, nh), encontros consonantais; "
            "separação silábica; noção de acento tônico; "
            "produção de textos curtos: bilhete, lista, convite (EF02LP12); "
            "gêneros: fábula, história em quadrinhos, receita — leitura e interpretação; "
            "vocabulário: sinônimos simples, significado de palavras pelo contexto. "
            "NÃO trabalhar: análise morfológica formal, pontuação complexa."
        ),
        "3º ano do Ensino Fundamental": (
            "Fluência leitora: textos de maior extensão; estratégias de leitura (predição, inferência simples); "
            "escrita de textos narrativos curtos com início, meio e fim (EF03LP14); "
            "parágrafo: conceito e uso; pontuação básica (ponto, vírgula, ponto de interrogação e exclamação); "
            "classes de palavras: substantivo e adjetivo — noção (EF03LP17); "
            "acentuação: oxítonas, paroxítonas, proparoxítonas — reconhecimento oral; "
            "gêneros: notícia simples, poema, carta."
        ),
        "4º ano do Ensino Fundamental": (
            "Leitura e interpretação de textos informativos, literários e de opinião (EF04LP01); "
            "produção de texto dissertativo simples (parágrafo com ideia principal e argumentos) (EF04LP14); "
            "classes de palavras: substantivo, adjetivo, verbo, pronome, artigo — identificação (EF04LP17); "
            "concordância nominal básica: artigo + substantivo + adjetivo (EF04LP19); "
            "pontuação: uso do travessão e dois-pontos em diálogos; "
            "acentuação gráfica: regras básicas (EF04LP16); "
            "gêneros: conto, poema narrativo, notícia, anúncio."
        ),
        "5º ano do Ensino Fundamental": (
            "Leitura crítica: identificar tema, ideia principal, intenção do autor; inferência (EF05LP01); "
            "produção de texto dissertativo: parágrafo introdutório, desenvolvimento e conclusão (EF05LP14); "
            "classes de palavras: verbo (tempo, modo, pessoa) — flexão básica (EF05LP17); "
            "concordância verbal básica: sujeito simples + verbo (EF05LP19); "
            "coesão textual: conectivos simples (mas, porém, porque, portanto) (EF05LP12); "
            "ortografia: uso de s/ss, c/ç, x/ch, g/j (EF05LP16); "
            "gêneros: reportagem, conto de mistério, texto de divulgação científica."
        ),
        # ── Anos Finais ────────────────────────────────────────────────────
        "6º ano do Ensino Fundamental": (
            "Gêneros textuais: conto, crônica, notícia, relato de viagem (EF06LP01/02); "
            "leitura e interpretação: inferência, identificação de tema e argumentos (EF06LP04); "
            "produção textual: parágrafo bem estruturado, coesão e coerência (EF06LP14); "
            "gramática: classes de palavras — substantivo (comum/próprio, concreto/abstrato, coletivo), "
            "adjetivo, verbo (conjugação no presente, passado e futuro), advérbio (EF06LP17/18); "
            "frase, oração e período — distinção; pontuação: uso correto do ponto, vírgula e dois-pontos; "
            "acentuação gráfica: regras gerais (EF06LP16); ortografia básica."
        ),
        "7º ano do Ensino Fundamental": (
            "Gêneros: reportagem, entrevista, poema, texto dramático (EF07LP01/02); "
            "leitura: identificar posicionamento do autor, linguagem persuasiva, ironia (EF07LP04); "
            "produção: texto dissertativo com introdução, desenvolvimento e conclusão (EF07LP14); "
            "gramática: pronomes (pessoais, possessivos, demonstrativos, relativos); "
            "preposições e conjunções — uso e sentido; "
            "concordância nominal e verbal básica (EF07LP18/19); "
            "semântica: sinonímia, antonímia, polissemia, denotação e conotação (EF07LP22)."
        ),
        "8º ano do Ensino Fundamental": (
            "Gêneros argumentativos: editorial, carta argumentativa, debate regrado (EF08LP01/02); "
            "análise crítica de textos midiáticos: fake news, publicidade (EF08LP04); "
            "produção: dissertação argumentativa com tese clara e argumentos estruturados (EF08LP14); "
            "gramática: regência nominal e verbal; crase (uso básico); "
            "concordância nominal e verbal avançada (EF08LP18/19); "
            "figuras de linguagem: metáfora, metonímia, hipérbole, antítese, ironia (EF08LP22); "
            "literatura: cordel, literatura de tradição oral brasileira (EF08LP26)."
        ),
        "9º ano do Ensino Fundamental": (
            "Gêneros: redação dissertativo-argumentativa (estrutura ENEM), artigo de opinião (EF09LP01/02); "
            "análise literária introdutória: classicismo, barroco, romantismo, realismo — estilos de época (EF09LP26); "
            "produção: proposta de intervenção social com respeito aos direitos humanos (EF09LP14); "
            "gramática: sintaxe do período composto — coordenação e subordinação; "
            "orações subordinadas substantivas, adjetivas e adverbiais (EF09LP18); "
            "variação linguística: regional, social, histórica; preconceito linguístico (EF09LP22)."
        ),
        # ── Ensino Médio ───────────────────────────────────────────────────
        "1º ano do Ensino Médio": (
            "Literatura: trovadorismo, humanismo, classicismo e quinhentismo brasileiro (leitura e análise de textos); "
            "redação dissertativo-argumentativa: aprofundamento da estrutura (tese, argumentos, conclusão/proposta); "
            "gramática: morfossintaxe — classes de palavras em contexto de análise textual; "
            "língua e linguagem: variação, registro formal e informal; "
            "gêneros: artigo científico, ensaio, manifesto — leitura e produção."
        ),
        "2º ano do Ensino Médio": (
            "Literatura: barroco, arcadismo, romantismo (prosa e poesia) — análise estética e histórico-cultural; "
            "redação: técnicas argumentativas avançadas (dados, citações, exemplificação, analogia); "
            "gramática: sintaxe — análise do período composto; regência e crase avançadas; "
            "semântica e estilística: figuras de linguagem em textos literários; "
            "gêneros: crônica literária, conto contemporâneo, texto jornalístico de opinião."
        ),
        "3º ano do Ensino Médio": (
            "Literatura: realismo, naturalismo, parnasianismo, simbolismo, pré-modernismo, "
            "modernismo (1ª, 2ª e 3ª fases), literatura contemporânea; "
            "redação ENEM: domínio pleno da estrutura, proposta de intervenção detalhada, "
            "repertório sociocultural; revisão de norma culta; "
            "linguagens da comunicação: multimodalidade, discurso midiático, publicidade crítica; "
            "gramática: revisão geral de sintaxe e análise de textos literários e não literários."
        ),
    },
    # =========================================================================
    # HISTÓRIA
    # =========================================================================
    "História": {
        # ── Anos Iniciais ──────────────────────────────────────────────────
        "1º ano do Ensino Fundamental": (
            "Eu e minha história: identidade, nome, família (EF01HI01); "
            "o tempo e as mudanças: antes e depois na vida da criança e da família; "
            "a escola: história e convivência; regras e direitos (EF01HI03); "
            "os diferentes modos de vida: culturas e tradições familiares."
        ),
        "2º ano do Ensino Fundamental": (
            "A vida em comunidade: bairro, vizinhança, trabalho (EF02HI01); "
            "história local e do município: marcos históricos do lugar onde vive; "
            "diversidade cultural: festas, tradições, culinária de diferentes grupos (EF02HI04); "
            "passado e presente: como as coisas mudaram (transporte, moradia, comunicação)."
        ),
        "3º ano do Ensino Fundamental": (
            "Povos indígenas do Brasil: modos de vida, cultura, territórios (EF03HI01/02); "
            "africanos e afro-brasileiros: contribuições culturais, resistência (EF03HI04); "
            "a cidade: história e organização (EF03HI06); "
            "o trabalho ontem e hoje: transformações no mundo do trabalho."
        ),
        "4º ano do Ensino Fundamental": (
            "Circulação de pessoas, produtos e culturas: rotas comerciais e migrações (EF04HI01); "
            "transformações históricas: invenções e sua influência na vida cotidiana (EF04HI03); "
            "diversidade cultural brasileira: imigração europeia e asiática (EF04HI05); "
            "patrimônio histórico e cultural: material e imaterial (EF04HI06)."
        ),
        "5º ano do Ensino Fundamental": (
            "Povos da América antes da chegada dos europeus: Maias, Astecas, Incas (EF05HI01); "
            "chegada dos europeus à América: expansão marítima, colonização (EF05HI02); "
            "Brasil colonial: exploração do pau-brasil, escravidão indígena e africana (EF05HI03/04); "
            "resistência: quilombos, revoltas coloniais (EF05HI06)."
        ),
        # ── Anos Finais ────────────────────────────────────────────────────
        "6º ano do Ensino Fundamental": (
            "Introdução à História: fontes históricas, tempo cronológico e histórico, "
            "periodização (EF06HI01/02); "
            "Pré-história: surgimento do Homo sapiens, ferramentas, pinturas rupestres (EF06HI03); "
            "Antiguidade Oriental: Mesopotâmia (escrita cuneiforme, código de Hamurábi), "
            "Egito (faraós, pirâmides, hieróglifos), Pérsia, Fenícia e Hebreus (EF06HI04/05); "
            "Grécia Antiga: pólis, democracia ateniense, cultura e filosofia (EF06HI06); "
            "Roma Antiga: República, Império, romanização, queda do Império Romano (EF06HI07)."
        ),
        "7º ano do Ensino Fundamental": (
            "Alta e Baixa Idade Média: feudalismo, servidão, Igreja Católica e poder (EF07HI01/02); "
            "Islamismo: origem, expansão e cultura islâmica (EF07HI03); "
            "Cruzadas: causas, desenvolvimento e consequências (EF07HI04); "
            "Renascimento Cultural e Científico (EF07HI05); "
            "Reforma Protestante e Contrarreforma (EF07HI06); "
            "Grandes Navegações: causas, rotas, consequências para América e África (EF07HI07); "
            "Colonização da América: exploração e resistência dos povos originários (EF07HI08); "
            "escravidão africana: tráfico, culturas africanas, resistência (EF07HI09)."
        ),
        "8º ano do Ensino Fundamental": (
            "Iluminismo: principais pensadores e influências (EF08HI01); "
            "Revoluções burguesas: Inglesa, Americana e Francesa (EF08HI02/03); "
            "Revolução Industrial: causas, fases, condições de trabalho e movimentos operários (EF08HI04); "
            "Brasil Colonial: Capitanias Hereditárias, Governo-Geral, economia açucareira (EF08HI06); "
            "escravidão no Brasil: resistências (quilombos, revoltas) e abolicionismo (EF08HI07); "
            "Independência do Brasil: processo, D. Pedro I, constituição de 1824 (EF08HI08); "
            "Período Regencial e Segundo Reinado; Proclamação da República (EF08HI09)."
        ),
        "9º ano do Ensino Fundamental": (
            "Imperialismo e partilha da África e Ásia (EF09HI01/02); "
            "Primeira Guerra Mundial: causas, desenvolvimento, consequências e Tratado de Versalhes (EF09HI03); "
            "Revolução Russa e surgimento da URSS (EF09HI04); "
            "totalitarismos: nazismo, fascismo e stalinismo (EF09HI05); "
            "Segunda Guerra Mundial: causas, Holocaust, bombas atômicas (EF09HI06); "
            "Guerra Fria: blocos capitalista e socialista, corrida armamentista e espacial (EF09HI07); "
            "descolonização da África e Ásia (EF09HI08); "
            "Brasil República: Era Vargas, Ditadura Militar (1964–1985), redemocratização (EF09HI09/10); "
            "mundo contemporâneo: globalização, terrorismo, crises ambientais."
        ),
        # ── Ensino Médio ───────────────────────────────────────────────────
        "1º ano do Ensino Médio": (
            "Revisão da Antiguidade ao Feudalismo; "
            "Renascimento, Reforma Protestante e Grandes Navegações (aprofundamento); "
            "formação do capitalismo comercial; "
            "colonização das Américas: comparação entre modelos ibérico, inglês e francês; "
            "Brasil Colonial aprofundado: economia, sociedade, cultura e resistências."
        ),
        "2º ano do Ensino Médio": (
            "Iluminismo e Revoluções (Americana, Francesa, Industrial) — aprofundamento; "
            "Imperialismo e neocolonialismo; "
            "Primeira Guerra Mundial e entreguerras; "
            "Revolução Russa; totalitarismos; "
            "Brasil: da Proclamação da República à Era Vargas."
        ),
        "3º ano do Ensino Médio": (
            "Segunda Guerra Mundial e Holocaust (aprofundamento); "
            "Guerra Fria e desdobramentos; descolonização; "
            "Brasil: Ditadura Militar, redemocratização, Constituição de 1988; "
            "mundo contemporâneo: globalização, conflitos regionais, questões ambientais, "
            "movimentos sociais, tecnologia e sociedade; revisão geral para ENEM/vestibulares."
        ),
    },
    # =========================================================================
    # GEOGRAFIA
    # =========================================================================
    "Geografia": {
        # ── Anos Iniciais ──────────────────────────────────────────────────
        "1º ano do Ensino Fundamental": (
            "Eu e meu lugar: casa, escola, bairro — localização espacial (EF01GE01); "
            "orientação: lateralidade (esquerda/direita, frente/atrás, perto/longe); "
            "paisagem: natural e cultural — diferenciação (EF01GE02); "
            "rotinas e organização do espaço cotidiano."
        ),
        "2º ano do Ensino Fundamental": (
            "O bairro e a cidade: características, serviços e convivência (EF02GE01); "
            "mapas: noção de legenda, título e orientação básica (EF02GE06); "
            "atividades econômicas locais: comércio, serviços, agricultura urbana (EF02GE03); "
            "campo e cidade: diferenças e interdependência."
        ),
        "3º ano do Ensino Fundamental": (
            "Brasil: estados, capitais e regiões — localização no mapa (EF03GE08); "
            "diversidade natural do Brasil: clima, vegetação e relevo de forma geral (EF03GE06); "
            "campo e cidade: migrações, êxodo rural (EF03GE03); "
            "atividades econômicas: extrativismo, agropecuária, indústria, serviços (EF03GE04)."
        ),
        "4º ano do Ensino Fundamental": (
            "O campo no Brasil: agricultura familiar e agronegócio; impactos ambientais (EF04GE07); "
            "diversidade cultural brasileira: povos indígenas, quilombolas, comunidades tradicionais (EF04GE05); "
            "representações cartográficas: escala, legenda, rosa dos ventos (EF04GE09); "
            "relevo, hidrografia e clima do Brasil: noções gerais (EF04GE06)."
        ),
        "5º ano do Ensino Fundamental": (
            "Continentes e oceanos: localização e características gerais (EF05GE11); "
            "países da América do Sul: localização, características naturais e culturais (EF05GE12); "
            "questões ambientais mundiais: desmatamento, poluição, aquecimento global (EF05GE10); "
            "fusos horários: noção de diferença de horário entre países (EF05GE14); "
            "globalização: circulação de pessoas, produtos e informações (noções) (EF05GE13)."
        ),
        # ── Anos Finais ────────────────────────────────────────────────────
        "6º ano do Ensino Fundamental": (
            "O sujeito e seu lugar no mundo: identidade, pertencimento e diversidade (EF06GE01); "
            "cartografia: orientação (rosa dos ventos, bússola), coordenadas geográficas (latitude/longitude), "
            "escala, projeções cartográficas (EF06GE08/09); "
            "litosfera: relevo terrestre (tipos e formação), rochas e minerais (EF06GE11); "
            "atmosfera: tempo x clima, elementos e fatores climáticos (EF06GE12); "
            "hidrosfera: rios, oceanos, ciclo da água, bacias hidrográficas (EF06GE13); "
            "impactos ambientais: erosão, desmatamento, poluição — causas e consequências (EF06GE14)."
        ),
        "7º ano do Ensino Fundamental": (
            "Globalização: fluxos de pessoas, capitais e mercadorias; desigualdades mundiais (EF07GE01/02); "
            "América do Sul e Central: paisagens naturais, organização política, econômica e cultural (EF07GE09); "
            "América do Norte: EUA, Canadá e México — características e influências globais (EF07GE10); "
            "África: diversidade física, cultural e histórica; desafios socioeconômicos (EF07GE11); "
            "Oriente Médio: localização, recursos naturais (petróleo), conflitos regionais (EF07GE12)."
        ),
        "8º ano do Ensino Fundamental": (
            "Brasil: formação territorial e organização político-administrativa (EF08GE01); "
            "biomas brasileiros: Amazônia, Cerrado, Mata Atlântica, Caatinga, Pampa, Pantanal "
            "— características e ameaças (EF08GE06); "
            "urbanização e industrialização no Brasil: metrópoles, megalópoles, periferias (EF08GE08); "
            "população brasileira: densidade demográfica, migrações internas, diversidade étnica (EF08GE04); "
            "agropecuária: agricultura familiar vs. agronegócio; questão agrária (EF08GE09); "
            "problemas ambientais brasileiros: desmatamento, queimadas, poluição hídrica (EF08GE12)."
        ),
        "9º ano do Ensino Fundamental": (
            "Geopolítica mundial: blocos econômicos (UE, Mercosul, NAFTA/USMCA, BRICS) (EF09GE01); "
            "conflitos regionais contemporâneos: causas e atores envolvidos (EF09GE02); "
            "matrizes energéticas mundiais: renováveis e não renováveis; transição energética (EF09GE10); "
            "questões ambientais globais: aquecimento global, Protocolo de Kyoto, Acordo de Paris (EF09GE11); "
            "tecnologia e espaço: redes de comunicação, cidades inteligentes, desigualdade digital (EF09GE14); "
            "Ásia: China, Japão e Índia — economia, cultura e influência global (EF09GE12)."
        ),
        # ── Ensino Médio ───────────────────────────────────────────────────
        "1º ano do Ensino Médio": (
            "Cartografia avançada: sensoriamento remoto, SIG (sistemas de informação geográfica); "
            "dinâmica da Terra: placas tectônicas, vulcanismo, terremotos; "
            "climatologia: tipos climáticos mundiais, fatores e elementos do clima; "
            "hidrologia: bacias hidrográficas mundiais, água como recurso estratégico; "
            "geopolítica: Estados, fronteiras, conflitos e organizações internacionais."
        ),
        "2º ano do Ensino Médio": (
            "Globalização e economia mundial: desenvolvimento e subdesenvolvimento, IDH; "
            "regionalização do mundo: América, Europa, África, Ásia e Oceania — aprofundamento; "
            "urbanização mundial: megacidades, problemas urbanos, mobilidade; "
            "industrialização: fordismo, toyotismo, terceira revolução industrial; "
            "questões migratórias: refugiados, diásporas, xenofobia."
        ),
        "3º ano do Ensino Médio": (
            "Brasil no contexto geopolítico mundial; "
            "questões ambientais globais aprofundadas: biodiversidade, desertificação, escassez hídrica; "
            "energia e sustentabilidade; "
            "tecnologia, trabalho e sociedade: automação, desemprego estrutural; "
            "revisão geral de geografia física, humana e econômica para ENEM/vestibulares."
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
    ("system", """Você é um professor especialista em didática do Ensino Básico brasileiro,
com ampla experiência em elaborar materiais pedagógicos claros e acessíveis.

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

⚠️ REGRAS DE FORMATAÇÃO — OBRIGATÓRIAS:
1. NUNCA use notação LaTeX (como \\times, \\div, \\frac, ^{{}} entre parênteses).
   Em vez disso, escreva as operações em texto simples:
   - Use × para multiplicação (ou escreva "vezes")
   - Use ÷ para divisão (ou escreva "dividido por")
   - Para potências, escreva: 2³, 5², 3⁴  (use os caracteres sobrescritos ³ ² ⁴ ⁵ ⁶)
   - OU escreva por extenso: "2 elevado à 3" = 2 × 2 × 2 = 8
2. Escreva em português claro e acessível — como um professor explicaria pessoalmente.
3. Nas propriedades e fórmulas, use linguagem textual:
   - Em vez de a^m × a^n = a^(m+n), escreva:
     "Produto de potências de mesma base: mantemos a base e somamos os expoentes.
      Exemplo: 2³ × 2² = 2^(3+2) = 2⁵ = 32"
4. Não use parênteses matemáticos isolados como (a^m) — escreva diretamente.

Contexto dos documentos curriculares oficiais (BNCC/PCN):
{context}

---

Estruture o conteúdo em Markdown com as seguintes seções OBRIGATÓRIAS:

## 📌 Habilidades BNCC Contempladas
Liste os códigos e descrições das habilidades deste ano que esta aula desenvolve.

## 🚫 O que NÃO trabalhar neste ano
Liste explicitamente os subtópicos que pertencem a anos superiores e devem ser evitados,
com a informação de em que ano eles aparecem.

## 📖 Conteúdo: Explicação para o Professor
Explicação completa do conteúdo para o professor dominar o tema.
Inclua: definições em linguagem acessível, conceitos-chave, contexto prático quando relevante.
Use exemplos numéricos escritos de forma simples, sem notação LaTeX.

## 🎓 Como Apresentar aos Alunos
Roteiro de como explicar o conteúdo em sala, com linguagem adequada à faixa etária.
Inclua: analogias do cotidiano, perguntas disparadoras, exemplos práticos e concretos.
Escreva como se estivesse orientando o professor a falar com os alunos.

## 📝 Exemplos Resolvidos
Pelo menos 3 exemplos resolvidos passo a passo, do mais simples ao mais complexo.
Escreva os cálculos de forma clara, em texto: "3 × 3 × 3 = 27, portanto 3³ = 27".

## ✏️ Atividades para os Alunos
5 a 8 exercícios graduados (fácil → médio → desafiador), todos dentro do escopo do ano.
Para cada atividade, indique o objetivo e a habilidade BNCC exercitada.
Escreva enunciados claros, sem notação LaTeX.

## 💡 Dicas Pedagógicas
Erros comuns dos alunos neste conteúdo e como o professor pode abordá-los.
Sugestões de materiais concretos, jogos ou recursos digitais adequados ao ano.
"""),
    ("human", """Tópico / Conteúdo: {topico}
Componente curricular: {componente}
Ano escolar: {ano}

Gere o conteúdo completo da aula respeitando o escopo curricular do ano informado.
Lembre-se: sem notação LaTeX, escreva tudo em português claro."""),
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

    # Busca contexto nos documentos curriculares com queries específicas
    # 1ª busca: habilidades BNCC específicas do tópico e ano
    query_habilidades = f"habilidades BNCC {topico} {ano_escolar} {componente} EF"
    # 2ª busca: conteúdo pedagógico do tópico
    query_conteudo = f"{topico} {componente} {ano_escolar} ensino aprendizagem"

    docs_hab = similarity_search(query_habilidades, k=5)
    docs_cont = similarity_search(query_conteudo, k=4)

    # Junta e deduplica por conteúdo, priorizando os de habilidades
    seen_contents: set[str] = set()
    docs = []
    for d in docs_hab + docs_cont:
        key = d.page_content[:120]
        if key not in seen_contents:
            seen_contents.add(key)
            docs.append(d)

    # Filtra trechos puramente estruturais/de apresentação da BNCC (pouco úteis)
    _SKIP_PHRASES = [
        "está organizado em cinco áreas",
        "competência específica à qual cada habilidade",
        "recentes mudanças na LDB",
        "Currículos: BNCC e itinerários",
        "itinerários formativos",
        "Parecer CNE/CEB",
    ]
    docs = [
        d for d in docs
        if not any(phrase in d.page_content for phrase in _SKIP_PHRASES)
    ][:8]

    context = "\n\n---\n\n".join(
        f"[{d.metadata.get('source', 'Fonte')}] {d.page_content}"
        for d in docs
    ) or "Sem trechos específicos encontrados no corpus. Use o escopo curricular acima como referência principal."

    llm = get_llm(temperature=0.3)
    chain = CONTENT_PROMPT | llm

    response = chain.invoke({
        "topico": topico,
        "componente": componente,
        "ano": ano_escolar,
        "escopo_curricular": escopo,
        "context": context,
    })
    content_text: str = _fix_latex(_strip_code_fences(response.content))

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
