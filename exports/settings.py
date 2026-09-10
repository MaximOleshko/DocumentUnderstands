from dataclasses import dataclass
from typing import Optional

from docx.shared import RGBColor

TEXT_COLOR_PRESETS = {
    'black': (0, 0, 0),
    'gray': (55, 65, 81),
    'navy': (30, 58, 95),
    'green': (20, 83, 45),
    'burgundy': (127, 29, 29),
    'brown': (68, 64, 60),
}

FONT_PRESETS = {
    'default': None,
    'times': 'Times New Roman',
    'arial': 'Arial',
    'calibri': 'Calibri',
    'georgia': 'Georgia',
    'cambria': 'Cambria',
    'verdana': 'Verdana',
    'garamond': 'Garamond',
}


def _parse_color_from_form(form, color_field, custom_field, default='black'):
    color_key = form.get(color_field, default)
    if color_key == 'custom':
        hex_color = form.get(custom_field, '#000000').lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return TEXT_COLOR_PRESETS[default]
    return TEXT_COLOR_PRESETS.get(color_key, TEXT_COLOR_PRESETS[default])  # ← ИСПРАВЛЕНО


TABLE_MODES = {
    'converter': 'converter',
    'word_native': 'word_native',
}


@dataclass
class ExportSettings:
    text_color: tuple[int, int, int] = (0, 0, 0)
    table_text_color: tuple[int, int, int] = (0, 0, 0)
    font_key: str = 'default'
    table_mode: str = 'converter'
    plain_code: bool = False
    strip_backticks: bool = False
    strip_bold: bool = False
    strip_italic: bool = False
    strip_blockquotes: bool = False
    strip_emojis: bool = False
    strip_horizontal_rules: bool = False
    strip_hidden_text: bool = False

    @property
    def rgb(self) -> RGBColor:
        return RGBColor(*self.text_color)

    @property
    def table_rgb(self) -> RGBColor:
        return RGBColor(*self.table_text_color)

    @property
    def font_name(self) -> Optional[str]:
        return FONT_PRESETS.get(self.font_key, FONT_PRESETS['default'])

    @classmethod
    def from_form(cls, form) -> 'ExportSettings':
        table_mode = form.get('table_mode', 'converter')
        if table_mode not in TABLE_MODES:
            table_mode = 'converter'

        return cls(
            text_color=_parse_color_from_form(form, 'text_color', 'custom_color'),
            table_text_color=_parse_color_from_form(form, 'table_text_color', 'table_custom_color'),
            font_key=form.get('font_family', 'default'),
            table_mode=table_mode,
            plain_code=form.get('plain_code') == 'on',
            strip_backticks=form.get('strip_backticks') == 'on',
            strip_bold=form.get('strip_bold') == 'on',
            strip_italic=form.get('strip_italic') == 'on',
            strip_blockquotes=form.get('strip_blockquotes') == 'on',
            strip_emojis=form.get('strip_emojis') == 'on',
            strip_horizontal_rules=form.get('strip_horizontal_rules') == 'on',
            strip_hidden_text=form.get('strip_hidden_text') == 'on',
        )
