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

import csv
from collections import defaultdict
from typing import Tuple, List, Optional, Union, Dict, Literal

Number = Union[int, float]
Point = Tuple[Optional[Number], Optional[Number]]


class ClickManager:
    r"""
    A class to manage user clicks grouped into named categories.

    This class stores 2D coordinates of points clicked on an image, grouped by string identifiers.
    It supports both float (subpixel) and integer precision modes.
    Points are all the time saved as float but the precision mode apply on output.
    """

    __slots__ = ["groups", "current_group", "_precision_mode"]

    def __init__(self, precision_mode: Literal["float", "int"] = "float") -> None:
        r"""
        Initialize the ClickManager.

        Parameters
        ----------
        precision_mode : str
            Precision mode for stored coordinates. Either "float" or "int".
            Default is "float".
        """
        self.groups: Dict[str, List[Point]] = defaultdict(list)
        self.current_group: str = "default"

        self._precision_mode: Literal["float", "int"] = "float"
        self.precision_mode = precision_mode

        self.add_group("default")

    # =========================================================
    # PRECISION MODE
    # =========================================================
    @property
    def precision_mode(self) -> str:
        r"""
        Get the current precision mode.

        Returns
        -------
        str
            Either "float" or "int".
        """
        return self._precision_mode

    @precision_mode.setter
    def precision_mode(self, mode: str) -> None:
        r"""
        Set precision mode.

        Parameters
        ----------
        mode : str
            Either "float" or "int".

        Raises
        ------
        ValueError
            If mode is not valid.
        """
        if mode not in ("float", "int"):
            raise ValueError("precision_mode must be 'float' or 'int'")
        self._precision_mode = mode

    @property
    def use_int_precision(self) -> bool:
        r"""
        True if precision mode is integer.
        """
        return self._precision_mode == "int"

    @use_int_precision.setter
    def use_int_precision(self, value: bool) -> None:
        r"""
        Set precision mode using boolean.
        """
        self._precision_mode = "int" if value else "float"

    @property
    def use_float_precision(self) -> bool:
        r"""
        True if precision mode is float.
        """
        return self._precision_mode == "float"

    @use_float_precision.setter
    def use_float_precision(self, value: bool) -> None:
        r"""
        Set float precision mode using boolean.
        """
        self._precision_mode = "float" if value else "int"

    def _convert(self, value: Optional[Number]) -> Optional[Number]:
        r"""
        Convert value according to precision mode.

        Parameters
        ----------
        value : Optional[Number]
            Input coordinate.

        Returns
        -------
        Optional[Number]
            Converted coordinate.
        """
        if value is None:
            return None
        if self._precision_mode == "int":
            return int(round(value))
        return float(value)

    # =========================================================
    # GROUPS
    # =========================================================

    def add_group(self, group_name: str) -> None:
        r"""
        Add a new group.

        Parameters
        ----------
        group_name : str
            Name of the group to add.
        """
        if not isinstance(group_name, str):
            raise ValueError("Group name must be a string.")
        self.groups.setdefault(group_name, [])

    def set_group(self, group_name: str) -> None:
        r"""
        Set current group.

        Parameters
        ----------
        group_name : str
            Name of the group to activate.
        """
        self.add_group(group_name)
        self.current_group = group_name

    def remove_group(self, group_name: Optional[str] = None) -> None:
        r"""
        Remove a group.

        Parameters
        ----------
        group_name : Optional[str]
            Name of the group to remove. If None, uses current group.
            Default is None.
        """
        group_name = group_name or self.current_group

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")

        del self.groups[group_name]

        if self.current_group == group_name:
            self.current_group = next(iter(self.groups), "default")

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
            If group does not exist or new name already used.
        """
        if old_name not in self.groups:
            raise KeyError(f"Group '{old_name}' does not exist.")
        if new_name in self.groups:
            raise KeyError(f"Group '{new_name}' already exists.")

        self.groups[new_name] = self.groups.pop(old_name)

        if self.current_group == old_name:
            self.current_group = new_name

    # =========================================================
    # CLICKS
    # =========================================================
    @property
    def n_clicks(self) -> int:
        r"""
        Return the number of clicks
        """
        return sum(len(g) for _, g in self.groups.items())

    def add_click(
        self, x: Optional[Number], y: Optional[Number], group_name: Optional[str] = None
    ) -> None:
        r"""
        Add a click to a group.

        Parameters
        ----------
        x : Optional[Number]
            X coordinate of the click.
        y : Optional[Number]
            Y coordinate of the click.
        group_name : Optional[str]
            Group name. If None, uses current group.
            Default is None.
        """
        group_name = group_name or self.current_group

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

    def extract_group(self, group_name: Optional[str] = None) -> List[Point]:
        r"""
        Extracts the clicks for the specified group.

        Parameters
        ----------
        group_name : Optional[str]
            The name of the group whose clicks are to be extracted. If None, uses the current group.
            Default is None.

        Returns
        -------
        List[Point]
            A list of tuples with the format (Click X, Click Y) for each click in the group.
        """
        group_name = group_name or self.current_group

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")

        out = [(self._convert(x), self._convert(y)) for x, y in self.groups[group_name]]

        return out

    def get_click(self, index: int, group_name: Optional[str] = None) -> Point:
        r"""
        Get a specific click.

        Parameters
        ----------
        index : int
            Index of the click.
        group_name : Optional[str]
            Group name. If None, uses current group.
            Default is None.

        Returns
        -------
        Tuple[Optional[Number], Optional[Number]]
            Click coordinates.
        """
        group_name = group_name or self.current_group
        x, y = self.groups[group_name][index]
        return self._convert(x), self._convert(y)

    def remove_click(self, index: int, group_name: Optional[str] = None) -> None:
        r"""
        Remove a click by index.

        Parameters
        ----------
        index : int
            Index of the click.
        group_name : Optional[str]
            Group name. If None, uses current group.
            Default is None.
        """
        group_name = group_name or self.current_group
        del self.groups[group_name][index]

    def clear_group(self, group_name: Optional[str] = None) -> None:
        r"""
        Clear all clicks in a group.

        Parameters
        ----------
        group_name : Optional[str]
            Group name. If None, uses current group.
            Default is None.
        """
        group_name = group_name or self.current_group
        self.groups[group_name].clear()

    # =========================================================
    # EXPORT
    # =========================================================

    def to_dict(self) -> dict:
        r"""
        Return internal data as dictionary.

        Returns
        -------
        dict
            Dictionary mapping group names to lists of points.
            Each point is a tuple (x, y) with values converted using `_convert()`
            depending on the current precision mode.
        """
        return {
            group: [(self._convert(x), self._convert(y)) for x, y in points]
            for group, points in self.groups.items()
        }

    def save_to_csv(self, path: str) -> None:
        r"""
        Save clicks to CSV.

        Parameters
        ----------
        path : str
            Output file path.
        """
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Group", "Index", "X", "Y"])

            for group, points in self.groups.items():
                for i, (x, y) in enumerate(points):
                    writer.writerow([group, i, self._convert(x), self._convert(y)])

    @classmethod
    def load_from_csv(
        cls, path: str, precision_mode: Literal["float", "int"] = "float"
    ) -> "ClickManager":
        r"""
        Load clicks from CSV.

        Parameters
        ----------
        path : str
            Path to CSV file.

        precision_mode : str
            Precision mode to use ("float" or "int").

        Returns
        -------
        ClickManager
            Loaded instance.
        """
        instance = cls(precision_mode=precision_mode)

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)

            for group, _, x, y in reader:

                instance.add_group(group)

                x_val = float(x) if x != "" else None
                y_val = float(y) if y != "" else None

                instance.groups[group].append((x_val, y_val))

        return instance
