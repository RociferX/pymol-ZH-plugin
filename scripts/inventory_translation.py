"""Inventory remaining real setting keys, help documents and native feedback."""
import ast
import argparse
import json
from pathlib import Path
import re
import sys
import string
import textwrap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pymol import cmd, setting
from pymol_zh_cn.settings_catalog import SETTINGS
from pymol_zh_cn.output_text import read_pairs

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=ROOT / 'downloads' / 'source-open-3.1.0',
                    help='Matching PyMOL source tree (for native feedback inventory)')
source_root = parser.parse_args().source.resolve()
if not (source_root / 'layer1').is_dir():
    parser.error('--source must point to a PyMOL source tree containing layer1/')


def location_of(path, line):
    return str(path) + ':' + str(line)

OUTPUT = ROOT / 'artifacts' / 'open-source'
OUTPUT.mkdir(parents=True, exist_ok=True)
help_translations = read_pairs('help_zh.tsv')
docs = {}
translated_docs = set()
for name, entry in {**cmd.keyword, **cmd.help_only}.items():
    if entry[0].__doc__:
        source = textwrap.dedent(entry[0].__doc__).strip()
        if source:
            docs.setdefault(source, []).append(name)
            if name in help_translations:
                translated_docs.add(source)
remaining_help = [{'topics': names, 'text': source} for source, names in docs.items()
                  if source not in translated_docs]
(OUTPUT / 'help-pending.json').write_text(json.dumps(remaining_help, ensure_ascii=False, indent=2), encoding='utf-8')

literal = r'"(?:\\.|[^"\\])*"'
blocks = re.compile(r'\b(?:PRINTF\b|PRINT(?:FB|FD|FF|B|F)\s*\([^;]*?\))(?P<body>.*?)\bEND(?:F|FB|FD|FF)\s*\(', re.S)
strings = re.compile(literal + r'(?:\s*' + literal + r')*')
feedback = {}
for file in source_root.rglob('*.cpp'):
    if 'contrib' in file.parts:
        continue
    text = file.read_text(encoding='utf-8', errors='replace')
    for block in blocks.finditer(text):
        match = strings.search(block['body'])
        if not match:
            continue
        try:
            source = ''.join(ast.literal_eval(token) for token in re.findall(literal, match[0])).strip()
        except (ValueError, SyntaxError):
            continue
        if source and re.search('[A-Za-z]{3}', source):
            location = location_of(file.relative_to(source_root), text.count('\n', 0, block.start()) + 1)
            feedback.setdefault(source, []).append(location)
    # Native error helpers carry their human-readable detail separately from
    # the generic "module-Error:" feedback format.
    error_calls = re.compile(r'\b(?:ErrMessage|ErrFatal)\s*\([^;]*?;|pymol::Error\s*\(\s*(?:' + literal + r'\s*)+', re.S)
    for call in error_calls.finditer(text):
        messages = list(strings.finditer(call[0]))
        if not messages:
            continue
        message = messages[-1] if call[0].startswith(('ErrMessage', 'ErrFatal')) else messages[0]
        try:
            source = ''.join(ast.literal_eval(token) for token in re.findall(literal, message[0])).strip()
        except (ValueError, SyntaxError):
            continue
        if source and re.search('[A-Za-z]{3}', source):
            location = location_of(file.relative_to(source_root), text.count('\n', 0, call.start()) + 1)
            feedback.setdefault(source, []).append(location)


def python_template(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ''.join(part.value if isinstance(part, ast.Constant) else '%s' for part in node.values)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Mod):
            return python_template(node.left)
        if isinstance(node.op, ast.Add):
            return python_template(node.left) + python_template(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'format':
        if isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
            return ''.join(text + ('%s' if field is not None else '')
                           for text, field, spec, conv in string.Formatter().parse(node.func.value.value))
    return '%s'


import pymol
import pmg_qt
python_files = [file for module in (pymol, pmg_qt)
                for file in Path(module.__file__).parent.rglob('*.py')]
for file in python_files:
    relative = file.relative_to(Path(pymol.__file__).parent.parent)
    if relative.name == 'make_simple.py':
        # This standalone generator prints force-field file records, not UI.
        continue
    try:
        tree = ast.parse(file.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeError):
        continue
    for node in ast.walk(tree):
        args = None
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            args = node.exc.args[:1]
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                if not any(keyword.arg == 'file' for keyword in node.keywords):
                    args = node.args
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'colorprinting' and node.func.attr in ('error', 'warning', 'suggest', 'parrot'):
                    args = node.args
        if args:
            source = ' '.join(python_template(arg) for arg in args).strip()
            if re.search(r'[A-Za-z]{3,}[ :]', source) and '\x00' not in source:
                location = location_of(relative, node.lineno)
                feedback.setdefault(source, []).append(location)
messages = read_pairs('messages_zh.tsv')
remaining_feedback = [{'text': text, 'locations': locations} for text, locations in feedback.items()
                      if text not in messages]
(OUTPUT / 'feedback-pending.json').write_text(json.dumps(remaining_feedback, ensure_ascii=False, indent=2), encoding='utf-8')

actual = set(setting.get_name_list())
report = {'settings_total': len(actual), 'settings_translated': len(actual & SETTINGS.keys()),
          'settings_missing': sorted(actual - SETTINGS.keys()),
          'help_documents_total': len(docs), 'help_documents_translated': len(translated_docs),
          'help_documents_remaining': len(remaining_help),
          'native_feedback_formats_found': len(feedback), 'native_feedback_formats_remaining': len(remaining_feedback),
          'visual_inspection_policy': 'Finish all requested translations and implementation before unified visual/real-input checks.'}
(OUTPUT / 'translation-progress.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
