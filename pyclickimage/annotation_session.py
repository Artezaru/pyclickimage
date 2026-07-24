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
from pathlib import Path
from typing import Dict, List, Optional, Union
import csv


from .common import Number, PrecisionMode, Group
from .click_manager import ClickManager


class AnnotationSession:
    r"""
    Manage a multi-image annotation session.

    An AnnotationSession manages several images, each associated with
    its own ClickManager.

    The session stores the global application state:
    images, groups, current image and current group.

    Notes
    -----
    ClickManager objects only store clicks.
    AnnotationSession manages synchronization between images and groups.
    """

    __slots__ = [
        "images",
        "click_managers",
        "groups",
        "current_image",
        "current_group",
        "precision_mode",
    ]

    def __init__(self) -> None:
        r"""
        Initialize an empty annotation session.

        The session starts without image and without group.
        """
        self.images: List[Path] = []
        self.click_managers: Dict[Path, ClickManager] = {}

        self.groups: List[str] = []

        self.current_image: Optional[Path] = None
        self.current_group: Optional[str] = None

        # Output precision mode
        self.precision_mode: PrecisionMode = "float"

    # =========================================================
    # PRECISION
    # =========================================================
    def set_precision_mode(
        self,
        precision_mode: PrecisionMode,
    ) -> None:
        r"""
        Change output precision mode.

        The internal coordinates remain stored as float.
        This only affects returned values and CSV export.

        Parameters
        ----------
        precision_mode : {"float", "int"}
            Output precision mode.

        Raises
        ------
        ValueError
            If the precision mode is invalid.
        """

        if precision_mode not in ("float", "int"):
            raise ValueError("precision_mode must be 'float' or 'int'.")

        self.precision_mode = precision_mode

    # =========================================================
    # IMAGES
    # =========================================================

    def add_image(
        self,
        image_path: Union[str, Path],
    ) -> None:
        r"""
        Add an image to the session.

        A ClickManager is automatically created for this image.
        Existing groups are copied into the new ClickManager.

        Parameters
        ----------
        image_path : str or pathlib.Path
            Path of the image to add.
        """
        image_path = Path(image_path)

        if "," in str(image_path):
            raise ValueError(
                f"Image path cannot contain commas to avoid conflic in the output CSV file. Given path :\n{image_path}"
            )

        if image_path in self.click_managers:
            return

        manager = ClickManager()

        for group in self.groups:
            manager.add_group(group)

        self.images.append(image_path)
        self.click_managers[image_path] = manager

        if self.current_image is None:
            self.current_image = image_path

    def change_current_image(
        self,
        image_path: Optional[Union[str, Path]],
    ) -> None:
        r"""
        Change the current image.

        Parameters
        ----------
        image_path : str, Path or None
            Image to select. None clears the current image.
        """

        if image_path is None:
            self.current_image = None
            return

        image_path = Path(image_path)

        if image_path not in self.click_managers:
            raise KeyError(f"Image '{image_path}' does not exist.")

        self.current_image = image_path

    def remove_image(
        self,
        image_path: Union[str, Path],
    ) -> None:
        r"""
        Remove an image from the session.

        Parameters
        ----------
        image_path : str or pathlib.Path
            Image to remove.

        Raises
        ------
        KeyError
            If the image does not exist.
        """

        image_path = Path(image_path)

        if image_path not in self.click_managers:
            raise KeyError(f"Image '{image_path}' does not exist.")

        # Remove image
        self.images.remove(image_path)
        del self.click_managers[image_path]

        # Update current image
        if self.current_image == image_path:
            self.current_image = None

    # =========================================================
    # GROUPS
    # =========================================================

    def add_group(
        self,
        group_name: str,
    ) -> None:
        r"""
        Add a new global annotation group.

        The group is created in every existing ClickManager.

        Parameters
        ----------
        group_name : str
            Name of the group.

        Raises
        ------
        TypeError
            If group_name is not a string.
        """

        if not isinstance(group_name, str):
            raise TypeError("Group name must be a string.")

        if group_name in self.groups:
            raise ValueError(f"Group '{group_name}' already exists.")

        self.groups.append(group_name)

        for manager in self.click_managers.values():
            manager.add_group(group_name)

        if self.current_group is None:
            self.current_group = group_name

    def delete_group(
        self,
        group_name: str,
    ) -> None:
        r"""
        Delete a global annotation group.

        The group and all associated clicks are removed
        from every image.

        Parameters
        ----------
        group_name : str
            Name of the group.
        """

        if group_name not in self.groups:
            return

        self.groups.remove(group_name)

        for manager in self.click_managers.values():
            if group_name in manager.groups:
                manager.remove_group(group_name)

        if self.current_group == group_name:
            self.current_group = None

    def rename_group(
        self,
        old_name: str,
        new_name: str,
    ) -> None:
        r"""
        Rename a global annotation group.

        Parameters
        ----------
        old_name : str
            Current group name.

        new_name : str
            New group name.

        Raises
        ------
        KeyError
            If old_name does not exist or new_name already exists.
        """

        if old_name not in self.groups:
            raise KeyError(f"Group '{old_name}' does not exist.")

        if new_name in self.groups:
            raise KeyError(f"Group '{new_name}' already exists.")

        index = self.groups.index(old_name)
        self.groups[index] = new_name

        for manager in self.click_managers.values():
            if old_name in manager.groups:
                manager.rename_group(
                    old_name,
                    new_name,
                )

        if self.current_group == old_name:
            self.current_group = new_name

    def change_current_group(
        self,
        group_name: Optional[str],
    ) -> None:
        r"""
        Change the current annotation group.

        Parameters
        ----------
        group_name : str or None
            Group to select. None clears the selection.
        """

        if group_name is None:
            self.current_group = None
            return

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")

        self.current_group = group_name

    # =========================================================
    # CLICKS
    # =========================================================
    @property
    def current_click_manager(self) -> Optional[ClickManager]:
        r"""
        Return the ClickManager of the current image.

        Returns
        -------
        ClickManager or None
            Current image click manager.

        Notes
        -----
        Returns None if no image is currently selected.
        """

        if self.current_image is None:
            return None

        return self.click_managers[self.current_image]

    @property
    def current_clicks(self) -> Group:
        r"""
        Return current image clicks in the current group.

        Returns
        -------
        Group
            List of points.

        Notes
        -----
        If no image or no group is selected, an empty list is returned.
        """

        if self.current_image is None:
            return []

        if self.current_group is None:
            return []

        manager = self.current_click_manager

        if manager is None:
            return []

        return manager.extract_group(
            self.current_group,
            precision_mode=self.precision_mode,
        )

    def add_click(
        self,
        x: Number,
        y: Number,
    ) -> None:
        r"""
        Add a click to the current image and group.

        If no image or group is selected, the click is ignored.
        """

        if self.current_image is None:
            return

        if self.current_group is None:
            return

        self.current_click_manager.add_click(
            x,
            y,
            group_name=self.current_group,
        )

    def remove_last_click(self) -> None:
        r"""
        Remove the last click from the current image and group.

        Does nothing if no image or group is selected.
        """

        if self.current_image is None:
            return

        if self.current_group is None:
            return

        clicks = self.current_click_manager.groups[self.current_group]

        if clicks:
            clicks.pop()

    def remove_all_clicks(self) -> None:
        r"""
        Remove all clicks from the current image and group.

        Does nothing if no image or group is selected.
        """

        if self.current_image is None:
            return

        if self.current_group is None:
            return

        self.current_click_manager.clear_group(self.current_group)

    # =========================================================
    # EXPORT
    # =========================================================

    def to_csv(
        self,
        path: str,
    ) -> None:
        r"""
        Save the complete session to CSV.

        Format
        ------
        Image, Group, Index, X, Y
        """

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(
                file,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writerow(
                [
                    "Image",
                    "Group",
                    "Index",
                    "X",
                    "Y",
                ]
            )

            for image, manager in self.click_managers.items():

                for group in self.groups:

                    if group not in manager.groups:
                        continue

                    points = manager.extract_group(
                        group,
                        precision_mode=self.precision_mode,
                    )

                    for index, (x, y) in enumerate(points):

                        writer.writerow(
                            [
                                str(image),
                                group,
                                index,
                                x,
                                y,
                            ]
                        )

    @classmethod
    def from_csv(
        cls,
        path: str,
    ) -> AnnotationSession:
        r"""
        Load a session from CSV.

        Parameters
        ----------
        path : str
            CSV file path.

        Returns
        -------
        AnnotationSession
            Loaded session.
        """

        session = cls()

        with open(
            path,
            "r",
            encoding="utf-8",
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

                session.add_image(image)

                if group not in session.groups:
                    session.add_group(group)

                # Empty clicks are stored as (None, None)
            if row["X"] == "" or row["Y"] == "":

                session.click_managers[Path(image)].add_click(
                    None,
                    None,
                    group_name=group,
                )

            else:

                session.click_managers[Path(image)].add_click(
                    float(row["X"]),
                    float(row["Y"]),
                    group_name=group,
                )
        return session
