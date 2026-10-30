"""Use PyMOL's selected Qt binding; allow standalone GUI regression tests."""
try:
    from pymol.Qt import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt6 import QtCore, QtGui, QtWidgets


def is_command_text(widget):
    """Previewed commands are program text even when hosted in a QLabel."""
    return isinstance(widget, QtWidgets.QWidget) and widget.objectName() in (
        'output_command', 'command_label')
