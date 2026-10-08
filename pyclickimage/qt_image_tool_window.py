"""
pyclickimage - Python library to select points on a image [pyqt5 GUI]
Copyright (C) 2025-2026 Artezaru, artezaru.github@proton.me

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from .qt_histogram import QtHistogram
from .qt_image_viewer import QtImageViewer
from .qt_linear_interpolator import QtLinearInterpolator
from .qt_profile_plot import QtProfilePlot
from . import theme as _theme

# ==========================================================================
# Colormaps
# ==========================================================================

def _build_colormaps() -> dict[str, Optional[int]]:
    """Return the available colormaps, keeping the historical order.

    Returns
    -------
    dict[str, int or None]
        Mapping ``display name -> OpenCV colormap identifier``.
        ``None`` means no OpenCV colormap: a neutral linear grayscale
        (``R = G = B``), from black (level 0) to white (level 1).
        Colormaps missing from the installed OpenCV are skipped.
    """
    colormaps: dict[str, Optional[int]] = {
        "B/W": None,
        "Bone": cv2.COLORMAP_BONE,
        "Hot": cv2.COLORMAP_HOT,
        "Jet": cv2.COLORMAP_JET,
        "Rainbow": cv2.COLORMAP_RAINBOW,
        "Cool": cv2.COLORMAP_COOL,
        "Spring": cv2.COLORMAP_SPRING,
    }

    for name in ("Viridis", "Magma", "Inferno", "Plasma", "Turbo"):
        identifier = getattr(cv2, f"COLORMAP_{name.upper()}", None)

        if identifier is not None:
            colormaps[name] = identifier

    return colormaps


COLORMAPS: dict[str, Optional[int]] = _build_colormaps()
"""dict[str, int or None]: Colormaps proposed by the window."""


# ==========================================================================
# Numerical helpers
# ==========================================================================
#
# These functions do not depend on Qt.

def read_image(path: str | Path) -> Optional[np.ndarray]:
    """Read an image file as ``cv2.imread(path, cv2.IMREAD_UNCHANGED)``.

    Unlike :func:`cv2.imread`, the path may contain non-ASCII characters
    on Windows (accents, typographic apostrophes, for example
    ``Capture d’écran.png``).

    Parameters
    ----------
    path : str or pathlib.Path
        Image file. Any format supported by OpenCV.

    Returns
    -------
    numpy.ndarray or None
        Image with its original dtype and channels (BGR/BGRA order), or
        ``None`` if the file cannot be read or decoded, like
        :func:`cv2.imread`.

    Notes
    -----
    The bytes are read with :func:`numpy.fromfile`, which uses the
    Python file API (Unicode paths), then decoded in memory with
    :func:`cv2.imdecode`.
    """
    try:
        buffer = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None

    if buffer.size == 0:
        return None

    return cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)


def validate_image(image: np.ndarray) -> np.ndarray:
    """Check that an array can be displayed by the window.

    Parameters
    ----------
    image : numpy.ndarray
        Image of shape ``(H, W)``, ``(H, W, 1)``, ``(H, W, 3)`` (BGR) or
        ``(H, W, 4)`` (BGRA), with an integer, floating-point or boolean
        dtype.

    Returns
    -------
    numpy.ndarray
        The same image. Boolean images are converted to ``uint8``
        (``0`` / ``255``).

    Raises
    ------
    TypeError
        If ``image`` is not a NumPy array or has an unsupported dtype.
    ValueError
        If the image is empty or has an unsupported shape.
    """
    if not isinstance(image, np.ndarray):
        raise TypeError(
            "image must be a numpy.ndarray."
        )

    if image.dtype == np.bool_:
        image = image.astype(np.uint8) * 255

    if not (
        np.issubdtype(image.dtype, np.integer)
        or np.issubdtype(image.dtype, np.floating)
    ):
        raise TypeError(
            f"Unsupported image type: {image.dtype}"
        )

    if image.ndim not in (2, 3):
        raise ValueError(
            f"Unsupported image dimensions: {image.shape}"
        )

    if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
        raise ValueError(
            f"Unsupported number of channels: {image.shape[2]}"
        )

    if image.size == 0:
        raise ValueError(
            "The image is empty."
        )

    return image


def to_scalar_image(
    image: np.ndarray,
) -> np.ndarray:
    """Convert an OpenCV image to a 2D scalar image.

    Supported:
        - grayscale images
        - BGR images
        - BGRA images (alpha is ignored)

    Parameters
    ----------
    image : numpy.ndarray
        Image of shape ``(H, W)``, ``(H, W, 1)``, ``(H, W, 3)`` or
        ``(H, W, 4)``.

    Returns
    -------
    numpy.ndarray
        2D image. The numerical dtype is preserved.

    Raises
    ------
    ValueError
        If the shape is not supported.

    Notes
    -----
    Luminance uses the ITU-R BT.601 weights of
    :func:`cv2.cvtColor` (``0.299 R + 0.587 G + 0.114 B``).

    ``cv2.cvtColor`` is used for ``uint8``, ``uint16`` and ``float32``
    images. Other dtypes (``float64``, ``int32``...), which it does not
    support, are converted with NumPy.
    """
    if image.ndim == 2:
        return image

    if image.ndim != 3:
        raise ValueError(
            f"Unsupported image dimensions: {image.shape}"
        )

    channels = image.shape[2]

    if channels == 1:
        return image[:, :, 0]

    if channels not in (3, 4):
        raise ValueError(
            f"Unsupported number of channels: {channels}"
        )

    if image.dtype in (np.uint8, np.uint16, np.float32):
        code = (
            cv2.COLOR_BGR2GRAY
            if channels == 3
            else cv2.COLOR_BGRA2GRAY
        )

        return cv2.cvtColor(
            np.ascontiguousarray(image),
            code,
        )

    weights = np.array([0.114, 0.587, 0.299])

    gray = image[:, :, :3].astype(np.float64) @ weights

    if np.issubdtype(image.dtype, np.integer):
        info = np.iinfo(image.dtype)

        return np.clip(
            np.rint(gray),
            info.min,
            info.max,
        ).astype(image.dtype)

    return gray.astype(image.dtype)


def finite_min_max(
    image: np.ndarray,
) -> tuple[float, float]:
    """Return the finite numerical range of an image.

    Parameters
    ----------
    image : numpy.ndarray
        Image of any shape and numerical dtype.

    Returns
    -------
    tuple of float
        ``(min, max)`` over finite values. ``(0.0, 1.0)`` when the image
        contains no finite value.
    """
    values = np.asarray(image)

    if np.issubdtype(values.dtype, np.floating):
        finite = values[np.isfinite(values)]

        if finite.size == 0:
            return 0.0, 1.0

        return (
            float(np.min(finite)),
            float(np.max(finite)),
        )

    return (
        float(np.min(values)),
        float(np.max(values)),
    )


def widen_range(
    vmin: float,
    vmax: float,
) -> tuple[float, float]:
    """Return a non-degenerate range.

    Parameters
    ----------
    vmin, vmax : float
        Range bounds.

    Returns
    -------
    tuple of float
        ``(vmin, vmax)`` unchanged when ``vmin < vmax``. Otherwise the
        range is widened by ``max(|vmin| * 0.01, 1.0)`` on each side.
    """
    if vmin < vmax:
        return vmin, vmax

    delta = max(abs(vmin) * 0.01, 1.0)

    return vmin - delta, vmax + delta


def intensity_range(
    image: np.ndarray,
) -> tuple[float, float]:
    """Return the total intensity range of an image.

    For integer images, this is the interpolation domain: it only
    depends on the dtype, so the nodes keep their meaning from one image
    to the next.

    Parameters
    ----------
    image : numpy.ndarray
        Scalar image.

    Returns
    -------
    tuple of float
        - Unsigned integers: ``(0, numpy.iinfo(dtype).max)``.
        - Signed integers: ``(numpy.iinfo(dtype).min,
          numpy.iinfo(dtype).max)``.
        - Floating point: the finite data range (widened with
          :func:`widen_range` when constant).

    Raises
    ------
    ValueError
        If the dtype is not numerical.
    """
    if np.issubdtype(image.dtype, np.integer):
        info = np.iinfo(image.dtype)

        return float(info.min), float(info.max)

    if np.issubdtype(image.dtype, np.floating):
        return widen_range(*finite_min_max(image))

    raise ValueError(
        f"Unsupported image type: {image.dtype}"
    )


def normalize_for_display(
    image: np.ndarray,
) -> np.ndarray:
    """Convert any numerical image to float64 in [0, 1].

    Important:
        This conversion is ONLY for display.

    The original numerical data are never modified.

    Parameters
    ----------
    image : numpy.ndarray
        Image of any shape.

    Returns
    -------
    numpy.ndarray
        ``float64`` array of the same shape, in ``[0, 1]``.

    Notes
    -----
    - Floating-point images already in ``[0, 1]`` are kept as-is;
      otherwise they are stretched from their finite min/max. Non-finite
      values become ``0``.
    - Unsigned integers are divided by the dtype maximum.
    - Signed integers are stretched from their min/max.

    Raises
    ------
    ValueError
        If the dtype is not numerical.
    """
    image = np.asarray(image)

    if image.size == 0:
        return np.zeros(
            image.shape,
            dtype=np.float64,
        )

    # --------------------------------------------------------------
    # Floating point
    # --------------------------------------------------------------

    if np.issubdtype(image.dtype, np.floating):

        data = image.astype(
            np.float64,
            copy=False,
        )

        finite_mask = np.isfinite(data)

        if not np.any(finite_mask):
            return np.zeros_like(
                data,
                dtype=np.float64,
            )

        finite_values = data[finite_mask]

        vmin = float(np.min(finite_values))
        vmax = float(np.max(finite_values))

        # If the image is already in [0, 1], preserve this convention.
        if vmin >= 0.0 and vmax <= 1.0:
            result = data.copy()
        else:
            if vmax == vmin:
                result = np.zeros_like(
                    data,
                    dtype=np.float64,
                )
            else:
                result = (
                    (data - vmin)
                    / (vmax - vmin)
                )

        result[~finite_mask] = 0.0

        return np.clip(
            result,
            0.0,
            1.0,
        )

    # --------------------------------------------------------------
    # Unsigned integer
    # --------------------------------------------------------------

    if np.issubdtype(image.dtype, np.unsignedinteger):

        info = np.iinfo(image.dtype)

        return (
            image.astype(np.float64)
            / float(info.max)
        )

    # --------------------------------------------------------------
    # Signed integer
    # --------------------------------------------------------------

    if np.issubdtype(image.dtype, np.signedinteger):

        data = image.astype(np.float64)

        vmin = float(np.min(data))
        vmax = float(np.max(data))

        if vmax == vmin:
            return np.zeros_like(
                data,
                dtype=np.float64,
            )

        return np.clip(
            (data - vmin) / (vmax - vmin),
            0.0,
            1.0,
        )

    raise ValueError(
        f"Unsupported image type: {image.dtype}"
    )


def colorize(
    values: np.ndarray,
    colormap: Optional[int] = None,
) -> np.ndarray:
    """Convert numerical values to a displayable uint8 RGB image.

    Parameters
    ----------
    values : numpy.ndarray
        Either a scalar image ``(H, W)``, or a color image
        ``(H, W, 3)`` / ``(H, W, 4)`` in OpenCV BGR(A) order.
    colormap : int, optional
        OpenCV colormap identifier. Only used for scalar images.
        ``None`` displays a gray image.

    Returns
    -------
    numpy.ndarray
        C-contiguous ``uint8`` array of shape ``(H, W, 3)`` in RGB order.

    Notes
    -----
    Color images are normalized with :func:`normalize_for_display`
    (globally over all channels, which keeps the color balance) and their
    alpha channel is dropped.
    """
    normalized = normalize_for_display(values)

    gray = np.round(
        normalized * 255.0
    ).astype(np.uint8)

    if gray.ndim == 3:

        code = (
            cv2.COLOR_BGR2RGB
            if gray.shape[2] == 3
            else cv2.COLOR_BGRA2RGB
        )

        rgb = cv2.cvtColor(
            gray,
            code,
        )

    elif colormap is None:

        rgb = cv2.cvtColor(
            gray,
            cv2.COLOR_GRAY2RGB,
        )

    else:

        bgr = cv2.applyColorMap(
            gray,
            colormap,
        )

        rgb = cv2.cvtColor(
            bgr,
            cv2.COLOR_BGR2RGB,
        )

    return np.ascontiguousarray(
        rgb,
        dtype=np.uint8,
    )


def histogram_counts(
    values: np.ndarray,
    number_of_bins: int = 256,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute a histogram over the finite values of an array.

    Parameters
    ----------
    values : numpy.ndarray
        Values of any shape.
    number_of_bins : int, default=256
        Number of equally spaced bins.

    Returns
    -------
    counts : numpy.ndarray
        ``float64`` array of length ``number_of_bins``.
    edges : numpy.ndarray
        ``float64`` array of length ``number_of_bins + 1``.

    Notes
    -----
    The result is meant for :meth:`QtHistogram.set_bins`. Binning with
    :func:`numpy.histogram` keeps large images fast.

    A constant array produces a range widened with :func:`widen_range`.
    An array without finite values produces zero counts on ``[0, 1]``.
    """
    values = np.asarray(values).ravel()

    if np.issubdtype(values.dtype, np.floating):
        values = values[np.isfinite(values)]

    if values.size == 0:
        edges = np.linspace(0.0, 1.0, number_of_bins + 1)
        return np.zeros(number_of_bins), edges

    vmin, vmax = widen_range(
        float(np.min(values)),
        float(np.max(values)),
    )

    counts, edges = np.histogram(
        values,
        bins=number_of_bins,
        range=(vmin, vmax),
    )

    return counts.astype(np.float64), edges.astype(np.float64)


