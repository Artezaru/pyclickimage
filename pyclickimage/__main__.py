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
from .tools import run


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

    This method contains the script executed when running::

        pyclickimage-gui

    The application can optionally preload images using
    ``--images`` or load an existing annotation session using
    ``--session``.

    Examples
    --------

    Launch empty application::

        pyclickimage-gui

    Open one image::

        pyclickimage-gui -i image.tif

    Open multiple images::

        pyclickimage-gui -i image1.tif image2.tif

    Load an existing session::

        pyclickimage-gui -s annotations.csv

    """

    parser = argparse.ArgumentParser(description="PyClickImage GUI application.")

    parser.add_argument(
        "-i",
        "--images",
        nargs="+",
        type=str,
        help=("Path(s) to image file(s) to preload."),
    )

    parser.add_argument(
        "-s",
        "--session",
        type=str,
        help=("Path to an annotation session CSV file to load."),
    )

    args = parser.parse_args()

    if args.images is not None and args.session is not None:

        parser.error("--images and --session cannot be used together.")

    run(
        images=args.images,
        session=args.session,
    )
