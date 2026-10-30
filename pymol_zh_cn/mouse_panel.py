"""Chinese display of stock mouse-mode defaults and live state/playback."""
from html import escape
from ._qt import QtCore, QtWidgets

ACTION = {
    'rota': '旋转', 'move': '平移', 'movz': '缩放', 'clip': '裁剪',
    'rotz': '绕轴转', 'clpn': '近裁面', 'clpf': '远裁面', 'none': '—',
    'pkat': '选原子', 'pkbd': '选化学键', 'pk1': '拾取', 'pktb': '选扭转键',
    'rotf': '旋片段', 'torf': '转扭角', 'movf': '移片段', 'orig': '旋转中心',
    'cent': '居中', 'slab': '裁剪厚度', 'movs': '移裁剪面', 'mvsz': '缩裁剪面',
    'mova': '移原子', 'menu': '菜单', 'sele': '选择', '+/-': '切换选择',
    '+box': '框选增加', '-box': '框选减少', 'roto': '旋对象', 'movo': '移对象',
    'mvoz': '对象纵移', 'drgm': '拖分子', 'rotv': '旋视图', 'movv': '移视图',
    'mvvz': '视图纵移', 'drgo': '拖对象', 'imvz': '缩放', 'imsz': '缩放',
    'box': '框选', 'irtz': '绕轴转', 'rotl': '旋光源', 'movl': '移光源',
    'mvzl': '光源纵移', 'mvfz': '片段纵移', 'mvaz': '原子纵移',
}
COMPACT = {'裁剪厚度': '厚度', '移裁剪面': '移裁面', '缩裁剪面': '缩裁面',
           '框选增加': '框加', '框选减少': '框减', '旋转中心': '旋心',
           '切换选择': '选/取消', '选化学键': '选键', '选扭转键': '扭转键'}
COMPACT.update({'移裁剪面': '移面', '缩裁剪面': '缩面', '切换选择': '切选',
                '选原子': '原子', '选扭转键': '扭键', '旋片段': '片旋',
                '移片段': '片移', '转扭角': '扭角', '移原子': '移原',
                '旋对象': '旋物', '移对象': '移物', '对象纵移': '纵移',
                '片段纵移': '纵移', '原子纵移': '纵移', '视图纵移': '纵移',
                '光源纵移': '纵移', '拖分子': '拖分', '旋视图': '旋视',
                '移视图': '移视', '拖对象': '拖物', '旋光源': '旋光',
                '移光源': '移光', '绕轴转': '轴转', '近裁面': '近面', '远裁面': '远面'})


class MouseStatus(QtWidgets.QWidget):
    def __init__(self, cmd, parent):
        super().__init__(parent)
        self.cmd = cmd
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.mode = QtWidgets.QPushButton()
        self.mode.clicked.connect(lambda: self.change_mode())
        self.mode.setToolTip('切换下一个鼠标模式；下表显示该模式的默认键位。')
        layout.addWidget(self.mode)
        self.bindings = QtWidgets.QLabel()
        self.bindings.setWordWrap(True)
        layout.addWidget(self.bindings)
        self.selection = QtWidgets.QPushButton()
        self.selection.clicked.connect(lambda: self.change_selection())
        layout.addWidget(self.selection)
        self.state = QtWidgets.QLabel()
        layout.addWidget(self.state)
        controls = QtWidgets.QGridLayout()
        controls.setSpacing(1)
        for index, (text, callback) in enumerate((('首帧', cmd.rewind), ('上帧', cmd.backward),
                               ('下帧', cmd.forward), ('末帧', cmd.ending),
                               ('播放', cmd.mplay), ('停止', cmd.mstop),
                               ('序列', lambda: cmd.set('seq_view', not cmd.get_setting_int('seq_view'))),
                               ('全屏', lambda: cmd.full_screen()))):
            button = QtWidgets.QPushButton(text)
            button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Fixed)
            button.setStyleSheet('QPushButton { padding: 2px; }')
            button.clicked.connect(lambda checked=False, f=callback: f())
            controls.addWidget(button, index // 4, index % 4)
        layout.addLayout(controls)
        self.refresh()

    def change_mode(self):
        self.cmd.mouse('forward')
        self.refresh()

    def change_selection(self):
        self.cmd.mouse('select_forward')
        self.refresh()

    def refresh(self):
        from pymol.controlling import mode_dict, mode_name_dict
        name = self.cmd.get('button_mode_name')
        key = next((key for key, value in mode_name_dict.items() if value == name), name)
        catalog = self.parentWidget().controller.style.catalog
        self.mode.setText(catalog.translate(name) if name else '鼠标模式未设置')
        data = {(button.lower(), modifier): action.lower()
                for button, modifier, action in mode_dict.get(key, [])}
        rows = ['<table width="100%" cellspacing="2" cellpadding="0">'
                '<tr><td>默认键位</td><td>左键</td><td>中键</td><td>右键</td><td>滚轮</td></tr>']
        descriptions = []
        for modifier, title in (('none', '拖动'), ('shft', 'Shift'), ('ctrl', 'Ctrl'),
                                ('ctsh', 'Ctrl+Shift'), ('alt', 'Alt')):
            cells = [title] + [ACTION.get(data.get((button, modifier), 'none'),
                                       data.get((button, modifier), '—'))
                               for button in ('l', 'm', 'r', 'w')]
            descriptions.append(title + '：' + '；'.join(key + value for key, value in zip(('左键 ', '中键 ', '右键 ', '滚轮 '), cells[1:])))
            rows.append('<tr>' + ''.join('<td>' + escape(COMPACT.get(c, c)).replace('Ctrl+Shift', 'Ctrl<br>+Shift') + '</td>' for c in cells) + '</tr>')
        for prefix, title in (('single_', '单击'), ('double_', '双击')):
            cells = [title] + [ACTION.get(data.get((prefix + button, 'none'), 'none'), '—')
                               for button in ('left', 'middle', 'right')] + ['—']
            rows.append('<tr>' + ''.join('<td>' + escape(COMPACT.get(c, c)) + '</td>' for c in cells) + '</tr>')
        rows.append('</table>')
        self.bindings.setText(''.join(rows))
        self.bindings.setToolTip('模式默认键位：\n' + '\n'.join(descriptions) +
                                '\n自定义 button 重绑定不在此表中同步。')
        modes = ('原子', '残基', '链', '片段', '对象', '分子', 'Cα 原子')
        index = self.cmd.get_setting_int('mouse_selection_mode')
        self.selection.setText('选择粒度：' + (modes[index] if 0 <= index < len(modes) else str(index)))
        self.state.setText(f'状态：{self.cmd.get_state()} / {self.cmd.count_states()}    帧：{self.cmd.get_frame()}')
