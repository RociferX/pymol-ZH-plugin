"""Exercise the companion ASHLC menus against the live open-source engine."""
import json
from pathlib import Path
from pymol import cmd
from pymol.Qt import QtWidgets, QtCore


def verify_panel(window, controller, output):
    panel = controller.object_panel
    from pymol import menu as stock_menu
    original_menu = panel.context_menus.originals['main_menu'][0]
    assert stock_menu.main_menu(cmd, (0., 0., 0.), (100, 100)) == original_menu(cmd, (0., 0., 0.), (100, 100))
    app = QtWidgets.QApplication.instance()
    cmd.fragment('gly', 'zh_menu_probe')
    cmd.fragment('ala', 'surface')
    panel.refresh()
    panel.target.setCurrentIndex(panel.target.findData('zh_menu_probe'))
    coordinates = cmd.get_coords('zh_menu_probe').copy()
    counts = {}
    untranslated = set()

    def all_actions(menu):
        for action in menu.actions():
            yield action
            if action.menu():
                yield from all_actions(action.menu())

    for letter in 'ASHLC':
        menu = panel.build_menu(letter)
        actions = list(all_actions(menu))
        counts[letter] = len(actions)
        assert len(actions) > 10
        for action in actions:
            if action.data():
                assert isinstance(action.data(), str)
            source = action.property('_pymol_zh_source')
            if source and action.text() == source and any(c.isalpha() for c in source):
                untranslated.add(source)
        menu.popup(panel.mapToGlobal(QtCore.QPoint(0, 80)))
        app.processEvents()
        for action in menu.actions():
            if action.text():
                assert menu.actionGeometry(action).width() >= menu.fontMetrics().horizontalAdvance(action.text())
        menu.grab().save(str(output / f'ashlc-{letter}.png'))
        if letter == 'S':
            original = 'cmd.show("sticks"    ,"zh_menu_probe")'
            action = next(a for a in actions if a.data() == original)
            assert action.data() == original
            action.trigger()
            assert 'zh_menu_probe' in cmd.get_names('objects', enabled_only=1)
            assert cmd.count_atoms('zh_menu_probe and rep sticks') == cmd.count_atoms('zh_menu_probe')
        elif letter == 'H':
            next(a for a in actions if a.property('_pymol_zh_source') == '  sticks').trigger()
            assert cmd.count_atoms('zh_menu_probe and rep sticks') == 0
        elif letter == 'L':
            next(a for a in actions if a.property('_pymol_zh_source') == 'atom name').trigger()
            labels = []
            cmd.iterate('zh_menu_probe', 'labels.append((name,label))', space={'labels': labels})
            assert all(name == label for name, label in labels)
            cmd.label('zh_menu_probe', "''")
        elif letter == 'C':
            red = next(a for a in actions if a.data() == 'cmd.color_deep("red", \'zh_menu_probe\', 0)')
            red.trigger()
            colors = []
            cmd.iterate('zh_menu_probe', 'colors.append(color)', space={'colors': colors})
            assert all(color == cmd.get_color_index('red') for color in colors)
        menu.close()
        menu.deleteLater()

    action_menu = panel.build_menu('A')
    copy = next(a.menu() for a in action_menu.actions() if a.property('_pymol_zh_source') == 'copy to object')
    copy.aboutToShow.emit()
    assert any(a.text() == 'surface' for a in copy.actions())
    assert not (cmd.get_coords('zh_menu_probe') != coordinates).any()
    cmd.select('zh_sel_probe', 'zh_menu_probe')
    cmd.group('zh_group_probe', 'zh_menu_probe')
    for name in ('all', 'zh_sel_probe', 'zh_group_probe'):
        panel.refresh()
        panel.target.setCurrentIndex(panel.target.findData(name))
        for letter in 'ASHLC':
            menu = panel.build_menu(letter)
            assert menu is not None
            menu.deleteLater()
    panel.target.setCurrentIndex(panel.target.findData('zh_menu_probe'))
    cmd.mouse('three_button_viewing')
    panel.refresh()
    app.processEvents()
    assert panel.parentWidget() is window.pymolwidget
    assert panel.geometry().right() == window.pymolwidget.width() - 1
    assert panel.width() == cmd.get_setting_int('internal_gui_width')
    assert '旋转' in panel.mouse_status.bindings.text()
    previous_selection = cmd.get_setting_int('mouse_selection_mode')
    panel.mouse_status.change_selection()
    assert cmd.get_setting_int('mouse_selection_mode') == (previous_selection + 1) % 7
    cmd.set('mouse_selection_mode', previous_selection)
    panel.mouse_status.change_mode()
    assert cmd.get('button_mode_name') != '3-Button Viewing'
    cmd.mouse('three_button_viewing')
    panel.refresh()
    app.processEvents()
    for button in panel.buttons.values():
        assert button.width() >= button.fontMetrics().horizontalAdvance(button.text().split('\n')[-1]) + 4
        assert button.mapTo(panel, QtCore.QPoint(button.width(), 0)).x() <= panel.width()
    panel.grab().save(str(output / 'object-panel-zh.png'))
    controller.set_enabled(False)
    assert stock_menu.main_menu is original_menu
    assert panel.isHidden() and not panel.timer.isActive()
    controller.set_enabled(True)
    assert not panel.isHidden() and panel.timer.isActive()
    cmd.delete('zh_group_probe zh_sel_probe zh_menu_probe surface')
    panel.refresh()
    assert panel.target.currentData() == 'all'
    # Wizard controls render independently; native wizard strings stay English.
    cmd.wizard('measurement')
    wizard = cmd.get_wizard()
    source_rows = wizard.get_panel()
    source_prompt = wizard.get_prompt()
    panel.refresh()
    app.processEvents()
    assert '请点击' in panel.wizard_display.prompt.text()
    assert wizard.get_panel() == source_rows and wizard.get_prompt() == source_prompt
    panel.grab().save(str(output / 'measurement-wizard-zh.png'))
    done = next(b for b in panel.wizard_display.findChildren(QtWidgets.QPushButton) if b.text() == '完成')
    done.click()
    assert cmd.get_wizard() is None
    panel.refresh()
    assert panel.wizard_display.prompt.isHidden()
    wizard_checks = []
    for name in ('pair_fit', 'density', 'appearance', 'sculpting', 'mutagenesis', 'label'):
        cmd.wizard(name)
        wizard = cmd.get_wizard()
        original_rows, original_prompts = wizard.get_panel(), wizard.get_prompt()
        panel.refresh()
        app.processEvents()
        for code, caption, payload in original_rows:
            if code and caption.strip():
                assert controller.style.catalog.translate(caption) != caption, (name, caption)
        for prompt in original_prompts or []:
            assert controller.style.catalog.translate(prompt) != prompt, (name, prompt)
        assert wizard.get_panel() == original_rows and wizard.get_prompt() == original_prompts
        panel.grab().save(str(output / f'{name}-wizard-zh.png'))
        wizard_checks.append(name)
        cmd.set_wizard()
    panel.refresh()
    # Check the stock Builder tabs without changing their source labels/values.
    window.open_builder_panel()
    builder = window.builder.widget()
    for index in range(builder.tabs.count()):
        builder.tabs.setCurrentIndex(index)
        app.processEvents()
        controller.layout.scan()
        app.processEvents()
        window.builder.grab().save(str(output / f'builder-{index}.png'))
    assert builder.ss_cbox.itemText(0) == 'Alpha Helix'
    window.builder.hide()
    report = {'menu_entries': counts, 'stock_show_hide_label_color_commands_executed': True,
              'coordinates_unchanged': True, 'lazy_submenu_object_name_preserved': True,
              'all_selection_group_menus': True, 'enable_disable_and_deleted_target': True,
              'overlay_geometry_and_mouse_controls': True,
              'wizard_original_text_and_commands_preserved': wizard_checks,
              'untranslated_captions': sorted(untranslated)}
    (output / 'ashlc-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
