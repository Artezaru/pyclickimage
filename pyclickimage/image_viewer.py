import sys
from PyQt5 import QtWidgets, QtGui, QtCore
from typing import Tuple


class ImageViewer(QtWidgets.QGraphicsView):
    r"""
    A class for viewing and interacting with images in a PyQt5 application.    
    """
    
    left_click_signal = QtCore.pyqtSignal(int, int)  # Signal to emit left-click coordinates
    right_click_signal = QtCore.pyqtSignal(int, int)  # Signal to emit right-click coordinates

    def __init__(self):
        super().__init__()
        
        # Create a scene for the graphics view
        self.setScene(QtWidgets.QGraphicsScene(self))
        self._pixmap_item = None  # Placeholder for the image item
        self._zoom = 0  # Current zoom level
        self._max_zoom = 20  # Maximum zoom level
        self._min_zoom = 0  # Minimum zoom level

        self._minimap_label = QtWidgets.QLabel(self)
        self._minimap_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); border: 1px solid white;")
        self._minimap_label.setVisible(False)  # Initially hidden
        self._minimap_size = 150  # Size of the minimap

        self._minimap_timer = QtCore.QTimer(self)
        self._minimap_timer.setSingleShot(True)
        self._minimap_timer.timeout.connect(self._hide_minimap)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        # Save the click press position to detect if it is a click or a slice release event
        self._click_press_pos = None

        # List to store drawn circles
        self._circles = []
        self._circles_color = QtGui.QColor(255, 0, 0)  # Default circle color is red
        self._circles_radius = 10  # Default circle radius
        self._circles_width = 2  # Default circle pen width

    # ===========================================================================
    # Image Loading and Display
    # ===========================================================================
    def reset_scene(self) -> None:
        r"""
        Reset the scene by clearing all items, including the image and circles.
        Reset also the zoom level and minimap visibility.
        """
        self.scene().clear()
        self._pixmap_item = None
        self._zoom = 0
        self.resetTransform()
        self._minimap_label.setVisible(False)
        self._circles.clear()


    def load_image(self, image_path: str) -> None:
        r"""
        Load an image from the specified path into the viewer.

        Parameters
        ----------
        image_path : str
            Path to the image file to be loaded.
        """
        pixmap = QtGui.QPixmap(image_path)

        if pixmap.isNull():
            print("Failed to load image")
            return
        
        self.reset_scene()  # Clear the scene before loading a new image

        self._pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self._pixmap_item)
        self.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)

 
    def set_image(self, image: QtGui.QPixmap) -> None:
        r"""
        Set the image to be displayed in the viewer.

        Parameters
        ----------
        image : QtGui.QPixmap
            The image to be displayed.
        """
        if not isinstance(image, QtGui.QPixmap):
            raise ValueError("Image must be a QPixmap instance.")
        
        self.reset_scene()
        self._pixmap_item = QtWidgets.QGraphicsPixmapItem(image)
        self.scene().addItem(self._pixmap_item)
        self.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)


    def manual_zoom(self, in_: bool = True) -> None:
        r"""
        Manually zoom in or out of the image.

        Parameters
        ----------
        in_ : bool, optional
            If True, zoom in; if False, zoom out. Default is True.
        """
        if not self._pixmap_item:
            return

        factor = 1.25 if in_ else 0.8
        new_zoom = self._zoom + (1 if in_ else -1)

        if self._min_zoom <= new_zoom <= self._max_zoom:
            if not in_ and not self._can_zoom_out(factor):
                return
            self._zoom = new_zoom
            self.scale(factor, factor)
            self._clamp_to_image()
            self._show_minimap()


    def toggle_drag_mode(self) -> None:
        r"""
        Toggle the drag mode of the viewer between scroll hand drag and no drag.
        """
        mode = self.dragMode()
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag if mode == QtWidgets.QGraphicsView.ScrollHandDrag
                         else QtWidgets.QGraphicsView.ScrollHandDrag)
        
    def reset_view(self) -> None:
        r"""
        Reset the view to the original image size and zoom level.
        """
        if self._pixmap_item:
            self._zoom = 0
            self.resetTransform()
            self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)
            self._clamp_to_image()
            self._show_minimap()


    def _can_zoom_out(self, factor: float) -> bool:
        r"""
        Check if zooming out is possible without exceeding the image bounds.

        Parameters
        ----------
        factor : float
            The zoom factor to apply.

        Returns
        -------
        bool
            True if zooming out is possible, False otherwise.
        """
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        image_rect = self._pixmap_item.sceneBoundingRect()
        predicted_width = view_rect.width() * factor
        predicted_height = view_rect.height() * factor
        return predicted_width <= image_rect.width() + 10 and predicted_height <= image_rect.height() + 10
    

    def _clamp_to_image(self) -> None:
        r"""
        Clamp the view to the image bounds to prevent scrolling outside the image.
        """
        if not self._pixmap_item:
            return

        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        image_rect = self._pixmap_item.sceneBoundingRect()
        dx = dy = 0

        if view_rect.left() < image_rect.left():
            dx = image_rect.left() - view_rect.left()
        elif view_rect.right() > image_rect.right():
            dx = image_rect.right() - view_rect.right()

        if view_rect.top() < image_rect.top():
            dy = image_rect.top() - view_rect.top()
        elif view_rect.bottom() > image_rect.bottom():
            dy = image_rect.bottom() - view_rect.bottom()

        if dx or dy:
            self.translate(dx, dy)


    def _show_minimap(self) -> None:
        r"""
        Show a minimap of the image in the top-left corner of the viewer.
        """
        if not self._pixmap_item:
            return

        image = self._pixmap_item.pixmap().scaled(
            self._minimap_size, self._minimap_size, QtCore.Qt.KeepAspectRatio)
        self._minimap_label.setPixmap(image)
        self._minimap_label.adjustSize()
        self._minimap_label.move(10, 10)
        self._minimap_label.setVisible(True)
        self._update_minimap_viewport()

        # Start a timer to hide the minimap after a short delay
        self._minimap_timer.start(3000)


    def _hide_minimap(self) -> None:
        r"""
        Hide the minimap label.
        """
        self._minimap_label.setVisible(False)

    
    def _update_minimap_viewport(self):
        r"""
        Update the minimap viewport to reflect the current view in the main window.
        """
        if not self._minimap_label.isVisible():
            return

        image_rect = self._pixmap_item.sceneBoundingRect()
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        label_pixmap = self._minimap_label.pixmap()

        if not label_pixmap:
            return

        scale_x = label_pixmap.width() / image_rect.width()
        scale_y = label_pixmap.height() / image_rect.height()
        x = (visible_rect.left() - image_rect.left()) * scale_x
        y = (visible_rect.top() - image_rect.top()) * scale_y
        w = visible_rect.width() * scale_x
        h = visible_rect.height() * scale_y

        overlay = QtGui.QPixmap(label_pixmap.width(), label_pixmap.height())
        overlay.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(overlay)
        painter.setPen(QtGui.QPen(QtCore.Qt.red, 2))
        painter.drawRect(int(x), int(y), int(w), int(h))
        painter.end()

        combined = self._pixmap_item.pixmap().scaled(
            label_pixmap.width(), label_pixmap.height(), QtCore.Qt.KeepAspectRatio)
        painter = QtGui.QPainter(combined)
        painter.drawPixmap(0, 0, overlay)
        painter.end()
        self._minimap_label.setPixmap(combined)


    # ===========================================================================
    # Mouse and Click Events
    # ===========================================================================
    def mousePressEvent(self, event):
        r"""
        Handle mouse press events to save the current click position in order to detect if it is a click or a slice release Event.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            The mouse event containing the position of the click.
        """
        super().mousePressEvent(event)
        self._click_press_pos = event.pos()  # Save the click position

       
    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        r"""
        Handle mouse wheel events for zooming in or out.

        Parameters
        ----------
        event : QtGui.QWheelEvent
            The wheel event containing the scroll direction.
        """
        if event.angleDelta().y() > 0:
            self.manual_zoom(in_=True)
        else:
            self.manual_zoom(in_=False)

        
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        r"""
        Handle mouse release events to emit click coordinates and draw a circle.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            The mouse event containing the position of the click.
        """
        super().mouseReleaseEvent(event)

        self._clamp_to_image()
        self._show_minimap()

        # compute the distance from the click press position to the release position
        if self._click_press_pos is not None:
            distance = (event.pos() - self._click_press_pos).manhattanLength()
            self._click_press_pos = None  # Reset the click press position
        else:
            distance = 0
        
        # If the distance is small, treat it as a click
        if distance <= 1: # in pixels
            # Emit the click coordinates (if left click)
            if event.button() == QtCore.Qt.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                self.left_click_signal.emit(int(scene_pos.x()), int(scene_pos.y()))
                self._show_coordinates(event)

            # Emit the right-click coordinates
            elif event.button() == QtCore.Qt.RightButton:
                scene_pos = self.mapToScene(event.pos())
                self.right_click_signal.emit(int(scene_pos.x()), int(scene_pos.y()))


    def _show_coordinates(self, event: QtGui.QMouseEvent) -> None:
        r"""
        Show the coordinates of the click in the minimap label.

        Parameters
        ----------
        event : QtGui.QMouseEvent
            The mouse event containing the position of the click.
        """
        if not self._pixmap_item:
            return

        scene_pos = self.mapToScene(event.pos())
        coords = f"Coordinates: ({int(scene_pos.x())}, {int(scene_pos.y())})"
        self._minimap_label.setText(coords)
        self._minimap_label.adjustSize()


    # ===========================================================================
    # Circle Drawing and Management
    # ===========================================================================
    def _draw_circle(self, center: QtCore.QPointF, _save: bool = True) -> None:
        r"""
        Draw a circle at the specified center with the given radius.

        Parameters
        ----------
        center : QtCore.QPointF
            The center coordinates of the circle.

        _save : bool, optional
            If True, save the circle to the list of circles. Default is True.
        """
        if not self._pixmap_item:
            return

        # Draw the circle at the specified center
        circle = QtWidgets.QGraphicsEllipseItem(center.x() - self._circles_radius + 0.5,
                                                center.y() - self._circles_radius + 0.5,
                                                2 * self._circles_radius, 2 * self._circles_radius)
        
        # Set the pen color and width for the circle
        pen = QtGui.QPen(self._circles_color)
        pen.setWidth(self._circles_width)
        circle.setPen(pen)
        self.scene().addItem(circle)
        
        # Save the circle to the list if required
        if _save:
            self._circles.append(circle)

    
    def _erase_circle(self, circle: QtWidgets.QGraphicsEllipseItem, _remove: bool = True) -> None:
        r"""
        Erase a specific circle from the scene.

        Parameters
        ----------
        circle : QtWidgets.QGraphicsEllipseItem
            The circle item to be erased.

        remove : bool, optional
            If True, remove the circle from the scene and the circles list. Default is True.
        """
        if circle in self._circles:
            self.scene().removeItem(circle)

            if _remove:
                self._circles.remove(circle)


    def _redraw_circle(self, circle: QtWidgets.QGraphicsEllipseItem):
        r"""
        Redraw a specific circle in the scene.

        Parameters
        ----------
        circle : QtWidgets.QGraphicsEllipseItem
            The circle item to be redrawn.
        """
        if circle not in self._circles:
            raise ValueError("Circle not found in the circles list.")
        
        self._erase_circle(circle, _remove=False)  # Remove the circle from the scene without deleting it
        self._draw_circle(QtCore.QPointF(circle.rect().center().x(), circle.rect().center().y()), _save=False)  # Redraw the circle at its center


    def _redraw_all_circles(self) -> None:
        r"""
        Redraw all circles in the scene.
        """
        for circle in self._circles:
            self._redraw_circle(circle)


    def add_circle(self, center: Tuple[float, float]) -> None:
        r"""
        Add a circle to the scene at the specified center with the given radius.

        Parameters
        ----------
        center : Tuple[float, float]
            The center coordinates of the circle.
        radius : int, optional
            The radius of the circle. Default is 10.
        """
        if not isinstance(center, tuple) or len(center) != 2:
            raise ValueError("Center must be a tuple of (x, y) coordinates.")
        
        self._draw_circle(QtCore.QPointF(center[0], center[1]))


    def remove_circle(self, index: int) -> None:
        r"""
        Remove a circle from the scene by its index.

        Parameters
        ----------
        index : int
            The index of the circle to remove.
        
        Raises
        ------
        IndexError
            If the index is out of range for the circles list.
        """
        if index < 0 or index >= len(self._circles):
            raise IndexError("Circle index out of range.")
        
        self._erase_circle(self._circles[index])


    def remove_all_circles(self) -> None:
        r"""
        Remove all circles from the scene.
        """
        for circle in self._circles:
            self._erase_circle(circle, _remove=False)
        self._circles.clear()


    @property
    def circles_color(self) -> QtGui.QColor:
        r"""
        Get the color of the circles.

        Returns
        -------
        QtGui.QColor
            The color of the circles.
        """
        return self._circles_color
    
    @circles_color.setter
    def circles_color(self, color: QtGui.QColor) -> None:
        r"""
        Set the color of the circles.

        Parameters
        ----------
        color : QtGui.QColor
            The new color for the circles.
        """
        if not isinstance(color, QtGui.QColor):
            raise ValueError("Color must be a QColor instance.")
        self._circles_color = color
        self._redraw_all_circles()

    @property
    def circles_radius(self) -> int:
        r"""
        Get the radius of the circles.

        Returns
        -------
        int
            The radius of the circles.
        """
        return self._circles_radius
    
    @circles_radius.setter
    def circles_radius(self, radius: int) -> None:
        r"""
        Set the radius of the circles.

        Parameters
        ----------
        radius : int
            The new radius for the circles.
        
        Raises
        ------
        ValueError
            If the radius is not a positive integer.
        """
        if not isinstance(radius, int) or radius <= 0:
            raise ValueError("Radius must be a positive integer.")
        self._circles_radius = radius
        self._redraw_all_circles()

    @property
    def circles_width(self) -> int:
        r"""
        Get the width of the circle pen.

        Returns
        -------
        int
            The width of the circle pen.
        """
        return self._circles_width
    
    @circles_width.setter
    def circles_width(self, width: int) -> None:
        r"""
        Set the width of the circle pen.

        Parameters
        ----------
        width : int
            The new width for the circle pen.
        
        Raises
        ------
        ValueError
            If the width is not a positive integer.
        """
        if not isinstance(width, int) or width <= 0:
            raise ValueError("Width must be a positive integer.")
        self._circles_width = width
        self._redraw_all_circles()



