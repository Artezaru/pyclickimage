Running the GUI
==================

Once the package is installed, you can run the GUI to select points on an image.
For installation instructions, refer to the :doc:`../installation` documentation.

Running the GUI via Command Line
---------------------------------

You can use the command line to launch the GUI application. 
In your terminal, run the following command in the Python environment where the package is installed:

.. code-block:: bash

    pyclickimage-gui

.. warning::

    The old ``pyclickimage`` command is deprecated and will be removed in future versions. 
    Please use ``pyclickimage-gui`` instead.

You can also specify the image path as an argument to the command using the ``-i`` or ``--image`` flag.

.. code-block:: bash

    pyclickimage-gui -i example.png
    # Or
    pyclickimage-gui --image example.png

Additionally, you can specify the path to the output CSV file where the clicked points will be saved using the ``-o`` or ``--output`` flag.

.. code-block:: bash

    pyclickimage-gui -i example.png -o output.csv
    # Or
    pyclickimage-gui --image example.png --output output.csv

Running the GUI via Python Script
---------------------------------

You can also run the package directly within a Python script. 
To do so, use the `pyclickimage.run()` function.

.. code-block:: python

    import pyclickimage

    # Run the application (with default settings)
    pyclickimage.run()

If you'd like to specify an image before running the application, you can do so as follows:

.. code-block:: python

    import cv2
    import pyclickimage

    # Read the image
    image = cv2.imread("example.png")

    # Run the application with the image
    pyclickimage.run(image=image)

You can also specify the output CSV file path where the clicked points will be saved:

.. code-block:: python

    import cv2
    import pyclickimage

    # Read the image
    image = cv2.imread("example.png")

    # Run the application with the image and output file path
    pyclickimage.run(image=image, output_csv_path="output.csv")
