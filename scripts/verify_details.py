"""Program-level checks of translated keys, unchanged models, and editing."""
from pymol.Qt import QtWidgets, QtCore


def verify(window, controller, output):
    from pmg_qt.advanced_settings_gui import PyMOLAdvancedSettings
    from pmg_qt.properties_dialog import PropsDialog
    app = QtWidgets.QApplication.instance()
    advanced = PyMOLAdvancedSettings(window, window.cmd)
    properties = PropsDialog(window)
    advanced.show()
    properties.form._dialog.show()
    app.processEvents()
    controller.details.scan()
    model = advanced.model
    row = next(row for row in range(model.rowCount()) if model.item(row, 0).text() == 'line_width')
    index = advanced.proxy_model.mapFromSource(model.index(row, 0))
    before = window.cmd.get('line_width')
    advanced.table.setCurrentIndex(index)
    app.processEvents()
    advanced.table.scrollTo(index.sibling(index.row(), 1))
    app.processEvents()
    assert advanced.table.horizontalScrollBar().value() == 0, 'Chinese setting names scrolled out of view'
    assert '线状' in controller.details.records[id(advanced.table)][4].text()
    delegate = advanced.table.itemDelegateForColumn(0)
    assert delegate.mapped('line_width') == '线宽'
    from pymol_zh_cn.settings_catalog import SETTINGS
    keys = {model.item(row, 0).text() for row in range(model.rowCount())}
    assert keys <= SETTINGS.keys(), sorted(keys - SETTINGS.keys())
    assert all(SETTINGS[key][0] and SETTINGS[key][1] for key in keys)
    assert model.item(row, 0).text() == 'line_width'
    model.item(row, 1).setText('3')
    assert window.cmd.get_setting_float('line_width') == 3
    model.item(row, 1).setText(before)
    assert window.cmd.get('line_width') == before
    advanced.filter_le.setText('卤键')
    assert advanced.proxy_model.rowCount() > 0
    visible_keys = {advanced.proxy_model.index(r, 0).data() for r in range(advanced.proxy_model.rowCount())}
    assert 'halogen_bond_distance' in visible_keys
    assert all('卤键' in SETTINGS[key][0] or '卤键' in SETTINGS[key][1] for key in visible_keys)
    assert advanced.filter_le.text() == '卤键'
    advanced.filter_le.clear()
    tree = properties.form.treeWidget
    assert tree.topLevelItem(0).text(0) == 'Object-Level'
    assert tree.itemDelegateForColumn(0).mapped('Object-Level') == '对象级'
    assert tree.itemDelegateForColumn(0).mapped('name') == '原子名称 (name)'
    advanced.grab().save(str(output / 'advanced-settings-zh.png'))
    properties.form._dialog.grab().save(str(output / 'properties-zh.png'))
    controller.set_enabled(False)
    assert advanced.table.itemDelegateForColumn(0) is not delegate
    assert model.item(row, 0).text() == 'line_width'
    controller.set_enabled(True)
    advanced.close()
    properties.form._dialog.close()
    # Keep controllers alive until their stock dialogs are destroyed.
    window._zh_verified_detail_windows = (advanced, properties)
    return {'stock_parameter_keys_unchanged': True, 'edit_reached_original_setting_and_restored': True,
            'property_keys_unchanged': True, 'display_delegate_restored_on_disable': True}
