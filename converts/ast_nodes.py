from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ASTNode:
    pass

@dataclass
class Document(ASTNode):
    children: List[ASTNode]

@dataclass
class Heading(ASTNode):
    level: int  # 1-6
    content: List[ASTNode]

@dataclass
class Paragraph(ASTNode):
    content: List[ASTNode]

@dataclass
class Text(ASTNode):
    value: str

@dataclass
class Bold(ASTNode):
    content: List[ASTNode]

@dataclass
class Italic(ASTNode):
    content: List[ASTNode]

@dataclass
class Code(ASTNode):
    value: str

@dataclass
class CodeBlock(ASTNode):
    language: Optional[str]
    code: str

@dataclass
class List(ASTNode):
    ordered: bool  # False = Bulleted, True = Numbered
    items: List['ListItem']

@dataclass
class ListItem(ASTNode):
    content: List[ASTNode]

@dataclass
class Link(ASTNode):
    text: List[ASTNode]
    url: str

@dataclass
class Image(ASTNode):
    alt: str
    url: str

@dataclass
class HorizontalRule(ASTNode):
    pass

@dataclass
class BlockQuote(ASTNode):
    content: List[ASTNode]

@dataclass
class Table(ASTNode):
    header: List[str]
    rows: List[List[List[ASTNode]]]
