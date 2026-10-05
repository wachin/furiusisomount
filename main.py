#!/usr/bin/env python3
"""Furius ISO Mount - application entry point.

Original application by Dean Harris <marcus_furius@hotmail.com>.
PyQt6 fork by Washington Indacochea Delgado <linuxfrontier@proton.me>.
Licensed under the GNU GPL v3.
"""

import sys

from PyQt6.QtWidgets import QApplication

from furiusisomount.app_info import APP_DISPLAY_NAME
from furiusisomount.i18n import install_translations
from furiusisomount.ui.main_window import FuriusIsoMount


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setOrganizationName("furiusisomount")

    # Load Qt + application translations (English is the source language)
    install_translations(app)

    window = FuriusIsoMount()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
