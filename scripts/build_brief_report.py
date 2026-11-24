"""Render the reviewed Markdown report as a printable PDF.

Requires reportlab. Optional PyMuPDF renders each page for visual review.
Local task dependencies may be installed under ignored .lab/artifact-deps.
"""

import html
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.lab/artifact-deps'))
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak


def main():
    output = ROOT / 'output/pdf'
    output.mkdir(parents=True, exist_ok=True)
    pdf = output / 'ECOMPARTS_Informe_validacion_breve.pdf'
    font, bold = Path('C:/Windows/Fonts/arial.ttf'), Path('C:/Windows/Fonts/arialbd.ttf')
    if font.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont('Body', str(font)))
        pdfmetrics.registerFont(TTFont('BodyBold', str(bold)))
        pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='Body', boldItalic='BodyBold')
    else:
        pdfmetrics.registerFontFamily('Helvetica', normal='Helvetica', bold='Helvetica-Bold')
    family = 'Body' if font.exists() else 'Helvetica'
    strong = 'BodyBold' if font.exists() else 'Helvetica-Bold'
    navy, blue = colors.HexColor('#142D4E'), colors.HexColor('#1767A6')
    styles = {
        'body': ParagraphStyle('BodyText', fontName=family, fontSize=10.2, leading=14.2, spaceAfter=8, textColor=navy),
        'h1': ParagraphStyle('ReportTitle', fontName=strong, fontSize=22, leading=27, spaceAfter=16, textColor=navy),
        'h2': ParagraphStyle('Section', fontName=strong, fontSize=15, leading=20, spaceBefore=8, spaceAfter=11, textColor=blue, keepWithNext=True),
        'cell': ParagraphStyle('Cell', fontName=family, fontSize=9.2, leading=12.3, textColor=navy),
        'head': ParagraphStyle('Head', fontName=strong, fontSize=9.2, leading=12.3, textColor=colors.white),
    }
    def markup(text):
        text = html.escape(text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: '<link color="#1767A6" href="'+html.escape(m[2], quote=True)+'">'+m[1]+'</link>' if m[2].startswith('https://') else m[1], text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'`([^`]+)`', r'<font color="#1767A6">\1</font>', text)
        return text
    def table(rows, widths=None):
        cells = [[Paragraph(markup(value), styles['head' if index == 0 else 'cell']) for value in row]
                 for index, row in enumerate(rows)]
        if widths is None:
            widths = [495 / len(rows[0])] * len(rows[0])
        element = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
        element.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F5FA')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, -1), (-1, -1), .5, colors.HexColor('#BCD0E3')),
        ]))
        return element
    source = (ROOT / 'docs/INFORME_VALIDACION_BREVE.md').read_text(encoding='utf-8').splitlines()
    story, paragraph, rows = [], [], []
    def flush():
        if paragraph:
            story.append(Paragraph(markup(' '.join(paragraph)), styles['body']))
            paragraph.clear()
        if rows:
            n = len(rows[0])
            if n == 3 and rows[0][0] == 'Término':
                widths = [82, 194, 219]
            elif n == 4 and rows[0][0] == 'Tienda':
                widths = [55, 200, 110, 130]
            elif n == 3:
                widths = [285, 105, 105]
            else:
                widths = None
            story.append(table(rows, widths))
            story.append(Spacer(1, 11))
            rows.clear()
    in_code = False
    for line in source:
        if line.startswith('```'):
            if not in_code:
                flush()
            else:
                story.append(table([
                    ['Ubicación', 'Recorrido del pedido'],
                    ['Compose aislado', 'Django guarda el pedido en su base y encola la tarea en Redis. Celery recoge el encargo.'],
                    ['Red privada Docker', 'Celery accede al Service odoo-marketplace del nodo Minikube.'],
                    ['Kubernetes, un nodo', 'Odoo tiene 1 a 3 Pods con PostgreSQL común y un PVC de sesiones y archivos.'],
                ], [125, 370]))
                story.append(Spacer(1, 11))
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith('|'):
            if not rows:
                flush()
            if not re.match(r'^\|[\s:|-]+\|$', line):
                rows.append([cell.strip() for cell in line.strip('|').split('|')])
            continue
        if rows:
            flush()
        if line.startswith('# '):
            flush()
            story.append(Paragraph(markup(line[2:]), styles['h1']))
        elif line.startswith('## '):
            flush()
            if re.match(r'## (3\.|5\.|6\.|7\.|8\.)', line):
                story.append(PageBreak())
            story.append(Paragraph(markup(line[3:]), styles['h2']))
        elif line.startswith('- '):
            flush()
            story.append(Paragraph(markup(line[2:]), styles['body']))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
    flush()
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#BCD0E3'))
        canvas.line(50, 41, 545, 41)
        canvas.setFont(family, 8)
        canvas.setFillColor(navy)
        canvas.drawString(50, 28, 'ECOMPARTS / Validación breve / 23 noviembre 2026')
        canvas.drawRightString(545, 28, str(doc.page))
        canvas.restoreState()
    document = SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=50, rightMargin=50,
                                 topMargin=38, bottomMargin=56, title='ECOMPARTS: validación breve de Kubernetes',
                                 author='Frank / ECOMPARTS')
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    try:
        import pymupdf as fitz
        renders = ROOT / '.lab/report-renders'
        renders.mkdir(exist_ok=True)
        with fitz.open(pdf) as document:
            for index, page in enumerate(document):
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(renders / f'page-{index+1}.png')
            print(f'{len(document)} pages rendered for review')
    except ImportError:
        print('Install PyMuPDF or render with pdftoppm before delivery')
    print(pdf)


if __name__ == '__main__':
    main()
