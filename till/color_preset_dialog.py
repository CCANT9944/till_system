"""Color preset editor dialog for the till UI."""

from __future__ import annotations

from PyQt6 import QtGui, QtWidgets


ColorPresetResult = tuple[dict[str, str], dict[tuple[str, str], str], bool]


def edit_color_presets_dialog(
    parent: QtWidgets.QWidget,
    categories: list[str],
    subcategory_map: dict[str, list[str]],
    category_color_presets: dict[str, str],
    subcategory_color_presets: dict[tuple[str, str], str],
) -> ColorPresetResult | None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Color Presets")
    dialog.resize(520, 420)

    layout = QtWidgets.QVBoxLayout(dialog)
    info = QtWidgets.QLabel("Choose default colors for categories and subcategories.")
    layout.addWidget(info)

    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    layout.addWidget(scroll)

    content = QtWidgets.QWidget()
    form = QtWidgets.QFormLayout(content)
    scroll.setWidget(content)

    temp_categories = dict(category_color_presets)
    temp_subcategories = dict(subcategory_color_presets)

    def update_preview(button: QtWidgets.QPushButton, color_value: str):
        button.setText(color_value or "Choose")
        style = "font-size: 10pt;"
        if color_value:
            style += f" background-color: {color_value}; color: white;"
        button.setStyleSheet(style)

    def make_picker(getter, setter):
        button = QtWidgets.QPushButton()
        update_preview(button, getter())

        def choose_color():
            current = getter()
            color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current) if current else QtGui.QColor())
            if color.isValid():
                setter(color.name())
                update_preview(button, color.name())

        button.clicked.connect(choose_color)
        return button

    for category in categories:
        picker = make_picker(
            lambda cat=category: temp_categories.get(cat, ""),
            lambda value, cat=category: temp_categories.__setitem__(cat, value),
        )
        form.addRow(f"{category.capitalize()}:", picker)

    for category, subcategories in subcategory_map.items():
        for subcategory in subcategories:
            picker = make_picker(
                lambda cat=category, sub=subcategory: temp_subcategories.get((cat, sub), ""),
                lambda value, cat=category, sub=subcategory: temp_subcategories.__setitem__((cat, sub), value),
            )
            form.addRow(f"{category.capitalize()} / {subcategory}:", picker)

    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Save
        | QtWidgets.QDialogButtonBox.StandardButton.Cancel
    )
    layout.addWidget(button_box)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    reply = QtWidgets.QMessageBox.question(
        parent,
        "Apply presets",
        "Apply the new presets to existing items now?",
        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
    )
    apply_now = reply == QtWidgets.QMessageBox.StandardButton.Yes
    return temp_categories, temp_subcategories, apply_now