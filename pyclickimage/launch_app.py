import sys
from PyQt5 import QtWidgets
from .click_image_app import ClickImageApp

def launch_app(image, output_csv_path: str):
    """
    Launch the ClickImageApp as a standalone application.

    Parameters
    ----------
    image : cv2 Image
        The input image (OpenCV format).
    output_csv_path : str
        The path to save the click data as csv.
    """
    app = QtWidgets.QApplication(sys.argv)
    window = ClickImageApp(image, output_csv_path)
    window.show()
    # Wait before closing the app
    app.exec_()


