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

