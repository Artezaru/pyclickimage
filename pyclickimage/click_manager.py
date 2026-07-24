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

from collections import defaultdict

from .common import PyClickImageError, Number, Point, Group, Groups, PrecisionMode


class ClickManagerError(PyClickImageError):
    """Base ClickManager exception."""

    pass


class GroupNotFoundError(ClickManagerError):
    pass


class InvalidPrecisionError(ClickManagerError):
    pass


class GroupAlreadyExistError(ClickManagerError):
    pass


class ClickManager:
    r"""
    A class to manage user clicks grouped into named categories.

    This class stores 2D coordinates of points clicked on an image,
    grouped by string identifiers.

    Points are all the time saved as float but the precision mode (float or integer) apply on output.
    """

    __slots__ = ["groups"]

    def __init__(self) -> None:
        r"""
        Initialize the ClickManager.
        """
        self.groups: Groups = defaultdict(list)

    # =========================================================
    # VALIDATION
    # =========================================================
    @staticmethod
    def _check_precision(mode: PrecisionMode) -> None:
        if mode not in ("float", "int"):
            raise InvalidPrecisionError("precision_mode must be 'float' or 'int'.")

    @staticmethod
    def _check_group_name(group_name: str) -> None:
        if not isinstance(group_name, str):
            raise TypeError("Group name must be a string.")

    def _check_exist_group(self, group_name: str) -> None:
        self._check_group_name(group_name)
        if group_name not in self.groups:
            raise GroupNotFoundError(f"Group '{group_name}' does not exist.")

    def _convert(
        self,
        value: Number,
        precision_mode: PrecisionMode,
    ) -> Number:
        r"""
        Convert value according to precision mode.

        Parameters
        ----------
        value : Number
            Input coordinate.

        Returns
        -------
        Number
            Converted coordinate.
        """
        self._check_precision(precision_mode)

        if value is None:
            return None

        if precision_mode == "int":
            return int(round(value))

        return float(value)

    # =========================================================
    # GROUPS
    # =========================================================
    def add_group(self, group_name: str) -> None:
        r"""
        Add a new group.

        .. note::

            If the group already exist, nothing is done.

        Parameters
        ----------
        group_name : str
            Name of the group to add.
        """
        self._check_group_name(group_name)
        self.groups.setdefault(group_name, [])

    def remove_group(self, group_name: str) -> None:
        r"""
        Remove a group.

        Parameters
        ----------
        group_name : str
            Name of the group to remove.
        """
        self._check_exist_group(group_name)
        del self.groups[group_name]

    def rename_group(self, old_name: str, new_name: str) -> None:
        r"""
        Rename a group.

        Parameters
        ----------
        old_name : str
            Existing group name.

        new_name : str
            New group name.

        Raises
        ------
        KeyError
            If new name already used or old name not exist.
        """
        self._check_exist_group(old_name)
        self._check_group_name(new_name)
        if new_name in self.groups:
            raise GroupAlreadyExistError(f"Group '{new_name}' already exists.")

        self.groups[new_name] = self.groups.pop(old_name)

    # =========================================================
    # CLICKS
    # =========================================================
    @property
    def n_clicks(self) -> int:
        r"""
        Return the number of clicks
        """
        return sum(len(g) for _, g in self.groups.items())

    def add_click(self, x: Number, y: Number, *, group_name: str) -> None:
        r"""
        Add a click to a group.

        Parameters
        ----------
        x : Number
            X coordinate of the click.

        y : Number
            Y coordinate of the click.

        group_name : str
            Group name.

        """
        self.add_group(group_name)
        x = float(x) if x is not None else None
        y = float(y) if y is not None else None
        self.groups[group_name].append((x, y))

    def to_half_shift_on(self):
        r"""
        Shift all points by -0.5 to use pixel-centered coordinates.

        Point (a, b) -> (a - 0.5, b - 0.5)
        """
        for group_name, points in self.groups.items():
            self.groups[group_name] = [
                (
                    (x - 0.5) if x is not None else None,
                    (y - 0.5) if y is not None else None,
                )
                for (x, y) in points
            ]

    def to_half_shift_off(self):
        r"""
        Reverse the half-pixel shift.

        Point (a, b) -> (a + 0.5, b + 0.5)
        """
        for group_name, points in self.groups.items():
            self.groups[group_name] = [
                (
                    (x + 0.5) if x is not None else None,
                    (y + 0.5) if y is not None else None,
                )
                for (x, y) in points
            ]

    def extract_group(
        self, group_name: str, *, precision_mode: PrecisionMode = "float"
    ) -> Group:
        r"""
        Extracts the clicks for the specified group.

        Parameters
        ----------
        group_name : str
            The name of the group whose clicks are to be extracted.

        precision_mode : str, default is "float"
            The precision mode between "int" and "float".

        Returns
        -------
        List[Point]
            A list of tuples with the format (Click X, Click Y) for each click in the group.
        """
        self._check_exist_group(group_name)

        out = [
            (self._convert(x, precision_mode), self._convert(y, precision_mode))
            for x, y in self.groups[group_name]
        ]

        return out

    def get_click(
        self, index: int, *, group_name: str, precision_mode: PrecisionMode = "float"
    ) -> Point:
        r"""
        Get a specific click.

        Parameters
        ----------
        index : int
            Index of the click.

        group_name : str
            The group to get the click.

        precision_mode : str, default is "float"
            The precision mode between "int" and "float".

        Returns
        -------
        Tuple[Number, Number]
            Click coordinates.
        """
        self._check_exist_group(group_name)
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if not index < len(self.groups[group_name]):
            raise IndexError(
                "Index must be lower than the number of clicks in the group."
            )

        x, y = self.groups[group_name][index]
        return self._convert(x, precision_mode), self._convert(y, precision_mode)

    def remove_click(self, index: int, *, group_name: str) -> None:
        r"""
        Remove a click by index.

        Parameters
        ----------
        index : int
            Index of the click.

        group_name : str
            Group name.
        """
        self._check_exist_group(group_name)
        if not isinstance(index, int):
            raise TypeError("Index must be an integer")
        if not index < len(self.groups[group_name]):
            raise IndexError(
                "Index must be lower than the number of clicks in the group."
            )

        del self.groups[group_name][index]

    def clear_group(self, group_name: str) -> None:
        r"""
        Clear all clicks in a group.

        Parameters
        ----------
        group_name : str
            Group name.
        """
        self._check_exist_group(group_name)
        self.groups[group_name].clear()

    # =========================================================
    # EXPORT
    # =========================================================
    def to_dict(self, precision_mode: PrecisionMode = "float") -> Groups:
        r"""
        Return internal data as dictionary.

        Parameters
        ----------
        precision_mode : str, default is "float"
            The precision mode between "int" and "float".

        Returns
        -------
        dict
            Dictionary mapping group names to lists of points.
            Each point is a tuple (x, y) with values converted using `_convert()`
            depending on the current precision mode.
        """
        return {
            group: [
                (self._convert(x, precision_mode), self._convert(y, precision_mode))
                for x, y in points
            ]
            for group, points in self.groups.items()
        }
