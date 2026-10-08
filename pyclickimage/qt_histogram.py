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

from typing import Callable, Sequence
from bisect import bisect_right

from PyQt5.QtCore import QPointF, QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class QtHistogram(QWidget):
    """Interactive histogram and cumulative-distribution widget.

    The widget displays binned numeric data using four display modes:

    * histogram with absolute counts;
    * histogram with percentages;
    * cumulative histogram with absolute counts;
    * cumulative histogram with percentages.

    The underlying histogram always stores absolute bin values. Display
    transformations are applied only while painting, so changing the
    display mode never modifies the source data.

    Parameters
    ----------
    data : Sequence[float], optional
        Raw numeric samples used to build the histogram. Values are
        converted to ``float``.
    bins : Sequence[float], optional
        Explicit histogram heights. Values must be non-negative. When
        provided, ``edges`` must contain ``len(bins) + 1`` values.
    edges : Sequence[float], optional
        Monotonically increasing bin boundaries. When omitted with
        ``bins``, integer boundaries ``[0, 1, ..., len(bins)]`` are used.
    parent : QWidget, optional
        Parent Qt widget.

    Notes
    -----
    ``set_data`` computes equally spaced bins when no explicit edges are
    supplied. ``set_bins`` accepts already-computed histogram values.

    Percentage mode divides each displayed value by the sum of the original
    bin values and multiplies it by 100. In cumulative percentage mode, the
    final value is therefore 100 when the histogram contains data.

    The two display options are controlled by checkboxes placed below the
    histogram.

    Examples
    --------
    >>> histogram = QtHistogram(data=[1, 2, 2, 3, 3, 3])
    >>> histogram.cumulative = True
    >>> histogram.percentage = True
    >>> histogram.bin_count = 20
    >>> histogram.set_data([0, 1, 2, 3])
    """

    def __init__(
        self,
        data: Sequence[float] | None = None,
        bins: Sequence[float] | None = None,
        edges: Sequence[float] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the histogram widget.

        Parameters
        ----------
        data : Sequence[float], optional
            Raw samples used to compute the histogram.
        bins : Sequence[float], optional
            Precomputed non-negative bin values.
        edges : Sequence[float], optional
            Bin boundaries associated with ``bins``.
        parent : QWidget, optional
            Parent Qt widget.
        """
        super().__init__(parent)

        self._bins: list[float] = []
        self._edges: list[float] = []

        self._bin_count = 10
        self._cumulative = False
        self._percentage = False

        # Space between the widget border and the plotting area. The
        # bottom margin is measured from the top of the mode checkboxes
        # and holds the X tick labels and the X title.
        self._margin_left = 76
        self._margin_top = 36
        self._margin_right = 32
        self._margin_bottom = 52

        # Margins around the whole widget content (checkbox row included).
        self._content_margins = (12, 8, 12, 10)

        palette = self.palette()
        self._background_color = palette.base().color()
        self._border_color = palette.mid().color()
        self._bar_color = palette.highlight().color()
        self._bar_border_color = palette.highlight().color()

        self._grid_color = QColor(210, 210, 210)
        self._minor_grid_color = QColor(235, 235, 235)
        self._axis_color = QColor(80, 80, 80)
        self._text_color = QColor(80, 80, 80)

        self._border_width = 1
        self._bar_width = 1
        self._grid_width = 1
        self._minor_grid_width = 1
        self._axis_width = 1
        self._tick_width = 1

        self._tick_length = 4
        self._grid_x = 5
        self._grid_y = 5
        self._minor_grid = 0

        self._font = QFont()
        self._font.setPointSize(8)

        self._show_grid = True
        self._show_minor_grid = False
        self._show_axes = True
        self._show_ticks = True
        self._show_labels = True

        self._x_title = ""

        self._x_ticks: Sequence[float] | None = None
        self._x_formatter: Callable[[float], str] = lambda value: f"{value:g}"

        self._build_mode_controls()

        self.setMinimumSize(120, 80)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        if bins is not None:
            self.set_bins(bins, edges)
        elif data is not None:
            self.set_data(data)

    # ==================================================================
    # Modes
    # ==================================================================

    @property
    def cumulative(self) -> bool:
        """bool: Whether cumulative values are displayed."""
        return self._cumulative

    @cumulative.setter
    def cumulative(self, value: bool) -> None:
        self.set_cumulative(value)

    def set_cumulative(self, value: bool) -> None:
        """Enable or disable cumulative mode.

        Parameters
        ----------
        value : bool
            Whether cumulative values should be displayed.
        """
        value = bool(value)

        if self._cumulative == value:
            return

        self._cumulative = value
        self._cumulative_checkbox.setChecked(value)
        self.update()

    @property
    def percentage(self) -> bool:
        """bool: Whether values are displayed as percentages."""
        return self._percentage

    @percentage.setter
    def percentage(self, value: bool) -> None:
        self.set_percentage(value)

    def set_percentage(self, value: bool) -> None:
        """Enable or disable percentage mode.

        Parameters
        ----------
        value : bool
            Whether percentages should be displayed instead of absolute
            values.
        """
        value = bool(value)

        if self._percentage == value:
            return

        self._percentage = value
        self._percentage_checkbox.setChecked(value)
        self.update()

    # ==================================================================
    # Properties
    # ==================================================================

    @property
    def bins(self) -> list[float]:
        """list[float]: Copy of the original bin values."""
        return self._bins.copy()

    @property
    def edges(self) -> list[float]:
        """list[float]: Copy of the current bin boundaries."""
        return self._edges.copy()

    @property
    def bin_count(self) -> int:
        """int: Default number of bins used by :meth:`set_data`."""
        return self._bin_count

    @bin_count.setter
    def bin_count(self, value: int) -> None:
        value = int(value)

        if value <= 0:
            raise ValueError(
                "bin_count must be greater than zero."
            )

        self._bin_count = value

    def _color_property(name: str):
        def getter(self):
            return getattr(self, f"_{name}")

        def setter(self, value):
            setattr(self, f"_{name}", QColor(value))
            self.update()

        return property(getter, setter)

    background_color = _color_property("background_color")
    bar_color = _color_property("bar_color")
    bar_border_color = _color_property("bar_border_color")

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
        """bool: Whether axes are displayed."""
        return self._show_axes

    @show_axes.setter
    def show_axes(self, value: bool) -> None:
        self._show_axes = bool(value)
        self.update()

    @property
    def show_ticks(self) -> bool:
        """bool: Whether ticks are displayed."""
        return self._show_ticks

    @show_ticks.setter
    def show_ticks(self, value: bool) -> None:
        self._show_ticks = bool(value)
        self.update()

    @property
    def show_labels(self) -> bool:
        """bool: Whether axis labels are displayed."""
        return self._show_labels

    @show_labels.setter
    def show_labels(self, value: bool) -> None:
        self._show_labels = bool(value)
        self.update()

    @property
    def x_title(self) -> str:
        """str: X-axis title."""
        return self._x_title

    @x_title.setter
    def x_title(self, value: str) -> None:
        self._x_title = str(value)
        self.update()
        
    @property
    def x_ticks(self) -> Sequence[float] | None:
        """Sequence[float] | None: Explicit X-axis tick positions."""
        return self._x_ticks

    @x_ticks.setter
    def x_ticks(self, value: Sequence[float] | None) -> None:
        self._x_ticks = value
        self.update()

    @property
    def x_formatter(self) -> Callable[[float], str]:
        """Callable[[float], str]: X-axis label formatter."""
        return self._x_formatter

    @x_formatter.setter
    def x_formatter(self, value: Callable[[float], str]) -> None:
        self._x_formatter = value
        self.update()

    # ==================================================================
    # Mode controls
    # ==================================================================

    def _build_mode_controls(self) -> None:
        """Create the display checkboxes below the histogram."""
        self._cumulative_checkbox = QCheckBox(
            "Cumulative",
            self,
        )
        self._percentage_checkbox = QCheckBox(
            "Percentage",
            self,
        )

        self._cumulative_checkbox.toggled.connect(
            self.set_cumulative
        )
        self._percentage_checkbox.toggled.connect(
            self.set_percentage
        )

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self._cumulative_checkbox)
        controls_layout.addWidget(self._percentage_checkbox)
        controls_layout.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*self._content_margins)
        main_layout.setSpacing(2)
        main_layout.addStretch(1)
        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)

    # ==================================================================
    # Data
    # ==================================================================

    def set_data(
        self,
        data: Sequence[float],
        bins: int | Sequence[float] | None = None,
    ) -> None:
        """Build and store a histogram from raw numeric samples.

        The input samples are converted to ``float`` before binning.

        If ``bins`` is an integer, that value specifies the number of
        equally spaced bins between the minimum and maximum sample.

        If ``bins`` is a sequence, it is interpreted as explicit bin
        boundaries. In this case the boundaries do not need to be equally
        spaced.

        The rightmost edge is inclusive, so a value exactly equal to
        ``edges[-1]`` is assigned to the last bin.

        Parameters
        ----------
        data : Sequence[float]
            Raw numeric samples.
        bins : int or Sequence[float], optional
            Number of equally spaced bins, or explicit bin boundaries.

        Raises
        ------
        ValueError
            If the number of bins is not positive or if explicit bin
            boundaries are invalid.
        """
        values = [float(value) for value in data]

        if not values:
            self.clear()
            return

        if bins is None or isinstance(bins, int):
            bin_count = self._bin_count if bins is None else bins

            if bin_count <= 0:
                raise ValueError(
                    "bins must be greater than zero."
                )

            data_min = min(values)
            data_max = max(values)

            # Give a constant-valued dataset a finite histogram range.
            if data_min == data_max:
                data_min -= 0.5
                data_max += 0.5

            bin_width = (data_max - data_min) / bin_count

            edges = [
                data_min + index * bin_width
                for index in range(bin_count + 1)
            ]

        else:
            edges = [float(value) for value in bins]
            self._validate_edges(edges)

        bin_values = [0.0] * (len(edges) - 1)

        for value in values:
            # The last edge is inclusive.
            if value == edges[-1]:
                bin_index = len(bin_values) - 1
            else:
                # ``bisect_right`` correctly handles non-uniform edges.
                bin_index = bisect_right(edges, value) - 1

            if 0 <= bin_index < len(bin_values):
                bin_values[bin_index] += 1.0

        self._bins = bin_values
        self._edges = edges
        self._bin_count = len(bin_values)

        self.update()


    def set_bins(
        self,
        bins: Sequence[float],
        edges: Sequence[float] | None = None,
    ) -> None:
        """Set precomputed histogram bin values.

        The values are stored as absolute values. Display transformations
        such as cumulative values and percentages are applied only during
        painting.

        Parameters
        ----------
        bins : Sequence[float]
            Non-negative values associated with each histogram bin.
        edges : Sequence[float], optional
            Bin boundaries. There must be exactly ``len(bins) + 1``
            boundaries. If omitted, integer boundaries starting at zero
            are generated.

        Raises
        ------
        ValueError
            If a bin value is negative, if the edges are invalid, or if
            the number of edges does not match the number of bins.
        """
        bin_values = [float(value) for value in bins]

        if any(value < 0 for value in bin_values):
            raise ValueError(
                "Histogram values must be non-negative."
            )

        bin_edges = (
            [float(value) for value in range(len(bin_values) + 1)]
            if edges is None
            else [float(value) for value in edges]
        )

        if len(bin_edges) != len(bin_values) + 1:
            raise ValueError(
                "edges must contain len(bins) + 1 values."
            )

        self._validate_edges(bin_edges)

        self._bins = bin_values
        self._edges = bin_edges
        self._bin_count = len(bin_values)

        self.update()


    def clear(self) -> None:
        """Remove all histogram data.

        The current display mode, axis configuration, colors and other
        visual properties are preserved.
        """
        self._bins.clear()
        self._edges.clear()
        self.update()


    @staticmethod
    def _validate_edges(edges: Sequence[float]) -> None:
        """Validate histogram bin boundaries.

        Parameters
        ----------
        edges : Sequence[float]
            Bin boundaries.

        Raises
        ------
        ValueError
            If fewer than two boundaries are provided or if boundaries
            are not strictly increasing.
        """
        if len(edges) < 2:
            raise ValueError(
                "Bin edges must contain at least two values."
            )

        if any(
            first >= second
            for first, second in zip(edges, edges[1:])
        ):
            raise ValueError(
                "Bin edges must be strictly increasing."
            )


    # ==================================================================
    # Painting
    # ==================================================================

    def paintEvent(self, event) -> None:
        """Paint the complete histogram widget.

        Parameters
        ----------
        event : QPaintEvent
            Qt paint event requesting the widget to be repainted.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self._paint_histogram(painter)


    def _paint_histogram(self, painter: QPainter) -> None:
        """Paint the histogram plotting area and its frame.

        The method computes the displayed values from the original bins
        according to the current cumulative and percentage modes.

        Empty histograms still display the plotting frame but do not draw
        grid lines, bars or axes based on data.
        """
        painter.fillRect(
            self.rect(),
            self._background_color,
        )

        left = self._margin_left
        top = self._margin_top
        right = self.width() - self._margin_right

        # The plot ends ``margin_bottom`` pixels above the checkbox row.
        controls_top = self._cumulative_checkbox.geometry().top()

        if controls_top <= 0:
            controls_top = (
                self.height()
                - self._content_margins[3]
                - self._cumulative_checkbox.sizeHint().height()
            )

        bottom = controls_top - self._margin_bottom

        if right <= left or bottom <= top:
            return

        if not self._bins or not self._edges:
            self._frame(
                painter,
                left,
                top,
                right,
                bottom,
            )
            return

        x_min = self._edges[0]
        x_max = self._edges[-1]

        if x_max <= x_min:
            self._frame(
                painter,
                left,
                top,
                right,
                bottom,
            )
            return

        display_values = self._display_values()

        # Keep a finite positive plotting range even when all values are zero.
        y_max = max(display_values, default=0.0)

        if y_max <= 0:
            y_max = 1.0

        self._grid(
            painter,
            left,
            top,
            right,
            bottom,
            y_max,
        )

        self._bars(
            painter,
            left,
            top,
            right,
            bottom,
            x_min,
            x_max,
            y_max,
            display_values,
        )

        self._axes(
            painter,
            left,
            top,
            right,
            bottom,
            x_min,
            x_max,
            y_max,
        )

        self._frame(
            painter,
            left,
            top,
            right,
            bottom,
        )


    def _display_values(self) -> list[float]:
        """Return bin values transformed for the current display mode.

        The original ``self._bins`` values are never modified.

        Transformation order is:

        1. Start with absolute bin values.
        2. If cumulative mode is enabled, compute the cumulative sum.
        3. If percentage mode is enabled, divide by the total of the
        original histogram and multiply by 100.

        This ordering ensures that cumulative percentage mode reaches
        100 percent at the final non-empty bin.

        Returns
        -------
        list[float]
            Values that should be rendered by the histogram.
        """
        values = self._bins.copy()

        if self._cumulative:
            cumulative = 0.0
            values = [
                cumulative := cumulative + value
                for value in values
            ]

        if self._percentage:
            total = sum(self._bins)

            if total > 0:
                values = [
                    value / total * 100.0
                    for value in values
                ]
            else:
                values = [0.0] * len(values)

        return values


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
        y_max: float,
    ) -> None:
        """Draw major and minor grid lines.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plotting area boundaries in widget coordinates.
        y_max : float
            Maximum displayed Y value.

        Notes
        -----
        ``y_max`` is currently not required because horizontal grid lines
        are evenly distributed geometrically. It is kept in the signature
        so the grid method can later be adapted to non-linear axes without
        changing its callers.
        """
        del y_max

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

        if self._show_grid:
            self._draw_vertical_grid(
                painter,
                left,
                right,
                top,
                bottom,
                self._grid_x,
                self._grid_color,
                self._grid_width,
            )

            self._draw_horizontal_grid(
                painter,
                left,
                right,
                top,
                bottom,
                self._grid_y,
                self._grid_color,
                self._grid_width,
            )

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
        """Draw evenly spaced vertical grid lines.

        The grid includes both boundaries of the plotting area. Therefore,
        ``line_count`` represents the number of intervals between the first
        and last grid line, and the method draws ``line_count + 1`` lines.

        For example, with ``line_count=5`` the method draws six vertical
        lines at positions corresponding to::

            0 %, 20 %, 40 %, 60 %, 80 %, 100 %

        Parameters
        ----------
        painter : QPainter
            Painter used to draw the grid lines.
        left : int
            X coordinate of the left side of the plotting area.
        right : int
            X coordinate of the right side of the plotting area.
        top : int
            Y coordinate of the top of the plotting area.
        bottom : int
            Y coordinate of the bottom of the plotting area.
        line_count : int
            Number of intervals between vertical grid lines. Must be
            greater than zero.
        color : QColor
            Color used for the grid lines.
        width : int
            Width of the grid lines.

        Raises
        ------
        ValueError
            If ``line_count`` is not positive or if ``right`` is smaller
            than ``left``.
        """
        if line_count <= 0:
            raise ValueError(
                "line_count must be greater than zero."
            )

        if right < left:
            raise ValueError(
                "right must be greater than or equal to left."
            )

        painter.setPen(QPen(color, width))

        plot_width = right - left

        for line_index in range(line_count + 1):
            x_position = round(
                left
                + line_index * plot_width / line_count
            )

            painter.drawLine(
                x_position,
                top,
                x_position,
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
        """Draw evenly spaced horizontal grid lines.

        The grid includes both the top and bottom boundaries of the
        plotting area. Therefore, ``line_count`` represents the number
        of intervals, and the method draws ``line_count + 1`` horizontal
        lines.

        The first line is drawn at the bottom of the plotting area and
        subsequent lines are drawn upward until the top boundary is
        reached.

        For example, with ``line_count=5`` the method draws six horizontal
        lines at positions corresponding to::

            0 %, 20 %, 40 %, 60 %, 80 %, 100 %

        Parameters
        ----------
        painter : QPainter
            Painter used to draw the grid lines.
        left : int
            X coordinate of the left side of the plotting area.
        right : int
            X coordinate of the right side of the plotting area.
        top : int
            Y coordinate of the top of the plotting area.
        bottom : int
            Y coordinate of the bottom of the plotting area.
        line_count : int
            Number of intervals between horizontal grid lines. Must be
            greater than zero.
        color : QColor
            Color used for the grid lines.
        width : int
            Width of the grid lines.

        Raises
        ------
        ValueError
            If ``line_count`` is not positive or if ``bottom`` is smaller
            than ``top``.
        """
        if line_count <= 0:
            raise ValueError(
                "line_count must be greater than zero."
            )

        if bottom < top:
            raise ValueError(
                "bottom must be greater than or equal to top."
            )

        painter.setPen(QPen(color, width))

        plot_height = bottom - top

        for line_index in range(line_count + 1):
            y_position = round(
                bottom
                - line_index * plot_height / line_count
            )

            painter.drawLine(
                left,
                y_position,
                right,
                y_position,
            )

    # ==================================================================
    # Bars
    # ==================================================================

    def _bars(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        y_max: float,
        values: Sequence[float],
    ) -> None:
        """Draw histogram bars.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plotting area boundaries.
        x_min, x_max : float
            Numerical X-axis range.
        y_max : float
            Maximum displayed Y value.
        values : Sequence[float]
            Values to render for each histogram bin.

        Notes
        -----
        The bin boundaries in ``self._edges`` determine the horizontal
        position and width of each bar. This means non-uniform bins are
        rendered with their actual widths.

        The bar height is based on the transformed ``values`` argument,
        so cumulative and percentage modes do not modify the underlying
        histogram data.
        """
        if not values or not self._edges:
            return

        if len(self._edges) != len(values) + 1:
            raise ValueError(
                "The number of edges must be one greater than "
                "the number of bar values."
            )

        if x_max <= x_min or y_max <= 0:
            return

        plot_width = right - left
        plot_height = bottom - top

        painter.setBrush(self._bar_color)
        painter.setPen(
            QPen(
                self._bar_border_color,
                self._bar_width,
            )
        )

        for index, value in enumerate(values):
            # Do not allow invalid negative display values to extend below
            # the X axis. This is mainly defensive; normal histogram data
            # is non-negative.
            value = max(0.0, float(value))

            edge_left = self._edges[index]
            edge_right = self._edges[index + 1]

            # Convert numerical X coordinates into pixel coordinates.
            x1 = left + (
                (edge_left - x_min)
                / (x_max - x_min)
                * plot_width
            )

            x2 = left + (
                (edge_right - x_min)
                / (x_max - x_min)
                * plot_width
            )

            # Convert the value into a pixel height.
            y = bottom - (
                value / y_max * plot_height
            )

            # Use floor/ceil-style rounding so adjacent bins meet cleanly
            # even when their boundaries map to fractional pixels.
            rect_left = round(x1)
            rect_right = round(x2)
            rect_top = round(y)
            rect_bottom = bottom

            if rect_right <= rect_left:
                rect_right = rect_left + 1

            if rect_top > rect_bottom:
                rect_top = rect_bottom

            painter.drawRect(
                rect_left,
                rect_top,
                rect_right - rect_left,
                rect_bottom - rect_top,
            )

    # ==================================================================
    # Axes
    # ==================================================================

    def _get_y_ticks(
        self,
        y_max: float,
    ) -> tuple[list[float], list[str], str]:
        """Generate Y-axis tick positions, labels and title.

        Tick positions are kept at their exact numerical positions.
        Only their textual representation is rounded. This prevents the
        visual position of a tick from becoming inconsistent with the
        actual Y-axis scale.

        Parameters
        ----------
        y_max : float
            Maximum value represented by the Y-axis.

        Returns
        -------
        tuple[list[float], list[str], str]
            A tuple containing the numerical tick positions, their
            formatted labels and the Y-axis title.

        Raises
        ------
        ValueError
            If ``y_max`` is negative or if ``_grid_y`` is not positive.
        """
        if y_max < 0:
            raise ValueError(
                "y_max must be greater than or equal to zero."
            )

        if self._grid_y <= 0:
            raise ValueError(
                "_grid_y must be greater than zero."
            )

        if y_max == 0:
            ticks = [
                0.0
                for _ in range(self._grid_y + 1)
            ]
        elif self._percentage:
            ticks = [
                index * y_max / self._grid_y
                for index in range(self._grid_y + 1)
            ]
        else:
            ticks = [
                round(index * y_max / self._grid_y, 0)
                for index in range(self._grid_y + 1)
            ]
            ticks = list(set(ticks)) # Ensure uniques

        if self._percentage:
            labels = [
                f"{value:.1f}"
                for value in ticks
            ]

            title = (
                "Cumulative count [%]"
                if self._cumulative
                else "Count [%]"
            )

        else:
            # Histogram counts are normally integers. Keep the formatting
            # compatible with weighted/precomputed floating-point bins too.
            labels = [
                f"{value:.3g}"
                for value in ticks
            ]

            title = (
                "Cumulative count"
                if self._cumulative
                else "Count"
            )

        return ticks, labels, title


    def _axes(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        y_max: float,
    ) -> None:
        """Draw axes, tick marks, labels and axis titles.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plotting area boundaries.
        x_min, x_max : float
            Numerical X-axis range.
        y_max : float
            Numerical Y-axis maximum.
        """
        painter.setFont(self._font)
        painter.setPen(
            QPen(
                self._axis_color,
                self._axis_width,
            )
        )

        if self._show_axes:
            painter.drawLine(
                left,
                bottom,
                right,
                bottom,
            )
            painter.drawLine(
                left,
                top,
                left,
                bottom,
            )

        if not self._show_ticks and not self._show_labels:
            return

        if self._grid_x <= 0:
            raise ValueError(
                "_grid_x must be greater than zero."
            )

        if x_max <= x_min:
            return

        x_ticks = self._x_ticks or [
            x_min
            + index * (x_max - x_min) / self._grid_x
            for index in range(self._grid_x + 1)
        ]

        y_ticks, y_labels, y_title = self._get_y_ticks(y_max)

        if self._show_ticks:
            self._ticks_x(
                painter,
                left,
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
                bottom,
                y_max,
                y_ticks,
            )

        if self._show_labels:
            self._labels_x(
                painter,
                left,
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
                bottom,
                y_max,
                y_ticks,
                y_labels,
            )

        self._titles(
            painter,
            left,
            top,
            right,
            bottom,
            y_title,
        )


    def _ticks_x(
        self,
        painter: QPainter,
        left: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw X-axis tick marks.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, right, bottom : int
            Plotting area boundaries.
        x_min, x_max : float
            Numerical X-axis range.
        ticks : Sequence[float]
            X values at which ticks should be drawn.
        """
        painter.setPen(
            QPen(
                self._axis_color,
                self._tick_width,
            )
        )

        if x_max <= x_min:
            return

        for tick_value in ticks:
            if x_min <= tick_value <= x_max:
                x_position = round(
                    left
                    + (tick_value - x_min)
                    / (x_max - x_min)
                    * (right - left)
                )

                painter.drawLine(
                    x_position,
                    bottom,
                    x_position,
                    bottom + self._tick_length,
                )


    def _ticks_y(
        self,
        painter: QPainter,
        left: int,
        top: int,
        bottom: int,
        y_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw Y-axis tick marks.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, bottom : int
            Plotting area boundaries.
        y_max : float
            Numerical Y-axis maximum.
        ticks : Sequence[float]
            Y values at which ticks should be drawn.
        """
        painter.setPen(
            QPen(
                self._axis_color,
                self._tick_width,
            )
        )

        if y_max <= 0:
            return

        for tick_value in ticks:
            if 0 <= tick_value <= y_max:
                y_position = round(
                    bottom
                    - tick_value / y_max * (bottom - top)
                )

                painter.drawLine(
                    left - self._tick_length,
                    y_position,
                    left,
                    y_position,
                )


    def _labels_x(
        self,
        painter: QPainter,
        left: int,
        right: int,
        bottom: int,
        x_min: float,
        x_max: float,
        ticks: Sequence[float],
    ) -> None:
        """Draw formatted X-axis labels.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, right, bottom : int
            Plotting area boundaries.
        x_min, x_max : float
            Numerical X-axis range.
        ticks : Sequence[float]
            X values whose labels should be drawn.
        """
        painter.setPen(self._text_color)

        if x_max <= x_min:
            return

        metrics = painter.fontMetrics()

        for tick_value in ticks:
            if x_min <= tick_value <= x_max:
                x_position = (
                    left
                    + (tick_value - x_min)
                    / (x_max - x_min)
                    * (right - left)
                )

                label = self._x_formatter(tick_value)
                label_width = metrics.horizontalAdvance(label)

                painter.drawText(
                    round(x_position - label_width / 2),
                    bottom
                    + self._tick_length
                    + metrics.ascent()
                    + 4,
                    label,
                )


    def _labels_y(
        self,
        painter: QPainter,
        left: int,
        top: int,
        bottom: int,
        y_max: float,
        ticks: Sequence[float],
        labels: Sequence[str],
    ) -> None:
        """Draw formatted Y-axis labels.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, bottom : int
            Plotting area boundaries.
        y_max : float
            Numerical Y-axis maximum.
        ticks : Sequence[float]
            Numerical Y positions corresponding to ``labels``.
        labels : Sequence[str]
            Text displayed for each Y-axis tick.

        Raises
        ------
        ValueError
            If the number of labels differs from the number of ticks.
        """
        painter.setPen(self._text_color)

        if len(ticks) != len(labels):
            raise ValueError(
                "The number of Y-axis ticks must match "
                "the number of Y-axis labels."
            )

        if y_max <= 0:
            return

        metrics = painter.fontMetrics()

        for tick_value, label in zip(ticks, labels):
            if 0 <= tick_value <= y_max:
                y_position = (
                    bottom
                    - tick_value / y_max * (bottom - top)
                )

                label_width = metrics.horizontalAdvance(label)

                baseline = (
                    y_position
                    + (metrics.ascent() - metrics.descent()) / 2
                )

                painter.drawText(
                    round(
                        left
                        - self._tick_length
                        - label_width
                        - 6
                    ),
                    round(baseline),
                    label,
                )

    def _titles(
        self,
        painter: QPainter,
        left: int,
        top: int,
        right: int,
        bottom: int,
        y_title: str,
    ) -> None:
        """Draw the X-axis and Y-axis titles.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plotting area boundaries.
        y_title : str
            Title of the Y-axis generated by :meth:`_get_y_ticks`.
        """
        painter.setPen(self._text_color)

        metrics = painter.fontMetrics()

        if self._x_title:
            title_width = metrics.horizontalAdvance(self._x_title)

            painter.drawText(
                round(
                    (left + right - title_width) / 2
                ),
                round(
                    bottom
                    + self._tick_length
                    + metrics.height()
                    + 14
                ),
                self._x_title,
            )

        # Y title above the Y axis, left-aligned with the tick labels.
        title_x = max(
            self._content_margins[0],
            left - metrics.horizontalAdvance(y_title) // 2,
        )

        painter.drawText(
            title_x,
            top - metrics.descent() - 10,
            y_title,
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
        """Draw the border surrounding the plotting area.

        Parameters
        ----------
        painter : QPainter
            Painter used for rendering.
        left, top, right, bottom : int
            Plotting area boundaries.
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