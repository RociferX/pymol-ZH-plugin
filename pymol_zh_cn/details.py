"""Display delegates for stock property keys and settings; models stay English."""
from ._qt import QtCore, QtGui, QtWidgets

from .settings_catalog import SETTINGS

FIELDS = dict(line.split(':', 1) for line in (
    'model:对象', 'index:原子索引', 'segi:片段标识', 'chain:链标识',
    'resi:残基编号', 'resn:残基名称', 'oneletter:单字母代码', 'name:原子名称',
    'alt:替代构象', 'ID:原子 ID', 'rank:顺序编号', 'elem:元素', 'q:占有率',
    'b:B 因子', 'type:原子类型', 'formal_charge:形式电荷', 'partial_charge:部分电荷',
    'numeric_type:数字类型', 'text_type:文本类型', 'vdw:范德华半径',
    'ss:二级结构', 'color:颜色编号', 'reps:表示位掩码', 'flags:标志位',
    'label:标签', 'cartoon:二级结构示意类型', 'protons:质子数',
    'geom:几何类型', 'valence:价态', 'elec_radius:静电半径',
    'state:状态', 'x:X 坐标', 'y:Y 坐标', 'z:Z 坐标'))


class KeyDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, view, original, controller, settings=False):
        super().__init__(view)
        self.original, self.controller, self.settings = original, controller, settings

    def mapped(self, source):
        if not self.settings and source in FIELDS:
            return FIELDS[source] + ' (' + source + ')'
        if source in SETTINGS:
            name = SETTINGS[source][0]
            return name if self.settings else name + ' (' + source + ')'
        return self.controller.style.catalog.translate(source) if not self.settings else source

    def paint(self, painter, option, index):
        if not self.controller.style.enabled:
            return self.original.paint(painter, option, index)
        copied = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(copied, index)
        copied.text = self.mapped(copied.text)
        style = copied.widget.style() if copied.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, copied, painter, copied.widget)

    def sizeHint(self, option, index):
        size = self.original.sizeHint(option, index)
        text = str(index.data() or '')
        if self.controller.style.enabled:
            translated_width = option.fontMetrics.horizontalAdvance(self.mapped(text)) + 12
            size.setWidth(translated_width if self.settings else max(size.width(), translated_width))
        return size

    def helpEvent(self, event, view, option, index):
        if self.controller.style.enabled and self.settings:
            key = str(index.data() or '')
            info = SETTINGS.get(key)
            if info:
                QtWidgets.QToolTip.showText(event.globalPos(), key + '\n' + info[1], view)
                return True
        return self.original.helpEvent(event, view, option, index)

    def createEditor(self, parent, option, index):
        return self.original.createEditor(parent, option, index)


class DetailDisplays:
    def __init__(self, controller):
        self.controller = controller
        self.records = {}
        self.filters = {}

    def scan(self):
        for widget in self.controller.app.allWidgets():
            if type(widget).__name__ == 'PyMOLAdvancedSettings' and hasattr(widget, 'table'):
                self.attach(widget.table, widget, True)
            elif type(widget).__name__ == 'PropsDialog' and hasattr(widget, 'form'):
                self.attach(widget.form.treeWidget, widget, False)
        for view, original, delegate, width, label, sizing in tuple(self.records.values()):
            enabled = self.controller.style.enabled
            desired = delegate if enabled else original
            if view.itemDelegateForColumn(0) is not desired:
                view.setItemDelegateForColumn(0, desired)
                if id(view) in self.filters:
                    self.filters[id(view)]()
                if enabled:
                    view.resizeColumnToContents(0)
                    if sizing:
                        widget, original_minimum = sizing
                        needed = widget.width() + sum(view.columnWidth(i) for i in range(2)) - view.viewport().width() + 2
                        available = widget.screen().availableGeometry().width() - 20
                        widget.setMinimumWidth(min(available, max(original_minimum, needed)))
                        view.horizontalScrollBar().setValue(0)
                else:
                    view.setColumnWidth(0, width)
                    if sizing:
                        sizing[0].setMinimumWidth(sizing[1])
            if label:
                label.setVisible(enabled)

    def attach(self, view, widget, settings):
        if id(view) in self.records:
            return
        original = view.itemDelegateForColumn(0) or view.itemDelegate()
        delegate = KeyDelegate(view, original, self.controller, settings)
        label = None
        if settings:
            label = QtWidgets.QLabel('选择设置项可查看中文说明。', widget)
            label.setWordWrap(True)
            widget.layout().addWidget(label)
            def describe(current, previous):
                if not current.isValid():
                    label.setText('选择设置项可查看中文说明。')
                    return
                key = str(current.sibling(current.row(), 0).data() or '')
                info = SETTINGS.get(key)
                label.setText(key + '\n' + (info[1] if info else '保留原始设置名称；可使用 PyMOL help 查询该参数。'))
            view.selectionModel().currentChanged.connect(describe)
            def filter_text(_text=None):
                import re
                query = widget.filter_le.text()
                if self.controller.style.enabled and re.search(r'[\u3400-\u9fff]', query):
                    expression = QtCore.QRegularExpression(query)
                    matches = [key for key, info in SETTINGS.items()
                               if expression.match(info[0] + '\n' + info[1]).hasMatch()]
                    widget.proxy_model.setFilterRegExp('^(?:' + '|'.join(matches) + ')$' if matches else '^$')
                else:
                    widget.proxy_model.setFilterRegExp(query)
            widget.filter_le.textChanged.connect(filter_text)
            self.filters[id(view)] = filter_text
        sizing = (widget, widget.minimumWidth()) if settings else None
        self.records[id(view)] = (view, original, delegate, view.columnWidth(0), label, sizing)
        view.destroyed.connect(lambda _=None, key=id(view): self.records.pop(key, None))
        view.destroyed.connect(lambda _=None, key=id(view): self.filters.pop(key, None))
