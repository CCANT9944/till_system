"""Entry point for the till application."""

from PyQt6 import QtWidgets
import os, sys

# support invocation both as a module and as a standalone script
if __name__ == "__main__" and __package__ is None:
    # when running `python main.py` inside the till/ folder
    # ensure the directory containing this file and its parent are on sys.path
    this_dir = os.path.dirname(__file__)
    sys.path.insert(0, this_dir)
    parent = os.path.dirname(this_dir)            # interface
    if parent not in sys.path:
        sys.path.insert(0, parent)
    root = os.path.dirname(parent)               # workspace root
    if root not in sys.path:
        sys.path.insert(0, root)
    # now interface package (in parent) should be importable
    from interface.till.views import MainWindow
else:
    from .views import MainWindow
    from .db import close_db

if __name__ == "__main__" and __package__ is None:
    from interface.till.db import close_db


def run():
    app = QtWidgets.QApplication([])
    app.aboutToQuit.connect(close_db)
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
