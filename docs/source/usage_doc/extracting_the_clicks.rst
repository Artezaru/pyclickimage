Extracting the Clicks from CSV
==============================

The clicks stored in the ``.csv`` file can be extracted directly or using the ``ClickManager`` class.

To extract the clicks, follow these steps:

1. **Load the CSV file**: Use the ``ClickManager.load_from_csv()`` method to load the clicks from the CSV file.
2. **Extract a specific group**: Use the ``extract_group()`` method to get all the clicks from a specific group (e.g., "default").

Here’s how you can extract the clicks from a CSV file:

.. code-block:: python

    from pyclickimage import ClickManager

    # Load the clicks from the CSV file
    click_manager = ClickManager.load_from_csv("clicks.csv")
    
    # Extract clicks for the "default" group
    default_clicks = click_manager.extract_group("default")
    
    # Print the extracted clicks
    print(default_clicks)

    # Output: [(276, 97), (242, 109), (317, 144), (253, 169)]

In this example:

- The CSV file contains the saved clicks, with each row including the group name, click index, and the X and Y coordinates.
- The ``extract_group()`` method filters and returns only the clicks from the specified group (in this case, the "default" group).
- The output is a list of tuples, where each tuple contains the X and Y coordinates of the clicks in the selected group.

The clicks can then be used for further processing, such as analysis or visualization.

