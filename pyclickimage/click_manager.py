import csv
from collections import defaultdict
from typing import Tuple, List, Optional
from numbers import Integral


class ClickManager:
    """
    A class to manage user clicks grouped into named categories.

    This class stores 2D coordinates of points clicked on an image, grouped by string identifiers.
    It also handles special markers like right-clicks by storing (None, None) tuples.

    Attributes
    ----------
    groups : dict[str, list[tuple[Optional[Integral], Optional[Integral]]]]
        A dictionary where keys are group names and values are lists of (x, y) coordinates.
    current_group : str
        The name of the currently active group for storing points.
    """

    def __init__(self) -> None:
        self.groups: dict[str, List[Tuple[Optional[Integral], Optional[Integral]]]] = defaultdict(list)
        self.set_group("default")

    
    def add_group(self, group_name: str) -> None:
        """
        Add a new group with the given name. 
        If it already exists, it will be ignored.

        Parameters
        ----------
        group_name : str
            The name of the group to add.
        """
        if not isinstance(group_name, str):
            raise ValueError("Group name must be a string.")
        if group_name not in self.groups:
            self.groups[group_name] = []


    def set_group(self, group_name: str) -> None:
        """
        Set the current group to the given name. 
        If it doesn't exist, it's created.

        Parameters
        ----------
        group_name : str
            The name of the group to switch to or create.
        """
        if not isinstance(group_name, str):
            raise ValueError("Group group_name must be a string.")
        self.add_group(group_name)
        self.current_group = group_name


    def remove_group(self, group_name: Optional[str] = None) -> None:
        """
        Remove a group by its name.
        If the group is the current group, it will switch to the first available group or "default".
        If group_name is None, it will remove the current group.

        Parameters
        ----------
        group_name : Optional[str]
            The name of the group to remove. If None, removes the current group. 
            Default is None.

        Raises
        ------
        KeyError
            If the group does not exist.
        """
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")
        
        del self.groups[group_name]

        if self.current_group == group_name:
            if len(self.groups) > 0:
                self.current_group = next(iter(self.groups))
            else:
                self.set_group("default")


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
        if new_name in self.groups and old_name != new_name:
            raise KeyError(f"Group '{new_name}' already exists.")

        # Rename the group
        self.groups[new_name] = self.groups.pop(old_name)
        if self.current_group == old_name:
            self.current_group = new_name


    def extract_group(self, group_name: Optional[str] = None) -> List[Tuple[Optional[Integral], Optional[Integral]]]:
        """
        Extracts the clicks for the specified group.

        Parameters
        ----------
        group_name : Optional[str]
            The name of the group whose clicks are to be extracted. If None, uses the current group.
            Default is None.

        Returns
        -------
        List[Tuple[Optional[Integral], Optional[Integral]]]
            A list of tuples with the format (Click X, Click Y) for each click in the group.
        """
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")
        
        return self.groups[group_name]
    

    def add_click(self, x: Optional[Integral], y: Optional[Integral], group_name: Optional[str] = None) -> None:
        """
        Add a click (or a placeholder) to a specific group.

        Parameters
        ----------
        x : Optional[Integral]
            The x-coordinate of the click. Use None for placeholder.
        y : Optional[Integral]
            The y-coordinate of the click. Use None for placeholder.
        group_name : Optional[str]
            The name of the group to add the click to. If None, uses the current group.
            Default is None.
        """
        if group_name is None:
            group_name = self.current_group
        if x is not None and not isinstance(x, Integral):
            raise ValueError("x must be a integer or None.")
        if y is not None and not isinstance(y, Integral):
            raise ValueError("y must be a integer or None.")

        if group_name not in self.groups:
            self.groups[group_name] = []
        self.groups[self.current_group].append((x, y))


    def get_click(self, index: int, group_name: Optional[str] = None) -> Optional[Tuple[Optional[Integral], Optional[Integral]]]:
        """
        Extracts a specific click's data by group and index.

        Parameters
        ----------
        group_name : str
            The group name.
        index : int
            The index of the click.

        Returns
        -------
        Tuple[int, int] or None
            A tuple with (Click X, Click Y) or None if not found.
        """
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.groups or index < 0 or index >= len(self.groups[group_name]):
            raise IndexError(f"Click at index {index} does not exist in group '{group_name}'.")
    
        # Extract the click data
        click_data = self.groups[group_name][index]
        return click_data
    

    def remove_click(self, index: int, group_name: Optional[str] = None) -> None:
        """
        Remove a click from a specific group by its index.

        Parameters
        ----------
        index : int
            The index of the click to remove.
        group_name : Optional[str]
            The name of the group to remove the click from. If None, uses the current group.
            Default is None.

        Raises
        ------
        IndexError
            If the index is out of range for the specified group.
        """
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.groups or index < 0 or index >= len(self.groups[group_name]):
            raise IndexError(f"Click at index {index} does not exist in group '{group_name}'.")
        
        del self.groups[group_name][index]


    def clear_group(self, group_name: Optional[str] = None) -> None:
        """
        Clear all clicks from a specific group.

        Parameters
        ----------
        group_name : str
            The name of the group to clear. If None, clears the current group.
            Default is None.

        Raises
        ------
        KeyError
            If the group does not exist.
        """
        if group_name is None:
            group_name = self.current_group

        if group_name not in self.groups:
            raise KeyError(f"Group '{group_name}' does not exist.")
        
        self.groups[group_name].clear()


    def to_dict(self) -> dict:
        """
        Return the internal data as a serializable dictionary.

        Returns
        -------
        dict
            A dictionary mapping group names to lists of (x, y) coordinates.
        """
        return dict(self.groups)
    

    def save_to_csv(self, path: str) -> None:
        """
        Save the click data to a CSV file with columns: Group, Index, Click X, Click Y.

        Parameters
        ----------
        path : str
            Path where the CSV file will be saved.
        """
        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Group", "Index", "Click X", "Click Y"])
            for group, points in self.groups.items():
                for i, (x, y) in enumerate(points):
                    writer.writerow([group, i, x if x is not None else '', y if y is not None else ''])


    @classmethod
    def load_from_csv(cls, path: str) -> None:
        """
        Load click data from a CSV file. The CSV should have columns: Group, Index, Click X, Click Y.

        Parameters
        ----------
        path : str
            Path to the CSV file to load.
        """
        instance = cls()
        with open(path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                group, index, x, y = row
                if group not in instance.groups:
                    instance.groups[group] = []
                x = round(int(x)) if x else None
                y = round(int(y)) if y else None
                instance.groups[group].append((x, y))
        return instance