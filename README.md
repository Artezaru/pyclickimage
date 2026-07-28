# pyclickimage

## Description

`pyclickimage` is a Python package providing a graphical interface to collect
2D coordinates of points on images.

The application supports:

- multiple images in the same annotation session,
- multiple annotation groups,
- floating-point coordinates for subpixel precision,
- CSV or JSON session import/export,
- visualization controls and annotation management.

Run the graphical application:

```bash
pyclickimage-gui
```

![GUI](https://raw.githubusercontent.com/Artezaru/pyclickimage/master/pyclickimage/resources/app.png)


## Annotation sessions

Annotations are stored as complete sessions.

Two file formats are supported:

- JSON: complete session backup and restoration.
- CSV: annotation export.

---

### JSON session format

The JSON format is the recommended format for saving and restoring annotation projects.

It stores the complete state of the annotation session, including:

- image paths,
- annotation groups,
- click coordinates,
- current selections,
- session options.

A JSON session can be loaded later to restore the project exactly as it was saved.

Example:

```python
{
    "precision_mode": "float",
    "current_image_index": 0,
    "current_group_index": 1,
    "groups": [
        "default",
        "Coco"
    ],
    "images": [
        {
            "path": "image_1.png",
            "groups": {
                "default": [
                    [128.5, 102.0],
                    [115.2, 153.7]
                ],
                "Coco": [
                    [201.0, 126.5]
                ]
            }
        }
    ]
}
```

---

### CSV export format

The CSV format is intended for exporting annotations to external tools such as spreadsheets or data processing pipelines.

The exported CSV file has the following format:

```
Image,Group,Index,X,Y
image_1.png,default,0,128.5,102.0
image_1.png,default,1,115.2,153.7
image_1.png,Coco,0,201.0,126.5
image_2.png,default,0,80.0,45.3
```

The CSV columns are:

- Image: image file path.
- Group: annotation group name.
- Index: point index inside the group.
- X: horizontal coordinate.
- Y: vertical coordinate.

## Coordinates

The coordinates can be stored either as floating-point values or displayed with integer precision depending on the selected application mode.

X is the horizontal coordinate (column index) and Y is the vertical coordinate (row index), following NumPy image indexing:

image[Y, X]

Empty points can also be stored when a click is intentionally skipped:

Image,Group,Index,X,Y
image_1.png,default,2,,

CSV files do not store the complete application state. They are intended for annotation exchange and analysis.

For saving and restoring complete projects, use the JSON format.


## Reading sessions

Session files can be loaded directly from Python without opening the GUI.

```python
import pyclickimage

data = pyclickimage.read_session(
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