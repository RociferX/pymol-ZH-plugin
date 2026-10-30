"""Display-only children for text that Qt paints outside QStyle.

The source QLabel.text() and QLineEdit.placeholderText() stay unchanged.
"""
from ._qt import QtCore, QtGui, QtWidgets, is_command_text

STOCK_TITLES = {
    'Reflection File Import', 'Map Import', 'Maestro File Import', 'Load Alignment',
    'Save Molecule', 'Shortcut Help', 'Properties Inspector', 'Plugin Manager',
    'Movie Export', 'Create Shortcut', 'Save PNG image',
    'Confirm Changing Existing Binding', 'Colors', 'Get PDB File',
    'Trajectory Import', 'Load Session', 'Builder', 'Scene Panel',
    'Keyboard Shortcut Menu', 'External GUI', 'PyMOL Advanced Settings',
    'Error', 'Warning', 'Save?', 'Load as structures?',
}

class TextOverlays:
    def __init__(self, controller):
        self.controller = controller
        self.records = {}
        self.title_records = {}
        self.title_busy = False
        self.busy = False

    def refresh(self, widget):
        if isinstance(widget, QtWidgets.QWidget) and widget.isWindow():
            self.refresh_title(widget)
        if (self.busy or not isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QLabel))
                or widget.property('_pymol_zh_overlay') or is_command_text(widget)):
            return
        self.busy = True
        try:
            key = id(widget)
            record = self.records.get(key)
            if not self.controller.style.enabled:
                if record:
                    self._restore(record)
                return
            catalog = self.controller.style.catalog
            if isinstance(widget, QtWidgets.QLineEdit):
                source = widget.placeholderText()
                translated = catalog.translate(source)
                kind = 'placeholder'
            else:
                source = widget.text()
                if source.lstrip().startswith('<'):
                    translated = catalog.translate_html(source)
                    kind = 'rich'
                else:
                    translated = catalog.translate(source)
                    kind = 'wrapped' if (widget.wordWrap() or
                               isinstance(widget.window(), QtWidgets.QMessageBox)) else 'label_width'
            if translated == source:
                if record:
                    self._restore(record)
                return
            if kind == 'label_width':
                return
            if record is None:
                record = {'widget': widget, 'minimum_width': widget.minimumWidth(),
                          'palette': QtGui.QPalette(widget.palette()), 'kind': kind}
                self.records[key] = record
                widget.destroyed.connect(lambda _=None, key=key: self.records.pop(key, None))
            record['active'] = True
            overlay = record.get('overlay')
            if overlay is None:
                overlay = QtWidgets.QLabel(widget)
                overlay.setProperty('_pymol_zh_overlay', True)
                overlay.setObjectName('_pymol_zh_display_text')
                record['overlay'] = overlay
                if kind == 'placeholder':
                    overlay.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    overlay.setStyleSheet('background: transparent; border: none; padding: 0px;')
                    widget.textChanged.connect(lambda _text, widget=widget: self.refresh(widget))
                else:
                    overlay.setAutoFillBackground(True)
                    overlay.linkActivated.connect(widget.linkActivated.emit)
                    overlay.linkHovered.connect(widget.linkHovered.emit)
            overlay.setFont(widget.font())
            overlay.setText(translated)
            if kind == 'placeholder':
                original = record['palette']
                color = original.color(QtGui.QPalette.ColorRole.PlaceholderText)
                hidden = QtGui.QPalette(original)
                hidden.setColor(QtGui.QPalette.ColorRole.PlaceholderText, QtGui.QColor(0, 0, 0, 0))
                widget.setPalette(hidden)
                palette = QtGui.QPalette(original)
                palette.setColor(QtGui.QPalette.ColorRole.WindowText, color)
                overlay.setPalette(palette)
                frame = QtWidgets.QStyleOptionFrame()
                frame.initFrom(widget)
                frame.lineWidth = widget.style().pixelMetric(
                    QtWidgets.QStyle.PixelMetric.PM_DefaultFrameWidth, frame, widget)
                rect = widget.style().subElementRect(
                    QtWidgets.QStyle.SubElement.SE_LineEditContents, frame, widget)
                margins = widget.textMargins()
                rect.adjust(margins.left() + 2, margins.top(), -margins.right() - 2, -margins.bottom())
                overlay.setGeometry(rect)
                # Long hints are allowed to use a smaller font inside the
                # input, but the user's editable content keeps its own font.
                available = rect.width()
                font = QtGui.QFont(widget.font())
                while (QtGui.QFontMetrics(font).horizontalAdvance(translated) > available
                       and font.pointSizeF() > 8):
                    font.setPointSizeF(max(8, font.pointSizeF() - 0.5))
                overlay.setFont(font)
                overlay.setAlignment(widget.alignment())
                centered_focus = (widget.hasFocus() and bool(
                    widget.alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter))
                overlay.setVisible(widget.isVisible() and not widget.text() and not centered_focus)
            else:
                overlay.setPalette(widget.palette())
                overlay.setWordWrap(widget.wordWrap() or isinstance(widget.window(), QtWidgets.QMessageBox))
                overlay.setAlignment(widget.alignment())
                overlay.setMargin(widget.margin())
                overlay.setTextInteractionFlags(widget.textInteractionFlags())
                overlay.setOpenExternalLinks(widget.openExternalLinks())
                overlay.setGeometry(widget.contentsRect())
                overlay.setVisible(widget.isVisible())
            overlay.raise_()
        finally:
            self.busy = False

    def refresh_title(self, widget):
        # Native title bars are drawn by Windows, so use its title API and
        # retain the original separately. Only exact stock titles are mapped.
        if self.title_busy:
            return
        self.title_busy = True
        try:
            key = id(widget)
            current = widget.windowTitle()
            record = self.title_records.get(key)
            source = record[0] if record and current == record[1] else current
            translated = self.controller.style.catalog.translate(source) if source in STOCK_TITLES else source
            if self.controller.style.enabled and translated != source:
                if key not in self.title_records:
                    widget.destroyed.connect(lambda _=None, key=key: self.title_records.pop(key, None))
                self.title_records[key] = (source, translated)
                if current != translated:
                    widget.setWindowTitle(translated)
            else:
                self.title_records.pop(key, None)
                if current != source:
                    widget.setWindowTitle(source)
        finally:
            self.title_busy = False

    def _restore(self, record):
        if not record.get('active'):
            return
        record['active'] = False
        widget = record['widget']
        if record['kind'] == 'placeholder':
            widget.setPalette(record['palette'])
        widget.setMinimumWidth(record['minimum_width'])
        if record.get('overlay') is not None:
            record['overlay'].hide()

    def scan(self):
        for widget in self.controller.app.allWidgets():
            self.refresh(widget)
