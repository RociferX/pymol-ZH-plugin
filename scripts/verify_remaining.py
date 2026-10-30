"""Program-level checks and Qt renders for the completed translation scope."""
import contextlib
import io
import json
from pymol.Qt import QtCore, QtWidgets


def verify(window, controller, output):
    cmd = window.cmd
    app = QtWidgets.QApplication.instance()
    panel = controller.object_panel
    cmd.wizard('label')
    wizard = cmd.get_wizard()
    original_modes = list(wizard.mode_names)
    sizes = []
    for mode in range(9):
        panel.refresh()
        app.processEvents()
        button = next(b for b in panel.wizard_display.findChildren(QtWidgets.QPushButton) if b.menu() and b.isVisible())
        menu = button.menu()
        menu.aboutToShow.emit()
        action = next(a for a in menu.actions() if a.data() == 'cmd.get_wizard().set_mode(%d)' % mode)
        action.trigger()
        panel.refresh()
        app.processEvents()
        assert wizard.mode == mode
        assert wizard.mode_names == original_modes
        button = next(b for b in panel.wizard_display.findChildren(QtWidgets.QPushButton) if b.menu() and b.isVisible())
        needed = button.fontMetrics().horizontalAdvance(button.text()) + 28
        sizes.append({'mode': mode, 'caption': button.text(), 'needed': needed, 'width': button.width()})
        assert needed <= button.width(), sizes[-1]
        if mode in (1, 3, 4, 8):
            panel.grab().save(str(output / f'label-mode-{mode}.png'))
    off = next(b for b in panel.wizard_display.findChildren(QtWidgets.QPushButton) if b.text() == '提示：开启' and b.isVisible())
    off.click()
    panel.refresh()
    app.processEvents()
    assert not wizard.messages and panel.wizard_display.prompt.isHidden()
    on = next(b for b in panel.wizard_display.findChildren(QtWidgets.QPushButton) if b.text() == '提示：关闭' and b.isVisible())
    on.click()
    panel.refresh()
    app.processEvents()
    assert wizard.messages and panel.wizard_display.prompt.isVisible()
    cmd.fragment('ala', 'zh_label_probe')
    wizard.do_select('zh_label_probe and name CA')
    labels = []
    cmd.iterate('zh_label_probe and name CA', 'labels.append(label)', space={'labels': labels})
    assert labels == ['CA'], labels
    cmd.set_wizard()
    cmd.delete('zh_label_probe')
    panel.refresh()

    from pmg_qt.advanced_settings_gui import PyMOLAdvancedSettings
    advanced = PyMOLAdvancedSettings(window, cmd)
    advanced.show()
    app.processEvents()
    controller.details.scan()
    metrics = advanced.table.fontMetrics()
    from pymol_zh_cn.settings_catalog import SETTINGS
    assert all(metrics.horizontalAdvance(name) + 8 <= advanced.table.columnWidth(0)
               for name, description in SETTINGS.values())
    advanced.filter_le.setText('卤键')
    advanced.table.setCurrentIndex(advanced.proxy_model.index(0, 0))
    app.processEvents()
    advanced.grab().save(str(output / 'advanced-settings-chinese-filter.png'))
    advanced.close()
    # Drain feedback from the preceding engine actions before checking a
    # controlled output document; later timer delivery is legitimate output.
    cmd.sync()
    window.update_feedback()

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        cmd.help('load')
    raw_help = captured.getvalue()
    assert 'DESCRIPTION' in raw_help and 'load filename' in raw_help
    from pymol import colorprinting
    window.browser.clear()
    window.browser.appendHtml(colorprinting.text2html(raw_help))
    stock_console_help = window.browser.toPlainText()
    app.processEvents()
    controller.output.scan()
    overlay = window.browser.findChild(QtWidgets.QPlainTextEdit, 'pymol_zh_output')
    assert overlay is not None
    assert 'DESCRIPTION' not in overlay.toPlainText()
    assert 'load filename' in overlay.toPlainText()
    assert window.browser.toPlainText() == stock_console_help
    overlay.verticalScrollBar().setValue(0)
    window.browser.grab().save(str(output / 'console-help-load-zh.png'))

    raw_error = ('PyMOL>set line_width, 3\n Setting: line_width set to 3.00000.\n'
                 'Traceback (most recent call last):\n'
                 '  File "C:/data/experiment.py", line 12, in run\n'
                 '    value = int("surface")\n'
                 "ValueError: invalid literal for int() with base 10: 'surface'")
    window.browser.setPlainText(raw_error)
    app.processEvents()
    assert '设置：' in overlay.toPlainText() and '异常调用栈' in overlay.toPlainText()
    assert 'C:/data/experiment.py' in overlay.toPlainText()
    assert window.browser.toPlainText() == raw_error
    window.browser.grab().save(str(output / 'console-error-zh.png'))
    box = QtWidgets.QMessageBox(window)
    box.setWindowTitle('Error')
    box.setText('Error: invalid arguments for load command.')
    box.setDetailedText(raw_error)
    box.show()
    app.processEvents()
    next(b for b in box.findChildren(QtWidgets.QAbstractButton) if b.text().startswith('Show Details')).click()
    app.processEvents()
    controller.output.scan()
    caption = next(label for label in box.findChildren(QtWidgets.QLabel)
                   if label.text() == 'Error: invalid arguments for load command.')
    caption_overlay = caption.findChild(QtWidgets.QLabel, '_pymol_zh_display_text')
    assert caption_overlay and caption_overlay.text() == '错误：load 命令的参数无效。'
    detail = next(w for w in box.findChildren(QtWidgets.QTextEdit) if not w.property('_pymol_zh_overlay'))
    detail_overlay = detail.findChild(QtWidgets.QPlainTextEdit, 'pymol_zh_output')
    assert detail_overlay and '异常调用栈' in detail_overlay.toPlainText()
    assert detail.toPlainText() == raw_error
    box.grab().save(str(output / 'exception-details-zh.png'))
    box.close()
    cmd.set('text', 1, quiet=1)
    controller.output.scan()
    assert controller.output.native.isVisible()
    assert not controller.output.native.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert controller.output.native.focusProxy() is window.lineedit
    assert '异常调用栈' in controller.output.native.toPlainText()
    cmd.set('text', 0, quiet=1)
    controller.output.scan()
    assert controller.output.native.isHidden()
    source_before_switch = window.browser.toPlainText()
    controller.set_enabled(False)
    assert overlay.isHidden() and window.browser.toPlainText() == source_before_switch
    controller.set_enabled(True)
    assert not overlay.isHidden()
    report = {'label_modes': sizes, 'label_original_fields_and_commands': True,
              'label_messages_toggle': True, 'user_atom_label_unchanged': labels,
              'all_setting_names_fit_column': True, 'chinese_filter': True,
              'actual_cmd_help_output_translated': True, 'source_output_unchanged': True,
              'exception_detail_overlay': True, 'native_text_console_overlay': True,
              'note': 'Program-level events and Qt renders; not physical screenshots or real keyboard/mouse.'}
    (output / 'remaining-windows-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    window._zh_verified_remaining = (advanced, box)
    return report
