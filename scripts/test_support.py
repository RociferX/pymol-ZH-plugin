"""Select a real CJK font for offscreen tests; never changes plugin font policy."""
from pathlib import Path


def set_test_font(app, QtGui):
    candidates = (
        Path('C:/Windows/Fonts/msyh.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/System/Library/Fonts/PingFang.ttc'),
    )
    for path in candidates:
        if path.is_file():
            QtGui.QFontDatabase.addApplicationFont(str(path))
    available = set(QtGui.QFontDatabase().families())
    for family in ('Microsoft YaHei UI', 'Microsoft YaHei', 'Noto Sans CJK SC', 'PingFang SC'):
        if family in available:
            font = QtGui.QFont(family, 10)
            raw = QtGui.QRawFont.fromFont(font)
            if all(raw.supportsCharacter(ord(char)) for char in '中文显示'):
                app.setFont(font)
                return
    raise RuntimeError('Offscreen checks need Microsoft YaHei, Noto Sans CJK SC or PingFang SC.')
