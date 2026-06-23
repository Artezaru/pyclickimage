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

import argparse
import cv2
from .run import run


def __main__() -> None:
    r"""
    Main entry point of the package.

    This method contains the script to run if the user enter the name of the package on the command line.

    .. code-block:: console
        pyclickimage

    """
    raise NotImplementedError(
        "This is a placeholder for the main entry point of the package. Use 'pyclickimage-gui' to run the GUI application."
    )


def __main_gui__() -> None:
    r"""
    Graphical user interface entry point of the package.

    This method contains the script to run if the user enter the name of the package on the command line with the ``gui`` extension.

    .. code-block:: console
        pyclickimage-gui

    This will launch the GUI application for image clicking and saving coordinates.

    You can also specify an image file to be displayed ``--image`` or ``-i`` and a CSV file path to save the click coordinates ``--output`` or ``-o``.

    """
    # Parser for command line arguments
    parser = argparse.ArgumentParser(description="PyClickImage GUI application.")
    parser.add_argument(
        "-i", "--image", type=str, help="Path to the image file to be displayed."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to save the CSV file with click coordinates.",
    )
    args = parser.parse_args()

    if args.image is not None:
        image = cv2.imread(args.image, cv2.IMREAD_UNCHANGED)
    else:
        image = None

    # Launch the GUI application
    run(image=image, output=args.output)
