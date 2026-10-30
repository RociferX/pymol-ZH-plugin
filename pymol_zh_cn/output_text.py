"""Offline output/help translation. Commands, paths and numeric data stay intact."""
from pathlib import Path
import re
import textwrap
from functools import lru_cache

ESCAPE = re.compile(r'\\([\\nrt])')


def decode_cell(value):
    return ESCAPE.sub(lambda m: {'\\': '\\', 'n': '\n', 'r': '\r', 't': '\t'}[m[1]], value)

def read_pairs(filename):
    path = Path(__file__).with_name(filename)
    result = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line and not (line.startswith('#') and '\t' not in line):
                source, target = line.split('\t', 1)
                key = decode_cell(source)
                if key in result:
                    raise ValueError(f'Duplicate translation in {filename}: {key!r}')
                result[key] = decode_cell(target)
    return result


PRINTF = re.compile(r'%(?:(?:\([^)]+\))?[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlzjtL]*[srdifFgGeExXopcaub]|%)')
FIELD = re.compile(r'\{(\d+)(?::(plural|message))?\}')


def compile_message(source, target):
    parts, cursor, count = [], 0, 0
    for match in PRINTF.finditer(source):
        parts.append(re.escape(source[cursor:match.start()]))
        spec = match.group()
        if spec == '%%':
            parts.append('%')
        else:
            kind = spec[-1]
            parts.append(r'[ \t]*([-+]?\d+)' if kind in 'diu' else
                         r'[ \t]*([-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?|nan|inf)' if kind in 'fFgGeE' else r'(.*?)')
            count += 1
        cursor = match.end()
    parts.append(re.escape(source[cursor:]))
    required = {int(m[1]) for m in FIELD.finditer(target)}
    if required != set(range(count)):
        raise ValueError(f'Output translation loses fields: {source!r}')
    return re.compile(''.join(parts)), target


def help_section(source, name):
    """Keep original usage, examples and API signatures byte-for-byte."""
    headers = list(re.finditer(r'(?m)^([A-Z][A-Z /_()\-]+)[ \t]*$', source))
    aliases = (('EXAMPLES', 'EXAMPLE') if name == 'EXAMPLES' else
               ('PYMOL API', 'PYMOL API (ONLY)') if name == 'PYMOL API' else (name,))
    for index, header in enumerate(headers):
        if header[1].strip() in aliases:
            end = headers[index + 1].start() if index + 1 < len(headers) else len(source)
            return source[header.end():end].strip('\n')
    raise ValueError(f'Missing original help section {name!r}')


EXCEPTIONS = {
    'ValueError': '参数值错误', 'TypeError': '参数类型错误',
    'KeyError': '找不到键', 'IndexError': '索引超出范围',
    'NameError': '名称未定义', 'AttributeError': '属性不存在',
    'SyntaxError': '语法错误', 'IndentationError': '缩进错误',
    'FileNotFoundError': '文件不存在', 'PermissionError': '访问被拒绝',
    'OSError': '系统操作错误', 'IOError': '输入输出错误',
    'ImportError': '模块导入错误', 'ModuleNotFoundError': '找不到模块',
    'RuntimeError': '运行时错误', 'MemoryError': '内存不足',
    'ZeroDivisionError': '除数为零', 'OverflowError': '数值溢出',
    'UnicodeDecodeError': '文本解码错误', 'UnicodeEncodeError': '文本编码错误',
    'ConnectionError': '连接错误', 'TimeoutError': '操作超时',
    'AssertionError': '断言失败', 'CmdException': 'PyMOL 命令错误',
    'IncentiveOnlyException': '此功能需要商业版',
}


