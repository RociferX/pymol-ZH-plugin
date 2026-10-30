"""Qt companion for the OpenGL ASHLC menus, using stock menu payloads."""
import re
from ._qt import QtCore, QtGui, QtWidgets

COLOR_CODE = re.compile(r'\\[0-9]{3}')


def menu_function(kind, letter):
    """Match Executive.cpp's ASHLC dispatch for each supported object type."""
    if letter == 'A':
        return {'all': 'all_action', 'selection': 'sele_action',
                'object:molecule': 'mol_action', 'object:group': 'group_action',
                'object:map': 'map_action', 'object:mesh': 'mesh_action',
                'object:surface': 'surface_action', 'object:slice': 'slice_action',
                'object:ramp': 'ramp_action'}.get(kind, 'simple_action')
    if letter in ('S', 'H'):
        prefix = {'all': 'mol', 'selection': 'mol', 'object:group': 'mol',
                  'object:molecule': 'mol', 'object:map': 'map', 'object:mesh': 'mesh',
                  'object:surface': 'surface', 'object:slice': 'slice',
                  'object:volume': 'volume', 'object:measurement': 'measurement',
                  'object:cgo': 'cgo', 'object:alignment': 'cgo'}.get(kind)
        return prefix + ('_show' if letter == 'S' else '_hide') if prefix else None
    if letter == 'L':
        return 'mol_labels' if kind in ('all', 'selection', 'object:group', 'object:molecule') else None
    return {'all': 'mol_color', 'selection': 'mol_color', 'object:group': 'mol_color',
            'object:molecule': 'mol_color', 'object:measurement': 'measurement_color',
            'object:map': 'general_color', 'object:cgo': 'general_color',
            'object:alignment': 'general_color', 'object:mesh': 'mesh_color',
            'object:surface': 'mesh_color', 'object:slice': 'slice_color',
            'object:volume': 'vol_color', 'object:ramp': 'ramp_color'}.get(kind)


