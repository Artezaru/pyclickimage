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

import math
from typing import Callable, Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget


class QtProfilePlot(QWidget):
    """Interactive 1D line-profile plot widget.

    ``QtProfilePlot`` is a lightweight Qt widget for displaying a sampled
    one-dimensional profile using only Qt painting primitives.

    Two display orientations are supported. The orientation describes
    where the profile is intended to be placed relative to an image.

    ``"horizontal"``
        Profile associated with the horizontal image direction.

        The data coordinates are mapped as follows:

        * X is mapped to the horizontal screen direction.
        * Y is mapped to the vertical screen direction.
        * X ticks and labels are displayed at the bottom.
        * Y ticks and labels are displayed on the left.

        This mode is therefore suitable for a profile displayed below
        an image.

        The resulting coordinate system is the conventional Cartesian
        representation::

            Y
            ^
            |
            |       /
            |     /
            |   /
            +-----------------> X

    ``"vertical"``
        Profile associated with the vertical image direction.

        The data coordinates are mapped as follows:

        * X is mapped to the vertical screen direction, increasing
          from top to bottom (image convention).
        * Y is mapped to the horizontal screen direction.
        * X ticks and labels are displayed on the right.
        * Y ticks and labels are displayed at the bottom.

        This mode is suitable for a profile displayed to the right of
        an image. All text remains horizontal and readable.

    The widget does not physically rotate itself using
    ``QPainter.rotate()``. Instead, the data-to-screen coordinate
    mapping is changed.

    This approach has several advantages:

    * the QWidget keeps its normal Qt geometry;
    * the widget can be inserted normally into Qt layouts;
    * text remains horizontal and readable;
    * tick labels do not need to be rotated;
    * the same widget can be used below or beside an image;
    * mouse interaction can later use the same coordinate mapping.

    Parameters
    ----------
    x : Sequence[float], optional
        X coordinates of the sampled profile.
    y : Sequence[float], optional
        Y values corresponding to ``x``.
    parent : QWidget, optional
        Parent Qt widget.

    Raises
    ------
    ValueError
        If only one of ``x`` or ``y`` is provided.
    ValueError
        If ``x`` and ``y`` have different lengths.
    ValueError
        If an invalid orientation is specified.

    Examples
    --------
    Create a standard horizontal profile::

        plot = QtProfilePlot(
            x=[0, 1, 2, 3],
            y=[0, 2, 1, 4],
        )

        plot.orientation = "horizontal"

    In this mode the profile is intended to be placed below an image.

    Create a vertical profile::

        plot.orientation = "vertical"

    In this mode X is vertical and Y is horizontal, so the profile can
    be placed to the right of an image.

    Configure axis titles::

        plot.x_title = "Position"
        plot.y_title = "Intensity"

    Fix the Y axis with explicit ticks (the axis spans
    ``[min(ticks), max(ticks)]``)::

        plot.y_ticks = [0, 51, 102, 153, 204, 255]

    Go back to automatic ticks computed from the data::

        plot.y_ticks = None

    Sample a function::

        plot.set_function(
            lambda x: x * x,
            0.0,
            10.0,
            samples=200,
        )

    Notes
    -----
    The widget intentionally performs its own drawing rather than using
    Qt Charts or another plotting library.

    The current implementation uses linear mappings for both axes.

    **Ticks and axis range.** For each axis:

    * explicit ticks (a sequence of at least two distinct values) are
      used as given, and the axis spans ``[min(ticks), max(ticks)]``;
      data outside this range are clipped to the plot area;
    * otherwise the axis spans the finite data range and
      ``grid + 1`` equally spaced ticks are built.

    The major grid lines are drawn at the tick positions.

    See Also
    --------
    set_data
        Set sampled profile data.
    set_function
        Sample and display a mathematical function.
    set_orientation
        Change the profile orientation.
    """

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"

    def __init__(
        self,
        x: Sequence[float] | None = None,
        y: Sequence[float] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the line plot widget.

        Parameters
        ----------
        x : Sequence[float], optional
            X coordinates.
        y : Sequence[float], optional
            Y values.
        parent : QWidget, optional
            Parent Qt widget.

        Raises
        ------
        ValueError
            If only one of ``x`` or ``y`` is provided.
        """
        super().__init__(parent)

        # ==============================================================
        # Data
        # ==============================================================

        self._x: list[float] = []
        self._y: list[float] = []

        # ==============================================================
        # Orientation
        # ==============================================================

        # Horizontal:
        #     X -> screen X
        #     Y -> screen Y
        #
        # Vertical:
        #     X -> screen Y
        #     Y -> screen X
        self._orientation = self.HORIZONTAL

        # ==============================================================
        # Margins
        # ==============================================================

        # These margins are deliberately large enough for tick labels.
        self._margin_left = 55
        self._margin_top = 25
        self._margin_right = 55
        self._margin_bottom = 55

        # ==============================================================
        # Colors
        # ==============================================================

        palette = self.palette()

        self._background_color = palette.base().color()
        self._border_color = palette.mid().color()
        self._line_color = palette.highlight().color()

        self._grid_color = QColor(210, 210, 210)
        self._minor_grid_color = QColor(235, 235, 235)

        self._axis_color = QColor(80, 80, 80)
        self._text_color = QColor(80, 80, 80)

        # ==============================================================
        # Line and drawing widths
        # ==============================================================

        self._line_width = 2

        self._border_width = 1
        self._grid_width = 1
        self._minor_grid_width = 1
        self._axis_width = 1
        self._tick_width = 1

        self._tick_length = 4

        # ==============================================================
        # Grid configuration
        # ==============================================================

        # Number of intervals of the automatic ticks.
        self._grid_x = 5
        self._grid_y = 5

        self._minor_grid = 0

        # ==============================================================
        # Font
        # ==============================================================

        self._font = QFont()
        self._font.setPointSize(8)

        # ==============================================================
        # Visibility
        # ==============================================================

        self._show_grid = True
        self._show_minor_grid = False
        self._show_axes = True
        self._show_ticks = True
        self._show_labels = True

        # ==============================================================
        # Axis titles
        # ==============================================================

        self._x_title = "pixels"
        self._y_title = "Intensity"

        # ==============================================================
        # Explicit ticks
        # ==============================================================

        # None, or a list of floats. Used only when it holds at least
        # two distinct values (see _resolve_axis).
        self._x_ticks: list[float] | None = None
        self._y_ticks: list[float] | None = None

        # ==============================================================
        # Formatters
        # ==============================================================

        self._x_formatter: Callable[[float], str] = (
            lambda value: f"{value:g}"
        )

        self._y_formatter: Callable[[float], str] = (
            lambda value: f"{value:g}"
        )

        # ==============================================================
        # Qt configuration
        # ==============================================================

        self.setMinimumSize(120, 80)

        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        # ==============================================================
        # Initial data
        # ==============================================================

        if x is not None or y is not None:
            if x is None or y is None:
                raise ValueError(
                    "x and y must be provided together."
                )

            self.set_data(x, y)

    # ==================================================================
    # Data
    # ==================================================================

    @property
    def x(self) -> list[float]:
        """list[float]: Copy of the X coordinates."""
        return self._x.copy()

    @property
    def y(self) -> list[float]:
        """list[float]: Copy of the Y values."""
        return self._y.copy()

    def set_data(
        self,
        x: Sequence[float],
        y: Sequence[float],
    ) -> None:
        """Set the sampled profile data.

        Parameters
        ----------
        x : Sequence[float]
            X coordinates.
        y : Sequence[float]
            Y values.

        Raises
        ------
        ValueError
            If ``x`` and ``y`` contain different numbers of values.

        Notes
        -----
        Values are converted to ``float`` before being stored.
        Non-finite values (``NaN``, ``inf``) are allowed: they are
        ignored when computing the automatic range and break the line.
        """
        x_values = [float(value) for value in x]
        y_values = [float(value) for value in y]

        if len(x_values) != len(y_values):
            raise ValueError(
                "x and y must contain the same number of values."
            )

        self._x = x_values
        self._y = y_values

        self.update()

    def set_function(
        self,
        function: Callable[[float], float],
        x_min: float,
        x_max: float,
        samples: int = 500,
    ) -> None:
        """Sample a function and display it.

        Parameters
        ----------
        function : Callable[[float], float]
            Function to evaluate.
        x_min : float
            Minimum X value.
        x_max : float
            Maximum X value.
        samples : int, default=500
            Number of uniformly spaced samples.

        Raises
        ------
        ValueError
            If ``samples < 2``.
        ValueError
            If ``x_max <= x_min``.
        """
        if samples < 2:
            raise ValueError(
                "samples must be greater than or equal to 2."
            )

        if x_max <= x_min:
            raise ValueError(
                "x_max must be greater than x_min."
            )

        step = (x_max - x_min) / (samples - 1)

        x_values = [
            x_min + index * step
            for index in range(samples)
        ]

        y_values = [
            float(function(value))
            for value in x_values
        ]

        self.set_data(x_values, y_values)

    def clear(self) -> None:
        """Remove all plotted data.

        The widget itself remains visible, but the profile is removed.
        """
        self._x.clear()
        self._y.clear()

        self.update()

    # ==================================================================
    # Orientation
    # ==================================================================

    @property
    def orientation(self) -> str:
        """str: Current plot orientation.

        Returns
        -------
        str
            Either ``"horizontal"`` or ``"vertical"``.

        Notes
        -----
        ``"horizontal"`` means:

        * X is horizontal.
        * Y is vertical.
        * X axis is at the bottom.
        * Y axis is at the left.

        ``"vertical"`` means:

        * X is vertical (increasing from top to bottom).
        * Y is horizontal.
        * X axis is at the right.
        * Y axis is at the bottom.
        """
        return self._orientation

    @orientation.setter
    def orientation(self, value: str) -> None:
        """Set the plot orientation."""
        self.set_orientation(value)

    def set_orientation(self, value: str) -> None:
        """Set the logical orientation of the profile.

        Parameters
        ----------
        value : str
            Either ``"horizontal"`` or ``"vertical"``.

        Raises
        ------
        ValueError
            If ``value`` is not a supported orientation.

        Notes
        -----
        The QWidget itself is never rotated.

        In ``horizontal`` mode::

            screen_x = X
            screen_y = Y

        In ``vertical`` mode::

            screen_x = Y
            screen_y = X

        This makes the vertical mode suitable for a profile displayed
        beside the right side of an image.
        """
        value = str(value).lower()

        if value not in (
            self.HORIZONTAL,
            self.VERTICAL,
        ):
            raise ValueError(
                "orientation must be 'horizontal' or 'vertical'."
            )

        if self._orientation == value:
            return

        self._orientation = value

        self.update()

    # ==================================================================
    # Appearance
    # ==================================================================

    def _color_property(name: str):
        """Create a QColor property."""

        def getter(self):
            return getattr(self, f"_{name}")

        def setter(self, value):
            setattr(
                self,
                f"_{name}",
                QColor(value),
            )
            self.update()

        return property(getter, setter)

    background_color = _color_property(
        "background_color"
    )

    line_color = _color_property(
        "line_color"
    )

    @property
    def line_width(self) -> int:
        """int: Width of the plotted line in pixels."""
        return self._line_width

    @line_width.setter
    def line_width(self, value: int) -> None:
        value = int(value)

        if value <= 0:
            raise ValueError(
                "line_width must be greater than zero."
            )

        self._line_width = value

        self.update()

    @property
    def show_grid(self) -> bool:
        """bool: Whether major grid lines are displayed."""
        return self._show_grid

    @show_grid.setter
    def show_grid(self, value: bool) -> None:
        self._show_grid = bool(value)
        self.update()

    @property
    def show_minor_grid(self) -> bool:
        """bool: Whether minor grid lines are displayed."""
        return self._show_minor_grid

    @show_minor_grid.setter
    def show_minor_grid(self, value: bool) -> None:
        self._show_minor_grid = bool(value)
        self.update()

    @property
    def show_axes(self) -> bool:
        """bool: Whether the main axes are displayed."""
        return self._show_axes

    @show_axes.setter
    def show_axes(self, value: bool) -> None:
        self._show_axes = bool(value)
        self.update()

    @property
    def show_ticks(self) -> bool:
        """bool: Whether tick marks are displayed."""
        return self._show_ticks

    @show_ticks.setter
    def show_ticks(self, value: bool) -> None:
        self._show_ticks = bool(value)
        self.update()

    @property
    def show_labels(self) -> bool:
        """bool: Whether tick labels are displayed."""
        return self._show_labels

    @show_labels.setter
    def show_labels(self, value: bool) -> None:
        self._show_labels = bool(value)
        self.update()

    # ==================================================================
    # Axis configuration
    # ==================================================================

    @property
    def x_title(self) -> str:
        """str: Title associated with the X data axis."""
        return self._x_title

    @x_title.setter
    def x_title(self, value: str) -> None:
        self._x_title = str(value)
        self.update()

    @property
    def y_title(self) -> str:
        """str: Title associated with the Y data axis."""
        return self._y_title

    @y_title.setter
    def y_title(self, value: str) -> None:
        self._y_title = str(value)
        self.update()

    @staticmethod
    def _parse_ticks(
        value: Sequence[float] | None,
    ) -> list[float] | None:
        """Convert a tick sequence to a list of floats.

        Parameters
        ----------
        value : Sequence[float] or None
            Tick positions.

        Returns
        -------
        list of float or None
            ``None`` if ``value`` is ``None``, otherwise the values as
            floats.

        Raises
        ------
        ValueError
            If a tick is not finite.
        """
        if value is None:
            return None

        ticks = [float(tick) for tick in value]

        if not all(math.isfinite(tick) for tick in ticks):
            raise ValueError(
                "Tick positions must be finite."
            )

        return ticks

    @property
    def x_ticks(self) -> list[float] | None:
        """list[float] or None: Explicit X-axis tick positions.

        A sequence of at least two distinct values is used as given:
        the X axis then spans ``[min(x_ticks), max(x_ticks)]``.
        Otherwise (``None``, fewer than two values, or all values
        equal), equally spaced ticks are built from the data range.
        """
        return None if self._x_ticks is None else self._x_ticks.copy()

    @x_ticks.setter
    def x_ticks(
        self,
        value: Sequence[float] | None,
    ) -> None:
        self._x_ticks = self._parse_ticks(value)
        self.update()

    @property
    def y_ticks(self) -> list[float] | None:
        """list[float] or None: Explicit Y-axis tick positions.

        A sequence of at least two distinct values is used as given:
        the Y axis then spans ``[min(y_ticks), max(y_ticks)]``, and
        values outside are clipped to the plot area. Otherwise
        (``None``, fewer than two values, or all values equal),
        equally spaced ticks are built from the data range.
        """
        return None if self._y_ticks is None else self._y_ticks.copy()

    @y_ticks.setter
    def y_ticks(
        self,
        value: Sequence[float] | None,
    ) -> None:
        self._y_ticks = self._parse_ticks(value)
        self.update()

    @property
    def x_formatter(self) -> Callable[[float], str]:
        """Callable[[float], str]: Formatter for X tick labels."""
        return self._x_formatter

    @x_formatter.setter
    def x_formatter(
        self,
        value: Callable[[float], str],
    ) -> None:
        if not callable(value):
            raise TypeError(
                "x_formatter must be callable."
            )

        self._x_formatter = value
        self.update()

    @property
    def y_formatter(self) -> Callable[[float], str]:
        """Callable[[float], str]: Formatter for Y tick labels."""
        return self._y_formatter

    @y_formatter.setter
    def y_formatter(
        self,
        value: Callable[[float], str],
    ) -> None:
        if not callable(value):
            raise TypeError(
                "y_formatter must be callable."
            )

        self._y_formatter = value
        self.update()

    # ==================================================================
    # Ticks and range
    # ==================================================================

    @staticmethod
    def _resolve_axis(
        ticks: list[float] | None,
        values: Sequence[float],
        intervals: int,
    ) -> tuple[list[float], float, float]:
        """Return the ticks and the range of one axis.

        Parameters
        ----------
        ticks : list of float or None
            Explicit ticks.
        values : Sequence[float]
            Data values along the axis.
        intervals : int
            Number of intervals of the automatic ticks.

        Returns
        -------
        ticks : list of float
            Sorted tick positions.
        vmin, vmax : float
            Axis range, with ``vmin < vmax``.

        Raises
        ------
        ValueError
            If automatic ticks are needed and ``intervals <= 0``.

        Notes
        -----
        - Explicit ticks with at least two distinct values: used as
          given, the range is ``[min(ticks), max(ticks)]``.
        - Otherwise: the range is the finite data range (widened by
          ``0.5`` on each side when constant, ``[0, 1]`` without
          finite value) and ``intervals + 1`` equally spaced ticks are
          built.
        """
        if ticks is not None and len(ticks) >= 2:
            ordered = sorted(ticks)

            if ordered[0] < ordered[-1]:
                return ordered, ordered[0], ordered[-1]

        if intervals <= 0:
            raise ValueError(
                "The number of grid intervals must be greater than zero."
            )

        finite = [value for value in values if math.isfinite(value)]

        if finite:
            vmin = min(finite)
            vmax = max(finite)
        else:
            vmin, vmax = 0.0, 1.0

        if vmin == vmax:
            vmin -= 0.5
            vmax += 0.5

        step = (vmax - vmin) / intervals

        built = [vmin + index * step for index in range(intervals)]
        built.append(vmax)

        return built, vmin, vmax

    # ==================================================================
    # Painting
    # ==================================================================

    def paintEvent(self, event) -> None:
        """Paint the complete widget.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event.
        """
        del event

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        self._paint_plot(painter)

        painter.end()

    def _paint_plot(
        self,
        painter: QPainter,
    ) -> None:
        """Paint the complete plotting area."""
        painter.fillRect(
            self.rect(),
            self._background_color,
        )

        left = self._margin_left
        top = self._margin_top

        right = (
            self.width()
            - self._margin_right
        )

        bottom = (
            self.height()
            - self._margin_bottom
        )

        if right <= left or bottom <= top:
            return

        self._frame(
            painter,
            left,
            top,
            right,
            bottom,
        )

        if len(self._x) < 2:
            return

        x_ticks, x_min, x_max = self._resolve_axis(
            self._x_ticks,
            self._x,
            self._grid_x,
        )

        y_ticks, y_min, y_max = self._resolve_axis(
            self._y_ticks,
            self._y,
            self._grid_y,
        )

        self._grid(
            painter,
            left,
            top,
            right,
            bottom,
            x_min,
            x_max,
            y_min,
            y_max,
            x_ticks,
            y_ticks,
        )

        self._line(
            painter,
            left,
            top,
            right,
            bottom,
            x_min,
            x_max,
            y_min,
            y_max,
        )

        self._axes(
            painter,
            left,
            top,
            right,
            bottom,
            x_min,
            x_max,
            y_min,
            y_max,
            x_ticks,
            y_ticks,
        )

    # ==================================================================
    # Coordinate mapping
    # ==================================================================

    def _map_x(
        self,
        value: float,
        left: int,
        right: int,
        top: int,
        bottom: int,
        x_min: float,
        x_max: float,
    ) -> float:
        """Map an X data value to its screen coordinate.

        Parameters
        ----------
        value : float
            X data value.
        left, right, top, bottom : int
            Plot boundaries.
        x_min, x_max : float
            X data range.

        Returns
        -------
        float
            Horizontal screen coordinate in ``horizontal`` mode,
            vertical screen coordinate in ``vertical`` mode.

        Notes
        -----
        ``vertical`` mode follows the image convention: ``x_min`` at
        the top, ``x_max`` at the bottom.
        """
        if self._orientation == self.HORIZONTAL:
            return (
                left
                + (value - x_min)
                / (x_max - x_min)
                * (right - left)
            )

        return (
            top
            + (value - x_min)
            / (x_max - x_min)
            * (bottom - top)
        )

    def _map_y(
        self,
        value: float,
        left: int,
        right: int,
        top: int,
        bottom: int,
        y_min: float,
        y_max: float,
    ) -> float:
        """Map a Y data value to its screen coordinate.

        Parameters
        ----------
        value : float
            Y data value.
        left, right, top, bottom : int
            Plot boundaries.
        y_min, y_max : float
            Y data range.

        Returns
        -------
        float
            Vertical screen coordinate in ``horizontal`` mode,
            horizontal screen coordinate in ``vertical`` mode.
        """
        if self._orientation == self.HORIZONTAL:
            return (
                bottom
                - (value - y_min)
                / (y_max - y_min)
                * (bottom - top)
            )

        return (
            left
            + (value - y_min)
            / (y_max - y_min)
            * (right - left)
        )

    # ==================================================================
    # Grid
    # ==================================================================

    def _grid(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        x_ticks: Sequence[float],
        y_ticks: Sequence[float],
    ) -> None:
        """Draw the minor and major grid.

        The minor grid is made of equally spaced lines. The major grid
        lines are drawn at the tick positions, so they always match the
        ticks and labels.
        """
        if self._show_minor_grid and self._minor_grid > 0:
            self._draw_vertical_grid(
                painter,
                left,
                right,
                top,
                bottom,
                self._minor_grid,
                self._minor_grid_color,
                self._minor_grid_width,
            )

            self._draw_horizontal_grid(
                painter,
                left,
                right,
                top,
                bottom,
                self._minor_grid,
                self._minor_grid_color,
                self._minor_grid_width,
            )

        if not self._show_grid:
            return

        painter.setPen(
            QPen(
                self._grid_color,
                self._grid_width,
            )
        )

        horizontal = self._orientation == self.HORIZONTAL

        for value in x_ticks:
            if not x_min <= value <= x_max:
                continue

            position = round(
                self._map_x(value, left, right, top, bottom, x_min, x_max)
            )

            if horizontal:
                painter.drawLine(position, top, position, bottom)
            else:
                painter.drawLine(left, position, right, position)

        for value in y_ticks:
            if not y_min <= value <= y_max:
                continue

            position = round(
                self._map_y(value, left, right, top, bottom, y_min, y_max)
            )

            if horizontal:
                painter.drawLine(left, position, right, position)
            else:
                painter.drawLine(position, top, position, bottom)

    @staticmethod
    def _draw_vertical_grid(
        painter: QPainter,
        left: int,
        right: int,
        top: int,
        bottom: int,
        line_count: int,
        color: QColor,
        width: int,
    ) -> None:
        """Draw equally spaced vertical grid lines.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, right, top, bottom : int
            Plot boundaries.
        line_count : int
            Number of intervals.
        color : QColor
            Grid line color.
        width : int
            Grid line width.

        Raises
        ------
        ValueError
            If ``line_count <= 0``.
        """
        if line_count <= 0:
            raise ValueError(
                "line_count must be greater than zero."
            )

        painter.setPen(
            QPen(color, width)
        )

        plot_width = right - left

        for index in range(line_count + 1):
            x = round(
                left
                + index * plot_width / line_count
            )

            painter.drawLine(
                x,
                top,
                x,
                bottom,
            )

    @staticmethod
    def _draw_horizontal_grid(
        painter: QPainter,
        left: int,
        right: int,
        top: int,
        bottom: int,
        line_count: int,
        color: QColor,
        width: int,
    ) -> None:
        """Draw equally spaced horizontal grid lines.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, right, top, bottom : int
            Plot boundaries.
        line_count : int
            Number of intervals.
        color : QColor
            Grid line color.
        width : int
            Grid line width.

        Raises
        ------
        ValueError
            If ``line_count <= 0``.
        """
        if line_count <= 0:
            raise ValueError(
                "line_count must be greater than zero."
            )

        painter.setPen(
            QPen(color, width)
        )

        plot_height = bottom - top

        for index in range(line_count + 1):
            y = round(
                bottom
                - index * plot_height / line_count
            )

            painter.drawLine(
                left,
                y,
                right,
                y,
            )

    # ==================================================================
    # Profile line
    # ==================================================================

    def _line(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        """Draw the sampled profile.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plot boundaries.
        x_min, x_max : float
            X axis range.
        y_min, y_max : float
            Y axis range.

        Notes
        -----
        The line is clipped to the plot area, so values outside an
        explicit tick range do not overflow on the labels. Non-finite
        samples break the line.
        """
        if x_max <= x_min or y_max <= y_min:
            return

        painter.save()

        painter.setClipRect(
            left,
            top,
            right - left,
            bottom - top,
        )

        painter.setPen(
            QPen(
                self._line_color,
                self._line_width,
            )
        )

        horizontal = self._orientation == self.HORIZONTAL

        previous: tuple[int, int] | None = None

        for x_value, y_value in zip(
            self._x,
            self._y,
        ):
            if not (math.isfinite(x_value) and math.isfinite(y_value)):
                previous = None
                continue

            along_x = self._map_x(
                x_value, left, right, top, bottom, x_min, x_max
            )
            along_y = self._map_y(
                y_value, left, right, top, bottom, y_min, y_max
            )

            if horizontal:
                point = (round(along_x), round(along_y))
            else:
                point = (round(along_y), round(along_x))

            if previous is not None:
                painter.drawLine(
                    previous[0],
                    previous[1],
                    point[0],
                    point[1],
                )

            previous = point

        painter.restore()

    # ==================================================================
    # Axes
    # ==================================================================

    def _axes(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        x_ticks: Sequence[float],
        y_ticks: Sequence[float],
    ) -> None:
        """Draw axes, ticks, labels and titles.

        ``horizontal`` mode
            X axis is at the bottom.
            Y axis is at the left.

        ``vertical`` mode
            X axis is at the right.
            Y axis is at the bottom.
        """
        painter.setFont(self._font)

        if self._show_axes:
            painter.setPen(
                QPen(
                    self._axis_color,
                    self._axis_width,
                )
            )

            if self._orientation == self.HORIZONTAL:
                # X axis: bottom
                painter.drawLine(
                    left,
                    bottom,
                    right,
                    bottom,
                )

                # Y axis: left
                painter.drawLine(
                    left,
                    top,
                    left,
                    bottom,
                )

            else:
                # X axis: right
                painter.drawLine(
                    right,
                    top,
                    right,
                    bottom,
                )

                # Y axis: bottom
                painter.drawLine(
                    left,
                    bottom,
                    right,
                    bottom,
                )

        if self._show_ticks:
            self._ticks_x(
                painter,
                left,
                top,
                right,
                bottom,
                x_min,
                x_max,
                x_ticks,
            )

            self._ticks_y(
                painter,
                left,
                top,
                right,
                bottom,
                y_min,
                y_max,
                y_ticks,
            )

        if self._show_labels:
            self._labels_x(
                painter,
                left,
                top,
                right,
                bottom,
                x_min,
                x_max,
                x_ticks,
            )

            self._labels_y(
                painter,
                left,
                top,
                right,
                bottom,
                y_min,
                y_max,
                y_ticks,
            )

        self._titles(
            painter,
            left,
            top,
            right,
            bottom,
        )

    # ==================================================================
    # X ticks
    # ==================================================================

    def _ticks_x(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw ticks associated with the X data axis.

        In ``horizontal`` mode, X ticks are displayed at the bottom.

        In ``vertical`` mode, X ticks are displayed on the right.
        """
        if x_max <= x_min:
            return

        painter.setPen(
            QPen(
                self._axis_color,
                self._tick_width,
            )
        )

        for value in ticks:
            if not x_min <= value <= x_max:
                continue

            position = round(
                self._map_x(value, left, right, top, bottom, x_min, x_max)
            )

            if self._orientation == self.HORIZONTAL:
                painter.drawLine(
                    position,
                    bottom,
                    position,
                    bottom + self._tick_length,
                )

            else:
                painter.drawLine(
                    right,
                    position,
                    right + self._tick_length,
                    position,
                )

    # ==================================================================
    # Y ticks
    # ==================================================================

    def _ticks_y(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        y_min: float,
        y_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw ticks associated with the Y data axis.

        In ``horizontal`` mode, Y ticks are displayed on the left.

        In ``vertical`` mode, Y ticks are displayed at the bottom.
        """
        if y_max <= y_min:
            return

        painter.setPen(
            QPen(
                self._axis_color,
                self._tick_width,
            )
        )

        for value in ticks:
            if not y_min <= value <= y_max:
                continue

            position = round(
                self._map_y(value, left, right, top, bottom, y_min, y_max)
            )

            if self._orientation == self.HORIZONTAL:
                painter.drawLine(
                    left - self._tick_length,
                    position,
                    left,
                    position,
                )

            else:
                painter.drawLine(
                    position,
                    bottom,
                    position,
                    bottom + self._tick_length,
                )

    # ==================================================================
    # X labels
    # ==================================================================

    def _labels_x(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw labels associated with the X data axis.

        In ``horizontal`` mode, labels are displayed below the plot.

        In ``vertical`` mode, labels are displayed to the right of the
        plot, ``x_min`` at the top and ``x_max`` at the bottom.
        """
        if x_max <= x_min:
            return

        painter.setPen(self._text_color)

        metrics = painter.fontMetrics()

        for value in ticks:
            if not x_min <= value <= x_max:
                continue

            label = self._x_formatter(value)

            position = self._map_x(
                value, left, right, top, bottom, x_min, x_max
            )

            if self._orientation == self.HORIZONTAL:
                width = metrics.horizontalAdvance(label)

                painter.drawText(
                    round(position - width / 2),
                    round(
                        bottom
                        + self._tick_length
                        + metrics.ascent()
                        + 4
                    ),
                    label,
                )

            else:
                baseline = (
                    position
                    + (
                        metrics.ascent()
                        - metrics.descent()
                    ) / 2
                )

                painter.drawText(
                    round(
                        right
                        + self._tick_length
                        + 6
                    ),
                    round(baseline),
                    label,
                )

    # ==================================================================
    # Y labels
    # ==================================================================

    def _labels_y(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        y_min: float,
        y_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw labels associated with the Y data axis.

        In ``horizontal`` mode, labels are displayed to the left.

        In ``vertical`` mode, labels are displayed below the plot.
        """
        if y_max <= y_min:
            return

        painter.setPen(self._text_color)

        metrics = painter.fontMetrics()

        for value in ticks:
            if not y_min <= value <= y_max:
                continue

            label = self._y_formatter(value)

            width = metrics.horizontalAdvance(label)

            position = self._map_y(
                value, left, right, top, bottom, y_min, y_max
            )

            if self._orientation == self.HORIZONTAL:
                baseline = (
                    position
                    + (
                        metrics.ascent()
                        - metrics.descent()
                    ) / 2
                )

                painter.drawText(
                    round(
                        left
                        - self._tick_length
                        - width
                        - 6
                    ),
                    round(baseline),
                    label,
                )

            else:
                painter.drawText(
                    round(position - width / 2),
                    round(
                        bottom
                        + self._tick_length
                        + metrics.ascent()
                        + 4
                    ),
                    label,
                )

    # ==================================================================
    # Titles
    # ==================================================================

    def _titles(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> None:
        """Draw X and Y axis titles.

        ``horizontal`` mode
            * X title: centered below the plot.
            * Y title: horizontal, centered above the Y axis.

        ``vertical`` mode
            * X title: vertical, rotated 90 degrees, to the right
              of the plot.
            * Y title: horizontal, centered below the plot.
        """
        painter.setPen(self._text_color)

        metrics = painter.fontMetrics()

        if self._orientation == self.HORIZONTAL:

            # ----------------------------------------------------------
            # X title: centered below the plot
            # ----------------------------------------------------------

            if self._x_title:
                width = metrics.horizontalAdvance(
                    self._x_title
                )

                painter.drawText(
                    round(
                        (left + right - width) / 2
                    ),
                    round(
                        bottom
                        + self._tick_length
                        + metrics.height()
                        + 14
                    ),
                    self._x_title,
                )

            # ----------------------------------------------------------
            # Y title: centered above the Y axis (located at ``left``)
            # ----------------------------------------------------------

            if self._y_title:
                width = metrics.horizontalAdvance(
                    self._y_title
                )

                painter.drawText(
                    round(left - width / 2),
                    round(top - 8),
                    self._y_title,
                )

        else:

            # ----------------------------------------------------------
            # X title: rotated, to the right of the plot
            # ----------------------------------------------------------

            if self._x_title:
                painter.save()

                painter.translate(
                    right
                    + self._tick_length
                    + metrics.height()
                    + 12,
                    (top + bottom) / 2,
                )

                painter.rotate(-90)

                width = metrics.horizontalAdvance(
                    self._x_title
                )

                painter.drawText(
                    round(-width / 2),
                    round(metrics.ascent() / 2),
                    self._x_title,
                )

                painter.restore()

            # ----------------------------------------------------------
            # Y title: centered below the plot
            # ----------------------------------------------------------

            if self._y_title:
                width = metrics.horizontalAdvance(
                    self._y_title
                )

                painter.drawText(
                    round(
                        (left + right - width) / 2
                    ),
                    round(
                        bottom
                        + self._tick_length
                        + metrics.height()
                        + 14
                    ),
                    self._y_title,
                )

    # ==================================================================
    # Frame
    # ==================================================================

    def _frame(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> None:
        """Draw the border around the plotting area.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plot boundaries.
        """
        painter.setBrush(Qt.NoBrush)

        painter.setPen(
            QPen(
                self._border_color,
                self._border_width,
            )
        )

        painter.drawRect(
            left,
            top,
            right - left,
            bottom - top,
        )