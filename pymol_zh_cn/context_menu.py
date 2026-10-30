"""Use Qt for native GL context menus while preserving stock menu payloads."""
import functools
import sys
from ._qt import QtCore, QtGui, QtWidgets

Signal = getattr(QtCore, 'Signal', None) or QtCore.pyqtSignal


class ContextMenus(QtCore.QObject):
    requested = Signal(object, object)

    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel
        self.originals = {}
        self.active = None
        self.last_call = None
        self.requested.connect(self.show_menu, QtCore.Qt.ConnectionType.QueuedConnection)

    def set_enabled(self, enabled):
        from pymol import menu
        if self.active:
            self.active.close()
        if not enabled:
            for name, (original, wrapper) in self.originals.items():
                if getattr(menu, name) is wrapper:
                    setattr(menu, name, original)
            self.originals.clear()
            return
        for name in ('main_menu', 'pick_menu', 'seq_option', 'pick_sele', 'pick_option'):
            if name in self.originals:
                continue
            original = getattr(menu, name)
            @functools.wraps(original)
            def wrapper(*args, _original=original, **kwargs):
                rows = _original(*args, **kwargs)
                caller = sys._getframe(1)
                frames = []
                frame = caller
                for _ in range(6):
                    if frame is None:
                        break
                    frames.append((frame.f_globals.get('__name__'), frame.f_code.co_name))
                    frame = frame.f_back
                self.last_call = {'menu': _original.__name__, 'callers': frames}
                # Only replace menus requested by the native GUI, not calls from
                # Python scripts or the stock menu's nested menu generators.
                native = (caller.f_globals.get('__name__') in ('pymol2', 'pmg_qt.pymol_gl_widget')
                          and any(module == 'pmg_qt.pymol_gl_widget' for module, _ in frames))
                if native and self.panel.controller.style.enabled:
                    self.requested.emit(rows, QtGui.QCursor.pos())
                    return []
                return rows
            self.originals[name] = (original, wrapper)
            setattr(menu, name, wrapper)

    def show_menu(self, rows, position):
        # The engine has finished handling the initiating mouse event. Release
        # its empty popup outside its bounds before Qt takes the mouse grab.
        self.panel.viewport.pymol.button(0, 1, -10, -10, 0)
        # The first release makes a freshly opened native menu passive during
        # its initial delay; the second release dismisses that empty menu.
        self.panel.viewport.pymol.button(0, 1, -10, -10, 0)
        if not self.panel.controller.style.enabled:
            return
        if self.active:
            self.active.close()
            self.active.deleteLater()
        self.active = QtWidgets.QMenu(self.panel)
        self.active.setProperty('_pymol_zh_verbatim', True)
        self.panel.populate(self.active, rows)
        self.active.popup(position)
