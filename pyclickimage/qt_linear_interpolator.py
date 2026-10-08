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

from typing import Callable, Iterable

import numpy as np

from PyQt5.QtCore import QPointF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget


def interpolate(
    values: np.ndarray,
    nodes,
) -> np.ndarray:
    """Apply piecewise-linear interpolation to an ND-array.

    Parameters
    ----------
    values : numpy.ndarray
        Floating-point NumPy array containing x-coordinates.

    nodes : sequence
        Interpolation nodes as ``(x, y)`` pairs.

    Returns
    -------
    numpy.ndarray
        Floating-point array with the same shape as ``values``.
        Values inside the interpolation domain are linearly interpolated.
        Values outside the interpolation domain are replaced by NaN.
    """

    if not isinstance(values, np.ndarray) or not np.issubdtype(
        values.dtype,
        np.floating,
    ):
        raise TypeError(
            "values must be a floating-point numpy.ndarray."
        )

    nodes = np.asarray(nodes, dtype=float)

    if nodes.ndim != 2 or nodes.shape[1] != 2:
        raise ValueError(
            "nodes must be an array of shape (N, 2)."
        )

    if len(nodes) < 2:
        raise ValueError(
            "At least two interpolation nodes are required."
        )

    if any(nodes[k, 0] >= nodes[k+1,0] for k in range(0,len(nodes)-1)):
        raise ValueError(
            "nodes must be ordered along the x-axis."
        )

    xmin = nodes[0, 0]
    xmax = nodes[-1, 0]

    result = np.full(
        values.shape,
        np.nan,
        dtype=float,
    )

    mask = (
        (values >= xmin)
        & (values <= xmax)
    )

    if np.any(mask):
        result[mask] = np.interp(
            values[mask],
            nodes[:, 0],
            nodes[:, 1],
        )

    return result


