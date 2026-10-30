"""Exact display-text mappings. Never apply replacements to commands or data."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
import re


class Catalog:
    def __init__(self, path=None):
        path = Path(path) if path else Path(__file__).with_name('translations.tsv')
        self.entries = {}
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if not line or line.startswith('#'):
                continue
            source, target = line.split('\t', 1)
            source = source.replace('\\n', '\n')
            if source in self.entries:
                raise ValueError(f'Duplicate translation at line {number}: {source}')
            self.entries[source] = target.replace('\\n', '\n')
        self.folded = {key.casefold(): value for key, value in self.entries.items()}
        from .output_text import OutputText
        self.output = OutputText()

    def translate_html(self, text):
        parser = _DisplayHTML(self)
        parser.feed(text)
        parser.close()
        return ''.join(parser.parts) if parser.changed else text

    def translate(self, text):
        if not text or not isinstance(text, str):
            return text
        if text in self.entries:
            return self.entries[text]
        # A menu accelerator is presentation, whereas a literal && is text.
        clean = text.replace('&&', '\x00').replace('&', '').replace('\x00', '&')
        if clean in self.entries:
            return self.entries[clean]
        if clean.casefold() in self.folded:
            return self.folded[clean.casefold()]
        # Preserve shortcut hints, ellipses, colons and whitespace verbatim.
        match = re.fullmatch(r'(\s*)(.*?)(\s*\[(?:Ctrl|Alt|Shift)[^\]]+\])?(\.\.\.|…|:)?(\s*)', clean, re.S)
        if match:
            leading, core, shortcut, suffix, trailing = match.groups()
            translated = self.folded.get(core.rstrip().casefold())
            if translated:
                return leading + translated + (shortcut or '') + (suffix or '') + trailing
        if '\t' in text:
            label, shortcut = text.split('\t', 1)
            translated = self.translate(label)
            if translated != label:
                return translated + '\t' + shortcut
        # Only fixed, numeric UI templates. No substring replacement of user text.
        patterns = (
            (r'([+-]?\d+(?:\.\d+)?) sigma', r'\1 σ'),
            (r'@ ([+-]?\d+(?:\.\d+)?) sigma', r'等值面：\1 σ'),
            (r'(\d+(?:\.\d+)?) A Cushion', r'\1 Å 缓冲范围'),
            (r'(\d+(?:\.\d+)?) A Radius', r'\1 Å 半径'),
            (r'Cushion: (\d+(?:\.\d+)?) A', r'缓冲范围：\1 Å'),
            (r'Radius: (\d+(?:\.\d+)?) A', r'半径：\1 Å'),
            (r'Fit (\d+) Pairs', r'拟合 \1 对原子'),
            (r'Map ([123]):\s*', r'密度图 \1：'),
            (r'Select a rotamer for (.+) or pick a new residue\.\.\.', r'为 \1 选择侧链构象，或拾取其他残基…'),
            (r'Mutate to (.+)', r'突变为 \1'),
            (r'N-Cap: (.+)', r'N 端封端：\1'),
            (r'C-Cap: (.+)', r'C 端封端：\1'),
            (r'(\d+(?:\.\d+)?) seconds?', r'\1 秒'),
            (r'(\d+(?:\.\d+)?) seconds each', r'每段 \1 秒'),
            (r'(\d+(?:\.\d+)?) second pause', r'暂停 \1 秒'),
            (r'(\d+) Cycles? per Update', r'每次更新 \1 个循环'),
            (r'(\d+) deg\. over (\d+) sec\.', r'\2 秒内转动 \1°'),
            (r'(\d+(?:\.\d+)?) Angstrom Sphere', r'\1 Å 球形范围'),
            (r'(\d+(?:\.\d+)?) Angstrom Slab', r'\1 Å 裁剪厚度'),
            (r'(\d+(?:\.\d+)?) Angstrom', r'\1 Å'),
            (r'(\d+) Point', r'\1 磅'),
            (r'1/(\d+) Speed', r'1/\1 速度'),
        )
        for pattern, replacement in patterns:
            stripped = clean.strip()
            if re.fullmatch(pattern, stripped):
                return (clean[:len(clean) - len(clean.lstrip())]
                        + re.sub(pattern, replacement, stripped)
                        + clean[len(clean.rstrip()):])
        from .settings_catalog import SETTINGS
        setting = SETTINGS.get(clean.strip())
        if setting:
            return setting[0]
        global_setting = re.fullmatch(r'(\w+) \(global setting\)', clean.strip())
        if global_setting and global_setting[1] in SETTINGS:
            return SETTINGS[global_setting[1]][0] + '（全局设置）'
        return self.output.translate_lines(text)


class _DisplayHTML(HTMLParser):
    """Translate known visible text nodes, retaining links and attributes."""
    def __init__(self, catalog):
        super().__init__(convert_charrefs=False)
        self.catalog = catalog
        self.parts = []
        self.changed = False

    def handle_starttag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        translated = self.catalog.translate(data)
        self.changed |= translated != data
        self.parts.append(escape(translated, quote=False) if translated != data else data)

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_decl(self, decl):
        self.parts.append(f'<!{decl}>')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')
