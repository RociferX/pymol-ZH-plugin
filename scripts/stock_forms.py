"""Load either Designer .ui files or generated forms shipped by PyMOL."""
import importlib
from pathlib import Path


def load_stock_form(name, dialog):
    module_name = 'pmg_qt.forms.' + name
    if importlib.util.find_spec(module_name) is not None:
        module = importlib.import_module(module_name)
        form = (getattr(module, 'Ui_Form', None) or module.Ui_Dialog)()
        form.setupUi(dialog)
        return form
    import pmg_qt
    from pymol.Qt.utils import loadUi
    return loadUi(str(Path(pmg_qt.__file__).parent / 'forms' / (name + '.ui')), dialog)
