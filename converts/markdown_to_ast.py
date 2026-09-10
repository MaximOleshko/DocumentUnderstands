import re
from converts.ast_nodes import *


def _merge_text_nodes(nodes: List[ASTNode]) -> List[ASTNode]:
    merged = []
    for node in nodes:
        if isinstance(node, Text) and merged and isinstance(merged[-1], Text):
            merged[-1].value += node.value
        else:
            merged.append(node)   # appending
    return merged                 # return whole list


class MarkdownParser:
    def __init__(self):
        self.lines = []
        self.current_pos = 0

    def parse(self, markdown: str) -> Document:
        markdown = markdown.replace('\r\n', '\n').replace('\r', '\n')
        markdown = markdown.replace('\u00a0', ' ')
        self.lines = [line.rstrip() for line in markdown.split('\n')]
        self.current_pos = 0

        children = []
        while self.current_pos < len(self.lines):
            node = self._parse_block()
            if node:
                children.append(node)

        return Document(children=children)

    def _current_line(self) -> str:
        if self.current_pos < len(self.lines):
            return self.lines[self.current_pos]
        return ''

    def _peek_line(self, offset: int = 1) -> str:
        # Looking for offset position forward
        pos = self.current_pos + offset
        if pos < len(self.lines):
            return self.lines[pos]
        return ''

    def _advance(self, count: int = 1):
        # Next string
        self.current_pos += count

    def _skip_empty_lines(self):
        while self.current_pos < len(self.lines) and not self._current_line().strip():
            self._advance()

    def _is_table_separator(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped or '|' not in stripped or '-' not in stripped:
            return False
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        return bool(cells) and all(re.fullmatch(r':?-+:?', cell) for cell in cells)

    def _looks_like_table(self) -> bool:
        line = self._current_line()
        if '|' not in line:
            return False
        return self._is_table_separator(self._peek_line())

    def _parse_block(self) -> None | Heading | CodeBlock | HorizontalRule | list | BlockQuote | Table | Paragraph:
        self._skip_empty_lines()

        if self.current_pos >= len(self.lines):
            return None

        line = self._current_line()

        # Header
        if match := re.match(r'^(#{1,6})\s+(.+)$', line):
            level = len(match.group(1))
            content = match.group(2).strip()
            self._advance()
            return Heading(level=level, content=self._parse_inline(content))

        # Code block
        if line.startswith('```'):
            return self._parse_code_block()

        # Horizontal line
        if re.match(r'^(---+|___+|\*\*\*+)\s*$', line):
            self._advance()
            return HorizontalRule()

        # Bulleted list
        if line.startswith('- ') or line.startswith('* '):
            return self._parse_list(ordered=False)

        # Numbered list
        if re.match(r'^\d+\.\s', line):
            return self._parse_list(ordered=True)

        # Quote
        if line.startswith('>'):
            return self._parse_blockquote()

        # Table
        if self._looks_like_table():
            return self._parse_table()

        # Simple paragraph
        if line.strip():
            return self._parse_paragraph()

        self._advance()
        return None

    def _parse_paragraph(self) -> Paragraph | None:
        lines = []
        while self.current_pos < len(self.lines):
            line = self._current_line()

            if not line.strip():
                break
            if re.match(r'^(#{1,6})\s+', line):
                break
            if line.startswith('```'):
                break
            if re.match(r'^(---+|___+|\*\*\*+)\s*$', line):
                break
            if line.startswith('- ') or line.startswith('* '):
                break
            if re.match(r'^\d+\.\s', line):
                break
            if line.startswith('>'):
                break

            if '|' in line and self._looks_like_table():
                break

            lines.append(line)
            self._advance()

        if not lines:
            self._advance()
            return None

        content_text = ' '.join(lines)
        content_text = re.sub(r' {2,}', ' ', content_text).strip()
        return Paragraph(content=self._parse_inline(content_text))

    def _parse_inline(self, text: str) -> List[ASTNode]:
        nodes = []
        pos = 0

        while pos < len(text):
            # Bold text **text**
            if match := re.match(r'\*\*(.+?)\*\*', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Bold(content=content))
                pos += len(match.group(0))
                continue

            # Bold text __text__
            if match := re.match(r'__(.+?)__', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Bold(content=content))
                pos += len(match.group(0))
                continue

            # Курсив *text*
            if match := re.match(r'\*(.+?)\*', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Italic(content=content))
                pos += len(match.group(0))
                continue

            # Italic _text_
            if match := re.match(r'_(.+?)_', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Italic(content=content))
                pos += len(match.group(0))
                continue

            # `code` block
            if match := re.match(r'`(.+?)`', text[pos:]):
                nodes.append(Code(value=match.group(1)))
                pos += len(match.group(0))
                continue

            # Link [text](url)
            if match := re.match(r'\[(.+?)\]\((.+?)\)', text[pos:]):
                link_text = self._parse_inline(match.group(1))
                nodes.append(Link(text=link_text, url=match.group(2)))
                pos += len(match.group(0))
                continue

            # Image ![alt](url)
            if match := re.match(r'!\[(.+?)\]\((.+?)\)', text[pos:]):
                nodes.append(Image(alt=match.group(1), url=match.group(2)))
                pos += len(match.group(0))
                continue

            # Simple text
            match = re.match(r'[^*_`\[\]!]+', text[pos:])
            if match:
                nodes.append(Text(value=match.group(0)))
                pos += len(match.group(0))
            else:
                nodes.append(Text(value=text[pos]))
                pos += 1

        # Merge near Text nodes
        return _merge_text_nodes(nodes)

    def _parse_code_block(self) -> CodeBlock:
        line = self._current_line()
        language = None
        if match := re.match(r'^```(\w+)?', line):
            language = match.group(1)
        self._advance()

        code_lines = []
        while self.current_pos < len(self.lines):
            line = self._current_line()
            if line.startswith('```'):
                self._advance()
                break
            code_lines.append(line)
            self._advance()

        code = '\n'.join(code_lines)
        return CodeBlock(language=language, code=code)

    def _parse_list(self, ordered: bool) -> List:
        items = []

        while self.current_pos < len(self.lines):
            line = self._current_line()

            if ordered:
                if not re.match(r'^\d+\.\s', line):
                    break
                match = re.match(r'^\d+\.\s(.+)$', line)
            else:
                if not (line.startswith('- ') or line.startswith('* ')):
                    break
                match = re.match(r'^[-*]\s(.+)$', line)

            if not match:
                break

            content_text = match.group(1)
            content = self._parse_inline(content_text)
            items.append(ListItem(content=content))
            self._advance()

        return List(ordered=ordered, items=items)

    def _parse_blockquote(self) -> BlockQuote:
        quote_lines = []

        while self.current_pos < len(self.lines):
            line = self._current_line()

            if not line.startswith('>'):
                break

            # Remove prefix ">" (with optional space)
            quote_text = line[1:].lstrip(' ')
            quote_lines.append(quote_text)
            self._advance()

        # Parse quote
        quote_content = '\n'.join(quote_lines)
        parser = MarkdownParser()
        doc = parser.parse(quote_content)

        return BlockQuote(content=doc.children)

    def _parse_table(self) -> Table:
        header_line = self._current_line()
        header = [cell.strip() for cell in header_line.split('|')[1:-1]]
        self._advance()

        separator_line = self._current_line()
        if not self._is_table_separator(separator_line):
            return None

        self._advance()

        rows = []
        while self.current_pos < len(self.lines):
            line = self._current_line()
            if not line.strip() or '|' not in line:
                break
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            parsed_cells = [self._parse_inline(cell) for cell in cells]
            rows.append(parsed_cells)
            self._advance()

        return Table(header=header, rows=rows)
