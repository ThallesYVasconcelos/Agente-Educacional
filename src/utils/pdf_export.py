"""
Exportação de conteúdo Markdown para PDF.

Usa fpdf2 (puro Python, sem dependências de sistema) com:
- Codificação UTF-8 (acentos, cedilha, caracteres especiais)
- Conversão correta de Markdown: **negrito**, *itálico*, # títulos, - listas
- Sem asteriscos visíveis no output
- Fontes core do PDF (Helvetica) — sem arquivos externos, funciona no Streamlit Cloud
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# Fontes DejaVu (Unicode completo) empacotadas junto ao módulo
_FONTS_DIR = Path(__file__).parent / "fonts"


# ---------------------------------------------------------------------------
# Constantes visuais
# ---------------------------------------------------------------------------

PRIMARY_R, PRIMARY_G, PRIMARY_B = 46, 91, 255
HEADING1_SIZE = 17
HEADING2_SIZE = 13
HEADING3_SIZE = 11
BODY_SIZE = 10
SMALL_SIZE = 9
LINE_H = 5.5
MARGIN = 16


# ---------------------------------------------------------------------------
# Spans inline — parse de **negrito** e *itálico*
# ---------------------------------------------------------------------------

class _Span(NamedTuple):
    text: str
    bold: bool
    italic: bool


_INLINE_RE = re.compile(
    r"\*\*\*(?P<bi>.+?)\*\*\*"   # ***bold+italic***
    r"|\*\*(?P<b>.+?)\*\*"        # **bold**
    r"|__(?P<b2>.+?)__"           # __bold__
    r"|\*(?P<i>.+?)\*"            # *italic*
    r"|_(?P<i2>.+?)_",            # _italic_
    re.DOTALL,
)


def _parse_inline(text: str) -> list[_Span]:
    """Converte texto com marcadores Markdown em lista de Spans tipados."""
    spans: list[_Span] = []
    cursor = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > cursor:
            spans.append(_Span(text[cursor:m.start()], False, False))
        if m.group("bi"):
            spans.append(_Span(m.group("bi"), True, True))
        elif m.group("b") or m.group("b2"):
            content = m.group("b") or m.group("b2")
            spans.append(_Span(content, True, False))
        elif m.group("i") or m.group("i2"):
            content = m.group("i") or m.group("i2")
            spans.append(_Span(content, False, True))
        cursor = m.end()
    if cursor < len(text):
        spans.append(_Span(text[cursor:], False, False))
    return spans or [_Span(text, False, False)]


def _strip_md(text: str) -> str:
    """Remove todos os marcadores Markdown de uma string."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove asteriscos e underscores soltos que sobram
    text = re.sub(r"(?<!\w)[*_]+(?!\w)", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Classe PDF
# ---------------------------------------------------------------------------

class _EduPDF(FPDF):
    def __init__(self, doc_title: str = "EduRAG"):
        super().__init__()
        self._doc_title = doc_title
        self.set_margins(MARGIN, MARGIN + 6, MARGIN)
        self.set_auto_page_break(auto=True, margin=MARGIN)
        # Registra fontes DejaVu para suporte total a UTF-8
        self.add_font("DV", "", str(_FONTS_DIR / "DejaVuSans.ttf"))
        self.add_font("DV", "B", str(_FONTS_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font("DV", "I", str(_FONTS_DIR / "DejaVuSans-Oblique.ttf"))
        self.add_font("DV", "BI", str(_FONTS_DIR / "DejaVuSans-BoldOblique.ttf"))

    # -- Cabeçalho --
    def header(self):
        self.set_fill_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
        self.rect(0, 0, 210, 7, "F")
        self.set_y(10)
        self.set_font("DV", "B", 7)
        self.set_text_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
        self.cell(0, 4, "Assistente do Professor \u2014 EduRAG",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    # -- Rodapé --
    def footer(self):
        self.set_y(-12)
        self.set_font("DV", "", 7)
        self.set_text_color(160, 160, 160)
        self.cell(
            0, 5,
            f"P\u00e1gina {self.page_no()} | Gerado pelo Assistente do Professor (BNCC/PCN)",
            align="C",
        )
        self.set_text_color(0, 0, 0)

    # -- Seleção de fonte --
    def _font(self, bold: bool = False, italic: bool = False, size: int = BODY_SIZE):
        style = ("B" if bold else "") + ("I" if italic else "")
        self.set_font("DV", style, size)

    # -- Escrita inline sem quebrar linha (acumula spans) --
    def _write_spans(self, spans: list[_Span], h: float = LINE_H):
        for span in spans:
            self._font(span.bold, span.italic, BODY_SIZE)
            self.write(h, span.text)

    # -- Título da seção h1/h2/h3 --
    def heading(self, text: str, level: int):
        self.ln(3)
        clean = _strip_md(text)
        if level == 1:
            self.set_fill_color(237, 241, 255)
            self._font(bold=True, size=HEADING1_SIZE)
            self.set_text_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
            self.cell(
                0, 11, clean, fill=True,
                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
        elif level == 2:
            self._font(bold=True, size=HEADING2_SIZE)
            self.set_text_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
            self.cell(0, 8, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            # Linha decorativa
            self.set_draw_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
            self.set_line_width(0.5)
            self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        elif level == 3:
            self._font(bold=True, size=HEADING3_SIZE)
            self.set_text_color(30, 45, 90)
            self.cell(0, 7, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    # -- Linha normal de parágrafo --
    def paragraph(self, spans: list[_Span]):
        self.set_x(MARGIN)
        self._write_spans(spans)
        self.ln(LINE_H)
        self.set_x(MARGIN)

    # -- Bullet list --
    def bullet(self, spans: list[_Span], level: int = 0):
        indent = MARGIN + level * 5
        self.set_x(indent)
        self._font(size=BODY_SIZE)
        bullet = "\u2022" if level == 0 else "\u25e6"
        self.cell(5, LINE_H, bullet)
        self._write_spans(spans)
        self.ln(LINE_H)
        self.set_x(MARGIN)

    # -- Numbered list --
    def numbered(self, spans: list[_Span], num: int):
        self.set_x(MARGIN)
        self._font(bold=True, size=BODY_SIZE)
        self.cell(8, LINE_H, f"{num}.")
        self._font(bold=False, size=BODY_SIZE)
        self._write_spans(spans)
        self.ln(LINE_H)
        self.set_x(MARGIN)

    # -- Blockquote --
    def blockquote(self, text: str):
        self.set_fill_color(240, 243, 255)
        self.set_draw_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
        self.set_line_width(1.2)
        y = self.get_y()
        self._font(italic=True, size=SMALL_SIZE)
        self.set_text_color(60, 75, 120)
        self.set_x(MARGIN + 6)
        self.multi_cell(
            0, LINE_H, _strip_md(text), fill=True,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.line(MARGIN + 1, y, MARGIN + 1, self.get_y())
        self.set_text_color(0, 0, 0)
        self.ln(1)

    # -- Divisor --
    def divider(self):
        self.ln(2)
        self.set_draw_color(200, 210, 240)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        self.ln(3)

    # -- Cabeçalho do documento (título principal) --
    def doc_title(self, title: str):
        self.set_fill_color(237, 241, 255)
        self._font(bold=True, size=HEADING1_SIZE + 3)
        self.set_text_color(PRIMARY_R, PRIMARY_G, PRIMARY_B)
        self.multi_cell(0, 12, _strip_md(title), align="C", fill=True,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(2)
        self.divider()


# ---------------------------------------------------------------------------
# Parser Markdown → chamadas PDF
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+(.*)")
_NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)")
_RULE_RE = re.compile(r"^\s*[-*_]{3,}\s*$")
_BQ_RE = re.compile(r"^>\s?(.*)")


def _clean_llm_output(text: str) -> str:
    """
    Remove artefatos que LLMs às vezes inserem no output:
    - Blocos de código ```markdown ... ``` ou ``` ... ```
    - Linhas que são só backticks
    """
    # Remove blocos ```markdown ... ``` ou ```qualquer_coisa ... ```
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def markdown_to_pdf(markdown_text: str, title: str = "Documento") -> bytes:
    """
    Converte texto Markdown para bytes de PDF.

    Trata corretamente:
    - UTF-8 (acentos, ç, ã, etc.)
    - **negrito** e *itálico* → aplicados como estilos reais (sem asteriscos visíveis)
    - # ## ### → títulos com hierarquia visual
    - - bullet / 1. numerado → listas
    - > blockquote → destaque com borda
    - --- → divisor
    - Remove artefatos de LLM (```markdown, ``` soltos)
    """
    markdown_text = _clean_llm_output(markdown_text)

    pdf = _EduPDF(doc_title=title)
    pdf.add_page()
    pdf.doc_title(title)

    lines = markdown_text.splitlines()
    num_counter = 0

    for raw in lines:
        stripped = raw.strip()

        # Linha vazia
        if not stripped:
            pdf.ln(2)
            num_counter = 0
            continue

        # Divisor
        if _RULE_RE.match(stripped):
            pdf.divider()
            num_counter = 0
            continue

        # Blockquote
        m_bq = _BQ_RE.match(stripped)
        if m_bq:
            pdf.blockquote(m_bq.group(1))
            num_counter = 0
            continue

        # Títulos
        m_h = _HEADING_RE.match(stripped)
        if m_h:
            pdf.heading(m_h.group(2).strip(), len(m_h.group(1)))
            num_counter = 0
            continue

        # Bullet
        m_b = _BULLET_RE.match(raw)
        if m_b:
            level = len(m_b.group(1)) // 2
            pdf.bullet(_parse_inline(m_b.group(2).strip()), level)
            num_counter = 0
            continue

        # Numerado
        m_n = _NUMBERED_RE.match(stripped)
        if m_n:
            num_counter += 1
            pdf.numbered(_parse_inline(m_n.group(2).strip()), num_counter)
            continue

        # Parágrafo normal
        num_counter = 0
        pdf.paragraph(_parse_inline(stripped))

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
