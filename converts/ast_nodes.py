from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ASTNode:
    """Базовый класс для всех узлов AST"""
    pass

@dataclass
class Document(ASTNode):
    """Корневой узел документа"""
    children: List[ASTNode]

@dataclass
class Heading(ASTNode):
    """Заголовок"""
    level: int  # 1-6
    content: List[ASTNode]

@dataclass
class Paragraph(ASTNode):
    """Параграф"""
    content: List[ASTNode]

@dataclass
class Text(ASTNode):
    """Простой текст"""
    value: str

@dataclass
class Bold(ASTNode):
    """Жирный текст"""
    content: List[ASTNode]

@dataclass
class Italic(ASTNode):
    """Курсив"""
    content: List[ASTNode]

@dataclass
class Code(ASTNode):
    """Встроенный код"""
    value: str

@dataclass
class CodeBlock(ASTNode):
    """Блок кода"""
    language: Optional[str]
    code: str

@dataclass
class List(ASTNode):
    """Список (маркированный или нумерованный)"""
    ordered: bool  # False = маркированный, True = нумерованный
    items: List['ListItem']

@dataclass
class ListItem(ASTNode):
    """Элемент списка"""
    content: List[ASTNode]

@dataclass
class Link(ASTNode):
    """Ссылка"""
    text: List[ASTNode]
    url: str

@dataclass
class Image(ASTNode):
    """Изображение"""
    alt: str
    url: str

@dataclass
class HorizontalRule(ASTNode):
    """Горизонтальная линия"""
    pass

@dataclass
class BlockQuote(ASTNode):
    """Цитата"""
    content: List[ASTNode]

@dataclass
class Table(ASTNode):
    """Таблица"""
    header: List[str]
    rows: List[List[List[ASTNode]]]
