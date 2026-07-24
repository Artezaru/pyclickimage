# pyclickimage

## Description

`pyclickimage` is a Python package providing a graphical interface to collect
2D coordinates of points on images.

The application supports:

- multiple images in the same annotation session,
- multiple annotation groups,
- floating-point coordinates for subpixel precision,
- CSV session import/export,
- visualization controls and annotation management.

Run the graphical application:

```bash
pyclickimage-gui
```

![GUI](https://raw.githubusercontent.com/Artezaru/pyclickimage/master/pyclickimage/resources/app.png)


## Annotation sessions

Annotations are stored as complete sessions.

A session can contain several images and several groups. The exported CSV file
has the following format:

```text
Image,Group,Index,X,Y
image_1.png,default,0,128.5,102.0
image_1.png,default,1,115.2,153.7
image_1.png,Coco,0,201.0,126.5
image_2.png,default,0,80.0,45.3
```

The coordinates can be stored either as floating-point values or displayed
with integer precision depending on the selected application mode.

**X** is the horizontal coordinate (column index) and **Y** is the vertical
coordinate (row index), following NumPy image indexing:

```python
image[Y, X]
```

Empty points can also be stored when a click is intentionally skipped:

```text
Image,Group,Index,X,Y
image_1.png,default,2,,
```


## Reading sessions

Session files can be loaded directly from Python without opening the GUI.

```python
import pyclickimage

data = pyclickimage.read_session_csv(
    "session.csv"
)

print(data)
```

The returned dictionary has the following structure:

```python
{
    "image_1.png": {
        "default": [
            (128.5, 102.0),
            (115.2, 153.7),
        ],
        "Coco": [
            (201.0, 126.5),
        ],
    }
}
```

Sessions can also be converted to JSON:

```python
import pyclickimage

pyclickimage.csv2json(
    "session.csv",
    "session.json",
)
```


## Authors

- Artezaru <artezaru.github@proton.me>

Project repository:

- **GitHub**: https://github.com/Artezaru/pyclickimage

Documentation:

- **Online documentation**: https://Artezaru.github.io/pyclickimage


## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/Artezaru/pyclickimage.git
```

Or clone the repository:

```bash
git clone https://github.com/Artezaru/pyclickimage.git
```


## Requirements and compatibility

This package uses `PyQt5` for the graphical interface.

If `opencv-python` is installed in the same environment, it is recommended to
replace it with `opencv-python-headless` to avoid conflicts between Qt and
OpenCV GUI backends.

The package is not compatible with the full `opencv-python` package.


## License

Copyright 2025-2026 Artezaru

Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.

See the `LICENSE` file for more information.