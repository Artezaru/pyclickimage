Extracting the Clicks from CSV
==============================

Annotation sessions saved by ``pyclickimage`` can be loaded directly from a
CSV file without opening the graphical interface.

For most use cases, the recommended approach is to use the
:func:`pyclickimage.read_session_csv` function. It provides a simple way to
access the annotations as a Python dictionary or as a pandas DataFrame.

Reading a session
-----------------

To extract the clicks from a saved session:

.. code-block:: python

    import pyclickimage

    session = pyclickimage.read_session(
        "session.csv"
    )

The default output is a nested dictionary organized as:

.. code-block:: python

    {
        "image_1.png": {
            "default": [
                (276.5, 97.0),
                (242.2, 109.8),
            ],
            "target": [
                (317.0, 144.5),
            ],
        },

        "image_2.png": {
            "default": [
                (50.0, 25.5),
            ],
        },
    }


Accessing clicks
----------------

Clicks can then be accessed by image and group:

.. code-block:: python

    clicks = session["image_1.png"]["default"]

    print(clicks)

    # Output:
    # [(276.5, 97.0), (242.2, 109.8)]



Using the core classes
----------------------

For advanced applications, the lower-level classes can be used directly.

``AnnotationSession`` allows loading and manipulating a complete annotation
session, while ``ClickManager`` manages the annotations associated with a
single image.

These classes are mainly intended for developers extending the package.
``read_session_csv`` is recommended for simple extraction and analysis tasks.