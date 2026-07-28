Using the GUI
=============

Once the application is running (see :doc:`running_the_GUI`), you can start
a new annotation session or load an existing one.

The application organizes annotations using two levels:

- **Images**: a session can contain multiple images.
- **Groups**: each image can contain annotations belonging to several groups.


Images management
-----------------

Images are managed from the **Images** panel.

To add images, click on the **"+"** button and select one or multiple image files.
Each image is loaded into the current session and receives its own annotation
manager.

Multiple images can be loaded at the same time:

.. code-block:: text

    image_1.png
    image_2.png
    image_3.png

The image selector allows switching between all loaded images.

.. note::

    Image paths containing commas (``,``) are not supported because commas are
    used as separators in the CSV session format.

To remove the current image, click on the **trash button**.
Removing an image permanently removes all annotations associated with it.


Groups management
-----------------

Annotations are organized into groups shared by all images.

To manage groups:

- **Add a group**:
  Click on the **"+"** button in the Groups panel and enter a group name.

- **Rename a group**:
  Select a group and click the **rename** button.

- **Delete a group**:
  Select a group and click the **trash button**.

- **Switch groups**:
  Use the group selector to change the active annotation group.

New clicks are always added to the currently selected image and group.


Adding Clicks
-------------

Annotations are created directly on the displayed image.

- **Left click**:
  Add a point at the clicked position.

- **Right click**:
  Add an empty point ``(None, None)``.

Empty points can be used when a click is intentionally skipped while keeping
the annotation order.

Coordinates are stored internally as floating-point values.

The coordinates follow NumPy indexing conventions:

.. code-block:: python

    image[y, x]

where:

- ``x`` is the horizontal coordinate (column),
- ``y`` is the vertical coordinate (row).


Coordinate system
-----------------

By default, pixel coordinates use the center of the first pixel as the
reference point:

.. code-block:: text

    (0, 0)

The **Half-shift coordinates** option changes this convention by shifting
coordinates by 0.5.

All coordinates remain stored as floating-point values. The display format in
the table can be changed using the **Integer precision** option.


Image navigation and display
----------------------------

The image viewer supports:

- **Mouse wheel**:
  Zoom in and out.

- **Middle mouse button drag**:
  Move the image while keeping the button pressed.

The display panel allows changing:

- contrast,
- colormap,
- marker appearance,
- click visibility.


Removing clicks
---------------

To remove annotations:

- **Undo**:
  Removes the last click from the current image and group.

- **Clear**:
  Removes all clicks from the current image and group.


Saving and loading sessions
---------------------------

A complete annotation session can be saved as a CSV file.

A session contains:

- all image paths,
- all groups,
- all annotation points.

To save a session:

1. Click **Save Session CSV**.
2. Choose the output ``.csv`` file.

The generated CSV format is:

.. code-block:: console

    Image,Group,Index,X,Y
    image_1.png,default,0,276.5,97.0
    image_1.png,default,1,242.2,109.8
    image_2.png,target,0,317.0,144.5

Empty clicks are stored as empty coordinates:

.. code-block:: console

    Image,Group,Index,X,Y
    image_1.png,default,2,,

To restore a previous annotation session:

1. Click **Load Session CSV**.
2. Select the session file.

The current session will be replaced by the loaded session.


Keyboard shortcuts
------------------

The following shortcuts are available:

.. list-table::
    :header-rows: 1

    * - Shortcut
      - Action

    * - ``Ctrl+O``
      - Add image(s)

    * - ``Ctrl+Shift+O``
      - Load annotation session

    * - ``Ctrl+S``
      - Save annotation session

    * - ``Ctrl+Z``
      - Remove last click

    * - ``Ctrl+Shift+Z``
      - Remove all clicks from current image/group

    * - ``Ctrl+G``
      - Create a new group

    * - ``F2``
      - Rename current group

    * - ``Ctrl+Q``
      - Quit application

    * - ``F1``
      - Open help

    * - ``Space``
      - Toggle click display

    * - ``Ctrl+Right // N``
      - Switch to next image

    * - ``Ctrl+Left // P``
      - Switch to previous image

    * - ``Ctrl+Down``
      - Switch to next group

    * - ``Ctrl+Up``
      - Switch to previous group