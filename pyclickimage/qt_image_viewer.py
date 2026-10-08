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

from typing import List, Optional, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets


class QtImageViewer(QtWidgets.QGraphicsView):
    r"""Interactive image viewer with zoom, annotations and selection.

    The widget displays a :class:`QPixmap` inside a
    :class:`QGraphicsScene` and provides:

    - subpixel image-coordinate tracking;
    - configurable crosshair;
    - mouse-coordinate signals;
    - mouse click signals;
    - zoom using the mouse wheel;
    - panning by dragging with the left mouse button;
    - click-safe left and right mouse signals;
    - cross, rectangle and ellipse markers;
    - rectangular region selection by mouse dragging.

    Image coordinates are expressed in the coordinate system of the
    displayed pixmap. When ``half_shift`` is enabled, coordinates are
    shifted by ``-0.5`` so that the center of the first pixel corresponds
    to ``(0, 0)``.

    Parameters
    ----------
    parent : QWidget, optional
        Parent Qt widget.
    half_shift : bool, default=True
        If ``True``, pixel centers are represented using coordinates
        ``(0, 0)`` for the first pixel. If ``False``, coordinates refer
        to pixel corners.

    Signals
    -------
    mouse_entered : pyqtSignal(float, float)
        Emitted when the mouse cursor enters the image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate of the cursor.
        y : float
            Vertical image coordinate of the cursor.

    mouse_moved : pyqtSignal(float, float)
        Emitted whenever the mouse cursor moves while it is inside the
        image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate of the cursor.
        y : float
            Vertical image coordinate of the cursor.

    mouse_left : pyqtSignal()
        Emitted when the mouse cursor leaves the image.

    left_pressed : pyqtSignal(float, float)
        Emitted when the left mouse button is pressed inside the image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate at the press position.
        y : float
            Vertical image coordinate at the press position.

    left_released : pyqtSignal(float, float)
        Emitted when the left mouse button is released inside the image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate at the release position.
        y : float
            Vertical image coordinate at the release position.

    right_pressed : pyqtSignal(float, float)
        Emitted when the right mouse button is pressed inside the image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate at the press position.
        y : float
            Vertical image coordinate at the press position.

    right_released : pyqtSignal(float, float)
        Emitted when the right mouse button is released inside the image.

        Parameters
        ----------
        x : float
            Horizontal image coordinate at the release position.
        y : float
            Vertical image coordinate at the release position.

    left_click : pyqtSignal(float, float)
        Emitted when a left-button press and release are detected as a
        click rather than as a drag. A left-button drag pans the view
        and does not emit this signal.

        Parameters
        ----------
        x : float
            Horizontal image coordinate of the click.
        y : float
            Vertical image coordinate of the click.

    right_click : pyqtSignal(float, float)
        Emitted when a right-button press and release are detected as a
        click rather than as a drag.

        Parameters
        ----------
        x : float
            Horizontal image coordinate of the click.
        y : float
            Vertical image coordinate of the click.

    rectangle_selected : pyqtSignal(float, float, float, float)
        Emitted when a right-button drag is finished. A right-button
        click (movement of at most 2 px) does not emit this signal.

        Parameters
        ----------
        x : float
            Horizontal image coordinate of the top-left corner of the
            selected rectangle.
        y : float
            Vertical image coordinate of the top-left corner of the
            selected rectangle.
        width : float
            Width of the selected rectangle in image coordinates.
        height : float
            Height of the selected rectangle in image coordinates.

    Notes
    -----
    All ``x`` and ``y`` coordinates are expressed in image coordinates,
    not widget or scene coordinates.

    When ``half_shift=True``, the center of the first pixel has coordinates
    ``(0, 0)``. When ``half_shift=False``, coordinates correspond directly
    to the image coordinate system used by the underlying
    ``QGraphicsPixmapItem``.

    For selection signals, ``x`` and ``y`` always identify the top-left
    corner of the normalized rectangle, regardless of the direction in
    which the user dragged the mouse. ``width`` and ``height`` are
    therefore always non-negative.


    Notes
    -----
    Mouse bindings:

    - wheel: zoom around the cursor;
    - left button: click (``left_click``), or pan the view when dragged;
    - right button: click (``right_click``), or rectangular selection
      (``rectangle_selected``) when dragged.

    A drag is distinguished from a click using a small movement
    tolerance (2 px). A drag therefore does not emit ``left_click`` or
    ``right_click``. Panning only starts once the tolerance is
    exceeded, so a click never moves the image.

    Mouse signals are only emitted while an image is displayed.
    :meth:`clear_image` removes the image; :meth:`has_image` tells
    whether one is displayed.

    To refresh the pixels without losing the zoom or the markers (for
    example after a colormap change), call
    ``set_image(pixmap, reset_view=False)``.
    """

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

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        half_shift: bool = True,
    ) -> None:
        """Initialize the image viewer.

        Parameters
        ----------
        parent : QWidget, optional
            Parent Qt widget.
        half_shift : bool, default=True
            Whether image coordinates are shifted by half a pixel.
        """
        super().__init__(parent)

        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QtWidgets.QGraphicsPixmapItem] = None
        self._press_pos: Optional[QtCore.QPoint] = None
        self._drag_start: Optional[QtCore.QPointF] = None

        self._selecting = False
        self._inside = False

        # Panning with a left-button drag. ``_pan_last`` is set while the
        # left button is pressed; ``_translating`` becomes True once the
        # click tolerance is exceeded.
        self._translating = False
        self._pan_last: Optional[QtCore.QPoint] = None

        # Maximum movement (Manhattan length, in widget pixels) between
        # press and release for a click.
        self._click_tolerance = 2

        self._zoom = 0
        self._max_zoom = 100
        self._min_zoom = -50

        self._half_shift = bool(half_shift)
        self.auto_marker = True

        self._crosshair_color = QtGui.QColor(255, 0, 0)
        self._cross_h = QtWidgets.QGraphicsLineItem()
        self._cross_v = QtWidgets.QGraphicsLineItem()

        self._selection_item: Optional[QtWidgets.QGraphicsRectItem] = None
        self._markers: List[QtWidgets.QGraphicsItem] = []

        self._coord_label = QtWidgets.QLabel(self)
        self._coord_label.setStyleSheet(
            "background: rgba(0,0,0,180); color: white;"
            "padding: 3px; border: 1px solid white;"
        )
        self._coord_label.move(10, 10)
        self._coord_label.hide()

        self.setMouseTracking(True)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.AnchorUnderMouse
        )
        self.setResizeAnchor(
            QtWidgets.QGraphicsView.AnchorUnderMouse
        )
        # Panning is handled manually with a left-button drag (see
        # mouseMoveEvent), so that a left click never moves the image.
        self.setDragMode(
            QtWidgets.QGraphicsView.NoDrag
        )

        self._create_crosshair()

    @property
    def half_shift(self) -> bool:
        """Whether image coordinates use half-pixel shifting.

        Returns
        -------
        bool
            ``True`` when the first pixel center corresponds to
            ``(0, 0)``.
        """
        return self._half_shift

    @half_shift.setter
    def half_shift(self, value: bool) -> None:
        """Set the image-coordinate convention.

        Parameters
        ----------
        value : bool
            If ``True``, subtract ``0.5`` from scene coordinates when
            converting them to image coordinates.
        """
        self._half_shift = bool(value)

    @property
    def crosshair_color(self) -> QtGui.QColor:
        """Color used to draw the crosshair.

        Returns
        -------
        QColor
            Current crosshair color.
        """
        return QtGui.QColor(self._crosshair_color)

    @crosshair_color.setter
    def crosshair_color(
        self,
        color: QtGui.QColor,
    ) -> None:
        """Set the crosshair color.

        Parameters
        ----------
        color : QColor
            New crosshair color.
        """
        self._crosshair_color = QtGui.QColor(color)

        pen = QtGui.QPen(self._crosshair_color)
        pen.setWidthF(0)

        self._cross_h.setPen(pen)
        self._cross_v.setPen(pen)

    def load_image(self, path: str) -> None:
        """Load an image from a file.

        Parameters
        ----------
        path : str
            Path to the image file.

        Raises
        ------
        ValueError
            If the image cannot be loaded.
        """
        pixmap = QtGui.QPixmap(path)

        if pixmap.isNull():
            raise ValueError(
                f"Unable to load image: {path}"
            )

        self.set_image(pixmap)

    def set_image(
        self,
        pixmap: QtGui.QPixmap,
        reset_view: bool = True,
    ) -> None:
        """Set the image displayed by the viewer.

        Parameters
        ----------
        pixmap : QPixmap
            Image to display.
        reset_view : bool, default=True
            If ``True``, the scene is rebuilt: existing markers and the
            current selection are removed and the view is fitted to the
            image.

            If ``False`` and the new pixmap has the same size as the
            displayed one, only the pixels are replaced. Markers, zoom
            and pan are preserved. This is the mode used to refresh the
            display after a colormap change. If the size differs, the
            method falls back to ``reset_view=True``.

        Raises
        ------
        ValueError
            If ``pixmap`` is null.
        """
        if pixmap.isNull():
            raise ValueError("pixmap must contain a valid image.")

        if (
            not reset_view
            and self._pixmap_item is not None
            and self._pixmap_item.pixmap().size() == pixmap.size()
        ):
            self._pixmap_item.setPixmap(pixmap)
            return

        self._scene.clear()

        self._pixmap_item = QtWidgets.QGraphicsPixmapItem(
            pixmap
        )
        self._scene.addItem(self._pixmap_item)

        self._cross_h = QtWidgets.QGraphicsLineItem()
        self._cross_v = QtWidgets.QGraphicsLineItem()

        self._create_crosshair()

        self._selection_item = None
        self._markers.clear()

        self.setSceneRect(
            self._pixmap_item.boundingRect()
        )

        self.resetTransform()
        self.fitInView(
            self._pixmap_item,
            QtCore.Qt.KeepAspectRatio,
        )

        self._zoom = 0

    def clear_image(self) -> None:
        """Remove the displayed image, markers and selection.

        After this call the viewer is empty: no coordinate signal is
        emitted until a new image is set with :meth:`set_image`.
        """
        self._scene.clear()

        self._pixmap_item = None
        self._selection_item = None
        self._markers.clear()

        self._inside = False
        self._selecting = False
        self._press_pos = None
        self._drag_start = None
        self._stop_panning()

        # The crosshair items were destroyed by ``clear``.
        self._cross_h = QtWidgets.QGraphicsLineItem()
        self._cross_v = QtWidgets.QGraphicsLineItem()

        self._create_crosshair()

        self._coord_label.hide()

        self.resetTransform()
        self.setSceneRect(QtCore.QRectF())
        self._zoom = 0

    def has_image(self) -> bool:
        """Return whether an image is currently displayed.

        Returns
        -------
        bool
            ``True`` if :meth:`set_image` was called and the image was
            not removed with :meth:`clear_image`.
        """
        return self._pixmap_item is not None

    def set_crosshair_color(
        self,
        color: QtGui.QColor,
    ) -> None:
        """Set the crosshair color.

        Method equivalent of the :attr:`crosshair_color` setter, kept
        for symmetry with :meth:`get_crosshair_color`.

        Parameters
        ----------
        color : QColor
            New crosshair color.
        """
        self.crosshair_color = color

    def get_crosshair_color(self) -> QtGui.QColor:
        """Return the current crosshair color.

        Returns
        -------
        QColor
            Current crosshair color.
        """
        return QtGui.QColor(self._crosshair_color)

    def _create_crosshair(self) -> None:
        """Create the graphical crosshair items."""
        pen = QtGui.QPen(self._crosshair_color)
        pen.setWidthF(0)

        self._cross_h.setPen(pen)
        self._cross_v.setPen(pen)

        self._scene.addItem(self._cross_h)
        self._scene.addItem(self._cross_v)

        self._cross_h.hide()
        self._cross_v.hide()

    def get_x_line(self) -> QtWidgets.QGraphicsLineItem:
        """Return the vertical crosshair line.

        Returns
        -------
        QGraphicsLineItem
            Graphics item representing the line at the current
            x-coordinate.
        """
        return self._cross_v

    def get_y_line(self) -> QtWidgets.QGraphicsLineItem:
        """Return the horizontal crosshair line.

        Returns
        -------
        QGraphicsLineItem
            Graphics item representing the line at the current
            y-coordinate.
        """
        return self._cross_h

    def _scene_to_image(
        self,
        point: QtCore.QPointF,
    ) -> Tuple[float, float]:
        """Convert scene coordinates to image coordinates."""
        shift = 0.5 if self._half_shift else 0.0
        return point.x() - shift, point.y() - shift

    def _image_to_scene(
        self,
        x: float,
        y: float,
    ) -> QtCore.QPointF:
        """Convert image coordinates to scene coordinates."""
        shift = 0.5 if self._half_shift else 0.0
        return QtCore.QPointF(x + shift, y + shift)

    def _inside_image(self, point: QtCore.QPointF) -> bool:
        """Return whether a scene position is inside the image."""
        return (
            self._pixmap_item is not None
            and self._pixmap_item.sceneBoundingRect().contains(point)
        )

    def _clamp_to_image(
        self,
        point: QtCore.QPointF,
    ) -> QtCore.QPointF:
        """Clamp a scene position to the image boundaries."""
        rect = self._pixmap_item.sceneBoundingRect()

        return QtCore.QPointF(
            max(rect.left(), min(point.x(), rect.right())),
            max(rect.top(), min(point.y(), rect.bottom())),
        )

    def _selection_rect(
        self,
        current: QtCore.QPointF,
    ) -> QtCore.QRectF:
        """Return the normalized selection rectangle."""
        start = self._clamp_to_image(self._drag_start)
        end = self._clamp_to_image(current)

        return QtCore.QRectF(
            min(start.x(), end.x()),
            min(start.y(), end.y()),
            abs(end.x() - start.x()),
            abs(end.y() - start.y()),
        )

    def _rect_to_image(
        self,
        rect: QtCore.QRectF,
    ) -> Tuple[float, float, float, float]:
        """Convert a scene rectangle to image coordinates."""
        x, y = self._scene_to_image(rect.topLeft())

        shift = 0.5 if self._half_shift else 0.0
        return (
            x,
            y,
            rect.width(),
            rect.height(),
        )

    def _stop_panning(self) -> None:
        """End a left-button pan and restore the cursor."""
        if self._translating:
            self.viewport().unsetCursor()

        self._translating = False
        self._pan_last = None

    def _pan(self, event: QtGui.QMouseEvent) -> None:
        """Pan the view during a left-button drag.

        Notes
        -----
        Panning starts once the cursor has moved more than the click
        tolerance from the press position. The first step then applies
        the whole displacement since the press, so the image stays
        under the cursor. The scroll bars are moved by the cursor
        displacement.
        """
        if self._pan_last is None:
            return

        if not self._translating:
            if self._press_pos is None:
                return

            distance = (event.pos() - self._press_pos).manhattanLength()

            if distance <= self._click_tolerance:
                return

            self._translating = True
            self.viewport().setCursor(QtCore.Qt.ClosedHandCursor)

        delta = event.pos() - self._pan_last
        self._pan_last = event.pos()

        horizontal = self.horizontalScrollBar()
        vertical = self.verticalScrollBar()

        horizontal.setValue(horizontal.value() - delta.x())
        vertical.setValue(vertical.value() - delta.y())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Process mouse movement, panning and selection updates.

        While the left button is pressed and dragged, the view follows
        the cursor (see :meth:`_pan`).
        """
        super().mouseMoveEvent(event)

        if event.buttons() & QtCore.Qt.LeftButton:
            self._pan(event)

        pos = self.mapToScene(event.pos())
        inside = self._inside_image(pos)

        if inside:
            x, y = self._scene_to_image(pos)

            if not self._inside:
                self._inside = True
                self.mouse_entered.emit(x, y)

            rect = self._pixmap_item.sceneBoundingRect()
            self._cross_h.setLine(
                rect.left(), pos.y(),
                rect.right(), pos.y(),
            )
            self._cross_v.setLine(
                pos.x(), rect.top(),
                pos.x(), rect.bottom(),
            )
            self._cross_h.show()
            self._cross_v.show()

            self.mouse_moved.emit(x, y)

            self._coord_label.setText(
                f"X={x:.3f}  Y={y:.3f}"
            )
            self._coord_label.adjustSize()
            self._coord_label.show()

        elif self._inside:
            self._inside = False
            self._cross_h.hide()
            self._cross_v.hide()
            self._coord_label.hide()
            self.mouse_left.emit()

        if self._selecting and self._pixmap_item is not None:
            self._update_selection(pos)


    def leaveEvent(self, event: QtCore.QEvent) -> None:
        """Hide the crosshair when the cursor leaves the widget.

        Leaving the widget directly from the image (for example toward
        a neighboring panel) hides the crosshair and emits
        :attr:`mouse_left`.
        """
        if self._inside:
            self._inside = False
            self._cross_h.hide()
            self._cross_v.hide()
            self._coord_label.hide()
            self.mouse_left.emit()

        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Process mouse-button presses.

        A left press starts a potential click or pan, and a right press
        starts a potential click or rectangular selection.
        """
        super().mousePressEvent(event)

        if self._pixmap_item is None:
            return

        pos = self.mapToScene(event.pos())

        x, y = self._scene_to_image(pos)

        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.pos()
            self._drag_start = pos
            self._translating = False
            self._pan_last = event.pos()
            self.left_pressed.emit(x, y)
            return

        if event.button() == QtCore.Qt.RightButton:
            self._press_pos = event.pos()
            self._drag_start = pos
            self._selecting = True
            self.right_pressed.emit(x, y)
            return

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Process mouse-button releases.

        Notes
        -----
        A release within 2 px of the press position is a click and emits
        :attr:`left_click` or :attr:`right_click`. A left-button release
        after a larger movement ends the pan. A right-button release
        after a larger movement finishes the selection and emits
        :attr:`rectangle_selected`.
        """
        super().mouseReleaseEvent(event)

        panned = False

        if event.button() == QtCore.Qt.LeftButton:
            panned = self._translating
            self._stop_panning()

        if self._pixmap_item is None:
            self._press_pos = None
            self._drag_start = None
            self._selecting = False
            return

        pos = self.mapToScene(event.pos())
        inside = self._inside_image(pos)
        x, y = self._scene_to_image(pos)

        distance = (
            (event.pos() - self._press_pos).manhattanLength()
            if self._press_pos is not None
            else 0
        )

        if event.button() == QtCore.Qt.LeftButton:
            self.left_released.emit(x, y)

            if not panned and distance <= self._click_tolerance and inside:
                self.left_click.emit(x, y)
                if self.auto_marker:
                    self.draw_cross(x, y)

        elif event.button() == QtCore.Qt.RightButton:
            self.right_released.emit(x, y)

            if distance <= self._click_tolerance:
                if inside:
                    self.right_click.emit(x, y)

                self.clear_selection()

            elif self._selecting:
                self._finish_selection(pos)

        self._press_pos = None
        self._drag_start = None
        self._selecting = False

    def _update_selection(
        self,
        current: QtCore.QPointF,
    ) -> None:
        """Update and emit the current selection rectangle."""
        rect = self._selection_rect(current)

        if not self._selecting:
            self._selecting = True
            x, y, _, _ = self._rect_to_image(rect)

        if self._selection_item is None:
            pen = QtGui.QPen(QtGui.QColor(255, 255, 0))
            pen.setWidthF(0)
            pen.setStyle(QtCore.Qt.DashLine)

            brush = QtGui.QBrush(
                QtGui.QColor(255, 255, 0, 40)
            )

            self._selection_item = QtWidgets.QGraphicsRectItem()
            self._selection_item.setPen(pen)
            self._selection_item.setBrush(brush)
            self._scene.addItem(self._selection_item)

        self._selection_item.setRect(rect)

    def _finish_selection(
        self,
        current: QtCore.QPointF,
    ) -> None:
        """Finish the current rectangular selection."""
        if self._drag_start is None or self._pixmap_item is None:
            return

        rect = self._selection_rect(current)

        if rect.width() <= 0 and rect.height() <= 0:
            self.clear_selection()
            return

        values = self._rect_to_image(rect)
        self.rectangle_selected.emit(*values)

        self.clear_selection()

    def clear_selection(self) -> None:
        """Remove the current selection overlay."""
        if self._selection_item is not None:
            self._scene.removeItem(self._selection_item)
            self._selection_item = None

    def draw_cross(
        self,
        x: float,
        y: float,
        color: QtGui.QColor = QtGui.QColor(0, 0, 255),
        size: float = 8.0,
        width: float = 0.0,
    ) -> Tuple[
        QtWidgets.QGraphicsLineItem,
        QtWidgets.QGraphicsLineItem,
    ]:
        """Draw a cross marker.

        Parameters
        ----------
        x, y : float
            Image coordinates.
        color : QColor, default=blue
            Marker color.
        size : float, default=8
            Half-size of the cross.
        width : float, default=0
            Pen width.

        Returns
        -------
        tuple of QGraphicsLineItem
            Horizontal and vertical marker lines.
        """
        p = self._image_to_scene(x, y)
        pen = QtGui.QPen(color)
        pen.setWidthF(width)

        h = QtWidgets.QGraphicsLineItem(
            p.x() - size, p.y(),
            p.x() + size, p.y(),
        )
        v = QtWidgets.QGraphicsLineItem(
            p.x(), p.y() - size,
            p.x(), p.y() + size,
        )

        h.setPen(pen)
        v.setPen(pen)
        self._scene.addItem(h)
        self._scene.addItem(v)
        self._markers.extend((h, v))

        return h, v

    def draw_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: QtGui.QColor = QtGui.QColor(0, 255, 0),
        pen_width: float = 0.0,
        brush: Optional[QtGui.QBrush] = None,
    ) -> QtWidgets.QGraphicsRectItem:
        """Draw a rectangular marker."""
        p = self._image_to_scene(x, y)
        item = QtWidgets.QGraphicsRectItem(
            p.x(), p.y(), width, height
        )

        pen = QtGui.QPen(color)
        pen.setWidthF(pen_width)
        item.setPen(pen)

        if brush is not None:
            item.setBrush(brush)

        self._scene.addItem(item)
        self._markers.append(item)
        return item

    def draw_ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: QtGui.QColor = QtGui.QColor(255, 0, 255),
        pen_width: float = 0.0,
        brush: Optional[QtGui.QBrush] = None,
    ) -> QtWidgets.QGraphicsEllipseItem:
        """Draw an elliptical marker."""
        p = self._image_to_scene(x, y)
        item = QtWidgets.QGraphicsEllipseItem(
            p.x(), p.y(), width, height
        )

        pen = QtGui.QPen(color)
        pen.setWidthF(pen_width)
        item.setPen(pen)

        if brush is not None:
            item.setBrush(brush)

        self._scene.addItem(item)
        self._markers.append(item)
        return item

    def clear_markers(self) -> None:
        """Remove all user markers."""
        for item in self._markers:
            self._scene.removeItem(item)
        self._markers.clear()

    def reset_view(self) -> None:
        """Reset the view and fit the image."""
        if self._pixmap_item is None:
            return

        self._zoom = 0
        self.resetTransform()
        self.fitInView(
            self._pixmap_item,
            QtCore.Qt.KeepAspectRatio,
        )

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Zoom around the mouse position.

        The wheel only zooms: it never scrolls the view (panning is a
        left-button drag).
        """
        if self._pixmap_item is None:
            return

        if event.angleDelta().y() > 0:
            if self._zoom >= self._max_zoom:
                return
            self.scale(1.1, 1.1)
            self._zoom += 1
        else:
            if self._zoom <= self._min_zoom:
                return
            self.scale(1 / 1.1, 1 / 1.1)
            self._zoom -= 1

    def resizeEvent(
        self,
        event: QtGui.QResizeEvent,
    ) -> None:
        """Handle viewer resizing without destroying an active zoom."""
        super().resizeEvent(event)

        if self._pixmap_item is None:
            return

        if self._zoom == 0:
            self.fitInView(
                self._pixmap_item,
                QtCore.Qt.KeepAspectRatio,
            )