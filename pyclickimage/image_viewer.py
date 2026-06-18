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

from typing import Tuple, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class ImageViewer(QtWidgets.QGraphicsView):
    r"""
    Interactive image viewer with:
    - subpixel cursor tracking
    - crosshair overlay
    - zoom with mouse wheel
    - precise click detection (drag-safe)
    - marker system for annotation
    """
    left_click_signal = QtCore.pyqtSignal(float, float)
    right_click_signal = QtCore.pyqtSignal(float, float)

    # ======================================================================
    # INIT
    # ======================================================================

    def __init__(self, parent=None):
        r"""
        Initialize the ImageViewer.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QtWidgets.QGraphicsPixmapItem] = None
        self._press_pos: Optional[QtCore.QPoint] = None

        # ------------------------------------------------------------------
        # Zoom state
        # ------------------------------------------------------------------
        self._zoom = 0
        self._max_zoom = 100
        self._min_zoom = -50

        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)

        # ------------------------------------------------------------------
        # Crosshair (red guide lines)
        # ------------------------------------------------------------------
        self._crosshair_color = QtGui.QColor(255, 0, 0)
        self._create_crosshair()

        # ------------------------------------------------------------------
        # Coordinate label
        # ------------------------------------------------------------------
        self._coord_label = QtWidgets.QLabel(self)
        self._coord_label.setStyleSheet("""
            background-color: rgba(0,0,0,180);
            color: white;
            padding: 3px;
            border: 1px solid white;
        """)
        self._coord_label.move(10, 10)
        self._coord_label.hide()

        # ------------------------------------------------------------------
        # Markers storage
        # ------------------------------------------------------------------
        self._markers: List[
            Tuple[QtWidgets.QGraphicsLineItem, QtWidgets.QGraphicsLineItem]
        ] = []
        self.auto_marker = True

    # ======================================================================
    # IMAGE LOADING
    # ======================================================================
    def load_image(self, path: str) -> None:
        r"""
        Load an image into the viewer.

        Parameters
        ----------
        path : str
            Path to image file.

        Raises
        ------
        ValueError
            If image cannot be loaded.
        """
        pixmap = QtGui.QPixmap(path)
        self.set_image(pixmap=pixmap)

    def set_image(self, pixmap: QtGui.QPixmap):
        r"""
        Set the displayed image in the viewer.

        Parameters
        ----------
        pixmap : QtGui.QPixmap
            Image already converted for Qt display.
        """

        if not hasattr(self, "_scene"):
            self._scene = QtWidgets.QGraphicsScene(self)
            self.setScene(self._scene)

        self._scene.clear()

        self._pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self._create_crosshair()

        self.setSceneRect(self._pixmap_item.boundingRect())

        self.resetTransform()
        self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)

        # IMPORTANT: reset markers if needed
        self._zoom = 0
        self._markers = []
        
    # ======================================================================
    # CROSSHAIR MANAGEMENT
    # ======================================================================
    def get_crosshair_color(self) -> QtGui.QColor:
        r"""
        Return current crosshair color.
        """
        return self._crosshair_color
        
        
    def set_crosshair_color(self, color):
        r"""
        Set the crosshair color
        """
        self._crosshair_color = QtGui.QColor(color)

        pen = QtGui.QPen(self._crosshair_color)
        pen.setWidthF(0)

        self._cross_h.setPen(pen)
        self._cross_v.setPen(pen)
        
    def _create_crosshair(self):
        r"""
        Create the crosshair
        """
        pen = QtGui.QPen(self._crosshair_color)
        pen.setWidthF(0)

        self._cross_h = QtWidgets.QGraphicsLineItem()
        self._cross_v = QtWidgets.QGraphicsLineItem()

        self._cross_h.setPen(pen)
        self._cross_v.setPen(pen)

        self._scene.addItem(self._cross_h)
        self._scene.addItem(self._cross_v)

        self._cross_h.hide()
        self._cross_v.hide()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        r"""
        Update crosshair and coordinate display.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            Mouse move event.
        """
        super().mouseMoveEvent(event)

        if self._pixmap_item is None:
            return

        scene_pos = self.mapToScene(event.pos())
        rect = self._pixmap_item.sceneBoundingRect()

        if not rect.contains(scene_pos):
            self._cross_h.hide()
            self._cross_v.hide()
            return

        self._cross_h.show()
        self._cross_v.show()

        self._cross_h.setLine(rect.left(), scene_pos.y(), rect.right(), scene_pos.y())

        self._cross_v.setLine(scene_pos.x(), rect.top(), scene_pos.x(), rect.bottom())

        self._coord_label.show()
        self._coord_label.setText(f"X={scene_pos.x():.3f}  Y={scene_pos.y():.3f}")
        self._coord_label.adjustSize()


    # ======================================================================
    # ZOOM
    # ======================================================================

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        r"""
        Handle zoom with mouse wheel.

        Parameters
        ----------
        event : QtGui.QWheelEvent
            Wheel event.
        """
        if self._pixmap_item is None:
            return

        factor = 1.1

        if event.angleDelta().y() > 0:
            if self._zoom >= self._max_zoom:
                return
            self.scale(factor, factor)
            self._zoom += 1
        else:
            if self._zoom <= self._min_zoom:
                return
            self.scale(1.0 / factor, 1.0 / factor)
            self._zoom -= 1

    def reset_view(self) -> None:
        r"""
        Reset the view to the initial state (no zoom, centered image).

        This method:
        - resets the internal zoom counter
        - resets Qt transformation matrix
        - re-applies fitInView on the current image
        """

        if self._pixmap_item is None:
            return

        # Reset zoom state
        self._zoom = 0

        # Reset transformation (important: clears wheel scaling)
        self.resetTransform()

        # Re-fit image in view (original behavior)
        self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)

        # Optional: re-anchor correctly
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

    # ======================================================================
    # CLICK HANDLING (SUBPIXEL SAFE)
    # ======================================================================

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        r"""
        Store press position for click validation.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            Mouse press event.
        """
        self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        r"""
        Detect valid click and emit coordinates.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            Mouse release event.
        """
        super().mouseReleaseEvent(event)

        if self._pixmap_item is None or self._press_pos is None:
            return

        distance = (event.pos() - self._press_pos).manhattanLength()
        self._press_pos = None

        # Ignore drag
        if distance > 2:
            return

        scene_pos = self.mapToScene(event.pos())
        rect = self._pixmap_item.sceneBoundingRect()

        if not rect.contains(scene_pos):
            return

        x, y = scene_pos.x(), scene_pos.y()

        if event.button() == QtCore.Qt.LeftButton:
            self.left_click_signal.emit(x, y)

        elif event.button() == QtCore.Qt.RightButton:
            self.right_click_signal.emit(x, y)

        if self.auto_marker:
            self.add_marker((x, y), QtGui.QColor(0, 0, 255))

    # ======================================================================
    # MARKERS (SUBPIXEL CROSS STYLE)
    # ======================================================================

    def add_marker(
        self,
        center: Tuple[float, float],
        color: QtGui.QColor = QtGui.QColor(0, 0, 255),
        size: int = 8,
    ) -> None:
        r"""
        Add a cross-style marker at a given position.

        Parameters
        ----------
        center : Tuple[float, float]
            (x, y) coordinates.
        color : QtGui.QColor
            Marker color.
        size : int
            Half-size of cross arms.
        """
        x, y = center

        pen = QtGui.QPen(color)
        pen.setWidthF(0)

        hline = QtWidgets.QGraphicsLineItem(x - size, y, x + size, y)
        vline = QtWidgets.QGraphicsLineItem(x, y - size, x, y + size)

        hline.setPen(pen)
        vline.setPen(pen)

        self.scene().addItem(hline)
        self.scene().addItem(vline)

        self._markers.append((hline, vline))

    def clear_markers(self) -> None:
        r"""
        Remove all markers from the scene.
        """
        for hline, vline in self._markers:
            self.scene().removeItem(hline)
            self.scene().removeItem(vline)

        self._markers.clear()
