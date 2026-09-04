from collections import Counter
from io import BytesIO
from typing import Optional

import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from exports.settings import ExportSettings
from exports.text_utils import remove_emojis

NEAR_WHITE_THRESHOLD = 240
TINY_SIZE_PT = 2.0
SMALL_RELATIVE_RATIO = 0.4
HIDDEN_COLOR_VALUES = {
    'FFFFFF', 'FEFEFE', 'FDFDFD', 'FCFCFC', 'FAFAFA', 'F8F8F8',
    'F7F7F7', 'F5F5F5', 'F0F0F0',
}


def process_docx_bytes(data: bytes, settings: ExportSettings) -> BytesIO:
    document = docx.Document(BytesIO(data))
    if settings.strip_hidden_text:
        _strip_hidden_content(document)
    if settings.strip_emojis:
        _strip_emojis_from_document(document)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer


def _iter_paragraphs(container) -> list[Paragraph]:
    paragraphs = list(getattr(container, 'paragraphs', []))
    for table in getattr(container, 'tables', []):
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(_iter_paragraphs(cell))
    return paragraphs


def _all_paragraphs(document) -> list[Paragraph]:
    paragraphs = _iter_paragraphs(document)
    for section in document.sections:
        paragraphs.extend(_iter_paragraphs(section.header))
        paragraphs.extend(_iter_paragraphs(section.footer))
    return paragraphs


def _run_size_pt(run: Run) -> Optional[float]:
    if run.font.size is not None:
        return float(run.font.size.pt)
    rPr = run._element.find(qn('w:rPr'))
    if rPr is None:
        return None
    sz = rPr.find(qn('w:sz'))
    if sz is None:
        return None
    value = sz.get(qn('w:val'))
    if not value:
        return None
    try:
        return int(value) / 2.0
    except ValueError:
        return None


def _is_on_off(element) -> bool:
    if element is None:
        return False
    value = element.get(qn('w:val'))
    if value is None:
        return True
    return value.lower() not in {'0', 'false', 'off'}


def _run_color_hex(run: Run) -> Optional[str]:
    rPr = run._element.find(qn('w:rPr'))
    if rPr is None:
        return None
    color = rPr.find(qn('w:color'))
    if color is None:
        return None
    theme = color.get(qn('w:themeColor'))
    if theme in {'background1', 'lt1'}:
        return 'FFFFFF'
    value = color.get(qn('w:val'))
    if not value:
        return None
    return value.upper()


def _hex_is_near_white(value: Optional[str]) -> bool:
    if not value:
        return False
    if value in HIDDEN_COLOR_VALUES:
        return True
    if len(value) != 6:
        return False
    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return False
    return red >= NEAR_WHITE_THRESHOLD and green >= NEAR_WHITE_THRESHOLD and blue >= NEAR_WHITE_THRESHOLD


def _is_vanished(run: Run) -> bool:
    rPr = run._element.find(qn('w:rPr'))
    if rPr is None:
        return False
    return _is_on_off(rPr.find(qn('w:vanish'))) or _is_on_off(rPr.find(qn('w:webHidden')))


def _typical_size_pt(paragraphs: list[Paragraph]) -> Optional[float]:
    sizes = []
    for paragraph in paragraphs:
        for run in paragraph.runs:
            if not (run.text or '').strip():
                continue
            if _is_vanished(run) or _hex_is_near_white(_run_color_hex(run)):
                continue
            size = _run_size_pt(run)
            if size is not None:
                sizes.append(round(size, 1))
    if not sizes:
        return None
    return Counter(sizes).most_common(1)[0][0]


def _is_hidden_run(run: Run, typical_size: Optional[float]) -> bool:
    text = run.text or ''
    if not text:
        return False
    if _is_vanished(run):
        return True
    if _hex_is_near_white(_run_color_hex(run)):
        return True

    size = _run_size_pt(run)
    if size is not None:
        if size <= TINY_SIZE_PT:
            return True
        if typical_size and size < typical_size * SMALL_RELATIVE_RATIO:
            return True
    return False


def _strip_hidden_content(document) -> None:
    paragraphs = _all_paragraphs(document)
    typical_size = _typical_size_pt(paragraphs)
    for paragraph in paragraphs:
        for run in list(paragraph.runs):
            if _is_hidden_run(run, typical_size):
                parent = run._element.getparent()
                if parent is not None:
                    parent.remove(run._element)


def _strip_emojis_from_document(document) -> None:
    for paragraph in _all_paragraphs(document):
        for run in paragraph.runs:
            if run.text:
                run.text = remove_emojis(run.text)
