"""Translate temporary Qt paint options, keeping widget/model values intact."""
from ._qt import QtCore, QtGui, QtWidgets, is_command_text
from .translation import Catalog


class ChineseDisplayStyle(QtWidgets.QProxyStyle):
    def __init__(self, base_style, catalog=None):
        super().__init__(base_style)
        self.catalog = catalog or Catalog()
        self.enabled = True
        self.drawn_sources = set()
        self._data_paint_depth = 0

    def mapped(self, text):
        translated = self.catalog.translate(text) if self.enabled else text
        if translated != text:
            self.drawn_sources.add(text)
        return translated

    def _text_field(self, option, widget=None):
        # Qt 5 stylesheet code can pass a basic option whose type tag looks
        # like QStyleOptionButton while measuring a QLineEdit. Reading its
        # nonexistent QString is a native crash, so match the owning widget
        # as well as the option type before accessing any text field.
        pairs = (
            (QtWidgets.QStyleOptionButton, QtWidgets.QAbstractButton, 'text'),
            (QtWidgets.QStyleOptionToolButton, QtWidgets.QToolButton, 'text'),
            (QtWidgets.QStyleOptionMenuItem, (QtWidgets.QMenu, QtWidgets.QMenuBar), 'text'),
            (QtWidgets.QStyleOptionTab, QtWidgets.QTabBar, 'text'),
            (QtWidgets.QStyleOptionHeader, QtWidgets.QHeaderView, 'text'),
            (QtWidgets.QStyleOptionGroupBox, QtWidgets.QGroupBox, 'text'),
            (QtWidgets.QStyleOptionComboBox, QtWidgets.QComboBox, 'currentText'),
            (QtWidgets.QStyleOptionDockWidget, QtWidgets.QDockWidget, 'title'),
            (QtWidgets.QStyleOptionTitleBar, QtWidgets.QMdiSubWindow, 'text'),
        )
        for option_type, widget_type, field in pairs:
            if isinstance(option, option_type) and (widget is None or isinstance(widget, widget_type)):
                return field
        if isinstance(option, QtWidgets.QStyleOptionViewItem) and self._is_combo_popup(widget):
            return 'text'
        return None

    def _option(self, option, widget=None):
        if option is None or not self.enabled or self._verbatim(widget):
            return option
        # PyQt5 can reuse a stack option wrapper with a stale Python class.
        # Native combo selection exposed a ViewItem wrapper around a ComboBox
        # option. Reading its nonexistent QString is an access violation.
        if (option.type != type(option).Type or option.version < type(option).Version):
            return option
        # Object names, filenames, sequences and editable settings are data.
        # Only standard combo-box option lists use translated item-view paint.
        if isinstance(option, QtWidgets.QStyleOptionViewItem):
            if not self._is_combo_popup(widget):
                return option
        if isinstance(option, QtWidgets.QStyleOptionComboBox) and option.editable:
            return option
        field = self._text_field(option, widget)
        if field is None:
            return option
        original = getattr(option, field)
        translated = self.mapped(original)
        if translated == original:
            return option
        copy = type(option)(option)
        setattr(copy, field, translated)
        return copy

    @staticmethod
    def _verbatim(widget):
        while widget is not None:
            if widget.property('_pymol_zh_verbatim'):
                return True
            widget = widget.parentWidget()
        return False

    @staticmethod
    def _is_combo_popup(widget):
        while widget is not None:
            if isinstance(widget, QtWidgets.QComboBox):
                return True
            widget = widget.parentWidget()
        return False

    def drawControl(self, element, option, painter, widget=None):
        preserve_data = (self._verbatim(widget) or
                         (isinstance(option, QtWidgets.QStyleOptionViewItem)
                          and not self._is_combo_popup(widget)))
        self._data_paint_depth += int(preserve_data)
        try:
            return super().drawControl(element, self._option(option, widget), painter, widget)
        finally:
            self._data_paint_depth -= int(preserve_data)

    def drawComplexControl(self, control, option, painter, widget=None):
        return super().drawComplexControl(control, self._option(option, widget), painter, widget)

    def drawItemText(self, painter, rect, flags, palette, enabled, text,
                     text_role=QtGui.QPalette.ColorRole.NoRole):
        # Plain QLabel text is drawn through this virtual method.
        return super().drawItemText(painter, rect, flags, palette, enabled,
                                    text if self._data_paint_depth or is_command_text(painter.device())
                                    else self.mapped(text), text_role)

    def itemTextRect(self, metrics, rect, flags, enabled, text):
        return super().itemTextRect(metrics, rect, flags, enabled, self.mapped(text))

    def sizeFromContents(self, contents_type, option, size, widget=None):
        copied = self._option(option, widget)
        adjusted = QtCore.QSize(size)
        # Widgets often precompute the English text width before calling style.
        if copied is not option and option is not None:
            field = self._text_field(option, widget)
            if field:
                metrics = option.fontMetrics
                before = getattr(option, field).split('\t')[0].replace('&', '')
                after = getattr(copied, field).split('\t')[0].replace('&', '')
                delta = metrics.horizontalAdvance(after) - metrics.horizontalAdvance(before)
                # Do not shrink controls or change established panel geometry.
                adjusted.setWidth(adjusted.width() + max(0, delta))
        return super().sizeFromContents(contents_type, copied, adjusted, widget)