def fit_nodes_to_domain(
    nodes: Sequence[Sequence[float]],
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
) -> tuple[list[tuple[float, float]], bool]:
    """Fit interpolation nodes to an interpolation domain.

    Intensities keep their absolute meaning: nodes are not rescaled.

    Parameters
    ----------
    nodes : sequence of (float, float)
        Nodes as ``(x, y)`` pairs, in any order. At least two nodes.
    xmin, xmax : float
        Target x-domain.
    ymin, ymax : float
        Target y-range.

    Returns
    -------
    nodes : list of tuple of float
        Valid nodes: sorted, strictly increasing in x, first node at
        ``xmin``, last node at ``xmax``, every y in ``[ymin, ymax]``.
    adjusted : bool
        ``True`` if the nodes had to be modified.

    Raises
    ------
    ValueError
        If fewer than two nodes are given or a coordinate is not finite.

    Notes
    -----
    - Interior nodes outside ``]xmin, xmax[`` are dropped.
    - The first (resp. last) node is moved to ``xmin`` (resp. ``xmax``),
      keeping its y-coordinate.
    - Nodes sharing the same x keep only the last one.
    - y-coordinates are clipped to ``[ymin, ymax]``.
    """
    parsed = [(float(x), float(y)) for x, y in nodes]

    if len(parsed) < 2:
        raise ValueError(
            "At least two nodes are required."
        )

    if not np.all(np.isfinite(parsed)):
        raise ValueError(
            "Node coordinates must be finite."
        )

    ordered = sorted(parsed, key=lambda node: node[0])

    first_y = ordered[0][1]
    last_y = ordered[-1][1]

    unique: dict[float, float] = {}

    for x, y in ordered[1:-1]:
        if xmin < x < xmax:
            unique[x] = y

    result = [
        (xmin, first_y),
        *sorted(unique.items()),
        (xmax, last_y),
    ]

    result = [
        (x, float(np.clip(y, ymin, ymax)))
        for x, y in result
    ]

    adjusted = (
        len(result) != len(parsed)
        or any(
            not np.isclose(a[0], b[0]) or not np.isclose(a[1], b[1])
            for a, b in zip(result, parsed)
        )
    )

    return result, adjusted


# ==========================================================================
# Window
# ==========================================================================

