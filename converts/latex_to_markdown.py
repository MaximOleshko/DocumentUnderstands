from __future__ import annotations
import re
import logging
from typing import Optional, Tuple, List

from pylatexenc.latex2text import LatexNodes2Text

# Set up debug logging
logger = logging.getLogger('latex_to_markdown')
logger.setLevel(logging.DEBUG)


def latex_to_markdown(latex_content: str, for_docx: bool = True) -> str:
    """
    Convert LaTeX content to Markdown format.

    Uses pylatexenc to parse LaTeX and convert it to plain text with Markdown formatting.
    Handles common LaTeX constructs like sections, lists, math, and special characters.
    
    For math formulas:
    - If for_docx=True: converts LaTeX math to unicode symbols for DOCX compatibility
    - If for_docx=False: preserves LaTeX format in $...$ for PDF/ODT (via LibreOffice)
    
    Args:
        latex_content: The LaTeX content to convert
        for_docx: If True, convert math to unicode for DOCX. If False, preserve LaTeX.
    """
    logger.debug(f"latex_to_markdown input: {repr(latex_content[:200])}")
    logger.debug(f"for_docx: {for_docx}")
    
    if not latex_content.strip():
        return ""

    # Step 1: Extract and replace math formulas with placeholders BEFORE pylatexenc sees them
    latex_with_placeholders, placeholders_info = _extract_and_replace_math(latex_content)
    logger.debug(f"After math extraction: {repr(latex_with_placeholders[:200])}")
    logger.debug(f"Placeholders info: {placeholders_info}")
    
    # Step 2: Clean and preprocess LaTeX (without math formulas)
    cleaned_latex = _preprocess_latex(latex_with_placeholders)
    logger.debug(f"After preprocessing: {repr(cleaned_latex[:200])}")
    
    # Step 3: Use pylatexenc for basic conversion (math is now protected)
    converter = LatexNodes2Text()
    try:
        plain_text = converter.latex_to_text(cleaned_latex)
        logger.debug(f"After pylatexenc: {repr(plain_text[:200])}")
    except Exception as e:
        logger.debug(f"pylatexenc failed: {e}")
        plain_text = _strip_latex_commands(cleaned_latex)
    
    # Step 4: Post-process to improve Markdown formatting
    markdown = _post_process_to_markdown(plain_text)
    logger.debug(f"After post-processing: {repr(markdown[:200])}")
    
    # Step 5: Restore math formulas
    # If for_docx, convert LaTeX math to unicode; otherwise preserve LaTeX
    markdown = _restore_math_formulas(markdown, placeholders_info, for_docx)
    logger.debug(f"Final markdown: {repr(markdown[:200])}")
    
    return markdown


def _extract_and_replace_math(latex: str) -> Tuple[str, List[Tuple[str, str, str]]]:
    """
    Extract math formulas from LaTeX, replace them with placeholders,
    and return the modified LaTeX and info about the formulas.
    
    This MUST be done BEFORE pylatexenc processes the text,
    otherwise pylatexenc will convert the math to unicode characters.
    
    Uses a simple character-by-character parser to handle:
    - Inline math: $...$ (single dollar signs)
    - Display math: $$...$$ (double dollar signs)
    
    Returns (latex_with_placeholders, placeholders_info)
    where placeholders_info is a list of (placeholder, math_type, formula)
    """
    logger.debug(f"_extract_and_replace_math input: {repr(latex[:200])}")
    
    placeholders_info = []
    result = []
    i = 0
    
    while i < len(latex):
        # Check for display math: $$
        if i + 1 < len(latex) and latex[i] == '$' and latex[i+1] == '$':
            formula = _extract_until(latex, i + 2, '$$')
            if formula is not None:
                placeholder = f'__MATH_DISPLAY_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'display', formula))
                result.append(placeholder)
                i += len(formula) + 4  # Skip past $$...$$
                continue
            else:
                # Malformed, just continue
                result.append(latex[i])
                i += 1
                continue
        
        # Check for inline math: $
        elif latex[i] == '$':
            formula = _extract_until(latex, i + 1, '$')
            if formula is not None:
                placeholder = f'__MATH_INLINE_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'inline', formula))
                result.append(placeholder)
                i += len(formula) + 2  # Skip past $...$
                continue
            else:
                # Malformed, just continue
                result.append(latex[i])
                i += 1
                continue
        
        result.append(latex[i])
        i += 1
    
    logger.debug(f"_extract_and_replace_math output: {repr(''.join(result)[:200])}")
    logger.debug(f"Placeholders: {placeholders_info}")
    
    return ''.join(result), placeholders_info


def _extract_until(latex: str, start_pos: int, end_marker: str) -> Optional[str]:
    """
    Extract content from start_pos until we find end_marker.
    Handles nested braces { } correctly.
    Returns the extracted content (without end_marker) or None if not found.
    """
    depth = 0
    i = start_pos
    content = []
    
    while i < len(latex):
        c = latex[i]
        
        if c == '{':
            depth += 1
            content.append(c)
        elif c == '}':
            if depth > 0:
                depth -= 1
                content.append(c)
        elif c == '\\' and i + 1 < len(latex):
            # Handle escape sequences - consume both characters
            content.append(c)
            content.append(latex[i+1])
            i += 1
        elif end_marker == '$$' and i + 1 < len(latex) and latex[i] == '$' and latex[i+1] == '$':
            # Found $$
            return ''.join(content)
        elif end_marker == '$' and latex[i] == '$':
            # Found $
            return ''.join(content)
        else:
            content.append(c)
        
        i += 1
    
    # If we get here, we didn't find the end marker
    return None


