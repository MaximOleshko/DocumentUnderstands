from dataclasses import dataclass, field
from typing import Optional, List

from docx.shared import RGBColor

TEXT_COLOR_PRESETS = {
    'black': (0, 0, 0),
    'gray': (55, 65, 81),
    'navy': (30, 58, 95),
    'green': (20, 83, 45),
    'burgundy': (127, 29, 29),
    'brown': (68, 64, 60),
}

HIDDEN_COLOR_PRESETS = {
    'white':      (255, 255, 255),
    'smoke':      (245, 245, 245),
    'gainsboro':  (220, 220, 220),
    'light_gray': (211, 211, 211),
    'cream':      (255, 253, 208),
    'pale_blue':  (219, 234, 254),
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
    return TEXT_COLOR_PRESETS.get(color_key, TEXT_COLOR_PRESETS[default])


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
    min_visible_size_pt: float = 2.0
    hidden_preset_keys: List[str] = field(default_factory=list)
    custom_hidden_colors: List[tuple[int, int, int]] = field(default_factory=list)

    @property
    def rgb(self) -> RGBColor:
        return RGBColor(*self.text_color)

    @property
    def table_rgb(self) -> RGBColor:
        return RGBColor(*self.table_text_color)

    @property
    def font_name(self) -> Optional[str]:
        return FONT_PRESETS.get(self.font_key, FONT_PRESETS['default'])

    @property
    def hidden_colors(self) -> set:
        colors = set(self.custom_hidden_colors)
        for key in self.hidden_preset_keys:
            rgb = HIDDEN_COLOR_PRESETS.get(key)
            if rgb is not None:
                colors.add(rgb)
        return colors

    @classmethod
    def from_form(cls, form) -> 'ExportSettings':
        table_mode = form.get('table_mode', 'converter')
        if table_mode not in TABLE_MODES:
            table_mode = 'converter'

        min_size_str = form.get('min_visible_size', '2.0')
        try:
            min_visible_size = float(min_size_str)
            min_visible_size = max(0.5, min(20.0, min_visible_size))
        except ValueError:
            min_visible_size = 2.0

        hidden_preset_keys = [
            key.split('hidden_preset_', 1)[1]
            for key, value in form.items()
            if key.startswith('hidden_preset_')
            and value == 'on'
            and key.split('hidden_preset_', 1)[1] in HIDDEN_COLOR_PRESETS
        ]

        custom_colors = []
        for key, value in form.items():
            if key.startswith('hidden_color_custom-hidden-color-'):
                hex_color = value.lstrip('#')
                if len(hex_color) == 6:
                    try:
                        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
                        custom_colors.append(rgb)
                    except ValueError:
                        pass

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
            min_visible_size_pt=min_visible_size,
            hidden_preset_keys=hidden_preset_keys,
            custom_hidden_colors=custom_colors,
        )
