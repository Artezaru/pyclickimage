import csv
from collections import defaultdict
from typing import Tuple, List, Optional


class ClickManager:
    """
    A class to manage user clicks grouped into named categories.

    This class stores 2D coordinates of points clicked on an image, grouped by string identifiers.
    It also handles special markers like right-clicks by storing (None, None) tuples.

    Attributes
    ----------
    groups : dict[str, list[tuple[Optional[int], Optional[int]]]]
        A dictionary where keys are group names and values are lists of (x, y) coordinates.
    current_group : str
        The name of the currently active group for storing points.
    """

    def __init__(self) -> None:
        self.groups: dict[str, List[Tuple[Optional[int], Optional[int]]]] = defaultdict(list)
        self.current_group: str = "default"
        self.groups[self.current_group] = []

    def set_group(self, name: str) -> None:
        """
        Set the current group to the given name. If it doesn't exist, it's created.

        Parameters
        ----------
        name : str
            The name of the group to switch to or create.
        """
        self.current_group = name
        if name not in self.groups:
            self.groups[name] = []

    def rename_group(self, old_name: str, new_name: str) -> None:
        """
        Rename a group.

        Parameters
        ----------
        old_name : str
            The current name of the group.
        new_name : str
            The new name for the group.

        Raises
        ------
        KeyError
            If the old group does not exist.
        """
        if old_name not in self.groups:
            raise KeyError(f"Group '{old_name}' does not exist.")
        self.groups[new_name] = self.groups.pop(old_name)
        if self.current_group == old_name:
            self.current_group = new_name

    def add_click(self, x: Optional[int], y: Optional[int]) -> None:
        """
        Add a click (or a placeholder) to the current group.

        Parameters
        ----------
        x : Optional[int]
            The x-coordinate of the click. Use None for placeholder.
        y : Optional[int]
            The y-coordinate of the click. Use None for placeholder.
        """
        self.groups[self.current_group].append((x, y))

    def to_dict(self) -> dict:
        """
        Return the internal data as a serializable dictionary.

        Returns
        -------
        dict
            A dictionary mapping group names to lists of (x, y) coordinates.
        """
        return dict(self.groups)

    def save_to_csv(self, path: str, as_integer: bool = False) -> None:
        """
        Save the click data to a CSV file with columns: Group, Index, Click X, Click Y.

        Parameters
        ----------
        path : str
            Path where the CSV file will be saved.
        as_integer : bool, optional
            If True, convert x and y coordinates to integers. Default is False.
        """
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Group", "Index", "Click X", "Click Y"])
            for group, points in self.groups.items():
                for i, (x, y) in enumerate(points):
                    if as_integer:
                        x = int(x) if x is not None else None
                        y = int(y) if y is not None else None
                    writer.writerow([group, i, x if x is not None else '', y if y is not None else ''])
