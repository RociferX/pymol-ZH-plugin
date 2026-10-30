"""Display a live wizard's original prompt, buttons and menus in Qt."""
import re
from ._qt import QtCore, QtWidgets

LABEL_MODES = {
    '{resn}-{resi}': '残基名称－编号',
    '{onelettercode}{resi}': '单字母代码与残基编号',
    '{chain}/{resn}`{resi}': '链／残基',
    '{chain}/{resn}`{resi}/{name}`{alt}': '链／残基／原子及替代构象',
    '/{model}/{segi}/{chain}/{resn}`{resi}/{name}`{alt}': '完整原子路径',
    '{chain}': '链标识', '{resn}': '残基名称',
    '{resi}': '残基编号', '{name}': '原子名称',
}

class WizardDisplay(QtWidgets.QGroupBox):
    def __init__(self, panel, layout):
        super().__init__('向导', panel)
        self.panel = panel
        self.signature = None
        self.content = QtWidgets.QVBoxLayout(self)
        layout.insertWidget(layout.count() - 1, self)
        self.prompt = QtWidgets.QLabel(panel.viewport)
        self.prompt.setObjectName('pymol_zh_wizard_prompt')
        self.prompt.setAutoFillBackground(True)
        self.prompt.setWordWrap(True)
        self.prompt.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        self.prompt.setMargin(6)
        self.prompt.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        self.prompt.hide()

    def refresh(self):
        wizard = self.panel.cmd.get_wizard()
        if wizard is None or not self.panel.controller.style.enabled:
            self.hide()
            self.prompt.hide()
            self.signature = None
            return
        rows = wizard.get_panel() or []
        prompts = wizard.get_prompt() or []
        signature = (id(wizard), repr(rows), repr(prompts))
        catalog = self.panel.controller.style.catalog
        text = '\n'.join(catalog.translate(re.sub(r'\\[0-9]{3}', '', s)) for s in prompts)
        self.prompt.setText(text)
        width = max(1, self.panel.viewport.width() - self.panel.width())
        height = max(self.prompt.heightForWidth(width),
                     len(prompts) * max(24, self.prompt.fontMetrics().lineSpacing()) + 24)
        self.prompt.setGeometry(0, 0, width, max(1, height))
        self.prompt.setVisible(bool(text))
        self.prompt.raise_()
        self.setVisible(bool(rows))
        if signature == self.signature:
            return
        self.signature = signature
        while self.content.count():
            item = self.content.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for code, source, payload in rows:
            if code == 0:
                continue
            caption = catalog.translate(re.sub(r'\\[0-9]{3}', '', source))
            if code == 1:
                widget = QtWidgets.QLabel(caption)
                widget.setWordWrap(True)
            else:
                widget = QtWidgets.QPushButton(caption)
                if code == 3:
                    menu = QtWidgets.QMenu(widget)
                    menu.setProperty('_pymol_zh_verbatim', True)
                    menu.aboutToShow.connect(lambda m=menu, w=wizard, tag=payload:
                                            self.panel.populate_lazy(m, lambda: w.get_menu(tag) or [], LABEL_MODES))
                    widget.setMenu(menu)
                elif code == 2:
                    widget.clicked.connect(lambda checked=False, command=payload: self.panel.cmd.do(command))
            self.content.addWidget(widget)

    def stop(self):
        self.hide()
        self.prompt.hide()
