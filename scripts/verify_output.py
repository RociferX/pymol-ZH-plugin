"""Check the complete output resources and original help/code preservation."""
import json
from pathlib import Path
import re
import sys
import textwrap
import time

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'artifacts' / 'open-source').mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
from pymol import cmd, setting
from pymol_zh_cn.settings_catalog import SETTINGS
from pymol_zh_cn.output_text import OutputText, PRINTF, read_pairs, compile_message, help_section

assert set(setting.get_name_list()) == SETTINGS.keys()
engine = OutputText()
help_pairs = read_pairs('help_zh.tsv')
before = {name: entry[0].__doc__ for name, entry in {**cmd.keyword, **cmd.help_only}.items()}
engine.load_help()
checked_sections = 0
for name, target in help_pairs.items():
    source = textwrap.dedent(before[name]).strip()
    translated = engine.translate(source)
    html_console_text = re.sub(r'(?m)^$', ' ', source)
    assert engine.translate(html_console_text) == translated, name
    assert re.search('[\u4e00-\u9fff]', translated), name
    assert '@@' not in translated, name
    for section in re.findall(r'@@([A-Z ]+)@@', target):
        original_code = help_section(source, section)
        assert original_code in translated, (name, section)
        checked_sections += 1
assert before == {name: entry[0].__doc__ for name, entry in {**cmd.keyword, **cmd.help_only}.items()}

pairs = read_pairs('messages_zh.tsv')
for source, target in pairs.items():
    values = []
    def substitute(match):
        spec = match[0]
        if spec == '%%':
            return '%'
        value = ('3.125' if spec[-1] in 'fFgGeE' else
                 '314' if spec[-1] in 'diu' else f'original_value_{len(values)}')
        values.append(value)
        return value
    sample = PRINTF.sub(substitute, source)
    pattern, compiled_target = compile_message(source, target)
    match = pattern.fullmatch(sample)
    assert match, source
    result = engine.render(compiled_target, match)
    assert all(value in result for value in values), source

assert '1.250 埃' in engine.line('cmd.get_distance: 1.250 Angstroms.')
assert engine.line('cmd.get_distance("pk1", "pk2")') == 'cmd.get_distance("pk1", "pk2")'
code = '    print("Error: invalid argument(s).")'
assert code in engine.translate('Traceback (most recent call last):\n  File "C:/x.py", line 5, in run\n' + code + '\nValueError: invalid range')
assert code in engine.translate('原版 Python 示例（保留原语法）\n' + code)
raw = ('PyMOL>load C:/data/test.pdb\n'
       ' Setting: line_width set to 3.00000.\n'
       ' Error: invalid arguments for load command.\n') * 200
start = time.perf_counter()
translated = engine.translate(raw)
elapsed = time.perf_counter() - start
assert translated.count('PyMOL>load C:/data/test.pdb') == 200
assert translated.count('3.00000') == 200
report = {'settings': len(SETTINGS), 'help_documents': len(engine.help_texts),
          'help_topics': sum(bool(doc and doc.strip()) for doc in before.values()),
          'original_code_sections_preserved': checked_sections,
          'output_templates': len(pairs), 'original_help_unchanged': True,
          'sample_600_lines_seconds': round(elapsed, 4)}
(ROOT / 'artifacts/open-source/output-verification.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
