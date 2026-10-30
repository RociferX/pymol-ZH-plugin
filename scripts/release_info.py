"""Read release metadata without importing Qt or loading the plugin."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'pymol_zh_cn/__init__.py').read_text(encoding='utf-8'))
VERSION = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == '__version__'
                       for target in node.targets))
PACKAGE = ROOT / 'dist' / f'pymol_zh_cn-{VERSION}.zip'