def _restore_math_formulas(text: str, placeholders_info: List[Tuple[str, str, str]], for_docx: bool = True) -> str:
    """
    Restore math formulas in the converted text.
    
    If for_docx is True, convert LaTeX math to unicode symbols.
    Otherwise, preserve LaTeX format in $...$ or $$...$$.
    """
    # Sort by placeholder length (longest first) to avoid partial replacements
    placeholders_info.sort(key=lambda x: len(x[0]), reverse=True)
    
    for placeholder, math_type, formula in placeholders_info:
        if for_docx:
            # Convert LaTeX math to unicode for DOCX compatibility
            replacement = _latex_math_to_unicode(formula)
        else:
            # Preserve LaTeX format
            if math_type == 'display':
                replacement = f'$$\n{formula}\n$$'
            else:
                replacement = f'${formula}$'
        text = text.replace(placeholder, replacement)
    
    logger.debug(f"_restore_math_formulas output: {repr(text[:200])}")
    
    return text


def _latex_math_to_unicode(math_latex: str) -> str:
    """
    Convert LaTeX math formula to unicode symbols.
    Uses pylatexenc's LatexNodes2Text for conversion.
    """
    converter = LatexNodes2Text()
    try:
        # Convert the math LaTeX to unicode
        unicode_text = converter.latex_to_text(math_latex)
        # Clean up any extra whitespace
        unicode_text = unicode_text.strip()
        # Remove any remaining LaTeX commands that weren't converted
        unicode_text = re.sub(r'\\', '', unicode_text)
        return unicode_text
    except Exception:
        # If conversion fails, return the original
        return math_latex


def _preprocess_latex(latex: str) -> str:
    """
    Preprocess LaTeX to make it easier to parse.
    """
    # Remove document class and preamble
    latex = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', latex)
    latex = re.sub(r'\\documentclass\{.*?\}', '', latex)
    latex = re.sub(r'\\usepackage\[.*?\]\{.*?\}', '', latex)
    latex = re.sub(r'\\usepackage\{.*?\}', '', latex)

    # Remove title/author/date
    latex = re.sub(r'\\title\{.*?\}', '', latex)
    latex = re.sub(r'\\author\{.*?\}', '', latex)
    latex = re.sub(r'\\date\{.*?\}', '', latex)

    # Remove maketitle
    latex = re.sub(r'\\maketitle', '', latex)

    # Remove comments
    latex = re.sub(r'%.+$', '', latex, flags=re.MULTILINE)

    return latex


def _strip_latex_commands(text: str) -> str:
    """
    Fallback method: remove LaTeX commands and keep only text content.
    """
    # Remove LaTeX commands
    text = re.sub(r'\\\[a-zA-Z]+\*?', '', text)
    text = re.sub(r'\\\[', '', text)
    text = re.sub(r'\\\]', '', text)
    text = re.sub(r'\\begin\{[^}]*\}', '', text)
    text = re.sub(r'\\end\{[^}]*\}', '', text)
    text = re.sub(r'\\', '', text)
    text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\$', '', text)
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _post_process_to_markdown(text: str) -> str:
    """
    Post-process the converted text to improve Markdown formatting.
    pylatexenc uses:
    - MIDDLE DOT (U+00A7, ord=167, char: \xa7) for section levels
    - Periods (.) as separators between section level dots
    - Asterisk (*) for itemize lists
    """
    if not text.strip():
        return ""

    # Use the actual MIDDLE DOT character that pylatexenc outputs (U+00A7)
    MIDDLE_DOT = '\xa7'  # U+00A7

    lines = text.split('\n')
    processed_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines at the start
        if not processed_lines and not stripped:
            continue

        # Handle section headers (pylatexenc adds · for section levels with . separators)
        # Pattern: \xa7.\xa7.\xa7 for \subsubsection, \xa7.\xa7 for \subsection, \xa7 for \section
        if MIDDLE_DOT in stripped:
            # Count the number of MIDDLE DOTs (section level indicators)
            level = stripped.count(MIDDLE_DOT)
            # Remove all MIDDLE DOTs and periods that are used as separators
            header_text = stripped.replace(MIDDLE_DOT, '').replace('.', '').strip()
            # Limit heading level to 6 (Markdown max)
            level = min(level, 6)
            processed_lines.append(f"{'#' * level} {header_text}")
            continue

        # Handle bullet lists - pylatexenc converts itemize to *
        if stripped.startswith('* '):
            content = stripped[2:].strip()
            processed_lines.append(f"- {content}")
            continue

        # Handle numbered lists (pylatexenc keeps the numbering)
        if re.match(r'^\d+\.\s', stripped):
            processed_lines.append(stripped)
            continue

        # Handle blockquotes
        if stripped.startswith('> '):
            processed_lines.append(stripped)
            continue

        # Handle horizontal rules
        if stripped in ('---', '___', '***', '+++'):
            processed_lines.append('---')
            continue

        # Preserve the line as-is
        processed_lines.append(line)

    result = '\n'.join(processed_lines)

    # Clean up multiple empty lines (more than 2)
    result = re.sub(r'\n{4,}', '\n\n', result)
    result = result.strip()

    # Add empty line after headers for better Markdown formatting
    result = re.sub(r'(^#.+$)\n([^\n#])', r'\1\n\n\2', result, flags=re.MULTILINE)

    # Clean up trailing whitespace
    result = '\n'.join(line.rstrip() for line in result.split('\n'))

    return result


def extract_text_from_latex(latex_content: str) -> str:
    """
    Extract plain text from LaTeX content, removing all commands.
    Used as a fallback when full conversion is not possible.
    """
    return _strip_latex_commands(latex_content)
