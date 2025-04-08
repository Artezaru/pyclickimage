import pandas as pd
from typing import List, Tuple

class ExtractClick:
    """
    A class to extract click data and groups from a CSV file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file containing the click data.
        The CSV file should have the following columns: [Group, Index, Click X, Click Y].

    Attributes
    ----------
    csv_path : str
        Path to the CSV file.
    data : pd.DataFrame
        DataFrame containing the loaded click data.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data = self.load_data()

    def load_data(self) -> pd.DataFrame:
        """
        Loads the CSV file into a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            The loaded DataFrame containing click data.
        """
        try:
            return pd.read_csv(self.csv_path)
        except Exception as e:
            raise ValueError(f"Error loading data: {e}")

    def extract_group(self, group_name: str) -> List[Tuple[float, float]]:
        """
        Extracts the clicks for the specified group.

        Parameters
        ----------
        group_name : str
            The name of the group whose clicks are to be extracted.

        Returns
        -------
        List[Tuple[float, float]]
            A list of tuples with the format (Click X, Click Y) for each click in the group.
        """
        group_data = self.data[self.data['Group'] == group_name]
        return list(group_data[['Click X', 'Click Y']].itertuples(index=False, name=None))

    def get_click(self, group_name: str, index: int) -> Tuple[float, float]:
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
        Tuple[float, float] or None
            A tuple with (Click X, Click Y) or None if not found.
        """
        group_data = self.data[(self.data['Group'] == group_name) & (self.data['Index'] == index)]
        if not group_data.empty:
            return tuple(group_data[['Click X', 'Click Y']].iloc[0])
        return None

