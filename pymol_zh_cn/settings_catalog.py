"""Offline Chinese setting names and explanations; English keys are unchanged."""
from pathlib import Path


def load_settings():
    result = {}
    path = Path(__file__).with_name('settings_zh.tsv')
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        key, name, explanation = line.split('\t', 2)
        if key in result:
            raise ValueError(f'Duplicate setting translation at line {number}: {key}')
        result[key] = (name, explanation.replace('\\n', '\n'))
    return result


SETTINGS = load_settings()