class OutputText:
    def __init__(self):
        pairs = sorted(read_pairs('messages_zh.tsv').items(),
                       key=lambda item: len(PRINTF.sub('', item[0])), reverse=True)
        self.messages = [compile_message(s, t) for s, t in pairs]
        self.multiline = [(re.compile(r'(?m)^[ \t]*' + pattern.pattern + r'[ \t]*$'), target)
                          for pattern, target in self.messages if '\n' in pattern.pattern]
        self.help_texts = None

    def render(self, target, match):
        def field(token):
            value = match[int(token[1]) + 1]
            if token[2] == 'plural':
                return '' if value in ('', 's') else value
            if token[2] == 'message':
                return self.line(value)
            return value
        return FIELD.sub(field, target)

    def load_help(self):
        from pymol import cmd
        translations = read_pairs('help_zh.tsv')
        result = {}
        for name, target in translations.items():
            entry = cmd.keyword.get(name) or cmd.help_only.get(name)
            if entry and entry[0].__doc__:
                source = textwrap.dedent(entry[0].__doc__).strip()
                if source:
                    target = re.sub(r'@@([A-Z ]+)@@', lambda m: help_section(source, m[1]), target)
                    result[source] = target
        self.help_texts = sorted(result.items(), key=lambda pair: len(pair[0]), reverse=True)
        # PyMOL's HTML console represents an empty output line as one space.
        # Accept that rendering difference only inside a complete known help
        # block; do not normalize arbitrary source code or user output.
        self.help_patterns = [(re.compile(r'(?<=\n)' + '\n'.join(
            re.escape(line) if line.strip() else r'[ \t]*' for line in source.split('\n')) + r'(?=\n)'), target)
            for source, target in self.help_texts]

    @lru_cache(maxsize=4096)
    def line(self, text):
        # Echoed executable input and Python traceback source lines remain code.
        if (text.lstrip().startswith(('PyMOL>', '>>>', '...'))
                or re.match(r'^\s*cmd\.\w+\s*(?:\(|=)', text)):
            return text
        stripped = text.strip()
        leading = text[:len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()):]
        if stripped == 'Traceback (most recent call last):':
            return leading + '异常调用栈（最近一次调用位于最后）：' + trailing
        frame = re.fullmatch(r'File "(.*)", line (\d+), in (.*)', stripped)
        if frame:
            return leading + f'文件 "{frame[1]}"，第 {frame[2]} 行，函数 {frame[3]}' + trailing
        for pattern, target in self.messages:
            match = pattern.fullmatch(stripped)
            if match:
                return leading + self.render(target, match) + trailing
        exception = re.fullmatch(r'([A-Za-z_]\w*):\s*(.*)', stripped)
        if exception and exception[1] in EXCEPTIONS:
            detail = self.line(exception[2]) if exception[2] != stripped else exception[2]
            return leading + exception[1] + '（' + EXCEPTIONS[exception[1]] + '）：' + detail + trailing
        return text

    def translate(self, text):
        if self.help_texts is None:
            self.load_help()
        # Replace whole, known documentation blocks. Never translate command
        # examples by replacing individual words inside executable text.
        wrapped = '\n' + text + '\n'
        for pattern, translated in self.help_patterns:
            wrapped = pattern.sub(lambda _match, translated=translated: translated, wrapped)
        text = wrapped[1:-1]
        return self.translate_lines(text)

    def translate_lines(self, text):
        result, prose = [], []
        def flush():
            text = '\n'.join(prose)
            for pattern, translated in self.multiline:
                text = pattern.sub(lambda m: self.render(translated, m), text)
            result.extend(self.line(line) for line in text.split('\n'))
            prose.clear()
        trace_code = help_code = False
        for line in text.split('\n'):
            stripped = line.strip()
            if re.fullmatch(r'File ".*", line \d+, in .*', stripped):
                if prose:
                    flush()
                trace_code = True
                result.append(self.line(line))
                continue
            if trace_code:
                if not stripped or line.startswith(('    ', '\t')):
                    result.append(line)
                    continue
                trace_code = False
            if not line.startswith((' ', '\t')) and re.match(
                    r'^(?:(?:原版 )?Python (?:API|示例)|原版用法|用法|原版示例|命令示例|示例)(?:$|[（：:])', stripped):
                if prose:
                    flush()
                help_code = True
                result.append(line)
                continue
            if help_code:
                if not stripped or line.startswith((' ', '\t')):
                    result.append(line)
                    continue
                help_code = False
            prose.append(line)
        if prose:
            flush()
        return '\n'.join(result)
