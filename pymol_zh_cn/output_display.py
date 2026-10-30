"""Overlay Chinese output while retaining the stock English text documents."""
from ._qt import QtCore, QtWidgets
from .output_text import OutputText


class OutputView(QtWidgets.QPlainTextEdit):
    def __init__(self, source, parent, converter):
        super().__init__(parent)
        self.source, self.converter = source, converter
        self.previous = ''
        self.setProperty('_pymol_zh_overlay', True)
        self.setProperty('_pymol_zh_verbatim', True)
        self.setObjectName('pymol_zh_output')
        self.setReadOnly(True)
        self.setFont(source.font())
        self.setPalette(source.palette())
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        proxy = source.focusProxy()
        if proxy:
            self.setFocusProxy(proxy)
            def copy_focus(selected):
                self.setFocusProxy(None if selected else proxy)
                if selected:
                    self.setFocus()
            self.copyAvailable.connect(copy_focus)
        source.document().contentsChanged.connect(self.sync)
        source.installEventFilter(self)
        self.sync()

    def eventFilter(self, watched, event):
        if watched is self.source:
            if event.type() == QtCore.QEvent.Type.Resize and self.parentWidget() is self.source:
                self.setGeometry(self.source.contentsRect())
            elif event.type() == QtCore.QEvent.Type.FontChange:
                self.setFont(self.source.font())
            elif event.type() == QtCore.QEvent.Type.PaletteChange:
                self.setPalette(self.source.palette())
        return False

    def sync(self):
        translated = self.converter.translate(self.source.toPlainText())
        if translated == self.previous:
            return
        bar = self.verticalScrollBar()
        bottom, value = bar.value() >= bar.maximum() - 1, bar.value()
        self.setPlainText(translated)
        self.previous = translated
        bar.setValue(bar.maximum() if bottom else value)


class OutputDisplays:
    def __init__(self, controller):
        self.controller = controller
        self.converter = OutputText()
        self.records = {}
        self.native = None
        self.busy = False

    def refresh(self, widget):
        if self.busy or not isinstance(widget, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            return
        if widget.property('_pymol_zh_overlay') or not widget.isReadOnly():
            return
        if widget.objectName() != 'feedback_browser' and not isinstance(widget.window(), QtWidgets.QMessageBox):
            return
        self.busy = True
        try:
            key = id(widget)
            overlay = self.records.get(key)
            if overlay is None and self.controller.style.enabled:
                overlay = OutputView(widget, widget, self.converter)
                self.records[key] = overlay
                widget.destroyed.connect(lambda _=None, key=key: self.records.pop(key, None))
            if overlay is not None:
                overlay.setGeometry(widget.contentsRect())
                overlay.setVisible(self.controller.style.enabled and widget.isVisible())
                overlay.raise_()
        finally:
            self.busy = False

    def scan(self):
        for widget in self.controller.app.allWidgets():
            self.refresh(widget)
        panel = getattr(self.controller, 'object_panel', None)
        enabled = bool(panel and self.controller.style.enabled and panel.cmd.get_setting_int('text'))
        if enabled and self.native is None:
            source = panel.viewport.window().browser
            self.native = OutputView(source, panel.viewport, self.converter)
            self.native.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow)
            # Full repaint avoids stale scroll blits above the OpenGL child.
            self.native.verticalScrollBar().valueChanged.connect(
                lambda _: QtCore.QTimer.singleShot(0, self.native.viewport().repaint))
        if self.native is not None:
            if panel:
                side = panel.width() if panel.isVisible() else 0
                self.native.setGeometry(0, 0, max(1, panel.viewport.width() - side), panel.viewport.height())
            self.native.setVisible(enabled)
            if enabled:
                self.native.raise_()
