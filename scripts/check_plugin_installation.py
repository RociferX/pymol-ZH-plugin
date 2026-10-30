"""Verify ZIP installation and subsequent autoload in an isolated user profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from release_info import ROOT, VERSION, PACKAGE
from test_support import set_test_font

OUTPUT = ROOT / 'artifacts' / 'open-source'


def check(phase, profile):
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    import pymol
    pymol.invocation.parse_args(['pymol', '-k', '-q'])
    from pymol.Qt import QtGui
    from pmg_qt import pymol_qt_gui as gui
    app = gui.PyMOLApplication(['Plugin installation check'])
    set_test_font(app, QtGui)
    gui.window = window = gui.PyMOLQtGUI()
    window.show()
    import pymol.gui
    import pymol.plugins as plugins
    from pymol.plugins import installation
    pymol.gui.createlegacypmgapp = window.createlegacypmgapp
    # Redirect discovery/preferences only; do not read or write the user's setup.
    default = profile / 'default-startup'
    default.mkdir(exist_ok=True)
    plugins.startup.__path__[:] = [str(default)]
    plugins.N_NON_USER_PATHS = 1
    plugins.PYMOLPLUGINSRC = str(profile / 'pluginsrc.py')
    plugins.preferences['instantsave'] = False
    window.initializePlugins()
    notifications = []
    if phase == 'install':
        destination = profile / 'installed-plugins'
        destination.mkdir()
        from pymol.plugins.legacysupport import tkMessageBox
        tkMessageBox.showinfo = lambda title, message, **kw: notifications.append([title, message])
        installation.installPluginFromFile(
            str(PACKAGE), parent=window,
            plugdir=str(destination))
        plugins.pref_save(filename=plugins.PYMOLPLUGINSRC)
        assert any(title == 'Success' for title, _ in notifications), notifications
    # No import of the workspace plugin and no call to its enable/init methods.
    for _ in range(4):
        app.processEvents()
    info = plugins.plugins['pymol_zh_cn']
    module = info.module
    assert info.loaded and info.autoload
    assert info.get_version() == VERSION
    assert Path(module.__file__).resolve().is_relative_to(profile.resolve())
    assert 'pymol_zh_cn' not in sys.modules, 'Workspace module was imported'
    controller = module._controller
    assert controller.style.enabled
    assert controller.object_panel.isVisible()
    assert controller.style.catalog.translate('File') == '文件'
    report = {'phase': phase, 'version': info.get_version(),
              'loaded_from_installed_package': True, 'default_autoload': info.autoload,
              'chinese_enabled': controller.style.enabled, 'object_panel_visible': True,
              'chinese_startup_script_used': False, 'notifications': notifications}
    (profile / f'{phase}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    controller.shutdown()
    os._exit(0)


if len(sys.argv) == 3:
    check(sys.argv[1], Path(sys.argv[2]))
else:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='plugin-install-', dir=OUTPUT) as folder:
        profile = Path(folder).resolve()
        assert profile.is_relative_to(OUTPUT.resolve())
        results = []
        for phase in ('install', 'restart'):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), phase, str(profile)],
                           cwd=profile, check=True, timeout=45)
            results.append(json.loads((profile / f'{phase}.json').read_text(encoding='utf-8')))
        (OUTPUT / 'plugin-installation-verification.json').write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(results, ensure_ascii=False))
