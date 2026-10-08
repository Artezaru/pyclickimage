Usage
=====

This section explains how to launch the application, where to find help
on the interface, and how to read the saved clicks from Python.

An example is provided in the ``examples`` folder of the repository.


Launching the application
-------------------------

From a terminal, once the package is installed:

.. code-block:: bash

    # Empty application
    pyclickimage-gui

    # Preload one or several images
    pyclickimage-gui -i image_1.tif image_2.tif

    # Restore a saved session
    pyclickimage-gui -s annotations.json

From Python:

.. code-block:: python

    import pyclickimage

    pyclickimage.run()
    pyclickimage.run(["image_1.tif", "image_2.tif"])
    pyclickimage.run(session="annotations.json")

``images`` and ``session`` are mutually exclusive: a session already
contains its list of images.

Without Python, download the standalone executable of the
`latest release <https://github.com/Artezaru/pyclickimage/releases/latest>`_
(Windows ``.exe``, Linux binary or Debian ``.deb`` package).


Using the interface
-------------------

The complete description of the interface (mouse controls, keyboard
shortcuts, groups, display tools...) is available directly in the
application: click **Help** in the toolbar or press :kbd:`F1`.


Reading the clicks
------------------

Sessions saved from the application (``.json`` or ``.csv``) can be read
without opening the interface, using :func:`pyclickimage.read_session`.
The format is detected from the file extension.

.. code-block:: python

    import pyclickimage

    data = pyclickimage.read_session("annotations.json")

The result is a nested dictionary ``image -> group -> list of (x, y)``:

.. code-block:: python

    {
        "image_1.png": {
            "default": [(128.5, 102.0), (115.2, 153.7)],
            "Coco": [(201.0, 126.5)],
        },
    }

For example, to get the points of one group on one image:

.. code-block:: python

    points = data["image_1.png"]["default"]

    for x, y in points:
        print(x, y)

Points skipped with a right click in the application are returned as
``(None, None)``, so that point indices stay aligned between images.

The coordinates follow NumPy image indexing: ``X`` is the column and
``Y`` the row, so a point ``(x, y)`` corresponds to ``image[y, x]``.