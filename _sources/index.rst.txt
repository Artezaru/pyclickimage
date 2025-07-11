Welcome to pyclickimage's documentation!
=========================================================================================

Description of the package
--------------------------

UI to collect 2D-coordinates of points on an image.

Contents
--------

The documentation is divided into the following sections:

- **Installation**: This section describes how to install the package.
- **API Reference**: This section contains the documentation of the package's API.
- **Usage**: This section contains the documentation of how to use the package.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   ./installation
   ./api
   ./usage

A terminal commmand is created to run the GUI and collect the points on the image. The command is called `pyclickimage-gui` and can be used as follows:

.. code-block:: bash

    pyclickimage-gui

.. image:: ../../pyclickimage/resources/app.png
    :align: center

The clicks care in integer coordinates (``PyQt5`` does not support float coordinates) and are saved in a CSV file.
The clicks are saved by groups in their order of creation.

.. code-block:: bash

    Group,Index,Click X,Click Y
    default,0,128,102
    default,1,115,153
    default,2,207,181
    default,3,261,134
    default,4,220,83
    default,5,151,37
    Coco,0,201,126
    Coco,1,105,119
    Coco,2,90,80
    Coco,3,126,51
    Coco,4,206,59
    Coco,5,261,93
    Coco,6,212,157
    Coco,7,166,175

``X`` is the column-index of the click in the image and ``Y`` is the row-index of the click in the image such as for a ``numpy.ndarray`` the click is at ``image[Y, X]``.

Author
------

The package ``pyclickimage`` was created by the following authors:

- Artezaru <artezaru.github@proton.me>

You can access the package and the documentation with the following URL:

- **Git Plateform**: https://github.com/Artezaru/pyclickimage.git
- **Online Documentation**: https://Artezaru.github.io/pyclickimage

License
-------

Please refer to the [LICENSE] file for the license of the package.
