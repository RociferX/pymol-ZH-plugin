# Name: PyMOL Chinese Display
# Version: 0.3.2
# Description: Reversible Simplified Chinese GUI display mapping; English values unchanged.
"""PyMOL Chinese Display: a reversible, paint-time language mapping plugin."""
__version__ = '0.3.2'
_controller = None
_menu_added = False


def enable():
    global _controller
    from ._qt import QtWidgets
    from .style import DisplayController
    app = QtWidgets.QApplication.instance()
    if app is None:
        raise RuntimeError('请在 PyMOL 图形界面启动后加载中文显示插件。')
    if _controller is None or _controller.disposed:
        _controller = DisplayController(app)
    _controller.set_enabled(True)
    return _controller


def disable():
    if _controller is not None:
        _controller.set_enabled(False)


def about():
    from ._qt import QtWidgets
    QtWidgets.QMessageBox.information(
        QtWidgets.QApplication.activeWindow(), 'PyMOL 中文显示',
        f'PyMOL 中文显示插件 v{__version__}\n\n'
        '中文用于界面显示，英文命令、菜单动作、选项值和模型数据保持原样。\n'
        '覆盖常用菜单、按钮、标签、选项卡、下拉选项、输入提示及工具提示。\n'
        '右侧中文对象操作区提供 A/S/H/L/C 及其多级菜单，复用原始英文命令。\n'
        '包含绘图区右键菜单、标签等向导、属性字段和全部 779 项高级设置说明。\n'
        '包含命令帮助、控制台反馈和异常详情；原始英文输出文档保持不变。\n\n'
        '在插件菜单中选择“恢复英文显示”即可关闭映射。')


def __init_plugin__(app=None):
    global _menu_added
    from ._qt import QtCore, QtWidgets
    from pymol.plugins import addmenuitemqt
    if not _menu_added:
        for label, callback in (
            ('中文显示 / Chinese Display|启用中文显示', enable),
            ('中文显示 / Chinese Display|恢复英文显示', disable),
            ('中文显示 / Chinese Display|关于中文显示插件', about),
        ):
            addmenuitemqt(label, callback)
        _menu_added = True
    # Avoid replacing the application style in the middle of plugin startup.
    if QtWidgets.QApplication.instance() is not None:
        QtCore.QTimer.singleShot(0, _enable_with_object_panel)


def _enable_with_object_panel():
    controller = enable()
    if not hasattr(controller, 'object_panel'):
        from .object_panel import attach
        attach(controller)
