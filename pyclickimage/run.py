"""
pyclickimage - Python library to select points on a image [pyqt5 GUI]
Copyright (C) 2025-2026 Artezaru, artezaru.github@proton.me

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import sys
import numpy
from PyQt5 import QtWidgets
from .click_image_app import ClickImageApp
from typing import Optional


def run(image: Optional[numpy.ndarray] = None, output: Optional[str] = None) -> None:
    """
    Launch the ClickImageApp as a standalone application.

    Parameters
    ----------
    image : numpy.ndarray, optional
        The image to be displayed. If None, a blank window will be shown.
        Default is None.
    output : str, optional
        The path where the CSV file will be saved. If None, the app will not save to a file.
        Default is None.
    """
    app = QtWidgets.QApplication(sys.argv)
    window = ClickImageApp(image, output)
    window.show()
    # Wait before closing the app
    app.exec_()
