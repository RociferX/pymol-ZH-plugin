"""Construct the unmodified official Qt GUI without depending on GL redraw."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(os.environ.get('PYMOL_ZH_ARTIFACTS', str(ROOT / 'artifacts' / 'open-source')))
OUTPUT.mkdir(parents=True, exist_ok=True)
stage = OUTPUT / 'pymol-stage.txt'
stage.write_text('importing official GUI', encoding='utf-8')
def record_exception(kind, value, tb):
    (OUTPUT / 'pymol-signal-error.txt').write_text(
        ''.join(traceback.format_exception(kind, value, tb)), encoding='utf-8')
sys.excepthook = record_exception
try:
    import pymol
    pymol.invocation.parse_args(['pymol', '-k', '-q'])
    from pymol.Qt import QtGui
    from pmg_qt import pymol_qt_gui as gui
    app = gui.PyMOLApplication(['PyMOL GUI verification'])
    if not QtGui.QFontDatabase().families():
        QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
        app.setFont(QtGui.QFont('Microsoft YaHei UI', 10))
    stage.write_text('constructing official GUI', encoding='utf-8')
    gui.window = gui.PyMOLQtGUI()
    gui.window.show()
    stage.write_text('official GUI constructed', encoding='utf-8')
    import verify_in_pymol
    app.exec_()
except BaseException:
    stage.with_name('pymol-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    raise
