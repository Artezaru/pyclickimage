Running the GUI
===============

Once the package is installed, you can run the GUI to annotate images.
For installation instructions, refer to the :doc:`../installation` documentation.

Running the GUI via Command Line
--------------------------------

You can launch the GUI application from the command line.
In your terminal, run the following command in the Python environment where
the package is installed:

.. code-block:: bash

    pyclickimage-gui

You can optionally preload one or multiple images using the ``-i`` or
``--image`` option.

Single image:

.. code-block:: bash

    pyclickimage-gui -i example.png

Multiple images:

.. code-block:: bash

    pyclickimage-gui \
        -i image1.png image2.png image3.png

You can also preload an existing annotation session using the ``-s`` or
``--session`` option.

.. code-block:: bash

    pyclickimage-gui -s session.csv

.. note::

    A session file and image files are mutually exclusive inputs.
    Use either ``--image`` or ``--session``.

The GUI will automatically load the selected images or session when starting.

Running the GUI via Python Script
---------------------------------

You can also launch the application directly from Python using
:func:`pyclickimage.run`.

Run an empty application:

.. code-block:: python

    import pyclickimage

    pyclickimage.run()

Preload one image:

.. code-block:: python

    import pyclickimage

    pyclickimage.run(
        images="example.png",
    )

Preload multiple images:

.. code-block:: python

    import pyclickimage

    pyclickimage.run(
        images=[
            "image1.png",
            "image2.png",
            "image3.png",
        ],
    )

You can also load an existing annotation session:

.. code-block:: python

    import pyclickimage

    pyclickimage.run(
        session="session.csv",
    )

.. warning::

    ``images`` and ``session`` cannot be provided together.
    A session already contains the associated image paths and annotations.

