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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal
import csv
import re

from .common import Number, PrecisionMode, Group
from .click_manager import ClickManager


@dataclass(slots=True)
class ImageEntry:
    r"""
    Store an image and its associated annotations.

    An :class:`ImageEntry` links an image file path with the
    :class:`ClickManager` responsible for storing its annotation points.

    Parameters
    ----------
    path : pathlib.Path
        Path to the image file.
    click_manager : ClickManager
        Manager storing annotation clicks associated with this image.

    Notes
    -----
    Each image in an :class:`AnnotationSession` owns a dedicated
    :class:`ClickManager`. This avoids maintaining separate synchronized
    containers for images and click managers.
    """

    path: Path
    click_manager: ClickManager


class AnnotationSession:
    r"""
    Manage a multi-image annotation session.

    An :class:`AnnotationSession` stores the complete state of an
    annotation project, including loaded images, annotation groups,
    current selections, and output formatting options.

    Each image is represented by an :class:`ImageEntry` containing:

    - the image file path,
    - the associated :class:`ClickManager`.

    Parameters
    ----------
    None

    Attributes
    ----------
    images : list[ImageEntry]
        Images included in the current session.

    groups : list[str]
        Names of annotation groups available in the session.

    current_image_index : int
        Index of the currently selected image.
        ``-1`` means that no image is selected.

    current_group_index : int or None
        Index of the currently selected annotation group.
        ``-1`` means that no group is selected.

    precision_mode : PrecisionMode
        Output coordinate precision mode.

    Notes
    -----
    The session object manages the relationship between images and groups.
    :class:`ClickManager` objects only store annotation data and do not
    manage global session state.
    """

    __slots__ = [
        "images",
        "groups",
        "_current_image_index",
        "_current_group_index",
        "precision_mode",
    ]

    def __init__(self) -> None:
        r"""
        Initialize an empty annotation session.

        The session starts without image and without group.

        Notes
        -----
        A negative index indicates that no element is currently selected.
        """

        self.images: List[ImageEntry] = []

        self.groups: List[str] = []

        # Current selections
        self._current_image_index: int = -1
        self._current_group_index: int = -1

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
    def _find_image_index(
        self,
        image_path: str | Path,
    ) -> int:
        r"""
        Return the index of an image.

        Parameters
        ----------
        image_path : str or pathlib.Path
            Image path to search.

        Returns
        -------
        int
            Index of the image in the session.

        Raises
        ------
        KeyError
            If the image does not exist.
        """

        image_path = Path(image_path)

        for index, entry in enumerate(self.images):
            if entry.path == image_path:
                return index

        raise KeyError(f"Image '{image_path}' does not exist.")

    def _find_image(
        self,
        image_path: str | Path,
    ) -> ImageEntry:
        r"""
        Return an image entry.

        Parameters
        ----------
        image_path : str or pathlib.Path
            Image path to search.

        Returns
        -------
        ImageEntry
            Matching image entry.

        Raises
        ------
        KeyError
            If the image does not exist.
        """

        return self.images[self._find_image_index(image_path)]

    def _create_click_manager(self) -> ClickManager:
        r"""
        Create a click manager initialized with all session groups.

        Returns
        -------
        ClickManager
            Newly created click manager.
        """

        manager = ClickManager()

        for group in self.groups:
            manager.add_group(group)

        return manager

    def add_image(
        self,
        image_path: str | Path,
    ) -> None:
        r"""
        Add an image to the session.

        A dedicated :class:`ClickManager` is automatically created for the
        image and initialized with every existing annotation group.

        Parameters
        ----------
        image_path : str or pathlib.Path
            Image path.

        Raises
        ------
        ValueError
            If the path contains a comma.
        """

        image_path = Path(image_path)

        if "," in str(image_path):
            raise ValueError(
                "Image path cannot contain commas to avoid conflicts "
                "with the CSV export.\n"
                f"Given path:\n{image_path}"
            )

        if any(entry.path == image_path for entry in self.images):
            return

        self.images.append(
            ImageEntry(
                path=image_path,
                click_manager=self._create_click_manager(),
            )
        )

    def select_current_image_path(
        self,
        image_path: str | Path | None,
    ) -> None:
        r"""
        Select the current image.

        Parameters
        ----------
        image_path : str, pathlib.Path or None
            Image to select.
            If ``None``, the current selection is cleared.

        Raises
        ------
        KeyError
            If the image does not exist.
        """

        if image_path is None:
            self._current_image_index = -1
            return

        self._current_image_index = self._find_image_index(image_path)

    def select_current_image_index(
        self,
        index: int,
    ) -> None:
        r"""
        Select the current image by index.

        Parameters
        ----------
        index : int
            Image index.
            Use ``-1`` to clear the selection.

        Raises
        ------
        TypeError
            If ``index`` is not an integer.

        IndexError
            If the index is out of range.
        """

        if not isinstance(index, int):
            raise TypeError("index must be an integer.")

        if index < -1 or index >= len(self.images):
            raise IndexError(f"Invalid image index: {index}")

        self._current_image_index = index

    def remove_image(
        self,
        image_path: str | Path,
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

        index = self._find_image_index(image_path)

        self.images.pop(index)

        if self._current_image_index == index:
            self._current_image_index = -1

        elif self._current_image_index > index:
            self._current_image_index -= 1

    @property
    def current_image(self) -> ImageEntry | None:
        r"""
        Return the currently selected image.

        Returns
        -------
        ImageEntry or None
            Selected image, or ``None`` if no image is selected.
        """

        if self._current_image_index < 0:
            return None

        return self.images[self._current_image_index]

    @property
    def current_image_index(self) -> int:
        r"""
        Return the currently selected image.

        Returns
        -------
        ImageEntry or None
            Current image entry index, or ``-1`` if no image is selected.
        """
        return self._current_image_index

    @property
    def current_image_path(self) -> Path | None:
        r"""
        Return the path of the currently selected image.

        Returns
        -------
        pathlib.Path or None
            Path of the selected image, or ``None`` if no image is selected.
        """
        image = self.current_image

        if image is None:
            return None

        return image.path

    def _restore_current_image(
        self,
        current_image: ImageEntry | None,
    ) -> None:
        r"""
        Restore the current image selection after reordering.

        Parameters
        ----------
        current_image : ImageEntry or None
            Previously selected image.

        Notes
        -----
        The selection is restored by object identity, allowing the image
        list to be reordered without losing the current selection.
        """

        if current_image is None:
            return

        for index, entry in enumerate(self.images):
            if entry is current_image:
                self._current_image_index = index
                return

    @staticmethod
    def _natural_path_sorting_key(
        path: Path,
        fullpath: bool = True,
    ) -> list:
        r"""
        Return a natural sorting key for an image path.

        Parameters
        ----------
        path : pathlib.Path
            Image path.

        fullpath : bool, default=True
            If ``True``, use the full path.
            Otherwise, use only the filename.

        Returns
        -------
        list
            Natural sorting key.
        """

        value = str(path) if fullpath else path.name

        return [
            int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", value.lower())
        ]

    def _sort_images(
        self,
        *,
        key,
    ) -> None:
        r"""
        Sort images while preserving the current selection.

        Parameters
        ----------
        key : callable
            Sorting key passed to :meth:`list.sort`.
        """

        current_image = self.current_image

        self.images.sort(key=key)

        self._restore_current_image(current_image)

    def sort_images_alpha(
        self,
        fullpath: bool = True,
    ) -> None:
        r"""
        Sort images alphabetically.

        Parameters
        ----------
        fullpath : bool, default=True
            If ``True``, sort using the complete path.
            Otherwise, sort using only the filename.

        Notes
        -----
        The current image selection is preserved.
        """

        if fullpath:
            key = lambda entry: str(entry.path).lower()
        else:
            key = lambda entry: entry.path.name.lower()

        self._sort_images(key=key)

    def sort_images_natural(
        self,
        fullpath: bool = True,
    ) -> None:
        r"""
        Sort images using natural ordering.

        Parameters
        ----------
        fullpath : bool, default=True
            If ``True``, sort using the complete path.
            Otherwise, sort using only the filename.

        Notes
        -----
        The current image selection is preserved.
        """

        self._sort_images(
            key=lambda entry: self._natural_path_sorting_key(
                entry.path,
                fullpath=fullpath,
            )
        )

    # =========================================================
    # GROUPS
    # =========================================================

    def _find_group_index(
        self,
        group_name: str,
    ) -> int:
        r"""
        Return the index of a group.

        Parameters
        ----------
        group_name : str
            Name of the group.

        Returns
        -------
        int
            Index of the group.

        Raises
        ------
        KeyError
            If the group does not exist.
        """

        try:
            return self.groups.index(group_name)
        except ValueError as exc:
            raise KeyError(f"Group '{group_name}' does not exist.") from exc

    def _find_group(
        self,
        group_name: str,
    ) -> str:
        r"""
        Return a group.

        Parameters
        ----------
        group_name : str
            Name of the group.

        Returns
        -------
        str
            Matching group.

        Raises
        ------
        KeyError
            If the group does not exist.
        """

        return self.groups[self._find_group_index(group_name)]

    def add_group(
        self,
        group_name: str,
    ) -> None:
        r"""
        Add a new annotation group.

        The group is created in every existing
        :class:`ClickManager`.

        Parameters
        ----------
        group_name : str
            Group name.

        Raises
        ------
        TypeError
            If ``group_name`` is not a string.

        ValueError
            If the group already exists.
        """

        if not isinstance(group_name, str):
            raise TypeError("Group name must be a string.")

        if group_name in self.groups:
            raise ValueError(f"Group '{group_name}' already exists.")

        self.groups.append(group_name)

        for image in self.images:
            image.click_manager.add_group(group_name)

    def delete_group(
        self,
        group_name: str,
    ) -> None:
        r"""
        Delete an annotation group.

        The group and all associated clicks are removed
        from every image.

        Parameters
        ----------
        group_name : str
            Group name.
        """

        try:
            index = self._find_group_index(group_name)
        except KeyError:
            return

        self.groups.pop(index)

        for image in self.images:
            image.click_manager.remove_group(group_name)

        if self._current_group_index == index:
            self._current_group_index = -1

        elif self._current_group_index > index:
            self._current_group_index -= 1

    def rename_group(
        self,
        old_name: str,
        new_name: str,
    ) -> None:
        r"""
        Rename an annotation group.

        Parameters
        ----------
        old_name : str
            Current group name.

        new_name : str
            New group name.

        Raises
        ------
        KeyError
            If ``old_name`` does not exist.

        ValueError
            If ``new_name`` already exists.
        """

        index = self._find_group_index(old_name)

        if new_name in self.groups:
            raise ValueError(f"Group '{new_name}' already exists.")

        self.groups[index] = new_name

        for image in self.images:
            image.click_manager.rename_group(
                old_name,
                new_name,
            )

    def select_current_group(
        self,
        group_name: str | None,
    ) -> None:
        r"""
        Select the current annotation group.

        Parameters
        ----------
        group_name : str or None
            Group to select.
            If ``None``, clears the current selection.

        Raises
        ------
        KeyError
            If the group does not exist.
        """

        if group_name is None:
            self._current_group_index = -1
            return

        self._current_group_index = self._find_group_index(group_name)

    def select_current_group_index(
        self,
        index: int,
    ) -> None:
        r"""
        Select the current annotation group by index.

        Parameters
        ----------
        index : int
            Group index.
            Use ``-1`` to clear the selection.

        Raises
        ------
        TypeError
            If ``index`` is not an integer.

        IndexError
            If the index is invalid.
        """

        if not isinstance(index, int):
            raise TypeError("index must be an integer.")

        if index < -1 or index >= len(self.groups):
            raise IndexError(f"Invalid group index: {index}")

        self._current_group_index = index

    @property
    def current_group(self) -> str | None:
        r"""
        Return the currently selected annotation group.

        Returns
        -------
        str or None
            Current group, or ``None`` if no group is selected.
        """

        if self._current_group_index < 0:
            return None

        return self.groups[self._current_group_index]

    @property
    def current_group_index(self) -> int:
        r"""
        Return the index of the currently selected group.

        Returns
        -------
        int
            Current group index, or ``-1`` if no group is selected.
        """

        return self._current_group_index

    def _restore_current_group(
        self,
        current_group: str | None,
    ) -> None:
        r"""
        Restore the current group selection after reordering.

        Parameters
        ----------
        current_group : str or None
            Previously selected group.
        """

        if current_group is None:
            return

        for index, group in enumerate(self.groups):
            if group == current_group:
                self._current_group_index = index
                return

    @staticmethod
    def _natural_group_sorting_key(
        group: str,
    ) -> list:
        r"""
        Return a natural sorting key for a group.

        Parameters
        ----------
        group : str
            Group name.

        Returns
        -------
        list
            Natural sorting key.
        """

        return [
            int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", group.lower())
        ]

    def _sort_groups(
        self,
        *,
        key,
    ) -> None:
        r"""
        Sort groups while preserving the current selection.

        Parameters
        ----------
        key : callable
            Sorting key passed to :meth:`list.sort`.
        """

        current_group = self.current_group

        self.groups.sort(key=key)

        self._restore_current_group(current_group)

    def sort_groups_alpha(
        self,
    ) -> None:
        r"""
        Sort groups alphabetically.

        Notes
        -----
        The current group selection is preserved.
        """

        self._sort_groups(
            key=lambda group: group.lower(),
        )

    def sort_groups_natural(
        self,
    ) -> None:
        r"""
        Sort groups using natural ordering.

        Notes
        -----
        The current group selection is preserved.
        """

        self._sort_groups(
            key=self._natural_group_sorting_key,
        )

    # =========================================================
    # CLICKS
    # =========================================================
    @property
    def _current_annotation(self) -> tuple[ClickManager, str] | None:
        r"""
        Return the current annotation context.

        Returns
        -------
        tuple[ClickManager, str] or None
            The current click manager and selected group, or ``None`` if
            no image or no group is currently selected.
        """

        manager = self.current_click_manager
        group = self.current_group

        if manager is None or group is None:
            return None

        return manager, group

    @property
    def current_click_manager(self) -> ClickManager | None:
        r"""
        Return the click manager associated with the current image.

        Returns
        -------
        ClickManager or None
            Click manager of the selected image, or ``None`` if no image is
            selected.
        """

        image = self.current_image

        if image is None:
            return None

        return image.click_manager

    @property
    def current_clicks(self) -> Group:
        r"""
        Return the clicks of the current annotation group.

        Returns
        -------
        Group
            Clicks of the current image and group.

        Notes
        -----
        Returns an empty group if no image or group is selected.
        """

        annotation = self._current_annotation

        if annotation is None:
            return []

        manager, group = annotation

        return manager.extract_group(
            group,
            precision_mode=self.precision_mode,
        )

    def get_clicks(self, group_name: str) -> Group:
        r"""
        Return the clicks of the group.

        Parameters
        ----------
        group_name : str
            Group name.

        Returns
        -------
        Group
            Clicks of the current image and selected group.

        Notes
        -----
        Returns an empty group if no image is selected.
        """
        if not isinstance(group_name, str):
            raise TypeError("Group name must be a string.")

        if group_name not in self.groups:
            raise ValueError(f"Group '{group_name}' not exists.")

        manager = self.current_click_manager

        if manager is None:
            return []

        return manager.extract_group(
            group_name,
            precision_mode=self.precision_mode,
        )

    def add_click(
        self,
        x: Number,
        y: Number,
    ) -> None:
        r"""
        Add a click to the current annotation group.

        Parameters
        ----------
        x : numbers.Number
            Horizontal coordinate.

        y : numbers.Number
            Vertical coordinate.

        Notes
        -----
        Does nothing if no image or group is selected.
        """

        annotation = self._current_annotation

        if annotation is None:
            return

        manager, group = annotation

        manager.add_click(
            x,
            y,
            group_name=group,
        )

    def remove_last_click(self) -> None:
        r"""
        Remove the last click from the current annotation group.

        Notes
        -----
        Does nothing if no image or group is selected.
        """

        annotation = self._current_annotation

        if annotation is None:
            return

        manager, group = annotation

        clicks = manager.groups[group]

        if clicks:
            clicks.pop()

    def remove_all_clicks(self) -> None:
        r"""
        Remove all clicks from the current annotation group.

        Notes
        -----
        Does nothing if no image or group is selected.
        """

        annotation = self._current_annotation

        if annotation is None:
            return

        manager, group = annotation

        manager.clear_group(group)

    def apply_half_shift(
        self,
        mode: Literal["on", "off"],
    ) -> None:
        r"""
        Enable or disable half-shift mode for every image.

        Parameters
        ----------
        mode : {"on", "off"}
            Half-shift mode to apply to every :class:`ClickManager`.

        Raises
        ------
        ValueError
            If ``mode`` is invalid.
        """

        if mode not in ("on", "off"):
            raise ValueError("mode must be 'on' or 'off'.")

        for image in self.images:
            if mode == "on":
                image.click_manager.to_half_shift_on()
            else:
                image.click_manager.to_half_shift_off()

    # =========================================================
    # EXPORT
    # =========================================================

    def to_csv(
        self,
        path: str,
    ) -> None:
        r"""
        Save the complete session to CSV.

        Parameters
        ----------
        path : str
            Output CSV file path.

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

            for image_entry in self.images:

                manager = image_entry.click_manager

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
                                str(image_entry.path),
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
            Loaded annotation session.

        Raises
        ------
        ValueError
            If the CSV format is invalid.
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

            if reader.fieldnames is None:
                raise ValueError("CSV file is empty.")

            if not required_columns.issubset(reader.fieldnames):
                raise ValueError(
                    "Invalid CSV format. " "Expected columns: Image, Group, Index, X, Y"
                )

            for row in reader:

                image = Path(row["Image"])
                group = row["Group"]

                if image not in [entry.path for entry in session.images]:
                    session.add_image(image)

                if group not in session.groups:
                    session.add_group(group)

                manager = None

                for entry in session.images:
                    if entry.path == image:
                        manager = entry.click_manager
                        break

                if manager is None:
                    raise RuntimeError(f"Missing ClickManager for image '{image}'.")

                if row["X"] == "" or row["Y"] == "":
                    manager.add_click(
                        None,
                        None,
                        group_name=group,
                    )

                else:
                    manager.add_click(
                        float(row["X"]),
                        float(row["Y"]),
                        group_name=group,
                    )

        return session

    def to_json(
        self,
        path: str | Path,
    ) -> None:
        r"""
        Save the complete annotation session to JSON.

        Parameters
        ----------
        path : str or pathlib.Path
            Output JSON file path.
        """

        import json

        data = {
            "precision_mode": self.precision_mode,
            "current_image_index": self.current_image_index,
            "current_group_index": self.current_group_index,
            "images": [],
            "groups": self.groups,
        }

        for image in self.images:

            manager = image.click_manager

            image_data = {
                "path": str(image.path),
                "groups": {},
            }

            for group in self.groups:

                image_data["groups"][group] = manager.extract_group(
                    group,
                    precision_mode="float",
                )

            data["images"].append(image_data)

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
            )

    @classmethod
    def from_json(
        cls,
        path: str | Path,
    ) -> AnnotationSession:
        r"""
        Load an annotation session from JSON.

        Parameters
        ----------
        path : str or pathlib.Path
            JSON file path.

        Returns
        -------
        AnnotationSession
            Loaded session.

        Raises
        ------
        ValueError
            If the JSON structure is invalid.
        """

        import json

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        session = cls()

        session.precision_mode = data.get(
            "precision_mode",
            "float",
        )

        for group in data["groups"]:
            session.add_group(group)

        for image_data in data["images"]:

            image = Path(image_data["path"])

            session.add_image(image)

            manager = session._find_image(image).click_manager

            for group, points in image_data["groups"].items():

                for point in points:

                    manager.add_click(
                        point[0],
                        point[1],
                        group_name=group,
                    )

        session.select_current_image_index(
            data.get(
                "current_image_index",
                -1,
            )
        )

        session.select_current_group_index(
            data.get(
                "current_group_index",
                -1,
            )
        )

        return session

    @classmethod
    def from_file(
        cls,
        path: str | Path,
    ) -> AnnotationSession:
        r"""
        Load an annotation session from a supported file format.

        Supported formats:

        - JSON
        - CSV
        """

        path = Path(path)

        suffix = path.suffix.lower()

        if suffix == ".json":
            return cls.from_json(path)

        if suffix == ".csv":
            return cls.from_csv(path)

        raise ValueError(f"Unsupported session format: '{suffix}'.")
