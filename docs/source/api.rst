API Reference
=============

The ``pyclickimage`` package provides a high-level user API for common
operations and lower-level classes for developers.

User API
--------

Functions intended for regular users.

.. toctree::
    :maxdepth: 1

    ./api_doc/run
    ./api_doc/reading_session

To learn how to use the package effectively, refer to the documentation
:doc:`../usage`.


Developer API
-------------

Internal classes and helpers used to build the graphical application.

These objects are documented for developers who want to understand,
extend or embed the application. They are not part of the stable public
API: their names, signatures and behavior may change between versions
without notice. Regular users should rely on the functions of the
`User API`_ section.

Application
~~~~~~~~~~~

Main window of the application.

.. toctree::
    :maxdepth: 1

    ./api_doc/click_image_app

Annotation data
~~~~~~~~~~~~~~~

Storage of images, groups and clicks, independent of Qt.

.. toctree::
    :maxdepth: 1

    ./api_doc/annotation_session
    ./api_doc/click_manager
    ./api_doc/common

Qt widgets
~~~~~~~~~~

Image viewer and custom-painted plots, reusable in other applications.

.. toctree::
    :maxdepth: 1

    ./api_doc/qt_image_tool_window
    ./api_doc/qt_image_viewer
    ./api_doc/qt_histogram
    ./api_doc/qt_profile_plot
    ./api_doc/qt_linear_interpolator

Appearance
~~~~~~~~~~

Visual themes of the application and of the plots.

.. toctree::
    :maxdepth: 1

    ./api_doc/theme