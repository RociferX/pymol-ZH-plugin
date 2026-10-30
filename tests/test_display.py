"""Behavior and rendering regressions for English values / Chinese display."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_support import set_test_font
from pymol_zh_cn._qt import QtCore, QtGui, QtWidgets
from pymol_zh_cn.style import DisplayController
from pymol_zh_cn.translation import Catalog


class CatalogTests(unittest.TestCase):
    def test_menu_syntax_and_unknown_user_content(self):
        catalog = Catalog()
        self.assertEqual(catalog.translate('&Open...'), '打开...')
        self.assertEqual(catalog.translate('Undo [Ctrl-Z]'), '撤销 [Ctrl-Z]')
        self.assertEqual(catalog.translate('Open...\tCtrl+O'), '打开...\tCtrl+O')
        self.assertEqual(catalog.translate('my_Surface.pdb'), 'my_Surface.pdb')
        self.assertEqual(catalog.translate('show surface, all'), 'show surface, all')

    def test_rich_text_preserves_link_destination(self):
        source = '<p>For technical details, visit <a href="https://example.org/Help">Help</a></p>'
        mapped = Catalog().translate_html(source)
        self.assertIn('技术说明请参阅', mapped)
        self.assertIn('href="https://example.org/Help"', mapped)


class DisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        set_test_font(cls.app, QtGui)
        cls.controller = DisplayController(cls.app)

    def setUp(self):
        self.widgets = []
        self.controller.set_enabled(True)

    def widget(self, widget):
        self.widgets.append(widget)
        return widget

    def tearDown(self):
        self.controller.set_enabled(False)
        for widget in self.widgets:
            widget.hide()
            widget.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_button_pixels_match_chinese_reference_without_changing_text(self):
        button = self.widget(QtWidgets.QPushButton('Save Session'))
        button.setFixedSize(180, 36)
        button.show()
        self.app.processEvents()
        chinese = button.grab().toImage()
        self.assertEqual(button.text(), 'Save Session')
        self.controller.set_enabled(False)
        self.app.processEvents()
        english = button.grab().toImage()
        self.assertNotEqual(chinese, english)
        button.setText('保存会话')  # Test oracle: native Qt rendering of the intended text.
        self.app.processEvents()
        self.assertEqual(chinese, button.grab().toImage())

    def test_original_action_callbacks_shortcuts_and_data_survive(self):
        menu = self.widget(QtWidgets.QMenu())
        action = menu.addAction('Save Session')
        action.setShortcut('Ctrl+S')
        action.setData('save_session')
        calls = []
        action.triggered.connect(lambda: calls.append(action.data()))
        menu.show()
        self.app.processEvents()
        action.trigger()
        self.assertEqual(calls, ['save_session'])
        self.assertEqual(action.text(), 'Save Session')
        self.assertEqual(action.shortcut().toString(), 'Ctrl+S')

    def test_combo_values_and_signals_unchanged_on_language_switch(self):
        combo = self.widget(QtWidgets.QComboBox())
        combo.addItems(['Default', 'Maximum Quality'])
        changes = []
        combo.currentTextChanged.connect(changes.append)
        combo.show()
        for enabled in (False, True, False, True):
            self.controller.set_enabled(enabled)
            self.app.processEvents()
        self.assertEqual(changes, [])
        self.assertEqual(combo.currentText(), 'Default')
        self.assertEqual(combo.itemText(1), 'Maximum Quality')
        combo.setCurrentIndex(1)
        self.assertEqual(changes, ['Maximum Quality'])

    def test_model_user_data_is_drawn_verbatim(self):
        view = self.widget(QtWidgets.QTreeWidget())
        view.setHeaderHidden(True)
        view.addTopLevelItem(QtWidgets.QTreeWidgetItem(['Surface']))
        view.resize(240, 100)
        view.show()
        self.app.processEvents()
        chinese_mode = view.grab().toImage()
        self.controller.set_enabled(False)
        self.app.processEvents()
        self.assertEqual(chinese_mode, view.grab().toImage())
        self.assertEqual(view.topLevelItem(0).text(0), 'Surface')

    def test_placeholder_overlay_keeps_source_and_input(self):
        edit = self.widget(QtWidgets.QLineEdit())
        edit.setPlaceholderText('Object name (optional)')
        events = []
        edit.textChanged.connect(events.append)
        edit.show()
        self.app.processEvents()
        overlay = edit.findChild(QtWidgets.QLabel, '_pymol_zh_display_text')
        self.assertIsNotNone(overlay)
        self.assertIn('对象名称', overlay.text())
        self.assertEqual(edit.placeholderText(), 'Object name (optional)')
        self.assertEqual(edit.text(), '')
        self.assertEqual(events, [])
        edit.setText('Surface')
        self.assertFalse(overlay.isVisible())
        self.assertEqual(edit.text(), 'Surface')
        self.controller.set_enabled(False)
        self.assertFalse(overlay.isVisible())

    def test_rich_label_and_link_signal_are_preserved(self):
        source = '<p>For technical details, visit <a href="https://example.org/Help">Help</a></p>'
        label = self.widget(QtWidgets.QLabel(source))
        links = []
        label.linkActivated.connect(links.append)
        label.show()
        self.app.processEvents()
        overlay = label.findChild(QtWidgets.QLabel, '_pymol_zh_display_text')
        self.assertIsNotNone(overlay)
        self.assertEqual(label.text(), source)
        overlay.linkActivated.emit('https://example.org/Help')
        self.assertEqual(links, ['https://example.org/Help'])
        self.controller.set_enabled(False)
        self.assertFalse(overlay.isVisible())

    def test_qt5_lineedit_option_type_tag_is_not_read_as_a_button(self):
        edit = self.widget(QtWidgets.QLineEdit())
        option = QtWidgets.QStyleOptionButton()
        option.text = 'Save Session'
        self.assertIs(self.controller.style._option(option, edit), option)

    def test_tooltip_maps_only_the_display(self):
        button = self.widget(QtWidgets.QPushButton('Open'))
        button.setToolTip('Create an image')
        button.show()
        self.app.processEvents()
        event = QtGui.QHelpEvent(QtCore.QEvent.Type.ToolTip, QtCore.QPoint(3, 3),
                                button.mapToGlobal(QtCore.QPoint(3, 3)))
        self.app.sendEvent(button, event)
        self.assertEqual(button.toolTip(), 'Create an image')
        self.assertEqual(QtWidgets.QToolTip.text(), '创建图像')
        QtWidgets.QToolTip.hideText()

    def test_fixed_button_grows_for_chinese_and_restores_english_constraints(self):
        button = self.widget(QtWidgets.QPushButton('Install New Plugin'))
        button.setFixedSize(46, 18)
        before = (button.minimumSize(), button.maximumSize())
        button.show()
        self.app.processEvents()
        metrics = button.fontMetrics()
        self.assertGreater(button.width(), metrics.horizontalAdvance('安装新插件'))
        self.assertGreaterEqual(button.height(), metrics.height())
        self.assertEqual(button.text(), 'Install New Plugin')
        chinese = button.grab().toImage()
        self.controller.set_enabled(False)
        self.assertEqual((button.minimumSize(), button.maximumSize()), before)
        # At the same larger size, the mapping must match a native Chinese
        # button pixel-for-pixel, including all characters at both edges.
        button.setFixedSize(round(chinese.width() / chinese.devicePixelRatio()),
                            round(chinese.height() / chinese.devicePixelRatio()))
        button.setText('安装新插件')
        self.app.processEvents()
        self.assertEqual(chinese, button.grab().toImage())

    def test_label_caption_and_tabs_have_room_for_complete_text(self):
        form = self.widget(QtWidgets.QWidget())
        layout = QtWidgets.QVBoxLayout(form)
        label = QtWidgets.QLabel('PDB ID:')
        layout.addWidget(label)
        tabs = QtWidgets.QTabWidget()
        for text in ('Generic Options', 'PDB Options', 'Multi-File'):
            tabs.addTab(QtWidgets.QWidget(), text)
        layout.addWidget(tabs)
        form.resize(150, 120)
        form.show()
        self.app.processEvents()
        self.assertGreaterEqual(label.width(), label.fontMetrics().horizontalAdvance('PDB 编号:'))
        bar = tabs.tabBar()
        for index in range(bar.count()):
            rectangle = bar.tabRect(index)
            text = self.controller.style.catalog.translate(bar.tabText(index))
            self.assertGreaterEqual(rectangle.width(), bar.fontMetrics().horizontalAdvance(text))
            self.assertTrue(bar.rect().contains(rectangle))
        self.assertEqual(bar.tabText(2), 'Multi-File')

    def test_font_growth_recalculates_button_size_without_changing_source(self):
        button = self.widget(QtWidgets.QPushButton('Save Session'))
        button.setFixedSize(40, 22)
        button.show()
        self.app.processEvents()
        initial = button.width()
        font = QtGui.QFont(button.font())
        font.setPointSizeF(font.pointSizeF() * 2)
        button.setFont(font)
        self.app.processEvents()
        self.assertGreater(button.width(), initial)
        self.assertGreater(button.width(), button.fontMetrics().horizontalAdvance('保存会话'))
        self.assertEqual(button.text(), 'Save Session')

    def test_readonly_command_preview_is_drawn_verbatim(self):
        label = self.widget(QtWidgets.QLabel('load ...'))
        label.setObjectName('output_command')
        label.resize(180, 40)
        label.setWordWrap(True)
        label.show()
        self.app.processEvents()
        chinese_mode = label.grab().toImage()
        self.assertIsNone(label.findChild(QtWidgets.QLabel, '_pymol_zh_display_text'))
        self.controller.set_enabled(False)
        self.app.processEvents()
        self.assertEqual(chinese_mode, label.grab().toImage())
        self.assertEqual(label.text(), 'load ...')

    def test_verbatim_menu_and_object_selector_keep_user_names(self):
        combo = self.widget(QtWidgets.QComboBox())
        combo.setProperty('_pymol_zh_verbatim', True)
        combo.addItem('surface')
        option = QtWidgets.QStyleOptionComboBox()
        combo.initStyleOption(option)
        self.assertEqual(self.controller.style._option(option, combo).currentText, 'surface')
        menu = self.widget(QtWidgets.QMenu())
        menu.setProperty('_pymol_zh_verbatim', True)
        option = QtWidgets.QStyleOptionMenuItem()
        option.text = 'surface'
        self.assertEqual(self.controller.style._option(option, menu).text, 'surface')

    def test_output_overlay_preserves_source_commands_paths_and_values(self):
        raw = ('PyMOL>set line_width, 3\n'
               ' Setting: line_width set to 3.00000.\n'
               'Traceback (most recent call last):\n'
               '  File "C:/data/experiment.py", line 12, in run\n'
               '    value = int("surface")\n'
               "ValueError: invalid literal for int() with base 10: 'surface'")
        source = self.widget(QtWidgets.QPlainTextEdit())
        source.setObjectName('feedback_browser')
        source.setReadOnly(True)
        source.setPlainText(raw)
        source.show()
        self.app.processEvents()
        self.controller.output.scan()
        overlay = source.findChild(QtWidgets.QPlainTextEdit, 'pymol_zh_output')
        self.assertIsNotNone(overlay)
        translated = overlay.toPlainText()
        self.assertIn('设置：line_width 已设为 3.00000。', translated)
        self.assertIn('异常调用栈', translated)
        self.assertIn('C:/data/experiment.py', translated)
        self.assertIn('第 12 行', translated)
        self.assertIn("'surface'", translated)
        self.assertIn('PyMOL>set line_width, 3', translated)
        self.assertIn('    value = int("surface")', translated)
        self.assertEqual(source.toPlainText(), raw)
        source.appendPlainText('list index out of range')
        self.assertIn('列表索引超出范围', overlay.toPlainText())
        self.controller.set_enabled(False)
        self.assertTrue(overlay.isHidden())
        self.assertIn('list index out of range', source.toPlainText())
        self.controller.set_enabled(True)
        self.assertFalse(overlay.isHidden())

    def test_native_combo_item_delegate_preserves_values_and_restores(self):
        from pymol_zh_cn.combo_display import ComboDelegate
        combo = self.widget(QtWidgets.QComboBox())
        combo.addItems(['automatic handling', 'as separate objects'])
        original = QtWidgets.QItemDelegate(combo)
        combo.setItemDelegate(original)
        combo.show()
        combo.showPopup()
        self.app.processEvents()
        self.controller.combos.scan()
        self.assertIsInstance(combo.itemDelegate(), ComboDelegate)
        view = combo.view()
        point = view.visualRect(view.model().index(1, 0)).center()
        for kind, buttons in ((QtCore.QEvent.Type.MouseButtonPress, QtCore.Qt.MouseButton.LeftButton),
                              (QtCore.QEvent.Type.MouseButtonRelease, QtCore.Qt.MouseButton.NoButton)):
            event = QtGui.QMouseEvent(kind, QtCore.QPointF(point), QtCore.Qt.MouseButton.LeftButton,
                                     buttons, QtCore.Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(view.viewport(), event)
        self.app.processEvents()
        self.assertEqual(combo.currentIndex(), 1)
        combo.setCurrentIndex(1)
        self.assertEqual(combo.currentText(), 'as separate objects')
        self.assertEqual(combo.itemText(0), 'automatic handling')
        self.controller.set_enabled(False)
        self.assertIs(combo.itemDelegate(), original)
        self.assertEqual(combo.currentIndex(), 1)
        combo.hidePopup()

    def test_stale_native_option_wrapper_is_not_read_as_an_item(self):
        combo = self.widget(QtWidgets.QComboBox())
        option = QtWidgets.QStyleOptionViewItem()
        option.type = QtWidgets.QStyleOptionComboBox.Type
        option.version = QtWidgets.QStyleOptionComboBox.Version
        self.assertIs(self.controller.style._option(option, combo), option)

    def test_native_title_restores_and_accepts_subsequent_application_changes(self):
        dialog = self.widget(QtWidgets.QDialog())
        dialog.setWindowTitle('Properties Inspector')
        dialog.show()
        self.app.processEvents()
        self.assertEqual(dialog.windowTitle(), '属性检查器')
        self.controller.set_enabled(False)
        self.assertEqual(dialog.windowTitle(), 'Properties Inspector')
        self.controller.set_enabled(True)
        dialog.setWindowTitle('Get PDB File')
        self.assertEqual(dialog.windowTitle(), '获取 PDB 文件')
        dialog.setWindowTitle('Surface')
        self.assertEqual(dialog.windowTitle(), 'Surface')
        dialog.setWindowTitle('my_experiment.pse')
        self.controller.set_enabled(False)
        self.assertEqual(dialog.windowTitle(), 'my_experiment.pse')

    def test_wrapped_description_reserves_height_and_keeps_english_source(self):
        source = ('Paste a link to a script or plugin, or a PyMOLWiki url which then '
                  'will be downloaded and scanned for scripts that extend the PyMOL API')
        label = self.widget(QtWidgets.QLabel(source))
        label.setWordWrap(True)
        label.setFixedSize(160, 18)
        label.show()
        self.app.processEvents()
        overlay = label.findChild(QtWidgets.QLabel, '_pymol_zh_display_text')
        self.assertIsNotNone(overlay)
        self.assertIn('粘贴脚本', overlay.text())
        self.assertGreaterEqual(overlay.height(), overlay.heightForWidth(overlay.width()))
        self.assertEqual(label.text(), source)
        self.controller.set_enabled(False)
        self.assertEqual(label.minimumHeight(), 18)
        self.assertEqual(label.maximumHeight(), 18)


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if hasattr(DisplayTests, 'controller'):
        DisplayTests.controller.shutdown()
    sys.exit(0 if result.wasSuccessful() else 1)
