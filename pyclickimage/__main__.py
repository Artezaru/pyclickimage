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

from __future__ import annotations

import argparse
from typing import Callable, Optional, Sequence


def _launch(run: Callable[..., None], argv: Optional[Sequence[str]] = None) -> None:
    r"""
    Parse the command line arguments and start the application.

    Shared by :func:`__main__` and :func:`__main_gui__`, which only differ
    by the way they import ``run``.

    Parameters
    ----------
    run : Callable
        The ``pyclickimage.tools.run`` function.

    argv : Sequence[str], optional
        Arguments to parse. Defaults to ``sys.argv[1:]``.

    """
    parser = argparse.ArgumentParser(
        prog="pyclickimage",
        description="PyClickImage GUI application.",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "-i",
        "--images",
        nargs="+",
        type=str,
        help="Path(s) to image file(s) to preload.",
    )

    group.add_argument(
        "-s",
        "--session",
        type=str,
        help="Path to an annotation session CSV file to load.",
    )

    args = parser.parse_args(argv)

    run(
        images=args.images,
        session=args.session,
    )


def __main__() -> None:
    r"""
    Main entry point of the package.

    Runs via ``python -m pyclickimage`` and from the standalone executable
    (PyInstaller).

    PyInstaller runs this file as a top-level script, without a parent
    package, so the import **must be absolute**.

    .. code-block:: console

        python -m pyclickimage
        python -m pyclickimage -i image1.tif image2.tif
        python -m pyclickimage -s annotations.csv

    """
    try:
        from pyclickimage.tools import run
    except:
        import os
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from pyclickimage.tools import run

    _launch(run)


def __main_gui__() -> None:
    r"""
    Graphical user interface entry point of the package.

    This method contains the script executed when running the
    ``pyclickimage`` command installed by pip
    (``[project.gui-scripts]`` or ``[project.scripts]`` in
    ``pyproject.toml``). It is always imported as part of the package,
    so the import is **relative**.

    The application can optionally preload images using
    ``--images`` or load an existing annotation session using
    ``--session``.

    Examples
    --------

    Launch empty application::

        pyclickimage

    Open one image::

        pyclickimage -i image.tif

    Open multiple images::

        pyclickimage -i image1.tif image2.tif

    Load an existing session::

        pyclickimage -s annotations.csv

    """
    from .tools import run

    _launch(run)


if __name__ == "__main__":
    __main__()