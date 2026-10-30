"""Run with official PyMOL -k -q -r <this file>; save real-interface evidence."""
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(os.environ.get('PYMOL_ZH_ARTIFACTS', str(ROOT / 'artifacts' / 'open-source')))
OUTPUT.mkdir(parents=True, exist_ok=True)

from pymol import cmd
from pymol.Qt import QtCore, QtGui, QtWidgets, PYQT_NAME


def verify():
    status = 1
    try:
        (OUTPUT / 'pymol-stage.txt').write_text('verification started', encoding='utf-8')
        from pmg_qt.pymol_qt_gui import window
        import pymol_zh_cn
        app = QtWidgets.QApplication.instance()
        window.resize(1280, 850)
        # Offscreen QPA does not enumerate Windows fonts. This is test setup,
        # not plugin behavior; the normal desktop uses its existing fonts.
        if not QtGui.QFontDatabase().families():
            QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
            app.setFont(QtGui.QFont('Microsoft YaHei UI', 10))
        app.processEvents()
        window.grab().save(str(OUTPUT / 'pymol-main-en.png'))
        original_menu_keys = tuple(window.menudict)
        original_actions = [(action, action.text(), action.shortcut().toString())
                            for menu in window.menudict.values()
                            for action in menu.actions()]
        controller = pymol_zh_cn.enable()
        app.processEvents()
        window.grab().save(str(OUTPUT / 'pymol-main-zh.png'))
        assert tuple(window.menudict) == original_menu_keys
        assert all(action.text() == text and action.shortcut().toString() == shortcut
                   for action, text, shortcut in original_actions)
        # Exercise the original real QAction and observe its real PyMOL setting.
        sequence = next(a for a in window.menudict['Display'].actions()
                        if a.text() == 'Sequence')
        before = cmd.get_setting_int('seq_view')
        sequence.trigger()
        assert cmd.get_setting_int('seq_view') != before
        sequence.trigger()
        assert cmd.get_setting_int('seq_view') == before
        # A real dynamic form, including the combo values used by PNG sizing.
        window.render_dialog()
        dialog = next(w for w in app.topLevelWidgets()
                      if w is not window and w.findChild(QtWidgets.QComboBox, 'input_units'))
        units_combo = dialog.findChild(QtWidgets.QComboBox, 'input_units')
        dpi_combo = dialog.findChild(QtWidgets.QComboBox, 'input_dpi')
        units = units_combo.currentText()
        dpi = dpi_combo.currentText()
        app.processEvents()
        dialog.grab().save(str(OUTPUT / 'pymol-render-zh.png'))
        (OUTPUT / 'pymol-stage.txt').write_text('render screenshot saved', encoding='utf-8')
        assert units_combo.currentText() == units
        assert dpi_combo.currentText() == dpi
        # Change unit via its original English value and exercise size math.
        units_combo.setCurrentText('inch')
        (OUTPUT / 'pymol-stage.txt').write_text('inch selected', encoding='utf-8')
        assert units_combo.currentText() == 'inch'
        width = dialog.findChild(QtWidgets.QSpinBox, 'input_width')
        physical_width = dialog.findChild(QtWidgets.QDoubleSpinBox, 'input_width_units')
        width.setValue(900)
        (OUTPUT / 'pymol-stage.txt').write_text('width changed', encoding='utf-8')
        assert abs(physical_width.value() - 900 / float(dpi)) < 0.02
        (OUTPUT / 'pymol-stage.txt').write_text('conversion passed', encoding='utf-8')
        units_combo.setCurrentText(units)
        (OUTPUT / 'pymol-stage.txt').write_text('units restored', encoding='utf-8')
        dialog.hide()
        (OUTPUT / 'pymol-stage.txt').write_text('render dialog hidden', encoding='utf-8')
        fetch_form = window.load_form('fetch')
        fetch_form._dialog.show()
        (OUTPUT / 'pymol-stage.txt').write_text('fetch dialog created', encoding='utf-8')
        app.processEvents()
        fetch_dialog = fetch_form._dialog
        fetch_dialog.grab().save(str(OUTPUT / 'pymol-fetch-zh.png'))
        fetch_dialog.hide()
        menu = window.menudict['File']
        menu.popup(window.mapToGlobal(QtCore.QPoint(10, 30)))
        app.processEvents()
        menu.grab().save(str(OUTPUT / 'pymol-file-menu-zh.png'))
        menu.hide()
        pymol_zh_cn.disable()
        app.processEvents()
        window.grab().save(str(OUTPUT / 'pymol-restored-en.png'))
        pymol_zh_cn.enable()
        app.processEvents()
        # Reproduce the normal execapp plugin-menu environment without loading
        # any unrelated plugins or reading the user's plugin preferences.
        import pymol.gui
        import pymol.plugins
        pymol.gui.createlegacypmgapp = window.createlegacypmgapp
        window.menudict['PluginQt'] = window.menudict['Plugin']
        pymol.plugins.HAVE_QT = True
        pymol_zh_cn.__init_plugin__()
        app.processEvents()
        plugin_menu = next(a.menu() for a in window.menudict['PluginQt'].actions()
                           if a.menu() and a.text().startswith('中文显示'))
        assert len(plugin_menu.actions()) == 3
        plugin_menu.actions()[1].trigger()
        assert not controller.style.enabled
        plugin_menu.actions()[0].trigger()
        assert controller.style.enabled
        pymol_zh_cn.__init_plugin__()
        app.processEvents()
        assert len(plugin_menu.actions()) == 3
        window.grab().save(str(OUTPUT / 'pymol-main-zh.png'))
        from verify_object_panel import verify_panel
        ashlc_report = verify_panel(window, controller, OUTPUT)
        from verify_details import verify as verify_details
        details_report = verify_details(window, controller, OUTPUT)
        from verify_remaining import verify as verify_remaining
        remaining_report = verify_remaining(window, controller, OUTPUT)
        report = {
            'pymol_version': cmd.get_version()[0], 'qt_binding': PYQT_NAME,
            'qt_version': QtCore.QT_VERSION_STR,
            'catalog_entries': len(controller.style.catalog.entries),
            'menu_keys_unchanged': True,
            'action_texts_and_shortcuts_unchanged': len(original_actions),
            'original_sequence_action_toggled_setting_and_restored': True,
            'render_units_unchanged': units, 'render_dpi_unchanged': dpi,
            'render_inch_conversion_correct': True,
            'plugin_menu_enable_disable_and_idempotent_init': True,
            'painted_translations': sorted(controller.style.drawn_sources),
            'restored_english': True,
            'ashlc_companion': ashlc_report,
            'details_display': details_report,
            'remaining_scope': remaining_report,
        }
        (OUTPUT / 'pymol-verification.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (OUTPUT / 'pymol-stage.txt').write_text('verification passed', encoding='utf-8')
        (OUTPUT / 'pymol-error.txt').unlink(missing_ok=True)
        status = 0
    except BaseException:
        (OUTPUT / 'pymol-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        QtCore.QTimer.singleShot(200, lambda: os._exit(status))


QtCore.QTimer.singleShot(1500, verify)