class ObjectPanel(QtWidgets.QFrame):
    def __init__(self, window, controller):
        self.viewport = window.pymolwidget
        super().__init__(self.viewport)
        self.setObjectName('pymol_zh_object_panel')
        # A native child stacks above QGLWidget's native OpenGL surface.
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAutoFillBackground(True)
        self.controller = controller
        self.cmd = window.cmd
        self.signature = None
        self.menus = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        top = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(QtWidgets.QLabel('对象／选区'))
        self.target = QtWidgets.QComboBox()
        self.target.setProperty('_pymol_zh_verbatim', True)
        self.target.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.target.setMinimumContentsLength(8)
        self.target.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
        top_layout.addWidget(self.target)
        self.enabled_box = QtWidgets.QCheckBox('显示所选对象／选区')
        self.enabled_box.clicked.connect(self.toggle_target)
        top_layout.addWidget(self.enabled_box)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(2)
        self.buttons = {}
        for letter, caption in zip('ASHLC', ('动作', '显示', '隐藏', '标签', '颜色')):
            button = QtWidgets.QPushButton(letter + '\n' + caption)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(button.fontMetrics().lineSpacing() * 2 + 8)
            button.setStyleSheet('QPushButton { padding: 2px; }')
            button.clicked.connect(lambda checked=False, key=letter: self.popup(key))
            self.buttons[letter] = button
            button_layout.addWidget(button)
        top_layout.addLayout(button_layout)
        top_layout.addStretch()
        from .wizard_panel import WizardDisplay
        self.wizard_display = WizardDisplay(self, top_layout)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(top)
        layout.addWidget(scroll, 1)
        from .mouse_panel import MouseStatus
        self.mouse_status = MouseStatus(self.cmd, self)
        layout.addWidget(self.mouse_status)
        from .context_menu import ContextMenus
        self.context_menus = ContextMenus(self)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(400)
        self.timer.timeout.connect(self.refresh)
        self.target.currentIndexChanged.connect(self.update_buttons)
        self.viewport.installEventFilter(self)
        self.refresh()

    def reposition(self):
        width = max(1, self.cmd.get_setting_int('internal_gui_width'))
        self.setGeometry(max(0, self.viewport.width() - width), 0,
                         min(width, self.viewport.width()), self.viewport.height())
        visible = self.controller.style.enabled and bool(self.cmd.get_setting_int('internal_gui'))
        self.setVisible(visible)
        if visible:
            self.raise_()

    def eventFilter(self, watched, event):
        if watched is self.viewport and event.type() in (
                QtCore.QEvent.Type.Resize, QtCore.QEvent.Type.Show):
            self.reposition()
        return False

    def toggle_target(self, checked):
        name = self.target.currentData()
        (self.cmd.enable if checked else self.cmd.disable)(name)

    def set_enabled(self, enabled):
        self.context_menus.set_enabled(enabled)
        for menu in self.menus:
            menu.close()
        if enabled:
            self.refresh()
            self.reposition()
            self.timer.start()
        else:
            self.timer.stop()
            self.wizard_display.stop()
            self.hide()

    def refresh(self):
        if not self.controller.style.enabled:
            return
        self.reposition()
        self.mouse_status.refresh()
        self.wizard_display.refresh()
        self.controller.details.scan()
        self.controller.output.scan()
        self.enabled_box.setChecked(self.target.currentData() in self.cmd.get_names('all', enabled_only=1)
                                    if self.target.currentData() != 'all' else bool(self.cmd.get_names('objects', enabled_only=1)))
        names = self.cmd.get_names('public')
        entries = [('all', 'all')] + [(name, self.cmd.get_type(name)) for name in names]
        if entries == self.signature:
            return
        self.signature = entries
        previous = self.target.currentData()
        self.target.blockSignals(True)
        self.target.clear()
        for name, kind in entries:
            self.target.addItem('全部对象（all）' if kind == 'all' else name, name)
        index = self.target.findData(previous)
        self.target.setCurrentIndex(max(0, index))
        self.target.blockSignals(False)
        self.update_buttons()

    def kind(self):
        name = self.target.currentData()
        return 'all' if name == 'all' else self.cmd.get_type(name)

    def update_buttons(self):
        kind = self.kind()
        for letter, button in self.buttons.items():
            button.setEnabled(menu_function(kind, letter) is not None)

    def build_menu(self, letter):
        from pymol import menu as stock
        name = self.target.currentData()
        kind = self.kind()
        function = menu_function(kind, letter)
        if function is None:
            return None
        args = [self.cmd, '(all)' if kind == 'all' and letter == 'L' else name]
        if kind == 'object:surface' and letter == 'C':
            args.append('surface')
        rows = getattr(stock, function)(*args)
        menu = QtWidgets.QMenu(self)
        menu.setProperty('_pymol_zh_verbatim', True)
        self.populate(menu, rows)
        return menu

    def populate(self, menu, rows, captions=None):
        catalog = self.controller.style.catalog
        names = set(self.cmd.get_names('all'))
        for code, source, payload in rows:
            if code == 0:
                menu.addSeparator()
                continue
            clean = COLOR_CODE.sub('', source).strip()
            # Dynamic object/ramp names never go through the display dictionary.
            caption = ((captions or {}).get(clean) or
                       (clean if clean in names else catalog.translate(clean)))
            caption = caption.replace('&', '&&')
            if isinstance(payload, list) or callable(payload):
                child = menu.addMenu(caption)
                child.setProperty('_pymol_zh_verbatim', True)
                if callable(payload):
                    child.aboutToShow.connect(lambda m=child, f=payload, c=captions: self.populate_lazy(m, f, c))
                else:
                    self.populate(child, payload, captions)
                action = child.menuAction()
            else:
                action = menu.addAction(caption)
                action.setEnabled(code != 2 and bool(payload))
                if code != 2 and payload:
                    # Store and submit the exact stock command, never the caption.
                    action.setData(payload)
                    action.triggered.connect(lambda checked=False, command=payload: self.cmd.do(command))
            action.setProperty('_pymol_zh_source', source)
            if COLOR_CODE.search(source):
                colors = COLOR_CODE.findall(source)
                pixmap = QtGui.QPixmap(24, 16)
                painter = QtGui.QPainter(pixmap)
                for index, code in enumerate(colors):
                    start = round(index * 24 / len(colors))
                    end = round((index + 1) * 24 / len(colors))
                    color = QtGui.QColor(*(round(int(v) * 255 / 9) for v in code[1:]))
                    painter.fillRect(start, 0, end - start, 16, color)
                painter.end()
                action.setIcon(QtGui.QIcon(pixmap))

    def populate_lazy(self, menu, factory, captions=None):
        menu.clear()
        self.populate(menu, factory(), captions)

    def popup(self, letter):
        self.refresh()
        menu = self.build_menu(letter)
        if menu is None:
            return
        for previous in self.menus:
            previous.close()
            previous.deleteLater()
        self.menus = [menu]
        button = self.buttons[letter]
        menu.popup(button.mapToGlobal(QtCore.QPoint(0, button.height())))


def attach(controller):
    from pmg_qt.pymol_qt_gui import window
    if window is not None:
        controller.object_panel = ObjectPanel(window, controller)
        controller.object_panel.set_enabled(True)
