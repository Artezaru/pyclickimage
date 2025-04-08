Installation
============

To install ``pyclickimage``, you can use the following command:

.. code-block:: bash

    pip install git+https://github.com/Artezaru/pyclickimage.git

Or clone the repository and install it manually:

.. code-block:: bash

    git clone https://github.com/Artezaru/pyclickimage.git

Then, go to the directory and run the following command:

.. code-block:: bash

    pip install -e .

Use ``-e .[dev]`` to install it with the development dependencies.

Warning
-------

This package use ``PyQt5`` to display the GUI. 
If you have ``opencv-python`` installed on your environment, it will should be replaced by ``opencv-python-headless`` to avoid conflicts.
This package is not compatible with the full ``opencv-python``.

.. code-block:: bash

    pip uninstall opencv-python
    pip install opencv-python-headless

