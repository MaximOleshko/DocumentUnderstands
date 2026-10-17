"""
LaTeX to HTML conversion module using plasTeX.

This module provides functions to convert LaTeX content to HTML format
using plasTeX as the conversion engine. The HTML output can then be
converted to DOCX using python-docx and BeautifulSoup.

Requirements:
- plasTeX must be installed (pip install plasTeX)
- beautifulsoup4 must be installed (pip install beautifulsoup4)
- For math rendering, plasTeX uses its own math rendering
"""

from io import BytesIO, StringIO
from typing import Optional
import os
import tempfile
import shutil
import glob

# Try to import required libraries
try:
    import plasTeX
    from plasTeX import TeXDocument, TeXFragment
    from plasTeX.Renderers.XHTML import Renderer as XHTMLRenderer
    from plasTeX.Compile import parse
    from plasTeX.client import defaultConfig
    from plasTeX.TeX import TeX
    PLASTEX_AVAILABLE = True
except ImportError as e:
    PLASTEX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class PlasTeXNotFoundError(RuntimeError):
    """Raised when plasTeX is not found."""
    pass


class BeautifulSoupNotFoundError(RuntimeError):
    """Raised when BeautifulSoup is not found."""
    pass


def is_plastex_available() -> bool:
    """Check if plasTeX is available."""
    return PLASTEX_AVAILABLE


def is_beautifulsoup_available() -> bool:
    """Check if BeautifulSoup is available."""
    return BEAUTIFULSOUP_AVAILABLE


def latex_to_html(latex_content: str) -> str:
    """
    Convert LaTeX content to HTML using plasTeX.
    
    Args:
        latex_content: The LaTeX content to convert
        
    Returns:
        HTML string
        
    Raises:
        PlasTeXNotFoundError: If plasTeX is not installed
        RuntimeError: If conversion fails
    """
    if not PLASTEX_AVAILABLE:
        raise PlasTeXNotFoundError(
            'plasTeX is required for LaTeX conversion. '
            'Please install it with: pip install plasTeX'
        )
    
    if not latex_content.strip():
        return ""
    
    # Wrap in minimal document if needed
    full_latex = _wrap_latex_content(latex_content)
    
    # Create temporary directory for plasTeX processing
    temp_dir = tempfile.mkdtemp()
    old_cwd = os.getcwd()
    
    try:
        # Write LaTeX to temporary file
        tex_path = os.path.join(temp_dir, 'input.tex')
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(full_latex)
        
        # Change to temp directory
        os.chdir(temp_dir)
        
        # Create config
        config = defaultConfig()
        config['general']['renderer'] = 'XHTML'
        config['general']['theme'] = 'minimal'
        config['images']['enabled'] = False
        config['files']['directory'] = temp_dir
        config['files']['filename'] = 'output'
        
        # Parse the file
        tex = parse('input.tex', config)
        
        # Get the document
        document = tex.ownerDocument
        document.config = config
        
        # Render to HTML - plasTeX writes to file
        renderer = XHTMLRenderer()
        renderer.render(document)
        
        # Read the output HTML file
        # plasTeX creates index.html or output.html
        html_file = None
        for f in glob.glob(os.path.join(temp_dir, '*.html')) + glob.glob(os.path.join(temp_dir, '*.xhtml')):
            if os.path.isfile(f):
                html_file = f
                break
        
        if html_file is None:
            raise RuntimeError('plasTeX did not create an output HTML file')
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Extract body content from HTML
        html_content = _extract_body(html)
        
        return html_content
        
    except Exception as e:
        raise RuntimeError(f'plasTeX conversion failed: {e}')
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def _wrap_latex_content(latex_content: str) -> str:
    """
    Wrap LaTeX content in a minimal document structure.
    """
    # Check if it's already a full document
    if '\\documentclass' in latex_content or '\\begin{document}' in latex_content:
        return latex_content
    
    # Wrap in minimal document
    return r'''\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amssymb}

\begin{document}
''' + latex_content + r'''
\end{document}
'''