class QtLinearInterpolator(QWidget):
    """Interactive piecewise-linear interpolation widget.

    The widget displays a piecewise-linear curve defined by nodes whose
    coordinates are constrained to the
    ``[xmin, xmax] × [ymin, ymax]`` domain.

    The widget provides:

    - interactive node creation, translation and removal;
    - major and minor grid lines;
    - X and Y axes;
    - configurable tick labels;
    - configurable X and Y axis titles;
    - configurable value formatters for both axes;
    - configurable colors, fonts and line widths;
    - configurable margins around the plotting area.

    End nodes are always present and cannot be removed. Interior nodes can
    be created with a left-button double click, moved by dragging and
    removed with a right-button click.

    Parameters
    ----------
    xmin : float
        Minimum x-coordinate of the interpolation domain.
    xmax : float
        Maximum x-coordinate of the interpolation domain.
    ymin : float
        Minimum y-coordinate of the interpolation range.
    ymax : float
        Maximum y-coordinate of the interpolation range.
    parent : QWidget, optional
        Parent Qt widget.


    Notes
    -----
    Nodes are indexed by their position in the internal node sequence,
    starting at ``0``. The first and last nodes are always the mandatory
    endpoint nodes and therefore cannot be removed.

    Interior nodes may be added, removed or moved. Node indices may
    change after an insertion or removal, so indices should only be
    considered stable until the next modification of the node
    configuration.

    The first and last nodes always have fixed X-coordinates equal to
    ``xmin`` and ``xmax`` respectively. To fix X-coordinate (respectively Y-coordinate), 
    disable ``allow_drag_x``. The Y-coordinates
    remain constrained to ``[ymin, ymax]``.

    Node-related signals report the index at the time of the
    corresponding operation.


    Signals
    -------
    nodes_changed : pyqtSignal()
        Emitted when the node configuration changes.

        The signal is emitted immediately after a node is created or
        removed, and when a node translation is finished.

    node_added : pyqtSignal(int, float, float)
        Emitted when an interior node is added.

        Parameters are the node index, x-coordinate and y-coordinate.

    node_removed : pyqtSignal(int, float, float)
        Emitted when an interior node is removed.

        Parameters are the node index, x-coordinate and y-coordinate
        of the removed node.

    node_moved : pyqtSignal(int, float, float, float, float)
        Emitted when a node has finished being moved.

        Parameters are the node index, old x-coordinate, old
        y-coordinate, new x-coordinate and new y-coordinate.
    """

    nodes_changed = pyqtSignal()

    node_added = pyqtSignal(int, float, float)
    node_removed = pyqtSignal(int, float, float)
    node_moved = pyqtSignal(int, float, float, float, float)

    def __init__(
        self,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the interpolation widget.

        Parameters
        ----------
        xmin : float
            Minimum x-coordinate of the interpolation domain.
        xmax : float
            Maximum x-coordinate of the interpolation domain.
        ymin : float
            Minimum y-coordinate allowed for interpolation nodes.
        ymax : float
            Maximum y-coordinate allowed for interpolation nodes.
        parent : QWidget, optional
            Parent Qt widget.

        Raises
        ------
        ValueError
            If ``xmin >= xmax`` or ``ymin >= ymax``.
        """
        super().__init__(parent)

        self._xmin = float(xmin)
        self._xmax = float(xmax)
        self._ymin = float(ymin)
        self._ymax = float(ymax)
        self._validate_bounds()

        self._nodes: list[tuple[float, float]] = [
            (self._xmin, self._ymin),
            (self._xmax, self._ymax),
        ]

        self._dragged_node: int | None = None
        self._allow_drag_x = True
        self._allow_drag_y = True

        # Geometry
        self._margin_left = 45
        self._margin_top = 45
        self._margin_right = 45
        self._margin_bottom = 45
        self._node_radius = 5
        self._node_tolerance = 9

        # Colors
        self._background_color = self.palette().base().color()
        self._border_color = self.palette().mid().color()
        self._curve_color = self.palette().highlight().color()
        self._node_color = self.palette().highlight().color()

        self._grid_color = QColor(210, 210, 210)
        self._minor_grid_color = QColor(235, 235, 235)
        self._axis_color = QColor(80, 80, 80)
        self._text_color = QColor(80, 80, 80)

        # Background of the mouse-coordinate box.
        self._coordinate_background_color = QColor(255, 255, 255, 220)

        # Line widths
        self._border_width = 1
        self._curve_width = 2
        self._grid_width = 1
        self._minor_grid_width = 1
        self._axis_width = 1
        self._tick_width = 1
        self._tick_length = 4

        # Font
        self._font = QFont()
        self._font.setPointSize(8)

        # Grid
        self._grid_x = 5
        self._grid_y = 5
        self._minor_grid = 0

        # Visibility
        self._view_xmin = self._xmin
        self._view_xmax = self._xmax
        self._view_ymin = self._ymin
        self._view_ymax = self._ymax

        self._show_grid = True
        self._show_minor_grid = False
        self._show_axes = True
        self._show_ticks = True
        self._show_labels = True

        self._mouse_position: QPointF | None = None
        self._show_mouse_coordinates = True
        self.setMouseTracking(self._show_mouse_coordinates)

        # Axis titles
        self._x_title = ""
        self._y_title = ""

        # Axis ticks
        self._x_ticks = None
        self._y_ticks = None

        # Axis formatters
        self._x_formatter: Callable[[float], str] = (
            lambda value: f"{value:g}"
        )
        self._y_formatter: Callable[[float], str] = (
            lambda value: f"{value:g}"
        )

        self.setMinimumSize(120, 80)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    # ==================================================================
    # Geometry / domain
    # ==================================================================

    @property
    def xmin(self) -> float:
        """Minimum x-coordinate of the interpolation domain.

        Returns
        -------
        float
            Minimum x-coordinate. The first interpolation node always has
            this x-coordinate.
        """
        return self._xmin

    @xmin.setter
    def xmin(self, value: float) -> None:
        """Set the minimum x-coordinate of the interpolation domain.

        Parameters
        ----------
        value : float
            New minimum x-coordinate.

        Raises
        ------
        ValueError
            If ``value >= xmax`` or if an existing interior node would
            become invalid.

        Notes
        -----
        Setting ``xmin`` also updates ``view_xmin`` to the same value.

        If a different view minimum is desired, ``view_xmin`` must therefore
        be modified *after* setting ``xmin``.

        Examples
        --------
        Set the interpolation domain and keep the complete domain visible::

            widget.xmin = 100
            widget.xmax = 500

        Set the interpolation domain but display only a portion of it::

            widget.xmin = 100
            widget.view_xmin = 200
        """
        value = float(value)

        if value >= self._xmax:
            raise ValueError(
                "xmin must be smaller than xmax."
            )

        if any(x <= value for x, _ in self._nodes[1:]):
            raise ValueError(
                "xmin would invalidate an existing node."
            )

        self._xmin = value
        self._nodes[0] = (
            value,
            self._nodes[0][1],
        )

        # Changing the interpolation domain also resets the
        # corresponding view boundary.
        self._view_xmin = value

        self.update()

    @property
    def xmax(self) -> float:
        """Maximum x-coordinate of the interpolation domain.

        Returns
        -------
        float
            Maximum x-coordinate. The last interpolation node always has
            this x-coordinate.
        """
        return self._xmax

    @xmax.setter
    def xmax(self, value: float) -> None:
        """Set the maximum x-coordinate of the interpolation domain.

        Parameters
        ----------
        value : float
            New maximum x-coordinate.

        Raises
        ------
        ValueError
            If ``value <= xmin`` or if an existing interior node would
            become invalid.

        Notes
        -----
        Setting ``xmax`` also updates ``view_xmax`` to the same value.

        If a different view maximum is desired, ``view_xmax`` must therefore
        be modified *after* setting ``xmax``.
        """
        value = float(value)

        if value <= self._xmin:
            raise ValueError(
                "xmax must be greater than xmin."
            )

        if any(x >= value for x, _ in self._nodes[:-1]):
            raise ValueError(
                "xmax would invalidate an existing node."
            )

        self._xmax = value
        self._nodes[-1] = (
            value,
            self._nodes[-1][1],
        )

        # Changing the interpolation domain also resets the
        # corresponding view boundary.
        self._view_xmax = value

        self.update()

    @property
    def ymin(self) -> float:
        """Minimum y-coordinate allowed for interpolation nodes.

        Returns
        -------
        float
            Minimum allowed y-coordinate.
        """
        return self._ymin

    @ymin.setter
    def ymin(self, value: float) -> None:
        """Set the minimum y-coordinate of the interpolation range.

        Notes
        -----
        Setting ``ymin`` also updates ``view_ymin`` to the same value.
        If a different view minimum is desired, ``view_ymin`` must be
        modified after setting ``ymin``.
        """
        value = float(value)

        if value >= self._ymax:
            raise ValueError(
                "ymin must be smaller than ymax."
            )

        if any(y < value for _, y in self._nodes[1:-1]):
            raise ValueError(
                "ymin would invalidate an existing node."
            )

        self._ymin = value
        self._nodes[0] = (
            self._nodes[0][0],
            value,
        )

        # Changing the interpolation range also resets the view.
        self._view_ymin = value

        self.update()

    @property
    def ymax(self) -> float:
        """Maximum y-coordinate allowed for interpolation nodes.

        Returns
        -------
        float
            Maximum allowed y-coordinate.
        """
        return self._ymax

    @ymax.setter
    def ymax(self, value: float) -> None:
        """Set the maximum y-coordinate of the interpolation range.

        Notes
        -----
        Setting ``ymax`` also updates ``view_ymax`` to the same value.
        If a different view maximum is desired, ``view_ymax`` must be
        modified after setting ``ymax``.
        """
        value = float(value)

        if value <= self._ymin:
            raise ValueError(
                "ymax must be greater than ymin."
            )

        if any(y > value for _, y in self._nodes[1:-1]):
            raise ValueError(
                "ymax would invalidate an existing node."
            )

        self._ymax = value
        self._nodes[-1] = (
            self._nodes[-1][0],
            value,
        )

        # Changing the interpolation range also resets the view.
        self._view_ymax = value

        self.update()


    # ==================================================================
    # Geometry / view
    # ==================================================================

    @property
    def view_xmin(self) -> float:
        """Minimum x-coordinate currently visible in the plot.

        Returns
        -------
        float
            Minimum x-coordinate of the current view.
        """
        return self._view_xmin


    @view_xmin.setter
    def view_xmin(self, value: float) -> None:
        """Set the minimum x-coordinate currently visible in the plot.

        Parameters
        ----------
        value : float
            New minimum x-coordinate of the view.

        Raises
        ------
        ValueError
            If ``value >= view_xmax`` or if the value lies outside
            ``[xmin, xmax]``.

        Notes
        -----
        Changing ``view_xmin`` only changes the visible portion of the plot.
        It does not modify the interpolation domain.

        In contrast, setting :attr:`xmin` also updates ``view_xmin``.
        Therefore, if a different view is desired after changing ``xmin``,
        ``view_xmin`` must be set afterwards.
        """
        value = float(value)

        if value >= self._view_xmax:
            raise ValueError(
                "view_xmin must satisfy "
                "view_xmin < view_xmax."
            )

        self._view_xmin = value
        self.update()


    @property
    def view_xmax(self) -> float:
        """Maximum x-coordinate currently visible in the plot.

        Returns
        -------
        float
            Maximum x-coordinate of the current view.
        """
        return self._view_xmax


    @view_xmax.setter
    def view_xmax(self, value: float) -> None:
        """Set the maximum x-coordinate currently visible in the plot.

        Parameters
        ----------
        value : float
            New maximum x-coordinate of the view.

        Raises
        ------
        ValueError
            If ``value <= view_xmin`` or if the value lies outside
            ``[xmin, xmax]``.

        Notes
        -----
        Changing ``view_xmax`` only changes the visible portion of the plot.
        It does not modify the interpolation domain.

        In contrast, setting :attr:`xmax` also updates ``view_xmax``.
        Therefore, if a different view is desired after changing ``xmax``,
        ``view_xmax`` must be set afterwards.
        """
        value = float(value)

        if value <= self._view_xmin:
            raise ValueError(
                "view_xmax must satisfy "
                "view_xmin < view_xmax."
            )

        self._view_xmax = value
        self.update()


    @property
    def view_ymin(self) -> float:
        """Minimum y-coordinate currently visible in the plot.

        Returns
        -------
        float
            Minimum y-coordinate of the current view.
        """
        return self._view_ymin


    @view_ymin.setter
    def view_ymin(self, value: float) -> None:
        """Set the minimum y-coordinate currently visible in the plot.

        Parameters
        ----------
        value : float
            New minimum y-coordinate of the view.

        Raises
        ------
        ValueError
            If ``value >= view_ymax`` or if the value lies outside
            ``[ymin, ymax]``.

        Notes
        -----
        Changing ``view_ymin`` only changes the visible portion of the plot.
        It does not modify the interpolation range.

        In contrast, setting :attr:`ymin` also updates ``view_ymin``.
        Therefore, if a different view is desired after changing ``ymin``,
        ``view_ymin`` must be set afterwards.
        """
        value = float(value)

        if value < self._ymin or value >= self._view_ymax:
            raise ValueError(
                "view_ymin must satisfy "
                "ymin <= view_ymin < view_ymax."
            )

        self._view_ymin = value
        self.update()


    @property
    def view_ymax(self) -> float:
        """Maximum y-coordinate currently visible in the plot.

        Returns
        -------
        float
            Maximum y-coordinate of the current view.
        """
        return self._view_ymax


    @view_ymax.setter
    def view_ymax(self, value: float) -> None:
        """Set the maximum y-coordinate currently visible in the plot.

        Parameters
        ----------
        value : float
            New maximum y-coordinate of the view.

        Raises
        ------
        ValueError
            If ``value <= view_ymin`` or if the value lies outside
            ``[ymin, ymax]``.

        Notes
        -----
        Changing ``view_ymax`` only changes the visible portion of the plot.
        It does not modify the interpolation range.

        In contrast, setting :attr:`ymax` also updates ``view_ymax``.
        Therefore, if a different view is desired after changing ``ymax``,
        ``view_ymax`` must be set afterwards.
        """
        value = float(value)

        if value > self._ymax or value <= self._view_ymin:
            raise ValueError(
                "view_ymax must satisfy "
                "view_ymin < view_ymax <= ymax."
            )

        self._view_ymax = value
        self.update()

    @property
    def margin_left(self) -> int:
        """Left margin around the plotting area.

        Returns
        -------
        int
            Margin in pixels between the left edge of the widget and the
            plotting area. This margin also provides space for Y-axis labels
            and the Y-axis title.
        """
        return self._margin_left

    @margin_left.setter
    def margin_left(self, value: int) -> None:
        """Set the left margin around the plotting area.

        Parameters
        ----------
        value : int
            Margin in pixels between the left edge of the widget and the
            plotting area.

        Raises
        ------
        ValueError
            If ``value`` is negative.
        """
        value = int(value)

        if value < 0:
            raise ValueError("margin_left must be non-negative.")

        self._margin_left = value
        self.update()


    @property
    def margin_top(self) -> int:
        """Top margin around the plotting area.

        Returns
        -------
        int
            Margin in pixels between the top edge of the widget and the
            plotting area.
        """
        return self._margin_top

    @margin_top.setter
    def margin_top(self, value: int) -> None:
        """Set the top margin around the plotting area.

        Parameters
        ----------
        value : int
            Margin in pixels between the top edge of the widget and the
            plotting area.

        Raises
        ------
        ValueError
            If ``value`` is negative.
        """
        value = int(value)

        if value < 0:
            raise ValueError("margin_top must be non-negative.")

        self._margin_top = value
        self.update()


    @property
    def margin_right(self) -> int:
        """Right margin around the plotting area.

        Returns
        -------
        int
            Margin in pixels between the right edge of the plotting area and
            the right edge of the widget.
        """
        return self._margin_right

    @margin_right.setter
    def margin_right(self, value: int) -> None:
        """Set the right margin around the plotting area.

        Parameters
        ----------
        value : int
            Margin in pixels between the right edge of the plotting area and
            the right edge of the widget.

        Raises
        ------
        ValueError
            If ``value`` is negative.
        """
        value = int(value)

        if value < 0:
            raise ValueError("margin_right must be non-negative.")

        self._margin_right = value
        self.update()


    @property
    def margin_bottom(self) -> int:
        """Bottom margin around the plotting area.

        Returns
        -------
        int
            Margin in pixels between the bottom edge of the plotting area and
            the bottom edge of the widget. This margin also provides space for
            X-axis labels and the X-axis title.
        """
        return self._margin_bottom

    @margin_bottom.setter
    def margin_bottom(self, value: int) -> None:
        """Set the bottom margin around the plotting area.

        Parameters
        ----------
        value : int
            Margin in pixels between the bottom edge of the plotting area and
            the bottom edge of the widget.

        Raises
        ------
        ValueError
            If ``value`` is negative.
        """
        value = int(value)

        if value < 0:
            raise ValueError("margin_bottom must be non-negative.")

        self._margin_bottom = value
        self.update()

    # ==================================================================
    # Interpolation
    # ==================================================================

    def interpolate(self, values: np.ndarray) -> np.ndarray:
        """Apply the piecewise-linear interpolation to an ND-array.

        Parameters
        ----------
        values : numpy.ndarray
            Floating-point NumPy array containing x-coordinates. The
            input array may have any number of dimensions.

        Returns
        -------
        numpy.ndarray
            Floating-point array with the same shape as ``values``.
            Values inside ``[xmin, xmax]`` are linearly interpolated.
            Values outside the interpolation domain are replaced by
            ``NaN``.

        Raises
        ------
        TypeError
            If ``values`` is not a floating-point NumPy array.
        """
        return interpolate(values, self.nodes)
        
    # ==================================================================
    # Appearance - colors
    # ==================================================================

    @staticmethod
    def _color_property(name: str):
        """Create a QColor property backed by a private attribute."""
        def getter(self):
            return QColor(getattr(self, f"_{name}"))

        def setter(self, value):
            setattr(self, f"_{name}", QColor(value))
            self.update()

        return property(getter, setter)

    background_color = _color_property("background_color")
    border_color = _color_property("border_color")
    curve_color = _color_property("curve_color")
    node_color = _color_property("node_color")
    grid_color = _color_property("grid_color")
    minor_grid_color = _color_property("minor_grid_color")
    axis_color = _color_property("axis_color")
    text_color = _color_property("text_color")
    coordinate_background_color = _color_property(
        "coordinate_background_color"
    )

    # ==================================================================
    # Appearance - font
    # ==================================================================

    @property
    def font(self) -> QFont:
        """Font used for axis tick labels and titles.

        Returns
        -------
        QFont
            Copy of the font currently used for axis text.
        """
        return QFont(self._font)

    @font.setter
    def font(self, value: QFont) -> None:
        """Set the font used for axis text.

        Parameters
        ----------
        value : QFont
            Font used for tick labels and axis titles.

        Raises
        ------
        TypeError
            If ``value`` is not a :class:`QFont`.
        """
        if not isinstance(value, QFont):
            raise TypeError("font must be a QFont.")

        self._font = QFont(value)
        self.update()

    # ==================================================================
    # Appearance - axis titles
    # ==================================================================

    @property
    def x_title(self) -> str:
        """Title displayed below the X axis.

        Returns
        -------
        str
            X-axis title. An empty string disables the title.
        """
        return self._x_title

    @x_title.setter
    def x_title(self, value: str) -> None:
        """Set the X-axis title.

        Parameters
        ----------
        value : str
            Text displayed below the X axis. Set to an empty string to
            hide the title.
        """
        self._x_title = str(value)
        self.update()

    @property
    def y_title(self) -> str:
        """Title displayed beside the Y axis.

        Returns
        -------
        str
            Y-axis title. An empty string disables the title.
        """
        return self._y_title

    @y_title.setter
    def y_title(self, value: str) -> None:
        """Set the Y-axis title.

        Parameters
        ----------
        value : str
            Text displayed beside the Y axis. Set to an empty string to
            hide the title.
        """
        self._y_title = str(value)
        self.update()

    # ==================================================================
    # Appearance - axis formatters
    # ==================================================================

    @property
    def x_ticks(self) -> tuple[float, ...] | None:
        """X-axis tick positions.

        Returns
        -------
        tuple of float or None
            Explicit x-axis tick values. If ``None``, ticks are generated
            automatically from ``xmin``, ``xmax`` and ``grid_x``.
        """
        return None if self._x_ticks is None else tuple(self._x_ticks)


    def set_x_ticks(self, ticks: Iterable[float] | None) -> None:
        """Set explicit x-axis tick positions.

        Parameters
        ----------
        ticks : iterable of float or None
            Tick values in data coordinates. Values must lie within
            ``[xmin, xmax]``. If ``None``, x-axis ticks are generated
            automatically.
        """
        if ticks is None:
            self._x_ticks = None
        else:
            ticks = np.asarray(list(ticks), dtype=float)

            if ticks.ndim != 1 or len(ticks) == 0:
                raise ValueError("x ticks must be a non-empty 1D sequence.")

            if np.any(~np.isfinite(ticks)):
                raise ValueError("x ticks must contain finite values.")

            if np.any(np.diff(ticks) <= 0):
                raise ValueError("x ticks must be strictly increasing.")

            if np.any(ticks < self._xmin) or np.any(ticks > self._xmax):
                raise ValueError("x ticks must lie within [xmin, xmax].")

            self._x_ticks = ticks

        self.update()


    @property
    def y_ticks(self) -> tuple[float, ...] | None:
        """Y-axis tick positions.

        Returns
        -------
        tuple of float or None
            Explicit y-axis tick values. If ``None``, ticks are generated
            automatically from ``ymin``, ``ymax`` and ``grid_y``.
        """
        return None if self._y_ticks is None else tuple(self._y_ticks)


    def set_y_ticks(self, ticks: Iterable[float] | None) -> None:
        """Set explicit y-axis tick positions.

        Parameters
        ----------
        ticks : iterable of float or None
            Tick values in data coordinates. Values must lie within
            ``[ymin, ymax]``. If ``None``, y-axis ticks are generated
            automatically.
        """
        if ticks is None:
            self._y_ticks = None
        else:
            ticks = np.asarray(list(ticks), dtype=float)

            if ticks.ndim != 1 or len(ticks) == 0:
                raise ValueError("y ticks must be a non-empty 1D sequence.")

            if np.any(~np.isfinite(ticks)):
                raise ValueError("y ticks must contain finite values.")

            if np.any(np.diff(ticks) <= 0):
                raise ValueError("y ticks must be strictly increasing.")

            if np.any(ticks < self._ymin) or np.any(ticks > self._ymax):
                raise ValueError("y ticks must lie within [ymin, ymax].")

            self._y_ticks = ticks

        self.update()

    @property
    def x_formatter(self) -> Callable[[float], str]:
        """Formatter used to convert X tick values to text.

        The callable receives one floating-point x-coordinate and must
        return the text that should be displayed on the X axis.

        Returns
        -------
        Callable[[float], str]
            Current X-axis formatter.

        Examples
        --------
        >>> widget.x_formatter = lambda x: f"{round(x / 1000)}"
        """
        return self._x_formatter

    @x_formatter.setter
    def x_formatter(
        self,
        value: Callable[[float], str],
    ) -> None:
        """Set the X-axis tick formatter.

        Parameters
        ----------
        value : callable
            Callable receiving one float and returning a string.

        Raises
        ------
        TypeError
            If ``value`` is not callable.
        """
        if not callable(value):
            raise TypeError(
                "x_formatter must be callable."
            )

        self._x_formatter = value
        self.update()

    @property
    def y_formatter(self) -> Callable[[float], str]:
        """Formatter used to convert Y tick values to text.

        The callable receives one floating-point y-coordinate and must
        return the text that should be displayed on the Y axis.

        Returns
        -------
        Callable[[float], str]
            Current Y-axis formatter.

        Examples
        --------
        >>> widget.y_formatter = lambda y: f"{y:.1f}"
        """
        return self._y_formatter

    @y_formatter.setter
    def y_formatter(
        self,
        value: Callable[[float], str],
    ) -> None:
        """Set the Y-axis tick formatter.

        Parameters
        ----------
        value : callable
            Callable receiving one float and returning a string.

        Raises
        ------
        TypeError
            If ``value`` is not callable.
        """
        if not callable(value):
            raise TypeError(
                "y_formatter must be callable."
            )

        self._y_formatter = value
        self.update()

    # ==================================================================
    # Appearance - integer properties
    # ==================================================================

    @staticmethod
    def _int_property(name: str):
        """Create a non-negative integer Qt property."""
        def getter(self):
            return getattr(self, f"_{name}")

        def setter(self, value):
            value = int(value)

            if value < 0:
                raise ValueError(
                    f"{name} must be non-negative."
                )

            setattr(self, f"_{name}", value)
            self.update()

        return property(getter, setter)

    node_radius = _int_property("node_radius")
    node_tolerance = _int_property("node_tolerance")
    border_width = _int_property("border_width")
    curve_width = _int_property("curve_width")
    grid_width = _int_property("grid_width")
    minor_grid_width = _int_property("minor_grid_width")
    axis_width = _int_property("axis_width")
    tick_width = _int_property("tick_width")
    tick_length = _int_property("tick_length")

    # ==================================================================
    # Appearance - grid properties
    # ==================================================================

    @property
    def grid_x(self) -> int:
        """Number of major grid divisions along the X axis.

        Returns
        -------
        int
            Number of equal divisions between ``xmin`` and ``xmax``.
            This value also determines the number of major X-axis
            intervals and X-axis tick intervals.
        """
        return self._grid_x

    @grid_x.setter
    def grid_x(self, value: int) -> None:
        """Set the number of major X-axis divisions.

        Parameters
        ----------
        value : int
            Number of major divisions. Must be strictly positive.

        Raises
        ------
        ValueError
            If ``value < 1``.
        """
        value = int(value)

        if value < 1:
            raise ValueError(
                "grid_x must be greater than zero."
            )

        self._grid_x = value
        self.update()

    @property
    def grid_y(self) -> int:
        """Number of major grid divisions along the Y axis.

        Returns
        -------
        int
            Number of equal divisions between ``ymin`` and ``ymax``.
            This value also determines the number of major Y-axis
            intervals and Y-axis tick intervals.
        """
        return self._grid_y

    @grid_y.setter
    def grid_y(self, value: int) -> None:
        """Set the number of major Y-axis divisions.

        Parameters
        ----------
        value : int
            Number of major divisions. Must be strictly positive.

        Raises
        ------
        ValueError
            If ``value < 1``.
        """
        value = int(value)

        if value < 1:
            raise ValueError(
                "grid_y must be greater than zero."
            )

        self._grid_y = value
        self.update()

    @property
    def minor_grid(self) -> int:
        """Number of minor subdivisions between major grid lines.

        Returns
        -------
        int
            Number of minor intervals inserted into each major interval.
            A value of ``0`` disables minor grid lines.
        """
        return self._minor_grid

    @minor_grid.setter
    def minor_grid(self, value: int) -> None:
        """Set the number of minor grid subdivisions.

        Parameters
        ----------
        value : int
            Number of minor subdivisions per major interval.
            ``0`` disables minor grid lines.

        Raises
        ------
        ValueError
            If ``value < 0``.
        """
        value = int(value)

        if value < 0:
            raise ValueError(
                "minor_grid must be non-negative."
            )

        self._minor_grid = value
        self.update()

    # ==================================================================
    # Appearance - visibility
    # ==================================================================

    @staticmethod
    def _bool_property(name: str):
        """Create a boolean Qt property."""
        def getter(self):
            return getattr(self, f"_{name}")

        def setter(self, value):
            setattr(self, f"_{name}", bool(value))
            self.update()

        return property(getter, setter)

    show_grid = _bool_property("show_grid")
    show_minor_grid = _bool_property("show_minor_grid")
    show_axes = _bool_property("show_axes")
    show_ticks = _bool_property("show_ticks")
    show_labels = _bool_property("show_labels")


    # ==================================================================
    # Nodes
    # ==================================================================

    allow_drag_x = _bool_property("allow_drag_x")
    allow_drag_y = _bool_property("allow_drag_y")

    @property
    def nodes(self) -> tuple[tuple[float, float], ...]:
        """Current interpolation nodes.

        Returns
        -------
        tuple of tuple of float
            Nodes represented as ``(x, y)`` pairs and sorted by increasing
            x-coordinate. The first and last nodes are always located at
            ``xmin`` and ``xmax`` respectively.
        """
        return tuple(self._nodes)

    def set_nodes(
        self,
        nodes: Iterable[tuple[float, float]],
    ) -> None:
        """Replace the current interpolation nodes.

        Parameters
        ----------
        nodes : iterable of tuple of float
            Iterable containing ``(x, y)`` node coordinates. The first
            node must use ``xmin`` and the last node must use ``xmax``.

        Raises
        ------
        ValueError
            If fewer than two nodes are supplied, if the first or last
            node does not correspond to the domain limits, if x-values
            are not strictly increasing, or if any coordinate is outside
            the interpolation domain.
        """
        nodes = [(float(x), float(y)) for x, y in nodes]

        if len(nodes) < 2:
            raise ValueError("At least two nodes are required.")

        if (
            nodes[0][0] != self._xmin
            or nodes[-1][0] != self._xmax
        ):
            raise ValueError(
                "First and last nodes must match xmin and xmax."
            )

        xs = np.array([x for x, _ in nodes])
        ys = np.array([y for _, y in nodes])

        if np.any(np.diff(xs) <= 0):
            raise ValueError(
                "Node x-coordinates must be strictly increasing."
            )

        if np.any(xs < self._xmin) or np.any(xs > self._xmax):
            raise ValueError(
                "Node x-coordinate outside interpolation bounds."
            )

        if np.any(ys < self._ymin) or np.any(ys > self._ymax):
            raise ValueError(
                "Node y-coordinate outside interpolation bounds."
            )

        self._nodes = nodes
        self.nodes_changed.emit()
        self.update()

    def reset(self) -> None:
        """Remove all interior nodes.

        The two mandatory end nodes are restored to
        ``(xmin, ymin)`` and ``(xmax, ymax)``.

        The :attr:`nodes_changed` signal is emitted after the reset.
        """
        self._nodes = [
            (self._xmin, self._ymin),
            (self._xmax, self._ymax),
        ]

        self.nodes_changed.emit()
        self.update()


    def set_domain(
        self,
        xmin: float,
        xmax: float,
        ymin: float | None = None,
        ymax: float | None = None,
        keep_nodes: bool = False,
    ) -> None:
        """Replace the interpolation domain in a single operation.

        The individual :attr:`xmin`, :attr:`xmax`, :attr:`ymin` and
        :attr:`ymax` setters validate each bound against the *current*
        other bound and nodes, so their call order matters. This method
        validates the new bounds together and has no ordering
        constraint.

        Parameters
        ----------
        xmin, xmax : float
            New x-domain. Must satisfy ``xmin < xmax``.
        ymin, ymax : float, optional
            New y-range. ``None`` keeps the current value. The final
            range must satisfy ``ymin < ymax``.
        keep_nodes : bool, default=False
            If ``False``, the nodes are reset to ``(xmin, ymin)`` and
            ``(xmax, ymax)``.

            If ``True``, interior nodes strictly inside the new x-domain
            are kept (others are dropped), end nodes are moved to the new
            x-bounds and every y-coordinate is clipped to the new y-range.

        Raises
        ------
        ValueError
            If the bounds are not finite or not strictly increasing.

        Notes
        -----
        The view (``view_*``) is reset to the new domain.
        :attr:`nodes_changed` is emitted once.
        """
        xmin = float(xmin)
        xmax = float(xmax)
        ymin = self._ymin if ymin is None else float(ymin)
        ymax = self._ymax if ymax is None else float(ymax)

        if not all(np.isfinite([xmin, xmax, ymin, ymax])):
            raise ValueError("Domain bounds must be finite.")

        if xmin >= xmax:
            raise ValueError("xmin must be smaller than xmax.")

        if ymin >= ymax:
            raise ValueError("ymin must be smaller than ymax.")

        if keep_nodes:
            first_y = float(np.clip(self._nodes[0][1], ymin, ymax))
            last_y = float(np.clip(self._nodes[-1][1], ymin, ymax))

            interior = [
                (x, float(np.clip(y, ymin, ymax)))
                for x, y in self._nodes[1:-1]
                if xmin < x < xmax
            ]

            nodes = [(xmin, first_y), *interior, (xmax, last_y)]

        else:
            nodes = [(xmin, ymin), (xmax, ymax)]

        self._xmin = xmin
        self._xmax = xmax
        self._ymin = ymin
        self._ymax = ymax
        self._nodes = nodes

        self._view_xmin = xmin
        self._view_xmax = xmax
        self._view_ymin = ymin
        self._view_ymax = ymax

        # Explicit ticks may lie outside the new domain.
        self._x_ticks = None
        self._y_ticks = None

        self.nodes_changed.emit()
        self.update()

    def set_view(
        self,
        xmin: float | None = None,
        xmax: float | None = None,
        ymin: float | None = None,
        ymax: float | None = None,
    ) -> None:
        """Set the visible range in a single operation.

        Same purpose as :meth:`set_domain` for the ``view_*``
        properties: bounds are validated together, so they can be given
        in any order.

        Parameters
        ----------
        xmin, xmax : float, optional
            New visible x-range. ``None`` keeps the current value.
        ymin, ymax : float, optional
            New visible y-range. ``None`` keeps the current value.

        Raises
        ------
        ValueError
            If the resulting bounds are not finite or not strictly
            increasing.

        Notes
        -----
        Only the display is affected; the interpolation is unchanged.
        """
        xmin = self._view_xmin if xmin is None else float(xmin)
        xmax = self._view_xmax if xmax is None else float(xmax)
        ymin = self._view_ymin if ymin is None else float(ymin)
        ymax = self._view_ymax if ymax is None else float(ymax)

        if not all(np.isfinite([xmin, xmax, ymin, ymax])):
            raise ValueError("View bounds must be finite.")

        if xmin >= xmax or ymin >= ymax:
            raise ValueError(
                "View bounds must satisfy min < max on both axes."
            )

        self._view_xmin = xmin
        self._view_xmax = xmax
        self._view_ymin = ymin
        self._view_ymax = ymax

        self.update()

    # ==================================================================
    # Coordinate conversion
    # ==================================================================

    def _validate_bounds(self) -> None:
        """Validate the interpolation domain limits.

        Raises
        ------
        ValueError
            If the minimum bound is greater than or equal to the maximum
            bound on either axis.
        """
        if self._xmin >= self._xmax:
            raise ValueError(
                "xmin must be smaller than xmax."
            )

        if self._ymin >= self._ymax:
            raise ValueError(
                "ymin must be smaller than ymax."
            )

    def _plot_rect(
        self,
    ) -> tuple[float, float, float, float]:
        """Return the plotting rectangle in widget coordinates.

        Returns
        -------
        tuple of float
            Tuple ``(left, top, width, height)`` defining the rectangle
            reserved for the interpolation curve.
        """
        left = float(self._margin_left)
        top = float(self._margin_top)

        return (
            left,
            top,
            max(1.0, self.width() - left - self._margin_right),
            max(1.0, self.height() - top - self._margin_bottom),
        )

    def _to_widget(
        self,
        x: float,
        y: float,
    ) -> QPointF:
        """Convert data coordinates to widget coordinates.

        Parameters
        ----------
        x : float
            Data-space x-coordinate.
        y : float
            Data-space y-coordinate.

        Returns
        -------
        QPointF
            Corresponding position in widget coordinates.
        """
        left, top, width, height = self._plot_rect()

        px = (left + (x - self._view_xmin) / (self._view_xmax - self._view_xmin) * width)
        py = (top + (self._view_ymax - y) / (self._view_ymax - self._view_ymin) * height)

        return QPointF(px, py)

    def _to_data(
        self,
        point: QPointF,
    ) -> tuple[float, float]:
        """Convert widget coordinates to data coordinates.

        Parameters
        ----------
        point : QPointF
            Position in widget coordinates.

        Returns
        -------
        tuple of float
            Corresponding ``(x, y)`` data coordinates.
        """
        left, top, width, height = self._plot_rect()

        x = (self._view_xmin + (point.x() - left) / width * (self._view_xmax - self._view_xmin))
        y = (self._view_ymax - (point.y() - top) / height * (self._view_ymax - self._view_ymin))

        return x, y

    # ==================================================================
    # Node interaction
    # ==================================================================

    def _node_at(
        self,
        position: QPointF,
    ) -> int | None:
        """Find the node closest to a widget position.

        Parameters
        ----------
        position : QPointF
            Mouse position in widget coordinates.

        Returns
        -------
        int or None
            Index of the first node inside the configured node tolerance,
            or ``None`` if no node is close enough.
        """
        tolerance = self._node_tolerance

        for index, (x, y) in enumerate(self._nodes):
            point = self._to_widget(x, y)

            if (
                abs(point.x() - position.x()) <= tolerance
                and abs(point.y() - position.y()) <= tolerance
            ):
                return index

        return None

    def _insert_node(
        self,
        position: QPointF,
    ) -> None:
        """Insert an interpolation node at a widget position.

        The x-coordinate is determined by the mouse position and the
        y-coordinate is clipped to the interpolation range.

        Parameters
        ----------
        position : QPointF
            Mouse position in widget coordinates.
        """
        x, y = self._to_data(position)

        if not self._xmin < x < self._xmax:
            return

        index = np.searchsorted(
            [node_x for node_x, _ in self._nodes],
            x,
        )

        y = float(np.clip(y, self._ymin, self._ymax))
        self._nodes.insert(index, (x, y))

        self.node_added.emit(index, x, y)
        self.nodes_changed.emit()
        self.update()

    def _remove_node(self, index: int) -> None:
        """Remove an interior interpolation node.

        Parameters
        ----------
        index : int
            Index of the node to remove.

        Notes
        -----
        The first and last nodes are mandatory and therefore cannot
        be removed.
        """
        if index in (0, len(self._nodes) - 1):
            return

        x, y = self._nodes[index]
        self._nodes.pop(index)

        self.node_removed.emit(index, x, y)
        self.nodes_changed.emit()
        self.update()

    def _move_node(
        self,
        index: int,
        position: QPointF,
    ) -> None:
        """Move an interpolation node vertically.

        The x-coordinate remains fixed while the y-coordinate is obtained
        from the mouse position and clipped to ``[ymin, ymax]``.

        Parameters
        ----------
        index : int
            Index of the node being moved.
        position : QPointF
            Current mouse position in widget coordinates.
        """
        x, y = self._to_data(position)

        old_x, old_y = self._nodes[index]

        if index in (0, len(self._nodes) - 1):
            allow_x = False
        else:
            allow_x = self._allow_drag_x

        if allow_x:
            lower = self._nodes[index - 1][0]
            upper = self._nodes[index + 1][0]
            x = float(np.clip(x, lower + 1e-12, upper - 1e-12))
        else:
            x = old_x

        if self._allow_drag_y:
            y = float(np.clip(y, self._ymin, self._ymax))
        else:
            y = old_y

        self._nodes[index] = (x, y)
        self.update()

    # ==================================================================
    # Painting
    # ==================================================================

    def _get_ticks(
        self,
        axis: str,
    ) -> np.ndarray:
        """Return tick positions for one axis.

        Parameters
        ----------
        axis : {"x", "y"}
            Axis for which tick positions are requested.

        Returns
        -------
        numpy.ndarray
            Tick positions in data coordinates. Explicitly configured ticks
            are returned when available; otherwise, evenly spaced ticks are
            generated from the corresponding interpolation bounds.
        """
        if axis == "x":
            if self._x_ticks is not None:
                return self._x_ticks
            return np.linspace(
                self._view_xmin,
                self._view_xmax,
                self._grid_x + 1,
            )

        if axis == "y":
            if self._y_ticks is not None:
                return self._y_ticks
            return np.linspace(
                self._view_ymin,
                self._view_ymax,
                self._grid_y + 1,
            )

        raise ValueError("axis must be 'x' or 'y'")


    def _draw_grid(self, painter: QPainter) -> None:
        """Draw major and minor grid lines.

        Parameters
        ----------
        painter : QPainter
            Painter used to render the grid.
        """
        left, top, width, height = self._plot_rect()

        x_ticks = self._get_ticks("x")
        y_ticks = self._get_ticks("y")

        if self._show_minor_grid and self._minor_grid:
            painter.setPen(
                QPen(
                    self._minor_grid_color,
                    self._minor_grid_width,
                )
            )

            for ticks, axis in ((x_ticks, "x"), (y_ticks, "y")):
                for start, end in zip(ticks, ticks[1:]):
                    for j in range(1, self._minor_grid + 1):
                        value = start + j * (end - start) / (self._minor_grid + 1)

                        if axis == "x":
                            x = self._to_widget(value, self._ymin).x()
                            painter.drawLine(
                                QPointF(x, top),
                                QPointF(x, top + height),
                            )
                        else:
                            y = self._to_widget(self._xmin, value).y()
                            painter.drawLine(
                                QPointF(left, y),
                                QPointF(left + width, y),
                            )

        if self._show_grid:
            painter.setPen(QPen(self._grid_color, self._grid_width))

            for value in x_ticks[1:-1]:
                x = self._to_widget(value, self._ymin).x()
                painter.drawLine(
                    QPointF(x, top),
                    QPointF(x, top + height),
                )

            for value in y_ticks[1:-1]:
                y = self._to_widget(self._xmin, value).y()
                painter.drawLine(
                    QPointF(left, y),
                    QPointF(left + width, y),
                )



    def _draw_axes(self, painter: QPainter) -> None:
        """Draw axes, ticks, tick labels and axis titles.

        Parameters
        ----------
        painter : QPainter
            Painter used to render the axes.
        """
        if not self._show_axes:
            return

        left, top, width, height = self._plot_rect()
        right, bottom = left + width, top + height

        x_ticks = self._get_ticks("x")
        y_ticks = self._get_ticks("y")

        painter.setPen(QPen(self._axis_color, self._axis_width))

        x0 = self._to_widget(
            np.clip(0, self._view_xmin, self._view_xmax),
            self._ymin,
        ).x()

        y0 = self._to_widget(
            self._xmin,
            np.clip(0, self._view_ymin, self._view_ymax),
        ).y()

        painter.drawLine(
            QPointF(x0, top),
            QPointF(x0, bottom),
        )
        painter.drawLine(
            QPointF(left, y0),
            QPointF(right, y0),
        )

        painter.setFont(self._font)
        fm = painter.fontMetrics()

        if self._show_ticks:
            painter.setPen(QPen(self._axis_color, self._tick_width))

            for value in x_ticks:
                x = self._to_widget(value, self._ymin).x()
                painter.drawLine(
                    QPointF(x, bottom),
                    QPointF(x, bottom + self._tick_length),
                )

            for value in y_ticks:
                y = self._to_widget(self._xmin, value).y()
                painter.drawLine(
                    QPointF(left - self._tick_length, y),
                    QPointF(left, y),
                )

        if self._show_labels:
            painter.setPen(QPen(self._text_color, 1))

            for value in x_ticks:
                x = self._to_widget(value, self._ymin).x()
                text = self._x_formatter(value)

                painter.drawText(
                    int(x - fm.horizontalAdvance(text) / 2),
                    int(bottom + self._tick_length + fm.ascent()),
                    text,
                )

            for value in y_ticks:
                y = self._to_widget(self._xmin, value).y()
                text = self._y_formatter(value)

                painter.drawText(
                    int(
                        left
                        - self._tick_length
                        - fm.horizontalAdvance(text)
                        - 4
                    ),
                    int(y + fm.ascent() / 2),
                    text,
                )

        if self._x_title:
            painter.drawText(
                int(left + (width - fm.horizontalAdvance(self._x_title)) / 2),
                self.height() - max(4, self._margin_bottom // 4),
                self._x_title,
            )

        if self._y_title:
            painter.save()
            painter.translate(
                max(4, self._margin_left // 4),
                top + height / 2,
            )
            painter.rotate(-90)
            painter.drawText(
                int(-fm.horizontalAdvance(self._y_title) / 2),
                0,
                self._y_title,
            )
            painter.restore()


    def paintEvent(self, event) -> None:
        """Paint the interpolation curve and graphical elements.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        left, top, width, height = self._plot_rect()
        rect = (int(left), int(top), int(width), int(height))

        painter.fillRect(self.rect(), self._background_color)

        painter.save()
        painter.setClipRect(*rect)
        self._draw_grid(painter)
        painter.restore()

        painter.setPen(QPen(self._border_color, self._border_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(*rect)

        self._draw_axes(painter)
        self._draw_mouse_coordinates(painter)

        points = [self._to_widget(x, y) for x, y in self._nodes]

        painter.setPen(QPen(self._curve_color, self._curve_width))

        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._node_color))

        for point in points:
            painter.drawEllipse(
                point,
                self._node_radius,
                self._node_radius,
            )


    # ==================================================================
    # Mouse events
    # ==================================================================

    def mouseDoubleClickEvent(self, event) -> None:
        """Create an interior node on a left-button double click.

        A node is inserted only when the double-click does not occur
        close enough to an existing node.

        Parameters
        ----------
        event : QMouseEvent
            Qt mouse event.
        """
        if event.button() == Qt.LeftButton:
            if self._node_at(event.pos()) is None:
                self._insert_node(event.pos())

        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        """Start node dragging or remove a node.

        Parameters
        ----------
        event : QMouseEvent
            Qt mouse event.

        Notes
        -----
        A left-button press starts dragging the closest node.

        A right-button press removes the closest interior node.
        """
        index = self._node_at(event.pos())

        if event.button() == Qt.LeftButton and index is not None and (self.allow_drag_x or self.allow_drag_y):
            self._dragged_node = index
            self._drag_start = self._nodes[index]

        elif event.button() == Qt.RightButton and index is not None:
            self._remove_node(index)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Finish an active node drag.

        Parameters
        ----------
        event : QMouseEvent
            Qt mouse event.

        Notes
        -----
        The :attr:`nodes_changed` signal is emitted when the left-button
        drag is finished.
        """
        if (
            event.button() == Qt.LeftButton
            and self._dragged_node is not None
        ):
            index = self._dragged_node
            old_x, old_y = self._drag_start
            new_x, new_y = self._nodes[index]

            self._dragged_node = None

            if (old_x, old_y) != (new_x, new_y):
                self.node_moved.emit(
                    index,
                    old_x,
                    old_y,
                    new_x,
                    new_y,
                )
                self.nodes_changed.emit()

        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        """Update mouse coordinates and handle node dragging."""

        self._mouse_position = QPointF(event.pos())

        if self._dragged_node is not None:
            self._move_node(
                self._dragged_node,
                event.pos(),
            )

        self.update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        """Hide mouse coordinates when leaving the widget."""
        self._mouse_position = None
        self.update()
        super().leaveEvent(event)

    def _draw_mouse_coordinates(self, painter: QPainter) -> None:
        """Draw the current mouse coordinates inside the plot."""
        if not self._show_mouse_coordinates:
            return

        if self._mouse_position is None:
            return

        left, top, width, height = self._plot_rect()

        position = self._mouse_position

        if not (
            left <= position.x() <= left + width
            and top <= position.y() <= top + height
        ):
            return

        x, y = self._to_data(position)

        text = f"x = {self._x_formatter(x)}, y = {self._y_formatter(y)}"

        painter.setFont(self._font)

        fm = painter.fontMetrics()

        padding = 5
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        # Position en haut à droite du plot
        box_x = left + width - text_width - 2 * padding
        box_y = top + padding

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._coordinate_background_color)

        painter.drawRoundedRect(
            int(box_x),
            int(box_y),
            int(text_width + 2 * padding),
            int(text_height + 2 * padding),
            4,
            4,
        )

        painter.setPen(QPen(self._text_color))

        painter.drawText(
            int(box_x + padding),
            int(box_y + padding + fm.ascent()),
            text,
        )