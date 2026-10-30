"""Reserve space for translated display text, with reversible constraints."""
from ._qt import QtCore, QtGui, QtWidgets, is_command_text


def text_size(widget, text):
    # A single ampersand denotes a mnemonic; && denotes a visible ampersand.
    text = text.replace('&&', '\0').replace('&', '').replace('\0', '&')
    metrics = widget.fontMetrics()
    lines = text.split('\n')
    return QtCore.QSize(max((metrics.horizontalAdvance(line) for line in lines), default=0),
                        metrics.lineSpacing() * len(lines))


class DisplayLayout:
    def __init__(self, controller):
        self.controller = controller
        self.records = {}
        self.busy = False

    def _remember(self, widget):
        key = id(widget)
        if key not in self.records:
            self.records[key] = {
                'widget': widget, 'minimum': QtCore.QSize(widget.minimumSize()),
                'maximum': QtCore.QSize(widget.maximumSize()),
            }
            if isinstance(widget, QtWidgets.QTabBar):
                self.records[key]['elide'] = widget.elideMode()
                self.records[key]['expanding'] = widget.expanding()
                self.records[key]['scroll_buttons'] = widget.usesScrollButtons()
            widget.destroyed.connect(lambda _=None, key=key: self.records.pop(key, None))
        return self.records[key]

    def _fit(self, widget, needed):
        record = self._remember(widget)
        minimum = record['minimum'].expandedTo(needed)
        if isinstance(widget, (QtWidgets.QGroupBox, QtWidgets.QTabWidget)):
            # An explicit title minimum must not replace the larger minimum
            # required by translated controls inside this container.
            minimum = minimum.expandedTo(widget.minimumSizeHint())
        maximum = record['maximum'].expandedTo(minimum)
        # Preserve the natural size policy and existing larger minimums. Fixed
        # controls grow only as far as needed by the Chinese caption.
        if widget.maximumSize() != maximum:
            widget.setMaximumSize(maximum)
        if widget.minimumSize() != minimum:
            widget.setMinimumSize(minimum)

    def refresh(self, widget):
        if self.busy or not isinstance(widget, QtWidgets.QWidget):
            return
        if widget.property('_pymol_zh_overlay') or is_command_text(widget):
            return
        if not self.controller.style.enabled:
            record = self.records.pop(id(widget), None)
            if record:
                self._restore(record)
            return
        self.busy = True
        try:
            self._refresh(widget)
        finally:
            self.busy = False

    def _refresh(self, widget):
        catalog = self.controller.style.catalog
        if isinstance(widget, QtWidgets.QLabel):
            source = widget.text()
            rich = source.lstrip().startswith('<')
            translated = catalog.translate_html(source) if rich else catalog.translate(source)
            if translated == source:
                return
            margin = widget.margin() + widget.frameWidth()
            margins = widget.contentsMargins()
            inset = 2 * margin + margins.left() + margins.right() + max(0, widget.indent())
            size = text_size(widget, translated)
            message = isinstance(widget.window(), QtWidgets.QMessageBox)
            if widget.wordWrap() or rich or message:
                # Use the current line width; translation can need extra lines
                # even when the English source fit on one line.
                width = max(1, widget.contentsRect().width() - inset)
                document = QtGui.QTextDocument()
                document.setDocumentMargin(0)
                document.setDefaultFont(widget.font())
                if rich:
                    document.setHtml(translated)
                else:
                    document.setPlainText(translated)
                if widget.wordWrap() or message:
                    document.setTextWidth(width)
                self._fit(widget, QtCore.QSize(0, int(document.size().height() + 0.999) +
                                              2 * margin + margins.top() + margins.bottom()))
            else:
                size += QtCore.QSize(inset + 4, 2 * margin + margins.top() + margins.bottom() + 2)
                self._fit(widget, size)
        elif isinstance(widget, QtWidgets.QAbstractButton):
            source = widget.text()
            translated = catalog.translate(source)
            if translated == source or not translated:
                return
            size = text_size(widget, translated)
            option = QtWidgets.QStyleOptionButton()
            option.initFrom(widget)
            option.text = translated
            option.icon = widget.icon()
            option.iconSize = widget.iconSize()
            if not widget.icon().isNull():
                size.setWidth(size.width() + widget.iconSize().width() + 6)
                size.setHeight(max(size.height(), widget.iconSize().height()))
            if isinstance(widget, QtWidgets.QCheckBox):
                kind = QtWidgets.QStyle.ContentsType.CT_CheckBox
            elif isinstance(widget, QtWidgets.QRadioButton):
                kind = QtWidgets.QStyle.ContentsType.CT_RadioButton
            elif isinstance(widget, QtWidgets.QToolButton):
                # Tool buttons with icons may deliberately omit their caption.
                if widget.toolButtonStyle() == QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly:
                    return
                option = QtWidgets.QStyleOptionToolButton()
                option.initFrom(widget)
                option.text = translated
                option.icon = widget.icon()
                option.iconSize = widget.iconSize()
                kind = QtWidgets.QStyle.ContentsType.CT_ToolButton
            else:
                kind = QtWidgets.QStyle.ContentsType.CT_PushButton
                if widget.menu() is not None:
                    option.features |= QtWidgets.QStyleOptionButton.ButtonFeature.HasMenu
            # Use the native stylesheet too, so CSS padding/borders and check
            # indicators are counted instead of guessing pixel constants.
            needed = widget.style().sizeFromContents(kind, option, size, widget)
            self._fit(widget, needed + QtCore.QSize(4, 2))
        elif isinstance(widget, QtWidgets.QComboBox) and not widget.isEditable():
            sources = [widget.itemText(i) for i in range(widget.count())]
            translated = [catalog.translate(text) for text in sources]
            if sources == translated:
                return
            sizes = [text_size(widget, text) for text in translated]
            content = QtCore.QSize(max((s.width() for s in sizes), default=0),
                                   max((s.height() for s in sizes), default=0))
            option = QtWidgets.QStyleOptionComboBox()
            option.initFrom(widget)
            option.currentText = ''
            option.editable = False
            needed = widget.style().sizeFromContents(
                QtWidgets.QStyle.ContentsType.CT_ComboBox, option, content, widget)
            self._fit(widget, needed + QtCore.QSize(6, 2))
        elif isinstance(widget, QtWidgets.QTabBar):
            if not any(catalog.translate(widget.tabText(i)) != widget.tabText(i)
                       for i in range(widget.count())):
                return
            self._remember(widget)
            widget.setElideMode(QtCore.Qt.TextElideMode.ElideNone)
            widget.setExpanding(False)
            # Keep all common dialog tabs visible when they fit the screen.
            # Native Qt tab bars may reject protected tabSizeHint calls in
            # Python bindings. The public hint already combines all tab sizes.
            width = widget.sizeHint().width()
            screen = widget.screen()
            limit = screen.availableGeometry().width() - 32 if screen else 1200
            if width < limit:
                widget.setUsesScrollButtons(False)
                self._fit(widget, QtCore.QSize(width + 4, 0))
                parent = widget.parentWidget()
                if isinstance(parent, QtWidgets.QTabWidget):
                    self._fit(parent, QtCore.QSize(width + 12, 0))
        elif isinstance(widget, QtWidgets.QGroupBox):
            source = widget.title()
            translated = catalog.translate(source)
            if translated != source:
                size = text_size(widget, translated)
                self._fit(widget, QtCore.QSize(size.width() + 28, 0))

    def _restore(self, record):
        widget = record['widget']
        if widget.minimumSize() != record['minimum']:
            widget.setMinimumSize(record['minimum'])
        if widget.maximumSize() != record['maximum']:
            widget.setMaximumSize(record['maximum'])
        if 'elide' in record:
            widget.setElideMode(record['elide'])
            widget.setExpanding(record['expanding'])
            widget.setUsesScrollButtons(record['scroll_buttons'])

    def scan(self):
        # Child captions must settle before a parent tab/window measures them.
        widgets = list(self.controller.app.allWidgets())
        for widget in widgets:
            if not isinstance(widget, QtWidgets.QTabBar):
                self.refresh(widget)
        for widget in widgets:
            if isinstance(widget, QtWidgets.QTabBar):
                self.refresh(widget)
