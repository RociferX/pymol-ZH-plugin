"""Build the standard PyMOL plugin ZIP; do not bundle the PyMOL application."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
package = ROOT / 'pymol_zh_cn'
target = ROOT / 'dist' / 'pymol_zh_cn-0.3.1.zip'
target.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(package.iterdir()):
        if path.suffix in ('.py', '.tsv') or path.name == 'PYMOL-LICENSE.txt':
            archive.write(path, f'pymol_zh_cn/{path.name}')
    archive.write(ROOT / 'README.md', 'README.md')
    archive.write(ROOT / 'LICENSE', 'LICENSE')
    archive.write(ROOT / 'THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md')
print(target)
