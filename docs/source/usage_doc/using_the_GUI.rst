Using the GUI
==============

Once the application is running (see :doc:`running_the_GUI`), you can open an image if you haven't already done so.

Opening an Image
-----------------

To open an image, click on the **"Load Image"** button in the GUI.
When a new image is loaded, any previous clicks and groups will be cleared.
If you wish to load previously saved clicks, you can use the **"Load Clicks"** button and select the ``.csv`` file containing the saved clicks.

Managing the Click Groups
--------------------------

The clicks are organized into groups. Initially, there is one default group called **"default"**. All clicks you make are stored in this group unless you decide to create and select a new group.

To manage the groups:

- **Add a new group**: Click on the **"Add Group"** button and select a group name from the dropdown menu.
- **Switch between groups**: You can switch between groups using the **ComboBox** that allows you to choose the active group. When you select a group, any new clicks will be stored in that group.
- **Group name**: At the end of the session, the clicks will be saved in a ``.csv`` file with the group name as the first column.

For example, if you start with the default group, the saved file will contain rows with the group name **"default"**. However, if you create a new group (e.g., **"My_New_Group"**) and select it, the subsequent clicks will be saved under this new group.

Here’s how the data might appear in the CSV file:

.. code-block:: console

    Group,Index,Click X,Click Y
    default,0,276.22847682119203,97.5673076923077
    default,1,242.86754966887418,109.59615384615385
    My_New_Group,0,317.3954248366013,144.27014218009478
    My_New_Group,1,253.52124183006535,169.30331753554503
    My_New_Group,2,158.0392156862745,204.87677725118485

Using Integer Coordinates
---------------------------

By default, coordinates are stored as floating-point values. If you prefer to work only with integer pixel coordinates, you can enable the **"Use Integer Coordinates"** checkbox.

Removing Clicks
---------------

To remove clicks, you have the following options:

- **Remove the last click**: Click the **"Remove Last Click"** button.
- **Remove all clicks**: Click the **"Remove All Clicks"** button.

Saving the Clicks
-----------------

To save the clicks to a ``.csv`` file:

1. Set the path for the output ``.csv`` file in the **"CSV File Path"** field.
2. Click the **"Save Clicks"** button to save the clicks.

The saved ``.csv`` file will have the following format:

.. code-block:: console

    Group,Index,Click X,Click Y
    default,0,276.22847682119203,97.5673076923077
    default,1,242.86754966887418,109.59615384615385
    My_New_Group,0,317.3954248366013,144.27014218009478
    My_New_Group,1,253.52124183006535,169.30331753554503
    My_New_Group,2,158.0392156862745,204.87677725118485
