from __future__ import annotations
import re
from typing import Optional, Tuple, List

from pylatexenc.latex2text import LatexNodes2Text


def latex_to_markdown(latex_content: str) -> str:
    """
    Convert LaTeX content to Markdown format.

    Uses pylatexenc to parse LaTeX and convert it to plain text with Markdown formatting.
    Handles common LaTeX constructs like sections, lists, math, and special characters.
    
    For math formulas, preserves them in LaTeX format wrapped in $...$ or $$...$$ 
    for better compatibility with Markdown viewers and document export.
    """
    if not latex_content.strip():
        return ""

    # Step 1: Extract and replace math formulas with placeholders BEFORE pylatexenc sees them
    latex_with_placeholders, placeholders_info = _extract_and_replace_math(latex_content)
    
    # Step 2: Clean and preprocess LaTeX (without math formulas)
    cleaned_latex = _preprocess_latex(latex_with_placeholders)
    
    # Step 3: Use pylatexenc for basic conversion (math is now protected)
    converter = LatexNodes2Text()
    try:
        plain_text = converter.latex_to_text(cleaned_latex)
    except Exception:
        plain_text = _strip_latex_commands(cleaned_latex)
    
    # Step 4: Post-process to improve Markdown formatting
    markdown = _post_process_to_markdown(plain_text)
    
    # Step 5: Restore math formulas in LaTeX format
    markdown = _restore_math_formulas(markdown, placeholders_info)
    
    return markdown


def _extract_and_replace_math(latex: str) -> Tuple[str, List[Tuple[str, str, str]]]:
    """
    Extract math formulas from LaTeX, replace them with placeholders,
    and return the modified LaTeX and info about the formulas.
    
    This MUST be done BEFORE pylatexenc processes the text,
    otherwise pylatexenc will convert the math to unicode characters.
    
    Handles:
    - Inline math: $...$ or \(...\)
    - Display math: $$...$$ or \[...\]
    
    Uses a stateful parser to handle nested braces and dollar signs correctly.
    
    Returns (latex_with_placeholders, placeholders_info)
    where placeholders_info is a list of (placeholder, math_type, formula)
    """
    placeholders_info = []
    result = []
    i = 0
    
    while i < len(latex):
        # Check for display math: $$...$$
        if i + 1 < len(latex) and latex[i] == '$' and latex[i+1] == '$':
            # Found $$, find matching $$
            formula, end_pos = _extract_math_content(latex, i + 2, '$$')
            if formula is not None:
                placeholder = f'__MATH_DISPLAY_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'display', formula))
                result.append(placeholder)
                i = end_pos + 2
                continue
        
        # Check for inline math: $...$
        elif latex[i] == '$':
            # Found $, find matching $
            formula, end_pos = _extract_math_content(latex, i + 1, '$')
            if formula is not None:
                placeholder = f'__MATH_INLINE_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'inline', formula))
                result.append(placeholder)
                i = end_pos + 1
                continue
        
        # Check for \(...\)
        elif i + 1 < len(latex) and latex[i] == '\\' and latex[i+1] == '(':
            # Found \(, find matching \)
            formula, end_pos = _extract_math_content(latex, i + 2, '\\')
            if formula is not None and end_pos + 1 < len(latex) and latex[end_pos+1] == ')':
                placeholder = f'__MATH_INLINE_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'inline', formula))
                result.append(placeholder)
                i = end_pos + 2
                continue
        
        # Check for \[...\]
        elif i + 1 < len(latex) and latex[i] == '\\' and latex[i+1] == '[':
            # Found \[, find matching \]
            formula, end_pos = _extract_math_content(latex, i + 2, '\\')
            if formula is not None and end_pos + 1 < len(latex) and latex[end_pos+1] == ']':
                placeholder = f'__MATH_DISPLAY_{len(placeholders_info)}__'
                placeholders_info.append((placeholder, 'display', formula))
                result.append(placeholder)
                i = end_pos + 2
                continue
        
        result.append(latex[i])
        i += 1
    
    return ''.join(result), placeholders_info


def _extract_math_content(latex: str, start_pos: int, end_marker: str) -> Tuple[Optional[str], int]:
    """
    Extract math content from start_pos, looking for end_marker.
    Handles nested braces {} correctly.
    Returns (formula, end_position) or (None, start_pos-1) if not found.
    """
    depth = 0
    i = start_pos
    content = []
    
    while i < len(latex):
        if latex[i] == '{':
            depth += 1
            content.append(latex[i])
        elif latex[i] == '}':
            if depth > 0:
                depth -= 1
                content.append(latex[i])
        elif latex[i] == '\\' and i + 1 < len(latex):
            # Handle escape sequences
            content.append(latex[i])
            content.append(latex[i+1])
            i += 1
        elif end_marker == '$' and latex[i] == '$':
            # Found matching $ for inline math
            return ''.join(content), i
        elif end_marker == '\\' and latex[i] == '\\' and i + 1 < len(latex):
            # Check if this is the end marker
            if latex[i+1] == ')' or latex[i+1] == ']':
                return ''.join(content), i
            else:
                content.append(latex[i])
                content.append(latex[i+1])
                i += 1
        else:
            content.append(latex[i])
        
        i += 1
    
    # If we get here, we didn't find the end marker
    return None, start_pos - 1


def _restore_math_formulas(text: str, placeholders_info: List[Tuple[str, str, str]]) -> str:
    """
    Restore math formulas in the converted text.
    """
    # Sort by placeholder length (longest first) to avoid partial replacements
    placeholders_info.sort(key=lambda x: len(x[0]), reverse=True)
    
    for placeholder, math_type, formula in placeholders_info:
        if math_type == 'display':
            # Use $$...$$ for display math in Markdown
            replacement = f'$$\n{formula}\n$$'
        else:
            # Use $...$ for inline math
            replacement = f'${formula}$'
        text = text.replace(placeholder, replacement)
    
    return text


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
