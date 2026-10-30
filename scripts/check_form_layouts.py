"""Measure visible translated text in stock forms, including every tab page."""
import importlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pymol_zh_cn._qt import QtCore, QtGui, QtWidgets
from pymol_zh_cn.style import DisplayController
from pymol_zh_cn._qt import is_command_text
from stock_forms import load_stock_form
from test_support import set_test_font

app = QtWidgets.QApplication([])
set_test_font(app, QtGui)
controller = DisplayController(app)
scale = os.environ.get('QT_SCALE_FACTOR', '1')
output = Path(os.environ.get('PYMOL_ZH_ARTIFACTS', str(ROOT / 'artifacts' / 'open-source'))) / f'layout-{scale}'
output.mkdir(parents=True, exist_ok=True)
forms = []
checks = []
problems = []


def settle(dialog):
    for _ in range(3):
        app.processEvents()
        controller.layout.scan()
        controller.overlays.scan()
        if dialog.layout():
            dialog.layout().activate()
    app.processEvents()


def inspect(dialog, form_name, page):
    count = 0
    for widget in dialog.findChildren(QtWidgets.QWidget):
        if (not widget.isVisible() or widget.property('_pymol_zh_overlay')
                or is_command_text(widget)):
            continue
        if isinstance(widget, QtWidgets.QAbstractButton):
            source = widget.text()
        elif isinstance(widget, QtWidgets.QLabel):
            source = widget.text()
        else:
            continue
        mapped = controller.style.catalog.translate(source)
        if mapped == source or '<' in source or '\n' in source:
            continue
        count += 1
        # visibleRegion excludes our intentional opaque text overlay. Measure
        # ancestor bounds instead so overlays do not look like clipping.
        visible_rect = widget.rect()
        parent = widget.parentWidget()
        while parent is not None:
            origin = widget.mapTo(parent, QtCore.QPoint())
            visible_rect = visible_rect.intersected(parent.rect().translated(-origin))
            if parent is dialog:
                break
            parent = parent.parentWidget()
        if visible_rect.width() < widget.width() or visible_rect.height() < widget.height():
            problems.append({'form': form_name, 'page': page, 'class': type(widget).__name__,
                             'name': widget.objectName(), 'source': source,
                             'issue': 'translated control clipped by an ancestor',
                             'control': [widget.width(), widget.height()],
                             'visible': [visible_rect.width(), visible_rect.height()]})
        needed = widget.fontMetrics().horizontalAdvance(mapped.replace('&', ''))
        if isinstance(widget, QtWidgets.QLabel) and widget.wordWrap():
            continue
        if isinstance(widget, QtWidgets.QLabel):
            rect = widget.contentsRect()
            width = rect.width() - 2 * (widget.margin() + widget.frameWidth())
            height = rect.height() - 2 * (widget.margin() + widget.frameWidth())
        else:
            option = QtWidgets.QStyleOptionButton()
            option.initFrom(widget)
            option.text = mapped
            if isinstance(widget, QtWidgets.QCheckBox):
                element = QtWidgets.QStyle.SubElement.SE_CheckBoxContents
            elif isinstance(widget, QtWidgets.QRadioButton):
                element = QtWidgets.QStyle.SubElement.SE_RadioButtonContents
            else:
                element = QtWidgets.QStyle.SubElement.SE_PushButtonContents
            rectangle = widget.style().subElementRect(element, option, widget)
            width, height = rectangle.width(), rectangle.height()
        if needed > width or widget.fontMetrics().height() > height:
            problems.append({'form': form_name, 'page': page, 'class': type(widget).__name__,
                             'name': widget.objectName(), 'source': source, 'mapped': mapped,
                             'text_width': needed, 'available_width': width,
                             'font_height': widget.fontMetrics().height(), 'height': height})
    for overlay in dialog.findChildren(QtWidgets.QLabel, '_pymol_zh_display_text'):
        if not overlay.isVisible():
            continue
        if overlay.wordWrap() or overlay.text().lstrip().startswith('<'):
            needed_height = overlay.heightForWidth(overlay.width())
            if needed_height > overlay.height():
                problems.append({'form': form_name, 'page': page, 'class': 'wrapped display text',
                                 'source': overlay.parentWidget().text(),
                                 'text_height': needed_height, 'height': overlay.height()})
        elif isinstance(overlay.parentWidget(), QtWidgets.QLineEdit):
            needed_width = overlay.fontMetrics().horizontalAdvance(overlay.text())
            if needed_width > overlay.width():
                problems.append({'form': form_name, 'page': page, 'class': 'placeholder',
                                 'source': overlay.parentWidget().placeholderText(),
                                 'text_width': needed_width, 'available_width': overlay.width()})
    for bar in dialog.findChildren(QtWidgets.QTabBar):
        for i in range(bar.count()):
            text = controller.style.catalog.translate(bar.tabText(i))
            if text == bar.tabText(i):
                continue
            count += 1
            needed = bar.fontMetrics().horizontalAdvance(text)
            if needed > bar.tabRect(i).width():
                problems.append({'form': form_name, 'page': page, 'class': 'QTabBar',
                                 'source': bar.tabText(i), 'mapped': text,
                                 'text_width': needed, 'available_width': bar.tabRect(i).width()})
    checks.append({'form': form_name, 'page': page, 'visible_translations_checked': count,
                   'size': [dialog.width(), dialog.height()],
                   'device_pixel_ratio': dialog.devicePixelRatioF()})


for name in ('render', 'fetch', 'pluginmanager', 'save_molecule', 'shortcut_menu',
             'colors', 'png', 'movieexport', 'load_map', 'load_traj', 'props',
             'create_shortcut', 'change_confirm', 'help_shortcut', 'save_object',
             'load_aln', 'load_mae', 'load_mtz', 'pluginitem'):
    dialog = QtWidgets.QDialog()
    form = load_stock_form(name, dialog)
    forms.append((dialog, form))
    dialog.show()
    tabs = dialog.findChildren(QtWidgets.QTabWidget)
    pages = [(None, -1, 'main')] if not tabs else [
        (tab, i, tab.tabText(i)) for tab in tabs for i in range(tab.count())]
    for tab, index, title in pages:
        if tab is not None:
            tab.setCurrentIndex(index)
        settle(dialog)
        inspect(dialog, name, title)
        dialog.grab().save(str(output / f'{name}-{index + 1}.png'))
    dialog.hide()

report = {'scale_factor': scale, 'checks': checks, 'problems': problems,
          'note': 'Actual stock Qt forms; no molecular OpenGL rendering.'}
(output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'scale': scale, 'forms': len(forms), 'pages': len(checks),
                  'visible_translations_checked': sum(c['visible_translations_checked'] for c in checks),
                  'problems': problems}, ensure_ascii=False))
controller.shutdown()
for dialog, form in forms:
    dialog.close()
sys.exit(bool(problems))
