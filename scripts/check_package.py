"""Check the ZIP using PyMOL's installer parser and verify packaged bytes."""
from pathlib import Path
import json
import zipfile
from pymol.plugins.installation import extract_zipfile
from pymol.plugins import PluginInfo
from release_info import ROOT, VERSION, PACKAGE

(ROOT / 'artifacts').mkdir(exist_ok=True)
target = PACKAGE
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert {'LICENSE', 'THIRD_PARTY_NOTICES.md', 'pymol_zh_cn/PYMOL-LICENSE.txt'} <= set(archive.namelist())
    for name in archive.namelist():
        local = ROOT / name
        assert archive.read(name) == local.read_bytes(), name
tempdir, names = extract_zipfile(str(target), 'zip')
assert names == ('pymol_zh_cn',), names
info = PluginInfo('pymol_zh_cn', str(Path(tempdir) / names[0] / '__init__.py'))
assert info.get_version() == VERSION
report = {'installer_package_name': names[0], 'version': info.get_version(),
          'packaged_bytes_match_source': True, 'zip_size': target.stat().st_size}
(ROOT / 'artifacts' / 'package-verification.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