def _extract_body(html: str) -> str:
    """
    Extract the body content from a full HTML document.
    """
    import re
    
    # Try to extract body content
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if body_match:
        return body_match.group(1)
    
    # If no body tag, try to extract content between <html> and </html>
    html_match = re.search(r'<html[^>]*>(.*?)</html>', html, re.DOTALL)
    if html_match:
        return html_match.group(1)
    
    return html


def html_to_docx(html_content: str) -> BytesIO:
    """
    Convert HTML content to DOCX using python-docx and BeautifulSoup.
    
    This function uses BeautifulSoup to parse HTML and python-docx
    to create a properly formatted DOCX document.
    
    Args:
        html_content: HTML string to convert
        
    Returns:
        BytesIO object containing the DOCX file
        
    Raises:
        BeautifulSoupNotFoundError: If BeautifulSoup is not installed
        RuntimeError: If conversion fails
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        raise BeautifulSoupNotFoundError(
            'beautifulsoup4 is required for HTML conversion. '
            'Please install it with: pip install beautifulsoup4'
        )
    
    from docx import Document
    from bs4 import BeautifulSoup
    from docx.shared import Pt
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    
    if not html_content.strip():
        doc = Document()
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Create DOCX document
    doc = Document()
    
    # Process body or root
    body = soup.find('body') or soup.find()
    
    if body is None:
        body = soup
    
    _process_html_node(body, doc)
    
    # Save to BytesIO
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _process_html_node(node, doc):
    """
    Recursively process HTML nodes and add to DOCX document.
    """
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    
    # Skip None
    if node is None:
        return
    
    # Check if it's a string (NavigableString)
    if isinstance(node, str):
        if node.strip():
            if doc.paragraphs:
                last_para = doc.paragraphs[-1]
                last_para.add_run(node.strip())
            else:
                doc.add_paragraph(node.strip())
        return
    
    # Check if it has a name attribute (it's a tag)
    if hasattr(node, 'name') and node.name is not None:
        tag_name = node.name
    else:
        # It's a NavigableString or other non-tag node
        if isinstance(node, str) and node.strip():
            if doc.paragraphs:
                last_para = doc.paragraphs[-1]
                last_para.add_run(node.strip())
            else:
                doc.add_paragraph(node.strip())
        return
    
    # Handle different node types
    if tag_name == 'p':
        _process_paragraph(node, doc)
    
    elif tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        _process_heading(node, doc)
    
    elif tag_name == 'ul':
        _process_list(node, doc, ordered=False)
    
    elif tag_name == 'ol':
        _process_list(node, doc, ordered=True)
    
    elif tag_name == 'li':
        # Will be handled by list processing
        pass
    
    elif tag_name == 'table':
        _process_table(node, doc)
    
    elif tag_name == 'hr':
        doc.add_paragraph('---')
    
    elif tag_name == 'div':
        # Process children
        if hasattr(node, 'children'):
            for child in node.children:
                _process_html_node(child, doc)
    
    elif tag_name == 'span':
        # Process inline span
        _process_inline(node, doc)
    
    elif tag_name in ('strong', 'b'):
        _process_inline(node, doc, bold=True)
    
    elif tag_name in ('em', 'i'):
        _process_inline(node, doc, italic=True)
    
    elif tag_name == 'br':
        # Add a new paragraph for line break
        if doc.paragraphs:
            doc.add_paragraph('')
    
    elif tag_name == 'img':
        # Handle images (math formulas are rendered as images by plasTeX)
        _process_image(node, doc)
    
    else:
        # For unknown tags, just process children
        if hasattr(node, 'children'):
            for child in node.children:
                _process_html_node(child, doc)


def _process_paragraph(node, doc):
    """Process a paragraph node."""
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    
    # Get text and handle inline formatting
    para = doc.add_paragraph()
    
    # Process children with inline formatting
    _process_inline_children(node, para)
    
    # Apply paragraph styles
    style = node.get('style', '')
    if 'text-align: center' in style:
        para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    elif 'text-align: right' in style:
        para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT


def _process_heading(node, doc):
    """Process a heading node."""
    level = int(node.name[1])
    text = node.get_text().strip()
    if text:
        doc.add_heading(text, level=level)


def _process_list(node, doc, ordered: bool):
    """Process a list node."""
    items = node.find_all('li', recursive=False)
    for i, li in enumerate(items):
        text = li.get_text().strip()
        if text:
            if ordered:
                para = doc.add_paragraph(f"{i+1}. {text}", style='List Number')
            else:
                para = doc.add_paragraph(text, style='List Bullet')


def _process_table(node, doc):
    """Process a table node."""
    from docx import Document
    
    # Count rows and columns
    rows = node.find_all('tr')
    if not rows:
        return
    
    # Determine number of columns
    cols = max(len(row.find_all(['th', 'td'])) for row in rows)
    
    # Create table
    table = doc.add_table(rows=len(rows), cols=cols)
    
    # Process each row
    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        for j, cell in enumerate(cells):
            if j < cols:
                cell_text = cell.get_text().strip()
                table.cell(i, j).text = cell_text


def _process_inline(node, doc, bold: bool = False, italic: bool = False):
    """Process an inline element."""
    text = node.get_text().strip()
    if text:
        if doc.paragraphs:
            last_para = doc.paragraphs[-1]
            run = last_para.add_run(text)
            run.bold = bold
            run.italic = italic
        else:
            para = doc.add_paragraph(text)
            if bold:
                para.runs[0].bold = True
            if italic:
                para.runs[0].italic = True


def _process_image(node, doc):
    """Process an image node (math formulas are rendered as images)."""
    from docx import Document
    
    # Get alt text which contains the LaTeX formula
    alt_text = node.get('alt', '')
    if alt_text:
        # Add the alt text (LaTeX formula) as text
        if doc.paragraphs:
            last_para = doc.paragraphs[-1]
            last_para.add_run(alt_text)
        else:
            doc.add_paragraph(alt_text)


def _process_inline_children(node, paragraph):
    """Process children of a node, preserving inline formatting."""
    from docx import Document
    from docx.shared import Pt
    
    if hasattr(node, 'children'):
        for child in node.children:
            if child.name is None:
                # Text node
                if isinstance(child, str) and child.strip():
                    run = paragraph.add_run(child.strip())
            elif child.name in ('strong', 'b'):
                text = child.get_text().strip()
                if text:
                    run = paragraph.add_run(text)
                    run.bold = True
            elif child.name in ('em', 'i'):
                text = child.get_text().strip()
                if text:
                    run = paragraph.add_run(text)
                    run.italic = True
            elif child.name == 'span':
                _process_inline_children(child, paragraph)
            elif child.name == 'img':
                # Handle inline images (math formulas)
                alt_text = child.get('alt', '')
                if alt_text:
                    run = paragraph.add_run(alt_text)
            else:
                # For other tags, just get text
                text = child.get_text().strip()
                if text:
                    run = paragraph.add_run(text)


def convert_latex_to_docx(latex_content: str) -> BytesIO:
    """
    Convert LaTeX content directly to DOCX.
    
    This is the main function that combines LaTeX -> HTML -> DOCX conversion.
    
    Args:
        latex_content: The LaTeX content to convert
        
    Returns:
        BytesIO object containing the DOCX file
        
    Raises:
        RuntimeError: If conversion fails
    """
    # Step 1: LaTeX to HTML
    html_content = latex_to_html(latex_content)
    
    # Step 2: HTML to DOCX
    docx_buffer = html_to_docx(html_content)
    
    return docx_buffer
