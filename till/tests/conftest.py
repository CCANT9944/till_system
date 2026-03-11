import importlib.util
import os

import pytest


if importlib.util.find_spec("PyQt6") is not None:
    os.environ.setdefault("QT_QPA_PLATFORM", "minimal")


@pytest.fixture(scope="session")
def qapp():
    if importlib.util.find_spec("PyQt6") is None:
        pytest.skip("PyQt6 not available")

    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture(autouse=True)
def cleanup_qt_widgets(qapp):
    yield

    from PyQt6 import QtWidgets

    for widget in QtWidgets.QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    qapp.processEvents()