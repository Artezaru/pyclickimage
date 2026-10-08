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
import csv
import json
import pandas as pd
from pathlib import Path
from typing import Optional, Union, Sequence, Literal

from PyQt5 import QtWidgets

from .click_image_app import ClickImageApp
from .theme import Theme, apply_theme, get_theme


def run(
    images: Optional[Union[str, Path, Sequence[Union[str, Path]]]] = None,
    session: Optional[Union[str, Path]] = None,
    theme: Optional[Union[str, Theme]] = "light",
) -> None:
    r"""
    Launch the ClickImageApp as a standalone application.

    Parameters
    ----------
    images : str, pathlib.Path or sequence, optional
        Image or list of images to preload.

    session : str or pathlib.Path, optional
        CSV annotation session to load.

    theme : str, Theme or None, default="light"
        Visual theme of the application.

        - ``"dark"`` or ``"light"``: built-in theme
          (see :data:`theme.THEMES`).
        - :class:`Theme`: custom theme, for example derived with
          ``DARK_THEME.replace(...)``.
        - ``None``: keep the native style of the platform.

    Raises
    ------
    ValueError
        If ``images`` and ``session`` are both provided.
    KeyError
        If ``theme`` is an unknown theme name.
    TypeError
        If ``theme`` is neither a string, a :class:`Theme` nor ``None``.

    Notes
    -----
    ``images`` and ``session`` are mutually exclusive.
    A session CSV already contains the image list and annotations.

    The theme is applied to the whole application (style, palette,
    stylesheet) and to the custom-painted plots of the image tool
    (profiles, histogram, interpolation curve).

    Examples
    --------
    Launch with an empty application::

        run()

    Launch with images::

        run("image.tif")

    Launch with multiple images::

        run(["image1.tif", "image2.tif"])

    Load an existing session::

        run(session="annotations.csv")

    Use the dark theme::

        run("image.tif", theme="dark")

    Use a custom theme::

        from pyclickimage.theme import DARK_THEME

        run(theme=DARK_THEME.replace(accent="#3ecf8e"))

    Keep the native style of the platform::

        run(theme=None)
    """

    if images is not None and session is not None:
        raise ValueError("Only one of 'images' or 'session' can be provided.")

    # Resolve the theme before creating any window, so that an invalid
    # theme fails immediately.
    if isinstance(theme, str):
        theme = get_theme(theme)

    elif theme is not None and not isinstance(theme, Theme):
        raise TypeError(
            "theme must be a theme name, a Theme instance or None."
        )

    app = QtWidgets.QApplication(sys.argv)

    # Applied before the widgets are created so that they all pick up
    # the palette and the stylesheet.
    if theme is not None:
        apply_theme(app, theme)

    window = ClickImageApp(
        images=images,
        session=session,
    )

    # Custom-painted plots are not driven by the stylesheet.
    if theme is not None:
        window.image_tool.apply_theme(theme)

    window.show()

    app.exec_()


def read_session_json(
    path: str | Path,
    output: Literal[
        "dict",
        "raw",
    ] = "dict",
):
    r"""
    Read a pyclickimage JSON session file.

    Parameters
    ----------
    path : str or pathlib.Path
        JSON session file.

    output : {"dict", "raw"}, default="dict"
        Output format.

        - ``"dict"``:
            Return only the annotation data:
            ``image -> group -> list of (x, y)``.

        - ``"raw"``:
            Return the complete JSON session dictionary.

    Returns
    -------
    dict
        Session data.
    """

    path = Path(path)

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if output == "raw":
        return data

    if output != "dict":
        raise ValueError(f"Unknown output format: {output}")

    annotations = {}

    for image in data.get("images", []):

        image_path = image["path"]

        annotations[image_path] = {}

        for group, points in image.get(
            "groups",
            {},
        ).items():

            annotations[image_path][group] = [tuple(point) for point in points]

    return annotations


def read_session_csv(
    path: str | Path,
):
    r"""
    Read a pyclickimage CSV export.

    Parameters
    ----------
    path : str or pathlib.Path
        CSV export file.

    Returns
    -------
    dict
        Nested dictionary:

        ``image -> group -> list of (x, y)``
    """

    path = Path(path)

    session = {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file,
        )

        required_columns = {
            "Image",
            "Group",
            "Index",
            "X",
            "Y",
        }

        if reader.fieldnames is None:
            raise ValueError("CSV file is empty.")

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError("Invalid CSV format.")

        for row in reader:

            image = row["Image"]
            group = row["Group"]

            if image not in session:
                session[image] = {}

            if group not in session[image]:
                session[image][group] = []

            if row["X"] == "" or row["Y"] == "":
                point = (None, None)

            else:
                point = (
                    float(row["X"]),
                    float(row["Y"]),
                )

            session[image][group].append(point)

    return session


def read_session(
    path: str | Path,
):
    r"""
    Read a pyclickimage session file.

    The format is automatically detected
    from the file extension.

    Parameters
    ----------
    path : str or pathlib.Path
        Session file.

    Returns
    -------
    dict
        Annotation dictionary:
        ``image -> group -> list of points``.
    """

    path = Path(path)

    if path.suffix.lower() == ".json":
        return read_session_json(path)

    if path.suffix.lower() == ".csv":
        return read_session_csv(path)

    raise ValueError(f"Unsupported session format: {path.suffix}")