class QtImageToolWindow(QtWidgets.QMainWindow):
    r"""Image viewer with profiles, histogram and intensity interpolation.

    The window displays a 2D numerical image (grayscale or color) and
    provides:

    - zoom, pan, crosshair and markers (through :class:`QtImageViewer`);
    - horizontal and vertical intensity profiles under the cursor,
      arranged in a resizable 2 x 2 grid;
    - a histogram of the whole image, or of a region selected with a
      right-button drag;
    - an intensity interpolation: a piecewise-linear curve
      (:class:`QtLinearInterpolator`) mapping intensities to the
      normalized display range, followed by an OpenCV colormap.

    It can be used on its own, or embedded in another application which
    manages the images (``set_image``) and listens to the re-emitted
    viewer signals.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget. When given, the window is created as a plain
        child widget (``Qt.Widget`` flag) so it can be inserted in a
        layout. A parentless instance inserted in a layout later is also
        turned into a child widget by Qt.
    remove_open : bool, default=False
        If ``True``, the *Open* action is not created. Use it when the
        host application manages the images.
    show_profiles : bool, default=False
        Initial visibility of the profiles.
    half_shift : bool, default=True
        Coordinate convention of the viewer. ``True`` places the center
        of the first pixel at ``(0, 0)``.
    image_proportion : tuple of float, default=(0.8, 0.8)
        Initial ``(horizontal, vertical)`` fraction of the area given to
        the image cell when the profiles are visible. The profiles share
        the remaining ``(0.2, 0.2)``.

    Signals
    -------
    mouse_entered : pyqtSignal(float, float)
        Re-emitted from :attr:`QtImageViewer.mouse_entered`.
    mouse_moved : pyqtSignal(float, float)
        Re-emitted from :attr:`QtImageViewer.mouse_moved`.
    mouse_left : pyqtSignal()
        Re-emitted from :attr:`QtImageViewer.mouse_left`.
    left_pressed, left_released : pyqtSignal(float, float)
        Re-emitted from the viewer.
    right_pressed, right_released : pyqtSignal(float, float)
        Re-emitted from the viewer.
    left_click, right_click : pyqtSignal(float, float)
        Re-emitted from the viewer. Emitted for clicks, not drags.
    rectangle_selected : pyqtSignal(float, float, float, float)
        Re-emitted from the viewer (right-button drag). The window also
        uses it to show the histogram of the selected region.
    image_changed : pyqtSignal()
        Emitted after :meth:`set_image`, :meth:`load_image` or
        :meth:`clear_image`.
    display_updated : pyqtSignal()
        Emitted after the displayed pixels were recomputed (image,
        colormap, nodes or display mode change).

    All coordinates are image coordinates, following the viewer
    convention (see ``half_shift``).

    Attributes
    ----------
    viewer : QtImageViewer
        Underlying image viewer. Exposed for advanced customization
        (crosshair, markers...).
    horizontal_profile, vertical_profile : QtProfilePlot
        Profile widgets.
    histogram : QtHistogram
        Histogram widget (displayed in a separate window).
    interpolator : QtLinearInterpolator
        Interpolation curve (displayed in a separate window).
    source_image : numpy.ndarray or None
        Image exactly as given to :meth:`set_image` (may be color).
    original_image : numpy.ndarray or None
        2D scalar version of ``source_image``, used for profiles,
        histogram and interpolation.
    processed_image : numpy.ndarray or None
        Result of the interpolation curve (``NaN`` outside the
        domain). Computed in *Processed* mode only.
    display_image : numpy.ndarray or None
        Displayed ``uint8`` RGB image.

    Notes
    -----
    **Layout.** The image and the two profiles are placed in a 2 x 2 grid
    built from splitters::

        +-------------+-----+
        |    image    |  V  |   V : vertical profile (stops at the
        |   (0, 0)    |(0,1)|       bottom of the image)
        +-------------+-----+
        |      H      |     |   H : horizontal profile
        |   (1, 0)    |     |   (1, 1) is empty
        +-------------+-----+

    Both splitter handles can be dragged; the two rows always keep the same
    column widths. When the profiles are hidden, the image fills the whole
    area.

    **Display pipeline.** *Original* mode::

        image -> normalization to [0, 1]

    The colormap is never applied to the original image: a grayscale image
    is displayed in gray and a color image keeps its colors. The colormap
    selector is therefore disabled in this mode.

    *Processed* mode::

        scalar image -> interpolation curve -> normalization -> colormap

    Values outside the curve domain are displayed in black. Profiles,
    histogram and interpolation always work on the 2D scalar
    (luminance) version of the image.

    **Integration.** The window defines no keyboard shortcut, to avoid
    conflicts with the host application.


    Examples
    --------
    Stand-alone use::

        app = QtWidgets.QApplication([])
        window = QtImageToolWindow(show_profiles=True)
        window.load_image("image.tif")
        window.show()
        app.exec_()

    Embedded use, the host managing the images::

        tool = QtImageToolWindow(remove_open=True)
        layout.addWidget(tool)

        tool.left_click.connect(on_left_click)
        tool.set_image(read_image(path))
        tool.draw_cross(10.0, 20.0, QtGui.QColor("red"), 8)
    """

    # ------------------------------------------------------------------
    # Signals re-emitted from QtImageViewer
    # ------------------------------------------------------------------

    mouse_entered = QtCore.pyqtSignal(float, float)
    mouse_moved = QtCore.pyqtSignal(float, float)
    mouse_left = QtCore.pyqtSignal()

    left_pressed = QtCore.pyqtSignal(float, float)
    left_released = QtCore.pyqtSignal(float, float)
    right_pressed = QtCore.pyqtSignal(float, float)
    right_released = QtCore.pyqtSignal(float, float)

    left_click = QtCore.pyqtSignal(float, float)
    right_click = QtCore.pyqtSignal(float, float)

    rectangle_selected = QtCore.pyqtSignal(float, float, float, float)

    # ------------------------------------------------------------------
    # Own signals
    # ------------------------------------------------------------------

    image_changed = QtCore.pyqtSignal()
    display_updated = QtCore.pyqtSignal()

    #: Names of the viewer signals re-emitted by the window.
    VIEWER_SIGNALS = (
        "mouse_entered",
        "mouse_moved",
        "mouse_left",
        "left_pressed",
        "left_released",
        "right_pressed",
        "right_released",
        "left_click",
        "right_click",
        "rectangle_selected",
    )

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        remove_open: bool = False,
        show_profiles: bool = False,
        half_shift: bool = True,
        image_proportion: tuple[float, float] = (0.8, 0.8),
    ):
        """Initialize the window.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        remove_open : bool, default=False
            Whether to remove the *Open* action.
        show_profiles : bool, default=False
            Initial visibility of the profiles.
        half_shift : bool, default=True
            Coordinate convention of the viewer.
        image_proportion : tuple of float, default=(0.8, 0.8)
            Initial ``(horizontal, vertical)`` fraction of the image
            cell.

        Raises
        ------
        ValueError
            If a value of ``image_proportion`` is not in ``]0, 1[``.
        """
        super().__init__(parent)

        if parent is not None:
            # A QMainWindow is a top-level window by default.
            self.setWindowFlags(QtCore.Qt.Widget)

        self._remove_open = bool(remove_open)

        # Active theme, used for the colors set by the window itself (for
        # instance the custom-interpolation indicator). Updated by
        # apply_theme; the light theme is the default of run().
        self._theme: _theme.Theme = _theme.LIGHT_THEME

        # ------------------------------------------------------------------
        # Image data
        # ------------------------------------------------------------------

        # Image as given by the user or the host (may be color).
        self.source_image: Optional[np.ndarray] = None

        # Original image used for analysis.
        # Always stored as a 2D numpy array.
        self.original_image: Optional[np.ndarray] = None

        # Image resulting from the interpolation.
        # This contains the original numerical values after interpolation.
        self.processed_image: Optional[np.ndarray] = None

        # Displayed image is always uint8 RGB.
        self.display_image: Optional[np.ndarray] = None

        self.histogram_window: Optional[QtWidgets.QMainWindow] = None
        self.interpolation_window: Optional[QtWidgets.QMainWindow] = None

        # Dtype of the image the interpolation was configured for. The
        # domain and the nodes are kept while the dtype does not change.
        self._interpolation_dtype: Optional[np.dtype] = None

        # Actual finite intensities of the current image, used by the
        # "Crop X axis" option.
        self._data_range: Optional[tuple[float, float]] = None

        # X axis of the interpolation plot: full intensity range (False)
        # or cropped to the actual image intensities (True).
        self._crop_x_axis = False

        # Intensity axis of the profiles: nominal range of the dtype
        # (False) or range of the displayed profile (True).
        self._fit_profiles = False

        # Ticks of the nominal range, computed in set_image.
        self._profile_ticks: Optional[list[float]] = None

        # Image cell fractions (horizontal, vertical), see _apply_proportions.
        self._image_proportion = [0.8, 0.8]
        self.set_image_proportion(*image_proportion)

        # ------------------------------------------------------------------
        # Viewer
        # ------------------------------------------------------------------

        self.viewer = QtImageViewer(half_shift=half_shift)

        # Markers are managed by the host application.
        self.viewer.auto_marker = False

        # ------------------------------------------------------------------
        # Profiles
        # ------------------------------------------------------------------

        self.horizontal_profile = QtProfilePlot()
        self.horizontal_profile.orientation = QtProfilePlot.HORIZONTAL
        self.horizontal_profile.x_title = "X [px]"
        self.horizontal_profile.y_title = "Intensity"
        self.horizontal_profile.show_grid = True
        self.horizontal_profile.show_axes = True
        self.horizontal_profile.setMinimumHeight(110)

        self.vertical_profile = QtProfilePlot()
        self.vertical_profile.orientation = QtProfilePlot.VERTICAL
        self.vertical_profile.x_title = "Y [px]"
        self.vertical_profile.y_title = "Intensity"
        self.vertical_profile.show_grid = True
        self.vertical_profile.show_axes = True
        self.vertical_profile.setMinimumWidth(150)

        # ------------------------------------------------------------------
        # Interpolation
        # ------------------------------------------------------------------

        self.interpolator = QtLinearInterpolator(
            xmin=0,
            xmax=255,
            ymin=0,
            ymax=1,
        )

        self.interpolator.allow_drag_x = True
        self.interpolator.allow_drag_y = True
        self.interpolator.x_title = "Image intensity"
        self.interpolator.y_title = "Display level"

        # ------------------------------------------------------------------
        # Histogram
        # ------------------------------------------------------------------

        self.histogram = QtHistogram()
        self.histogram.x_title = "Intensity"
        self.histogram.show_grid = True
        self.histogram.show_axes = True

        # ------------------------------------------------------------------
        # UI
        # ------------------------------------------------------------------

        self._create_toolbar()
        self._create_layout()
        self._connect_signals()

        self.set_profiles_visible(show_profiles)

        self.resize(1400, 850)
        self.setWindowTitle("Image Analysis")

    # ======================================================================
    # UI
    # ======================================================================

    def _create_toolbar(self):
        """Create the toolbar.

        Notes
        -----
        - *Open* is only created when ``remove_open`` is ``False``.
        - *Original* / *Processed* are exclusive (``QActionGroup``).
        - The node file actions are in the interpolation window.
        """
        toolbar = QtWidgets.QToolBar("Tools", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.toolbar = toolbar

        if self._remove_open:
            self.open_action = None
        else:
            self.open_action = toolbar.addAction("Open")
            self.open_action.setToolTip("Open an image file")

            toolbar.addSeparator()

        self.display_mode_group = QtWidgets.QActionGroup(self)
        self.display_mode_group.setExclusive(True)

        self.original_action = toolbar.addAction("Original")
        self.original_action.setCheckable(True)
        self.original_action.setChecked(True)
        self.original_action.setToolTip(
            "Display the image values"
        )
        self.display_mode_group.addAction(self.original_action)

        self.processed_action = toolbar.addAction("Processed")
        self.processed_action.setCheckable(True)
        self.processed_action.setToolTip(
            "Display the image values mapped by the interpolation curve"
        )
        self.display_mode_group.addAction(self.processed_action)

        toolbar.addSeparator()

        toolbar.addWidget(QtWidgets.QLabel(" Colormap "))

        self.colormap_combo = QtWidgets.QComboBox()
        self.colormap_combo.addItems(list(COLORMAPS))
        self.colormap_combo.setToolTip(
            "Colormap of the Processed display (never applied to the "
            "original image)"
        )

        # Original mode is checked at startup: no colormap.
        self.colormap_combo.setEnabled(False)

        toolbar.addWidget(self.colormap_combo)

        # Colormap-related actions, next to the colormap selector.
        self.interpolation_action = toolbar.addAction("Interpolation")
        self.interpolation_action.setToolTip(
            "Edit the curve mapping intensities to display levels "
            "(Processed display)"
        )

        # Like the colormap, the interpolation only applies to the
        # Processed display: disabled in Original mode (startup state).
        self.interpolation_action.setEnabled(False)

        toolbar.addSeparator()

        self.profiles_action = toolbar.addAction("Profiles")
        self.profiles_action.setCheckable(True)
        self.profiles_action.setToolTip(
            "Show the intensity profiles under the cursor"
        )

        self.fit_profiles_action = toolbar.addAction("Fit profiles")
        self.fit_profiles_action.setCheckable(True)
        self.fit_profiles_action.setChecked(self._fit_profiles)
        self.fit_profiles_action.setToolTip(
            "Checked: the intensity axis of the profiles spans the minimum "
            "and maximum of the displayed profile.\nUnchecked: it spans the "
            "full range of the image type (for example 0 - 255 for 8-bit "
            "images, 0 - 1 for floating point)."
        )

        # Only meaningful while the profiles are shown.
        self.fit_profiles_action.setEnabled(False)

        self.histogram_action = toolbar.addAction("Histogram")
        self.histogram_action.setToolTip(
            "Histogram of the image (right-drag on the image: "
            "histogram of a region)"
        )

        toolbar.addSeparator()

        self.reset_view_action = toolbar.addAction("Reset view")

        self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

    def _create_layout(self):
        """Create the 2 x 2 splitter grid.

        The grid is made of one vertical splitter containing two
        horizontal splitters (one per row)::

            main_splitter (vertical)
            |-- top_splitter    : [viewer, vertical_profile]
            `-- bottom_splitter : [horizontal_profile, corner]

        The two row splitters are kept synchronized so that the columns
        stay aligned: the vertical profile therefore stops exactly at the
        bottom of the image cell.
        """
        self._syncing_splitters = False

        self.top_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.top_splitter.addWidget(self.viewer)
        self.top_splitter.addWidget(self.vertical_profile)

        # Empty cell (1, 1).
        self.corner_widget = QtWidgets.QWidget()
        self.corner_widget.setMinimumWidth(
            self.vertical_profile.minimumWidth()
        )

        self.bottom_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.bottom_splitter.addWidget(self.horizontal_profile)
        self.bottom_splitter.addWidget(self.corner_widget)

        # Same minimum widths in both rows so that both splitters accept
        # the same sizes.
        minimum_width = self.horizontal_profile.minimumWidth()
        self.viewer.setMinimumWidth(minimum_width)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)

        for splitter in (
            self.top_splitter,
            self.bottom_splitter,
            self.main_splitter,
        ):
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(6)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 0)

        self.setCentralWidget(self.main_splitter)

        self.main_splitter.installEventFilter(self)

        self.cursor_label = QtWidgets.QLabel("Cursor: ---")
        self.statusBar().addPermanentWidget(self.cursor_label)
        self.statusBar().setSizeGripEnabled(False)

    def _create_interpolation_panel(self) -> QtWidgets.QWidget:
        """Create the content of the interpolation window.

        Returns
        -------
        QWidget
            Widget holding the interpolator curve and its controls.
        """
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        help_label = QtWidgets.QLabel(
            "Double-click: add a node  ·  Drag: move  ·  "
            "Right-click: remove  ·  Values outside the curve are black."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        layout.addWidget(self.interpolator, 1)

        row = QtWidgets.QHBoxLayout()

        self.crop_x_axis_checkbox = QtWidgets.QCheckBox(
            "Crop X axis to the image intensities"
        )
        self.crop_x_axis_checkbox.setToolTip(
            "Checked: the X axis spans the minimum and maximum intensities "
            "of the image.\nUnchecked: it spans the full range of the "
            "image type (for example 0 - 255 for 8-bit images)."
        )
        self.crop_x_axis_checkbox.setChecked(self._crop_x_axis)
        self.crop_x_axis_checkbox.toggled.connect(
            self.set_x_axis_cropped
        )
        row.addWidget(self.crop_x_axis_checkbox)

        row.addStretch(1)

        self.reset_nodes_button = QtWidgets.QPushButton("Reset nodes")
        self.reset_nodes_button.clicked.connect(self.reset_nodes)
        row.addWidget(self.reset_nodes_button)

        self.save_nodes_button = QtWidgets.QPushButton("Save nodes…")
        self.save_nodes_button.clicked.connect(self.save_nodes)
        row.addWidget(self.save_nodes_button)

        self.load_nodes_button = QtWidgets.QPushButton("Load nodes…")
        self.load_nodes_button.clicked.connect(self.load_nodes)
        row.addWidget(self.load_nodes_button)

        layout.addLayout(row)

        return panel

    def _connect_signals(self):
        """Connect the internal signals.

        Notes
        -----
        Every signal listed in :attr:`VIEWER_SIGNALS` is connected to the
        signal of the same name of the window (signal-to-signal
        connection), which re-emits it unchanged.
        """
        for name in self.VIEWER_SIGNALS:
            getattr(self.viewer, name).connect(getattr(self, name))

        if self.open_action is not None:
            self.open_action.triggered.connect(self.open_image)

        self.original_action.triggered.connect(self.show_original)
        self.processed_action.triggered.connect(self.show_processed)

        self.colormap_combo.currentTextChanged.connect(
            self.update_image
        )

        self.profiles_action.toggled.connect(
            self.set_profiles_visible
        )

        self.fit_profiles_action.toggled.connect(
            self.set_profiles_fitted
        )

        self.profiles_action.toggled.connect(
            self.fit_profiles_action.setEnabled
        )

        self.histogram_action.triggered.connect(
            self.compute_histogram_on_image
        )

        self.interpolation_action.triggered.connect(
            self.open_interpolation
        )

        # The colormap and the interpolation only apply to the Processed
        # display.
        self.processed_action.toggled.connect(
            self.colormap_combo.setEnabled
        )

        self.processed_action.toggled.connect(
            self._on_processed_toggled
        )

        self.reset_view_action.triggered.connect(
            self.viewer.reset_view
        )

        self.viewer.mouse_entered.connect(
            self.update_profiles
        )

        self.viewer.mouse_moved.connect(
            self.update_profiles
        )

        self.viewer.mouse_left.connect(
            self.clear_profiles
        )

        self.viewer.rectangle_selected.connect(
            self.compute_histogram_on_rectangle
        )

        self.interpolator.nodes_changed.connect(
            self.update_image
        )

        self.interpolator.nodes_changed.connect(
            self._update_interpolation_indicator
        )

        self.top_splitter.splitterMoved.connect(
            self._on_row_splitter_moved
        )

        self.bottom_splitter.splitterMoved.connect(
            self._on_row_splitter_moved
        )

        self.main_splitter.splitterMoved.connect(
            self._on_main_splitter_moved
        )

    # ======================================================================
    # Image API
    # ======================================================================

    def set_image(
        self,
        image: Optional[np.ndarray],
        reset_view: bool = True,
    ) -> None:
        """Set the image to display and analyze.

        Parameters
        ----------
        image : numpy.ndarray or None
            Image of shape ``(H, W)``, ``(H, W, 1)``, ``(H, W, 3)`` (BGR)
            or ``(H, W, 4)`` (BGRA), as returned by
            ``cv2.imread(path, cv2.IMREAD_UNCHANGED)``. Integer,
            floating-point and boolean dtypes are supported. ``None`` is
            equivalent to :meth:`clear_image`.

            The array is stored by reference; it must not be modified in
            place afterwards.
        reset_view : bool, default=True
            If ``True``, markers are removed and the view is fitted to
            the image. If ``False`` and the new image has the same size,
            zoom, pan and markers are kept.

        Raises
        ------
        TypeError
            If ``image`` is not a NumPy array or has an unsupported
            dtype.
        ValueError
            If the image is empty or has an unsupported shape.

        Notes
        -----
        The display mode (*Original* / *Processed*) and the colormap are
        kept. Emits :attr:`image_changed`.

        Interpolation curve:

        - integer images: the domain is the full range of the dtype
          (``[0, numpy.iinfo(dtype).max]`` for unsigned integers), so it
          does not depend on the image content;
        - while the dtype does not change, the curve is kept exactly as
          it is (floating-point images only extend the domain when the
          new image exceeds it);
        - when the dtype changes (or for the first image), the curve is
          reset to a straight line from ``(xmin, 0)`` to ``(xmax, 1)``.

        Use :meth:`reset_nodes` to reset the curve explicitly.
        """
        if image is None:
            self.clear_image()
            return

        image = validate_image(image)
        scalar = to_scalar_image(image)

        self.source_image = image
        self.original_image = scalar
        self.processed_image = None

        # Nominal intensity range of the dtype, used by the profiles when
        # they are not fitted ([0, iinfo.max] for unsigned integers,
        # [0, 1] for floating point).
        if np.issubdtype(scalar.dtype, np.integer):
            info = np.iinfo(scalar.dtype)
            vmin, vmax = float(info.min), float(info.max)
        else:
            vmin, vmax = 0.0, 1.0

        self._profile_ticks = list(np.linspace(vmin, vmax, 5))
        self._apply_profile_range()

        # Configure the interpolator using the real image range.
        self._configure_interpolator()

        self._render(reset_view=reset_view)

        height, width = scalar.shape
        data_min, data_max = finite_min_max(scalar)

        channels = 1 if image.ndim == 2 else image.shape[2]

        self.statusBar().showMessage(
            f"{width} × {height} | "
            f"{channels} channel(s) | "
            f"dtype={image.dtype} | "
            f"range=[{data_min:.6g}, {data_max:.6g}]"
        )

        self.clear_profiles()

        if self.histogram_window is not None:
            self.histogram_window.close()

        self.image_changed.emit()


    def get_image(
        self,
        scalar: bool = False,
    ) -> Optional[np.ndarray]:
        """Return the current image.

        Parameters
        ----------
        scalar : bool, default=False
            If ``False``, return the image as given to :meth:`set_image`.
            If ``True``, return its 2D scalar (luminance) version used
            for the analysis.

        Returns
        -------
        numpy.ndarray or None
            Current image, or ``None`` if no image is set.
        """
        if scalar:
            return self.original_image

        return self.source_image

    def has_image(self) -> bool:
        """Return whether an image is set.

        Returns
        -------
        bool
            ``True`` if an image is currently displayed.
        """
        return self.original_image is not None

    def clear_image(self) -> None:
        """Remove the current image.

        The viewer, the profiles and the histogram are cleared. The
        interpolation nodes are kept. Emits :attr:`image_changed`.
        """
        self.source_image = None
        self.original_image = None
        self.processed_image = None
        self.display_image = None

        self.viewer.clear_image()

        self.clear_profiles()

        if self.histogram_window is not None:
            self.histogram_window.close()

        self.cursor_label.setText("Cursor: ---")
        self.statusBar().clearMessage()

        self.image_changed.emit()

    def load_image(
        self,
        filename: str | Path,
    ) -> None:
        """Read an image file and display it.

        Parameters
        ----------
        filename : str or pathlib.Path
            Image file. Any format readable by
            ``cv2.imread(..., cv2.IMREAD_UNCHANGED)``.

        Raises
        ------
        ValueError
            If the file cannot be read or the image is not supported.
        TypeError
            If the image dtype is not supported.

        Notes
        -----
        The file is read with :func:`read_image`, which also supports
        non-ASCII paths on Windows (``cv2.imread`` does not).
        """
        filename = Path(filename)

        image = read_image(filename)

        if image is None:
            raise ValueError(
                f"Unable to load the image: {filename}"
            )

        self.set_image(image)

        self.setWindowTitle(f"Image Analysis - {filename.name}")

    def open_image(self):
        """Ask for an image file and display it.

        Connected to the *Open* action (absent when ``remove_open`` is
        ``True``). Errors are reported in a message box.
        """
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open image",
            "",
            (
                "Images "
                "(*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.jp2 *.exr);;"
                "All files (*)"
            ),
        )

        if not filename:
            return

        try:
            self.load_image(filename)
        except (TypeError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(
                self,
                "Open image",
                str(exc),
            )

    # ======================================================================
    # Viewer shortcuts
    # ======================================================================

    @property
    def half_shift(self) -> bool:
        """bool: Coordinate convention of the viewer.

        ``True`` places the center of the first pixel at ``(0, 0)``.
        Shared with :attr:`viewer` (setting one sets the other).
        """
        return self.viewer.half_shift

    @half_shift.setter
    def half_shift(self, value: bool) -> None:
        self.viewer.half_shift = value

    @property
    def auto_marker(self) -> bool:
        """bool: Whether the viewer draws a cross on each left click.

        ``False`` by default in this window: markers are expected to be
        drawn by the host application.
        """
        return self.viewer.auto_marker

    @auto_marker.setter
    def auto_marker(self, value: bool) -> None:
        self.viewer.auto_marker = bool(value)

    def draw_cross(self, *args, **kwargs):
        """Draw a cross marker. See :meth:`QtImageViewer.draw_cross`."""
        return self.viewer.draw_cross(*args, **kwargs)

    def draw_rectangle(self, *args, **kwargs):
        """Draw a rectangle marker. See :meth:`QtImageViewer.draw_rectangle`."""
        return self.viewer.draw_rectangle(*args, **kwargs)

    def draw_ellipse(self, *args, **kwargs):
        """Draw an ellipse marker. See :meth:`QtImageViewer.draw_ellipse`."""
        return self.viewer.draw_ellipse(*args, **kwargs)

    def clear_markers(self) -> None:
        """Remove all markers. See :meth:`QtImageViewer.clear_markers`."""
        self.viewer.clear_markers()

    def reset_view(self) -> None:
        """Fit the image in the view. See :meth:`QtImageViewer.reset_view`."""
        self.viewer.reset_view()

    # ======================================================================
    # Interpolation configuration
    # ======================================================================

    def _configure_interpolator(self):
        """Configure the interpolator for the current image.

        Notes
        -----
        X range (interpolation domain):
            - Integer images: the full range of the dtype,
              ``[0, numpy.iinfo(dtype).max]`` for unsigned integers
              (``[iinfo.min, iinfo.max]`` for signed integers). It does
              not depend on the image content.
            - Floating-point images: there is no type range, so the
              domain is the data range of the first image, extended
              when a later image exceeds it.

        Nodes:
            - Same dtype as the previous image: the curve is kept as it
              is. Integer domains never change; floating-point domains
              can only grow, which keeps every interior node.
            - New dtype (or first image): the curve is reset to a
              straight line from ``(xmin, 0)`` to ``(xmax, 1)``, because
              a ``uint8`` mapping applied to a ``uint16`` image (or the
              reverse) is wrong.

        Y range:
            Always ``[0, 1]`` (normalized display level).

        The visible x-range is then set by :meth:`_apply_x_axis_range`.
        """
        if self.original_image is None:
            return

        image = self.original_image

        self._data_range = widen_range(*finite_min_max(image))

        same_dtype = image.dtype == self._interpolation_dtype
        self._interpolation_dtype = image.dtype

        is_integer = np.issubdtype(image.dtype, np.integer)

        # set_domain / set_nodes emit nodes_changed -> update_image. The
        # display is rendered once by the caller, so signals are blocked.
        self.interpolator.blockSignals(True)

        try:
            if not same_dtype:
                domain = (
                    intensity_range(image)
                    if is_integer
                    else self._data_range
                )

                # Straight line from (xmin, 0) to (xmax, 1), no
                # interior node.
                self.interpolator.set_domain(
                    *domain,
                    0.0,
                    1.0,
                    keep_nodes=False,
                )

            elif not is_integer:
                # Floating point: only extend the domain, never shrink
                # it, so that no node is lost.
                xmin = min(self.interpolator.xmin, self._data_range[0])
                xmax = max(self.interpolator.xmax, self._data_range[1])

                if (xmin, xmax) != (self.interpolator.xmin, self.interpolator.xmax):
                    self.interpolator.set_domain(
                        xmin,
                        xmax,
                        keep_nodes=True,
                    )

            # Integer image with the same dtype: nothing to do, the domain
            # and the nodes are kept exactly.

        finally:
            self.interpolator.blockSignals(False)

        self._apply_x_axis_range()

        # nodes_changed was blocked above.
        self._update_interpolation_indicator()

    def _apply_x_axis_range(self) -> None:
        """Set the visible x-range of the interpolation plot.

        Notes
        -----
        - :meth:`is_x_axis_cropped` is ``False``: the axis spans the
          whole interpolation domain (for example ``[0, 65535]`` for
          ``uint16``).
        - :meth:`is_x_axis_cropped` is ``True``: the axis spans the
          actual minimum and maximum intensities of the current image.

        Only the display of the curve is affected, not the
        interpolation: nodes outside the cropped view are kept.
        """
        if self._data_range is None:
            return

        if self._crop_x_axis:
            self.interpolator.set_view(
                xmin=self._data_range[0],
                xmax=self._data_range[1],
            )
        else:
            self.interpolator.set_view(
                xmin=self.interpolator.xmin,
                xmax=self.interpolator.xmax,
            )

    def is_x_axis_cropped(self) -> bool:
        """Return whether the interpolation x-axis is cropped.

        Returns
        -------
        bool
            ``True`` if the x-axis spans only the actual intensities of
            the image, ``False`` if it spans the total intensity range.
        """
        return self._crop_x_axis

    def set_x_axis_cropped(
        self,
        value: bool,
    ) -> None:
        """Crop (or not) the interpolation x-axis to the useful range.

        Parameters
        ----------
        value : bool
            ``True``: the x-axis spans the actual minimum and maximum
            intensities of the current image, which gives more room to
            edit the curve.

            ``False`` (default): the x-axis spans the whole
            interpolation domain (for example ``[0, 255]`` for
            ``uint8``).

        Notes
        -----
        The setting is kept when the image changes. The checkbox of the
        interpolation window is kept in sync.
        """
        self._crop_x_axis = bool(value)

        checkbox = getattr(self, "crop_x_axis_checkbox", None)

        if checkbox is not None and checkbox.isChecked() != self._crop_x_axis:
            checkbox.blockSignals(True)
            checkbox.setChecked(self._crop_x_axis)
            checkbox.blockSignals(False)

        self._apply_x_axis_range()

    def is_default_interpolation(self) -> bool:
        """Return whether the interpolation curve is the default one.

        Returns
        -------
        bool
            ``True`` if the curve is the straight line from
            ``(xmin, ymin)`` to ``(xmax, ymax)`` without interior node,
            i.e. the curve set by :meth:`reset_nodes`.
        """
        interpolator = self.interpolator

        default = (
            (interpolator.xmin, interpolator.ymin),
            (interpolator.xmax, interpolator.ymax),
        )

        nodes = interpolator.nodes

        return len(nodes) == 2 and bool(
            np.allclose(nodes, default, rtol=0.0, atol=1e-9 * max(
                1.0, abs(interpolator.xmax - interpolator.xmin)
            ))
        )

    def _update_interpolation_indicator(self, *_) -> None:
        """Color the *Interpolation* button when the curve is customized.

        Notes
        -----
        The button uses the ``warning`` colors of the active theme when
        :meth:`is_default_interpolation` is ``False``, also in *Original*
        mode (semi-transparent, since the button is then disabled): the
        custom curve will apply as soon as the *Processed* display is
        selected.
        """
        button = self.toolbar.widgetForAction(self.interpolation_action)

        if button is None:
            return

        if self.is_default_interpolation():
            button.setStyleSheet("")
            self.interpolation_action.setToolTip(
                "Edit the curve mapping intensities to display levels "
                "(Processed display)"
            )
            return

        t = self._theme

        disabled = QtGui.QColor(t.warning)
        disabled_rgba = (
            f"rgba({disabled.red()}, {disabled.green()}, "
            f"{disabled.blue()}, 110)"
        )

        button.setStyleSheet(
            "QToolButton {"
            f" background-color: {t.warning};"
            f" border: 1px solid {t.warning};"
            f" border-radius: {t.radius}px;"
            f" color: {t.warning_text};"
            "}"
            "QToolButton:hover {"
            f" background-color: {t.warning_hover};"
            f" border-color: {t.warning_hover};"
            "}"
            "QToolButton:disabled {"
            f" background-color: {disabled_rgba};"
            " border-color: transparent;"
            f" color: {t.text_muted};"
            "}"
        )

        self.interpolation_action.setToolTip(
            "A custom interpolation curve is active (Processed display). "
            "Use 'Reset nodes' to restore the default straight line."
        )

    def _on_processed_toggled(self, processed: bool) -> None:
        """Enable the interpolation tools only in *Processed* mode.

        Parameters
        ----------
        processed : bool
            ``True`` when the *Processed* display is selected.

        Notes
        -----
        If the interpolation window is open, its content is disabled in
        *Original* mode instead of being closed.
        """
        self.interpolation_action.setEnabled(processed)

        if self.interpolation_window is not None:
            self.interpolation_window.centralWidget().setEnabled(processed)

    def reset_nodes(self) -> None:
        """Reset the interpolation curve to a straight line.

        The curve goes from ``(xmin, 0)`` to ``(xmax, 1)``, for example
        from ``0`` to ``numpy.iinfo(dtype).max`` for an unsigned integer
        image.
        """
        self.interpolator.reset()

    def open_interpolation(self):
        """Show the interpolation window.

        Notes
        -----
        The window is created on first use, as a child window of this
        widget.
        """
        if self.interpolation_window is None:

            self.interpolation_window = QtWidgets.QMainWindow(self)
            self.interpolation_window.setWindowFlags(QtCore.Qt.Window)

            self.interpolation_window.setWindowTitle(
                "Interpolation"
            )

            self.interpolation_window.setCentralWidget(
                self._create_interpolation_panel()
            )

            self.interpolation_window.centralWidget().setEnabled(
                self.processed_action.isChecked()
            )

            self.interpolation_window.resize(
                760,
                480,
            )

        self.interpolation_window.show()
        self.interpolation_window.raise_()
        self.interpolation_window.activateWindow()

    # ======================================================================
    # Image processing
    # ======================================================================

    def update_image(self, *_):
        """Update the currently displayed image.

        Original:
            numerical image -> display normalization

            The colormap is never applied: a color image keeps its
            colors, a grayscale image is displayed in gray.

        Processed:
            scalar image -> interpolation -> display normalization
            -> colormap

        Notes
        -----
        Zoom, pan and markers are preserved. Emits
        :attr:`display_updated`.
        """
        self._render(reset_view=False)

    def _render(
        self,
        reset_view: bool,
    ) -> None:
        """Compute the displayed pixels and send them to the viewer.

        Parameters
        ----------
        reset_view : bool
            Forwarded to :meth:`QtImageViewer.set_image`.
        """
        if self.original_image is None:
            return

        # --------------------------------------------------------------
        # Original image (never colormapped)
        # --------------------------------------------------------------

        if self.original_action.isChecked():

            colormap = None

            source = self.source_image

            if (
                source is not None
                and source.ndim == 3
                and source.shape[2] in (3, 4)
            ):
                values = source
            else:
                values = self.original_image

        # --------------------------------------------------------------
        # Processed image
        # --------------------------------------------------------------

        else:

            colormap = self.get_selected_colormap()

            values = self.interpolator.interpolate(
                self.original_image.astype(np.float64)
            )

            self.processed_image = values

        # --------------------------------------------------------------
        # Display
        # --------------------------------------------------------------

        self.display_image = colorize(values, colormap)

        self._set_viewer_image(
            self.display_image,
            reset_view=reset_view,
        )

        self.display_updated.emit()

    def apply_colormap(
        self,
        values: np.ndarray,
    ) -> np.ndarray:
        """Convert arbitrary numerical values to uint8 RGB.

        Parameters
        ----------
        values : numpy.ndarray
            Scalar ``(H, W)`` or BGR(A) ``(H, W, 3|4)`` values.

        Returns
        -------
        numpy.ndarray
            ``uint8`` RGB image using the selected colormap.

        See Also
        --------
        colorize
        """
        return colorize(values, self.get_selected_colormap())

    @staticmethod
    def _set_qimage(
        image: np.ndarray,
    ) -> QtGui.QImage:
        """Create an independent QImage from an RGB uint8 numpy array.

        Parameters
        ----------
        image : numpy.ndarray
            ``uint8`` array of shape ``(H, W, 3)``.

        Returns
        -------
        QImage
            Deep copy, independent of the NumPy buffer.
        """
        image = np.ascontiguousarray(
            image,
            dtype=np.uint8,
        )

        height, width, channels = image.shape

        qimage = QtGui.QImage(
            image.data,
            width,
            height,
            channels * width,
            QtGui.QImage.Format_RGB888,
        )

        return qimage.copy()

    def _set_viewer_image(
        self,
        image: np.ndarray,
        reset_view: bool = True,
    ):
        """Send an RGB array to the viewer.

        Parameters
        ----------
        image : numpy.ndarray
            ``uint8`` RGB image.
        reset_view : bool, default=True
            Forwarded to :meth:`QtImageViewer.set_image`.
        """
        qimage = self._set_qimage(image)

        self.viewer.set_image(
            QtGui.QPixmap.fromImage(qimage),
            reset_view=reset_view,
        )

    # ======================================================================
    # Colormap
    # ======================================================================

    def get_selected_colormap(
        self,
    ) -> Optional[int]:
        """Return OpenCV colormap corresponding to current selection.

        Returns
        -------
        int or None
            OpenCV colormap identifier, ``None`` for *B/W*.
        """
        return COLORMAPS.get(
            self.colormap_combo.currentText(),
            None,
        )

    def set_colormap(
        self,
        name: str,
    ) -> None:
        """Select a colormap by name.

        Parameters
        ----------
        name : str
            One of the keys of :data:`COLORMAPS`.

        Raises
        ------
        KeyError
            If the colormap is unknown.
        """
        if name not in COLORMAPS:
            raise KeyError(
                f"Unknown colormap '{name}'. "
                f"Available: {', '.join(COLORMAPS)}."
            )

        self.colormap_combo.setCurrentText(name)

    # ======================================================================
    # Display mode
    # ======================================================================

    def show_original(self):
        """Display the image values (no interpolation curve)."""
        self.original_action.setChecked(True)

        self.update_image()

    def show_processed(self):
        """Display the image mapped by the interpolation curve."""
        self.processed_action.setChecked(True)

        self.update_image()

    # ======================================================================
    # Profiles and layout
    # ======================================================================

    def is_profiles_visible(self) -> bool:
        """Return whether the profiles are displayed.

        Returns
        -------
        bool
            State of the *Profiles* action.
        """
        return self.profiles_action.isChecked()

    def set_profiles_visible(
        self,
        visible: bool,
    ):
        """Show or hide the profiles.

        Parameters
        ----------
        visible : bool
            ``True``: image in cell (0, 0), vertical profile in (0, 1),
            horizontal profile in (1, 0), cell (1, 1) empty, with the
            stored proportions.

            ``False``: the image fills the whole area.

        Notes
        -----
        The *Profiles* action is kept in sync, so this method can be
        called by a host application.
        """
        visible = bool(visible)

        if self.profiles_action.isChecked() != visible:
            # Re-enters this method through the ``toggled`` signal.
            self.profiles_action.setChecked(visible)
            return

        self.vertical_profile.setVisible(visible)
        self.bottom_splitter.setVisible(visible)

        if visible:
            self._apply_proportions()

    def image_proportion(self) -> tuple[float, float]:
        """Return the proportion of the image cell.

        Returns
        -------
        tuple of float
            ``(horizontal, vertical)`` fraction of the area occupied by
            the image cell when the profiles are visible.
        """
        return tuple(self._image_proportion)

    def set_image_proportion(
        self,
        horizontal: float,
        vertical: float,
    ) -> None:
        """Set the proportion of the image cell.

        Parameters
        ----------
        horizontal : float
            Fraction of the width given to column 0 (image and
            horizontal profile). Must be in ``]0, 1[``.
        vertical : float
            Fraction of the height given to row 0 (image and vertical
            profile). Must be in ``]0, 1[``.

        Raises
        ------
        ValueError
            If a fraction is not in ``]0, 1[``.

        Examples
        --------
        The default layout (80 % / 20 % in both directions)::

            window.set_image_proportion(0.8, 0.8)
        """
        horizontal = float(horizontal)
        vertical = float(vertical)

        if not (0.0 < horizontal < 1.0 and 0.0 < vertical < 1.0):
            raise ValueError(
                "Image proportions must be in ]0, 1[."
            )

        self._image_proportion = [horizontal, vertical]

        if hasattr(self, "main_splitter") and self.is_profiles_visible():
            self._apply_proportions()

    def _apply_proportions(self) -> None:
        """Resize the splitters according to the stored proportions."""
        horizontal, vertical = self._image_proportion

        # Both row splitters span the whole width of the main splitter.
        width = self.main_splitter.width() - self.top_splitter.handleWidth()
        height = self.main_splitter.height() - self.main_splitter.handleWidth()

        # Before the first show, sizes are only used as ratios.
        width = width if width > 0 else 1000
        height = height if height > 0 else 1000

        left = round(width * horizontal)
        column_sizes = [left, width - left]

        top = round(height * vertical)

        self._syncing_splitters = True

        try:
            self.top_splitter.setSizes(column_sizes)
            self.bottom_splitter.setSizes(column_sizes)
            self.main_splitter.setSizes([top, height - top])
        finally:
            self._syncing_splitters = False

    def _on_row_splitter_moved(
        self,
        *_,
    ) -> None:
        """Synchronize both rows and store the horizontal proportion.

        Called when the user drags the handle of the top or bottom row.
        """
        if self._syncing_splitters:
            return

        source = self.sender()

        if source is self.top_splitter:
            target = self.bottom_splitter
        else:
            target = self.top_splitter

        sizes = source.sizes()

        self._syncing_splitters = True

        try:
            target.setSizes(sizes)
        finally:
            self._syncing_splitters = False

        total = sum(sizes)

        if total > 0:
            self._image_proportion[0] = sizes[0] / total

    def _on_main_splitter_moved(
        self,
        *_,
    ) -> None:
        """Store the vertical proportion after a user drag."""
        if self._syncing_splitters:
            return

        sizes = self.main_splitter.sizes()
        total = sum(sizes)

        if total > 0 and sizes[1] > 0:
            self._image_proportion[1] = sizes[0] / total

    def eventFilter(
        self,
        watched: QtCore.QObject,
        event: QtCore.QEvent,
    ) -> bool:
        """Keep the grid proportions when the grid is resized.

        The filter is installed on :attr:`main_splitter`: its resize
        event carries the final size of the grid, whereas the window's
        own ``resizeEvent`` happens before the layout is updated.

        Parameters
        ----------
        watched : QObject
            Object receiving the event.
        event : QEvent
            Event.

        Returns
        -------
        bool
            Always ``False``: the event is never consumed.
        """
        if (
            watched is self.main_splitter
            and event.type() == QtCore.QEvent.Resize
            and self.is_profiles_visible()
        ):
            self._apply_proportions()

        return super().eventFilter(watched, event)

    def showEvent(
        self,
        event: QtGui.QShowEvent,
    ) -> None:
        """Apply the grid proportions once the real size is known."""
        super().showEvent(event)

        if self.is_profiles_visible():
            self._apply_proportions()

    def _pixel_index(
        self,
        coordinate: float,
        size: int,
    ) -> int:
        """Convert an image coordinate to a pixel index.

        Parameters
        ----------
        coordinate : float
            Image coordinate (viewer convention).
        size : int
            Number of pixels along the axis.

        Returns
        -------
        int
            Index in ``[0, size - 1]``.

        Notes
        -----
        With ``half_shift=True`` pixel ``i`` covers ``[i - 0.5, i + 0.5[``
        (rounding). With ``half_shift=False`` it covers ``[i, i + 1[``
        (floor).
        """
        if self.half_shift:
            index = int(np.floor(coordinate + 0.5))
        else:
            index = int(np.floor(coordinate))

        return int(np.clip(index, 0, size - 1))

    def is_profiles_fitted(self) -> bool:
        """Return whether the profile intensity axis is fitted.

        Returns
        -------
        bool
            ``True`` if the axis spans the range of the displayed
            profile, ``False`` if it spans the nominal range of the
            image type.
        """
        return self._fit_profiles

    def set_profiles_fitted(self, value: bool) -> None:
        """Fit (or not) the profile intensity axis to the profile.

        Parameters
        ----------
        value : bool
            ``True``: the axis spans the minimum and maximum of the
            displayed profile, recomputed at each cursor move.

            ``False`` (default): the axis spans the nominal range of
            the image type, ``[0, numpy.iinfo(dtype).max]`` for unsigned
            integers and ``[0, 1]`` for floating point.

        Notes
        -----
        The setting is kept when the image changes. The toolbar action
        is kept in sync.
        """
        self._fit_profiles = bool(value)

        if self.fit_profiles_action.isChecked() != self._fit_profiles:
            self.fit_profiles_action.blockSignals(True)
            self.fit_profiles_action.setChecked(self._fit_profiles)
            self.fit_profiles_action.blockSignals(False)

        self._apply_profile_range()

    def _apply_profile_range(self) -> None:
        """Set the intensity ticks of both profiles.

        ``None`` lets :class:`QtProfilePlot` build the ticks from the
        displayed data; explicit ticks fix the axis to their range.
        """
        ticks = None if self._fit_profiles else self._profile_ticks

        self.horizontal_profile.y_ticks = ticks
        self.vertical_profile.y_ticks = ticks

    def update_profiles(
        self,
        x,
        y,
    ):
        """Update the profiles and the cursor label at a position.

        Parameters
        ----------
        x, y : float
            Image coordinates of the cursor.

        Notes
        -----
        The cursor label is updated even when the profiles are hidden.
        In *Processed* mode it also shows the mapped value.
        """
        if self.original_image is None:
            return

        image = self.original_image

        height, width = image.shape

        x = self._pixel_index(x, width)
        y = self._pixel_index(y, height)

        text = (
            f"Cursor: X={x}, Y={y} | "
            f"Value={float(image[y, x]):.6g}"
        )

        if (
            self.processed_action.isChecked()
            and self.processed_image is not None
        ):
            text += f" → {float(self.processed_image[y, x]):.4g}"

        self.cursor_label.setText(text)

        if not self.is_profiles_visible():
            return

        horizontal_values = (
            image[y, :]
            .astype(np.float64)
        )

        vertical_values = (
            image[:, x]
            .astype(np.float64)
        )

        self.horizontal_profile.set_data(
            np.arange(width),
            horizontal_values,
        )

        self.vertical_profile.set_data(
            np.arange(height),
            vertical_values,
        )

    def clear_profiles(self) -> None:
        """Clear the profiles and the cursor label.

        Called when the image changes and when the cursor leaves the
        image. The profiles are drawn again on the next mouse move over
        the image.
        """
        self.cursor_label.setText(
            "Cursor: ---" if self.original_image is None
            else "Cursor: outside image"
        )

        self.horizontal_profile.clear()
        self.vertical_profile.clear()

    def hide_profile_cursor(self):
        """Update the cursor label when the cursor leaves the image."""
        self.cursor_label.setText(
            "Cursor: outside image"
        )

     # ======================================================================
    # Histogram
    # ======================================================================

    def compute_histogram_on_image(self) -> None:
        """Show the histogram of the whole scalar image.

        Connected to the *Histogram* action. The histogram is recomputed
        at each call.
        """
        if self.original_image is None:
            return

        counts, edges = histogram_counts(self.original_image)

        self.histogram.set_bins(counts, edges)

        self.update_histogram("Histogram")

    def compute_histogram_on_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Show the histogram of a rectangular region.

        Connected to :attr:`QtImageViewer.rectangle_selected`.

        Parameters
        ----------
        x, y : float
            Image coordinates of the top-left corner (viewer convention).
        width, height : float
            Size of the region in pixels.

        Notes
        -----
        The region is converted to pixel indices with the same convention
        as the profiles, so it is consistent with ``half_shift``.
        """
        if self.original_image is None:
            return

        image_height, image_width = self.original_image.shape

        shift = 0.5 if self.half_shift else 0.0

        x1 = max(0, int(round(x + shift)))
        y1 = max(0, int(round(y + shift)))
        x2 = min(image_width, int(round(x + shift + width)))
        y2 = min(image_height, int(round(y + shift + height)))

        if x2 <= x1 or y2 <= y1:
            return

        values = self.original_image[y1:y2, x1:x2]

        counts, edges = histogram_counts(values)

        self.histogram.set_bins(counts, edges)

        self.update_histogram(
            f"Histogram - region x=[{x1}, {x2}[, y=[{y1}, {y2}["
        )

    def update_histogram(self, title: str = "Histogram") -> None:
        """Show the histogram window with its current bins.

        The window is created on first use, as a child window of this
        widget.

        Parameters
        ----------
        title : str, default="Histogram"
            Title of the histogram window.
        """
        if self.histogram_window is None:
            self.histogram_window = QtWidgets.QMainWindow(self)
            self.histogram_window.setWindowFlags(QtCore.Qt.Window)
            self.histogram_window.setCentralWidget(self.histogram)
            self.histogram_window.resize(700, 450)

        self.histogram_window.setWindowTitle(title)

        self.histogram_window.show()
        self.histogram_window.raise_()
        self.histogram_window.activateWindow()

    # ======================================================================
    # Nodes persistence
    # ======================================================================

    def save_nodes(self):
        """Save the interpolation nodes to a JSON file.

        Notes
        -----
        File format::

            {
                "version": 1,
                "xmin": ..., "xmax": ..., "ymin": ..., "ymax": ...,
                "nodes": [[x0, y0], [x1, y1], ...]
            }
        """
        parent = self.interpolation_window or self

        if self.original_image is None:
            QtWidgets.QMessageBox.warning(
                parent,
                "Save nodes",
                "No image is loaded.",
            )
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent,
            "Save colormap nodes",
            "",
            "JSON files (*.json);;All files (*)",
        )

        if not filename:
            return

        if not Path(filename).suffix:
            filename += ".json"

        try:
            nodes = [
                [float(x), float(y)]
                for x, y in self.interpolator.nodes
            ]

            data = {
                "version": 1,
                "xmin": float(self.interpolator.xmin),
                "xmax": float(self.interpolator.xmax),
                "ymin": float(self.interpolator.ymin),
                "ymax": float(self.interpolator.ymax),
                "nodes": nodes,
            }

            with open(
                filename,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    data,
                    file,
                    indent=4,
                )

        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                parent,
                "Save nodes",
                f"Unable to save nodes:\n{exc}",
            )
            return

        self.statusBar().showMessage(
            f"Nodes saved: {filename}"
        )

    def load_nodes(self):
        """Load interpolation nodes from a JSON file.

        Notes
        -----
        Nodes are fitted to the current interpolation domain with
        :func:`fit_nodes_to_domain`: absolute intensities are kept and
        nodes outside the domain are dropped. The status bar tells when
        the nodes were adjusted.
        """
        parent = self.interpolation_window or self

        if self.original_image is None:
            QtWidgets.QMessageBox.warning(
                parent,
                "Load nodes",
                "No image is loaded.",
            )
            return

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent,
            "Load colormap nodes",
            "",
            "JSON files (*.json);;All files (*)",
        )

        if not filename:
            return

        try:
            with open(
                filename,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            nodes = data.get("nodes") if isinstance(data, dict) else None

            if not isinstance(nodes, list):
                raise ValueError(
                    "Invalid node list."
                )

            for node in nodes:

                if not isinstance(node, (list, tuple)):
                    raise ValueError(
                        "Invalid node format."
                    )

                if len(node) != 2:
                    raise ValueError(
                        "Each node must contain x and y."
                    )

            fitted, adjusted = fit_nodes_to_domain(
                nodes,
                self.interpolator.xmin,
                self.interpolator.xmax,
                self.interpolator.ymin,
                self.interpolator.ymax,
            )

            # --------------------------------------------------------------
            # Restore nodes (emits nodes_changed -> update_image)
            # --------------------------------------------------------------

            self.interpolator.set_nodes(fitted)

        except Exception as exc:
            QtWidgets.QMessageBox.warning(
                parent,
                "Load nodes",
                f"Unable to load nodes:\n{exc}",
            )
            return

        message = f"Nodes loaded: {filename}"

        if adjusted:
            message += " (adjusted to the current interpolation domain)"

        self.statusBar().showMessage(message)

    # ======================================================================
    # Theme
    # ======================================================================

    def apply_theme(
        self,
        theme: "_theme.Theme",
    ) -> None:
        """Apply a theme to the custom-painted plots of the window.

        Parameters
        ----------
        theme : Theme
            Theme from :mod:`theme`.

        Notes
        -----
        Standard widgets follow the application stylesheet set by
        :func:`theme.apply_theme`; only the plots (profiles, histogram,
        interpolation curve) and the colors set by the window itself
        (custom-interpolation indicator) need this call.
        """
        self._theme = theme

        self._update_interpolation_indicator()

        _theme.style_plot_widgets(
            (
                self.horizontal_profile,
                self.vertical_profile,
                self.histogram,
                self.interpolator,
            ),
            theme,
        )