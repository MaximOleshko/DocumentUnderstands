from io import BytesIO

import docx


def extract_text_from_docx(file_storage) -> str:
    """Extract text from an uploaded .docx file, preserving paragraph breaks."""
    data = file_storage.read()
    document = docx.Document(BytesIO(data))
    return '\n'.join(paragraph.text for paragraph in document.paragraphs)
