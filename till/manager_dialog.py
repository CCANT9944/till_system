"""Manager dialog UI helpers for the till application."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6 import QtWidgets


ActionMap = dict[str, Callable[[], None]]


def show_manager_dialog(parent: QtWidgets.QWidget, product_actions: ActionMap, design_actions: ActionMap) -> None:
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Manager")
    dialog.resize(420, 260)
    dialog.setStyleSheet(
        "QPushButton[managerSection='true'] {"
        " min-height: 48px;"
        " font-size: 13pt;"
        " font-weight: 600;"
        " background-color: #242424;"
        " color: #d4d4d4;"
        " border: 1px solid #4a4a4a;"
        " border-radius: 10px;"
        " padding: 10px 18px;"
        "}"
        "QPushButton[managerSection='true']:checked {"
        " background-color: #103c2f;"
        " color: white;"
        " border: 2px solid #7dd3a7;"
        "}"
        "QPushButton[managerAction='true'] {"
        " min-height: 42px;"
        " font-size: 12pt;"
        " text-align: left;"
        " padding: 10px 14px;"
        " border-radius: 8px;"
        "}"
        "QWidget#managerActionContainer {"
        " background-color: #171717;"
        " border: 1px solid #333333;"
        " border-radius: 12px;"
        "}"
        "QLabel#managerTitle {"
        " font-size: 14pt;"
        " font-weight: 600;"
        " color: #f3f4f6;"
        " padding-bottom: 6px;"
        "}"
        "QLabel#managerHint {"
        " font-size: 10pt;"
        " color: #9ca3af;"
        " padding-bottom: 8px;"
        "}"
    )

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    title = QtWidgets.QLabel("Manager")
    title.setObjectName("managerTitle")
    layout.addWidget(title)

    hint = QtWidgets.QLabel("Choose a section to manage products or adjust the till design.")
    hint.setWordWrap(True)
    hint.setObjectName("managerHint")
    layout.addWidget(hint)

    section_layout = QtWidgets.QHBoxLayout()
    section_layout.setSpacing(10)
    layout.addLayout(section_layout)

    product_button = QtWidgets.QPushButton("Product")
    product_button.setCheckable(True)
    product_button.setProperty("managerSection", "true")
    design_button = QtWidgets.QPushButton("Design")
    design_button.setCheckable(True)
    design_button.setProperty("managerSection", "true")
    section_layout.addWidget(product_button)
    section_layout.addWidget(design_button)

    action_container = QtWidgets.QWidget()
    action_container.setObjectName("managerActionContainer")
    action_layout = QtWidgets.QVBoxLayout(action_container)
    action_layout.setContentsMargins(12, 12, 12, 12)
    action_layout.setSpacing(10)
    layout.addWidget(action_container)

    close_button = QtWidgets.QPushButton("Close")
    close_button.clicked.connect(dialog.accept)
    layout.addWidget(close_button)

    section_group = QtWidgets.QButtonGroup(dialog)
    section_group.setExclusive(True)
    section_group.addButton(product_button)
    section_group.addButton(design_button)

    def clear_actions() -> None:
        while action_layout.count():
            item = action_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def add_action_button(label: str, callback: Callable[[], None]) -> None:
        button = QtWidgets.QPushButton(label)
        button.setProperty("managerAction", "true")
        button.clicked.connect(lambda: (dialog.accept(), callback()))
        action_layout.addWidget(button)

    def show_section(section: str) -> None:
        product_button.setChecked(section == "product")
        design_button.setChecked(section == "design")
        clear_actions()
        actions = product_actions if section == "product" else design_actions
        for label, callback in actions.items():
            add_action_button(label, callback)
        action_layout.addStretch()

    product_button.clicked.connect(lambda: show_section("product"))
    design_button.clicked.connect(lambda: show_section("design"))
    show_section("product")

    dialog.exec()