class DisplayController(QtCore.QObject):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        name = app.style().objectName()
        self.base_style_name = name
        self.disposed = False
        # QProxyStyle takes ownership: create a separate base, never steal the
        # current QApplication style or modify a PyMOL class/method.
        base = QtWidgets.QStyleFactory.create(name)
        if base is None:
            raise RuntimeError(f'Unsupported Qt style: {name!r}')
        self.style = ChineseDisplayStyle(base)
        app.setStyle(self.style)
        from .overlays import TextOverlays
        from .layout import DisplayLayout
        self.overlays = TextOverlays(self)
        self.layout = DisplayLayout(self)
        from .details import DetailDisplays
        self.details = DetailDisplays(self)
        from .output_display import OutputDisplays
        self.output = OutputDisplays(self)
        from .combo_display import ComboDisplays
        self.combos = ComboDisplays(self)
        app.installEventFilter(self)
        app.aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        if self.disposed:
            return
        self.set_enabled(False)
        if hasattr(self, 'object_panel'):
            self.object_panel.viewport.removeEventFilter(self.object_panel)
            self.object_panel.wizard_display.prompt.deleteLater()
            self.object_panel.deleteLater()
            del self.object_panel
        self.app.removeEventFilter(self)
        self.disposed = True
        # Release Python virtual paint callbacks before Qt destroys its widgets.
        self.app.setStyle(self.base_style_name)

    def set_enabled(self, enabled):
        if self.disposed:
            return
        self.style.enabled = bool(enabled)
        if hasattr(self, 'object_panel'):
            self.object_panel.set_enabled(bool(enabled))
        self.overlays.scan()
        self.layout.scan()
        self.details.scan()
        self.output.scan()
        self.combos.scan()
        for widget in self.app.allWidgets():
            widget.updateGeometry()
            widget.update()
        QtWidgets.QToolTip.hideText()

    def eventFilter(self, watched, event):
        if event.type() in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.Polish,
                             QtCore.QEvent.Type.Resize, QtCore.QEvent.Type.FocusIn,
                             QtCore.QEvent.Type.FocusOut, QtCore.QEvent.Type.FontChange,
                             QtCore.QEvent.Type.WindowTitleChange):
            self.overlays.refresh(watched)
            self.layout.refresh(watched)
            self.output.refresh(watched)
            self.combos.refresh(watched)
        # Tooltip text also remains English on the original widget.
        if (self.style.enabled and event.type() == QtCore.QEvent.Type.ToolTip
                and isinstance(watched, QtWidgets.QWidget)):
            original = watched.toolTip()
            translated = self.style.mapped(original)
            if translated != original:
                QtWidgets.QToolTip.showText(event.globalPos(), translated, watched)
                event.accept()
                return True
        return False
