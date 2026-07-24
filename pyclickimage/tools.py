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

from .app import ClickImageApp


def run(
    images: Optional[Union[str, Path, Sequence[Union[str, Path]]]] = None,
    session: Optional[Union[str, Path]] = None,
) -> None:
    r"""
    Launch the ClickImageApp as a standalone application.

    Parameters
    ----------
    images : str, pathlib.Path or sequence, optional
        Image or list of images to preload.

    session : str or pathlib.Path, optional
        CSV annotation session to load.

    Notes
    -----
    ``images`` and ``session`` are mutually exclusive.
    A session CSV already contains the image list and annotations.

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
    """

    if images is not None and session is not None:
        raise ValueError("Only one of 'images' or 'session' can be provided.")

    app = QtWidgets.QApplication(sys.argv)

    window = ClickImageApp(
        images=images,
        session=session,
    )

    window.show()

    app.exec_()


def read_session_csv(
    path: str | Path,
    output: Literal[
        "dict",
        "pandas",
    ] = "dict",
):
    r"""
    Read a pyclickimage session CSV file.

    Parameters
    ----------
    path : str or pathlib.Path
        CSV session file.

    output : {"dict", "pandas"}, default="dict"
        Output format.

        - ``"dict"``:
            Return a nested dictionary:
            ``image -> group -> list of (x, y)``.

        - ``"pandas"``:
            Return a pandas DataFrame.

    Returns
    -------
    dict or pandas.DataFrame
        Session data.
    """

    path = Path(path)

    if output == "pandas":

        return pd.read_csv(
            path,
            sep=",",
            quotechar='"',
        )

    if output != "dict":
        raise ValueError(f"Unknown output format: {output}")

    session = {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file,
            delimiter=",",
            quotechar='"',
        )

        for row in reader:

            image = row["Image"]
            group = row["Group"]

            if row["X"] == "" or row["Y"] == "":
                point = (None, None)

            else:
                point = (
                    float(row["X"]),
                    float(row["Y"]),
                )

            if image not in session:
                session[image] = {}

            if group not in session[image]:
                session[image][group] = []

            session[image][group].append(point)

    return session


def csv2json(
    csv_path: Union[str, Path],
    json_path: Union[str, Path],
    indent: int = 4,
) -> None:
    r"""
    Convert a pyclickimage CSV session file into JSON.

    Parameters
    ----------
    csv_path : str or pathlib.Path
        Input CSV session file.

    json_path : str or pathlib.Path
        Output JSON file.

    indent : int, default=4
        JSON indentation level.

    Notes
    -----
    The generated JSON format is:

    .. code-block:: json

        {
            "image.png": {
                "group1": [
                    [x, y],
                    [x, y]
                ]
            }
        }

    Empty clicks are stored as ``[null, null]``.
    """

    csv_path = Path(csv_path)
    json_path = Path(json_path)

    data = {}

    with open(
        csv_path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file,
            delimiter=",",
            quotechar='"',
        )

        required_columns = {
            "Image",
            "Group",
            "Index",
            "X",
            "Y",
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "Invalid CSV format. " "Expected columns: Image, Group, Index, X, Y"
            )

        for row in reader:

            image = row["Image"]
            group = row["Group"]

            if image not in data:
                data[image] = {}

            if group not in data[image]:
                data[image][group] = []

            if row["X"] == "" or row["Y"] == "":
                point = [None, None]

            else:
                point = [
                    float(row["X"]),
                    float(row["Y"]),
                ]

            data[image][group].append(point)

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=indent,
            ensure_ascii=False,
        )
