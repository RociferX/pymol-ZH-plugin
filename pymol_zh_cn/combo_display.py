"""Translate native combo popup delegates without changing their models."""
from ._qt import QtCore, QtWidgets


class ComboDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, combo, original, controller):
        super().__init__(combo.view())
        self.original, self.controller = original, controller

    def paint(self, painter, option, index):
        source = str(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or '')
        target = self.controller.style.catalog.translate(source)
        if not self.controller.style.enabled or target == source:
            return self.original.paint(painter, option, index)
        copied = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(copied, index)
        copied.text = target
        style = copied.widget.style() if copied.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, copied, painter, copied.widget)

    def sizeHint(self, option, index):
        size = self.original.sizeHint(option, index)
        source = str(index.data(QtCore.Qt.ItemDataRole.DisplayRole) or '')
        target = self.controller.style.catalog.translate(source)
        if self.controller.style.enabled and source != target:
            delta = option.fontMetrics.horizontalAdvance(target) - option.fontMetrics.horizontalAdvance(source)
            size.setWidth(size.width() + max(0, delta))
            size.setHeight(max(size.height(), option.fontMetrics.height() + 4))
        return size


class ComboDisplays:
    def __init__(self, controller):
        self.controller, self.records = controller, {}
        self.busy = False

    def refresh(self, widget):
        if self.busy:
            return
        if isinstance(widget, QtWidgets.QAbstractItemView):
            while widget and not isinstance(widget, QtWidgets.QComboBox):
                widget = widget.parentWidget()
        if not isinstance(widget, QtWidgets.QComboBox):
            return
        self.busy = True
        try:
            key = id(widget)
            record = self.records.get(key)
            enabled = (self.controller.style.enabled and not widget.isEditable()
                       and not self.controller.style._verbatim(widget))
            if record is None and enabled and any(
                    self.controller.style.catalog.translate(widget.itemText(i)) != widget.itemText(i)
                    for i in range(widget.count())):
                original = widget.itemDelegate()
                record = (widget, original, ComboDelegate(widget, original, self.controller))
                self.records[key] = record
                widget.destroyed.connect(lambda _=None, key=key: self.records.pop(key, None))
            if record:
                desired = record[2] if enabled else record[1]
                if widget.itemDelegate() is not desired:
                    # QComboBox.setItemDelegate deletes its owned stock
                    # delegate. The view setter retains it for restoration.
                    widget.view().setItemDelegate(desired)
        finally:
            self.busy = False

    def scan(self):
        for widget in self.controller.app.allWidgets():
            if isinstance(widget, QtWidgets.QComboBox):
                self.refresh(widget)
