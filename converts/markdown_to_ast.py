import re
from typing import List, Optional, Tuple
from converts.ast_nodes import *


def _merge_text_nodes(nodes: List[ASTNode]) -> List[ASTNode]:
    merged = []
    for node in nodes:
        if isinstance(node, Text) and merged and isinstance(merged[-1], Text):
            merged[-1].value += node.value
        else:
            merged.append(node)   # накапливаем, а не возвращаем
    return merged                 # возвращаем весь список


class MarkdownParser:
    def __init__(self):
        self.lines = []
        self.current_pos = 0

    def parse(self, markdown: str) -> Document:
        """Парсит markdown текст и возвращает AST"""
        self.lines = markdown.split('\n')
        self.current_pos = 0

        children = []
        while self.current_pos < len(self.lines):
            node = self._parse_block()
            if node:
                children.append(node)

        return Document(children=children)

    def _current_line(self) -> str:
        """Получает текущую строку"""
        if self.current_pos < len(self.lines):
            return self.lines[self.current_pos]
        return ''

    def _peek_line(self, offset: int = 1) -> str:
        """Смотрит на строку на offset позиций вперед"""
        pos = self.current_pos + offset
        if pos < len(self.lines):
            return self.lines[pos]
        return ''

    def _advance(self, count: int = 1):
        """Переходит на следующую строку"""
        self.current_pos += count

    def _skip_empty_lines(self):
        """Пропускает пустые строки"""
        while self.current_pos < len(self.lines) and not self._current_line().strip():
            self._advance()

    def _is_table_separator(self, line: str) -> bool:
        """Проверяет, является ли строка разделителем таблицы (|---|, |:---|, etc.)"""
        stripped = line.strip()
        if not stripped or '|' not in stripped or '-' not in stripped:
            return False
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        return bool(cells) and all(re.fullmatch(r':?-+:?', cell) for cell in cells)

    def _looks_like_table(self) -> bool:
        """Проверяет, начинается ли текущая позиция с таблицы"""
        line = self._current_line()
        if '|' not in line:
            return False
        return self._is_table_separator(self._peek_line())

    def _parse_block(self) -> None | Heading | CodeBlock | HorizontalRule | list | BlockQuote | Table | Paragraph:
        """Парсит блочный элемент"""
        self._skip_empty_lines()

        if self.current_pos >= len(self.lines):
            return None

        line = self._current_line()

        # Заголовок
        if match := re.match(r'^(#{1,6})\s+(.+)$', line):
            level = len(match.group(1))
            content = match.group(2)
            self._advance()
            return Heading(level=level, content=self._parse_inline(content))

        # Блок кода
        if line.startswith('```'):
            return self._parse_code_block()

        # Горизонтальная линия
        if re.match(r'^(---+|___+|\*\*\*+)\s*$', line):
            self._advance()
            return HorizontalRule()

        # Маркированный список
        if line.startswith('- ') or line.startswith('* '):
            return self._parse_list(ordered=False)

        # Нумерованный список
        if re.match(r'^\d+\.\s', line):
            return self._parse_list(ordered=True)

        # Цитата
        if line.startswith('>'):
            return self._parse_blockquote()

        # Таблица
        if self._looks_like_table():
            return self._parse_table()

        # Обычный параграф
        if line.strip():
            return self._parse_paragraph()

        self._advance()
        return None

    def _parse_paragraph(self) -> Paragraph | None:
        """Парсит параграф"""
        lines = []
        while self.current_pos < len(self.lines):
            line = self._current_line()

            # Проверяем, не начинается ли новый блок
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
            if '|' in line:
                break

            lines.append(line)
            self._advance()

        if not lines:
            # Строка не подошла для параграфа (например, таблица) — пропускаем,
            # чтобы избежать бесконечного цикла
            self._advance()
            return None

        content_text = ' '.join(lines)
        return Paragraph(content=self._parse_inline(content_text))

    def _parse_inline(self, text: str) -> List[ASTNode]:
        """Парсит инлайн элементы (жирный, курсив, код, ссылки)"""
        nodes = []
        pos = 0

        while pos < len(text):
            # Жирный текст **text**
            if match := re.match(r'\*\*(.+?)\*\*', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Bold(content=content))
                pos += len(match.group(0))
                continue

            # Жирный текст __text__
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

            # Курсив _text_
            if match := re.match(r'_(.+?)_', text[pos:]):
                content = self._parse_inline(match.group(1))
                nodes.append(Italic(content=content))
                pos += len(match.group(0))
                continue

            # Встроенный код `code`
            if match := re.match(r'`(.+?)`', text[pos:]):
                nodes.append(Code(value=match.group(1)))
                pos += len(match.group(0))
                continue

            # Ссылка [text](url)
            if match := re.match(r'\[(.+?)\]\((.+?)\)', text[pos:]):
                link_text = self._parse_inline(match.group(1))
                nodes.append(Link(text=link_text, url=match.group(2)))
                pos += len(match.group(0))
                continue

            # Изображение ![alt](url)
            if match := re.match(r'!\[(.+?)\]\((.+?)\)', text[pos:]):
                nodes.append(Image(alt=match.group(1), url=match.group(2)))
                pos += len(match.group(0))
                continue

            # Обычный текст
            match = re.match(r'[^*_`\[\]!]+', text[pos:])
            if match:
                nodes.append(Text(value=match.group(0)))
                pos += len(match.group(0))
            else:
                nodes.append(Text(value=text[pos]))
                pos += 1

        # Объединяем соседние Text узлы
        return _merge_text_nodes(nodes)

    def _parse_code_block(self) -> CodeBlock:
        """Парсит блок кода"""
        line = self._current_line()

        # Определяем язык программирования
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
        """Парсит список (маркированный или нумерованный)"""
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
        """Парсит цитату"""
        quote_lines = []

        while self.current_pos < len(self.lines):
            line = self._current_line()

            if not line.startswith('>'):
                break

            # Убираем префикс ">" (с опциональным пробелом)
            quote_text = line[1:].lstrip(' ')
            quote_lines.append(quote_text)
            self._advance()

        # Парсим содержимое цитаты как отдельный документ
        quote_content = '\n'.join(quote_lines)
        parser = MarkdownParser()
        doc = parser.parse(quote_content)

        return BlockQuote(content=doc.children)

    def _parse_table(self) -> Table:
        """Парсит таблицу"""
        # Получаем заголовок
        header_line = self._current_line()
        header = [cell.strip() for cell in header_line.split('|')[1:-1]]
        self._advance()

        # Пропускаем разделитель
        self._advance()

        # Парсим строки
        rows = []
        while self.current_pos < len(self.lines):
            line = self._current_line()

            if not line.strip() or not '|' in line:
                break

            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            # Парсим инлайн элементы в каждой ячейке
            parsed_cells = [self._parse_inline(cell) for cell in cells]
            rows.append(parsed_cells)
            self._advance()

        return Table(header=header, rows=rows)
