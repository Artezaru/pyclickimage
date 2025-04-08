import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import numpy
import cv2
from .click_manager import ClickManager
from typing import Optional


class ClickImageApp(QtWidgets.QMainWindow):
    """
    A PyQt application to collect mouse clicks on an image,
    grouping them by user-defined categories.

    Parameters
    ----------
    image : Optional[numpy.ndarray]
        The input image to be displayed, loaded in GRAY or BGR format using OpenCV.
    output_csv_path : Optional[str]
        The path where the output csv file will be saved.
    """

    def __init__(self, image: Optional[numpy.ndarray] = None, output_csv_path: Optional[str] = None):
        super().__init__()

        self.set_image(image)
        if output_csv_path is None:
            output_csv_path = "clicks.csv"

        self.click_manager = ClickManager()
        self.setWindowTitle("Click Image UI")

        self.initialization_done = False
        self.init_ui(output_csv_path)
        self.initialization_done = True
        self.update()


    def init_ui(self, output_csv_path: str):
        """
        Initialize the UI layout, widgets, and connect signals.
        """
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(layout)

        # Left side: Image display
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area, stretch=3)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.on_mouse_click

        self.scroll_area.setWidget(self.image_label)  # Ajouter l'image dans le scroll_area

        # Right side: Organize widgets in logical groups
        side_panel = QtWidgets.QVBoxLayout()

        # Side panel widget with a fixed width
        side_panel_widget = QtWidgets.QWidget()
        side_panel_widget.setLayout(side_panel)
        side_panel_widget.setMinimumWidth(350)  # Fixed width for the side panel
        layout.addWidget(side_panel_widget)

        # ============================================================
        # Group : Load Image
        # ============================================================
        load_image_group = QtWidgets.QGroupBox("Load Image")
        load_image_layout = QtWidgets.QVBoxLayout()
        load_image_group.setLayout(load_image_layout)
        load_image_group.setStyleSheet("font-weight: bold;")

        # Load Image button
        load_image_button = QtWidgets.QPushButton("Load Image")
        load_image_button.clicked.connect(self.load_image)
        load_image_layout.addWidget(load_image_button)

        # Load Clicks button
        load_clicks_button = QtWidgets.QPushButton("Load Clicks")
        load_clicks_button.clicked.connect(self.load_clicks)
        load_image_layout.addWidget(load_clicks_button)

        side_panel.addWidget(load_image_group)

        # ============================================================
        # Group : Click settings
        # ============================================================
        click_settings_group = QtWidgets.QGroupBox("Click Settings")
        click_settings_layout = QtWidgets.QVBoxLayout()
        click_settings_group.setLayout(click_settings_layout)
        click_settings_group.setStyleSheet("font-weight: bold;")
        
        # Group selector
        self.group_selector = QtWidgets.QComboBox()
        self.group_selector.addItem("default")
        self.group_selector.currentTextChanged.connect(self.on_group_changed)
        click_settings_layout.addWidget(QtWidgets.QLabel("Select Group:"))
        click_settings_layout.addWidget(self.group_selector)

        # Add Group button
        self.add_group_button = QtWidgets.QPushButton("Add Group")
        self.add_group_button.clicked.connect(self.add_group)
        click_settings_layout.addWidget(self.add_group_button)

        # Rename Group button
        self.rename_group_button = QtWidgets.QPushButton("Rename Group")
        self.rename_group_button.clicked.connect(self.rename_group)
        click_settings_layout.addWidget(self.rename_group_button)

        # Checkbox for integer coordinates
        self.integer_coords_checkbox = QtWidgets.QCheckBox("Use Integer Coordinates")
        self.integer_coords_checkbox.setChecked(False)  # Default to floating-point coordinates
        self.integer_coords_checkbox.stateChanged.connect(self.update)
        click_settings_layout.addWidget(self.integer_coords_checkbox)

        side_panel.addWidget(click_settings_group)

        # ============================================================
        # Group : Display Options
        # ============================================================
        display_options_group = QtWidgets.QGroupBox("Display Options")
        display_options_layout = QtWidgets.QVBoxLayout()
        display_options_group.setLayout(display_options_layout)
        display_options_group.setStyleSheet("font-weight: bold;")

        # Colormap selector
        self.colormap_selector = QtWidgets.QComboBox()
        self.colormap_selector.addItem("Default")
        self.colormap_selector.addItem("Gray")
        self.colormap_selector.addItem("Hot")
        self.colormap_selector.addItem("Jet")
        self.colormap_selector.addItem("Rainbow")
        self.colormap_selector.addItem("Cool")
        self.colormap_selector.addItem("Spring")
        self.colormap_selector.setCurrentIndex(0)  # Default to "Default"
        self.colormap_selector.currentIndexChanged.connect(self.update)
        display_options_layout.addWidget(QtWidgets.QLabel("Colormap:"))
        display_options_layout.addWidget(self.colormap_selector)

        # Color selector
        self.color_selector = QtWidgets.QComboBox()
        self.color_selector.addItem("Red")
        self.color_selector.addItem("Green")
        self.color_selector.addItem("Blue")
        self.color_selector.addItem("Yellow")
        self.color_selector.addItem("White")
        self.color_selector.addItem("Black")
        self.color_selector.addItem("Cyan")
        self.color_selector.addItem("Magenta")
        self.color_selector.addItem("Gray")
        self.color_selector.setCurrentIndex(0)  # Default to "Red"
        self.color_selector.currentIndexChanged.connect(self.update)
        display_options_layout.addWidget(QtWidgets.QLabel("Click Color:"))
        display_options_layout.addWidget(self.color_selector)

        # Dropdown to choose circle size
        self.circle_size_selector = QtWidgets.QComboBox()
        self.circle_size_selector.addItem("Extra Small (XS)")
        self.circle_size_selector.addItem("Tiny")
        self.circle_size_selector.addItem("Small")
        self.circle_size_selector.addItem("Medium")
        self.circle_size_selector.addItem("Large")
        self.circle_size_selector.addItem("Extra Large (XL)")
        self.circle_size_selector.addItem("Huge")
        self.circle_size_selector.currentIndexChanged.connect(self.update)
        self.circle_size_selector.setCurrentIndex(2)  # Default to "Small"
        display_options_layout.addWidget(QtWidgets.QLabel("Circle Size:"))
        display_options_layout.addWidget(self.circle_size_selector)

        # Checkbox to control whether clicks should be drawn
        self.display_click_checkbox = QtWidgets.QCheckBox("Display Clicks")
        self.display_click_checkbox.setChecked(True)  # By default, display clicks
        self.display_click_checkbox.stateChanged.connect(self.update)
        display_options_layout.addWidget(self.display_click_checkbox)

        # Checkbox to control if the clicks should be filled
        self.fill_click_checkbox = QtWidgets.QCheckBox("Fill Circles")
        self.fill_click_checkbox.setChecked(False)  # By default, do not fill circles
        self.fill_click_checkbox.stateChanged.connect(self.update)
        display_options_layout.addWidget(self.fill_click_checkbox)

        side_panel.addWidget(display_options_group)

        # ============================================================
        # Group : Clicks Table
        # ============================================================
        self.table_group = QtWidgets.QGroupBox("Clicks Table")
        table_layout = QtWidgets.QVBoxLayout()
        self.table_group.setLayout(table_layout)
        self.table_group.setStyleSheet("font-weight: bold;")

        # Table to show clicks in the current group
        self.table = QtWidgets.QTableWidget(0, 3)  # 3 columns: Index, Click X, Click Y
        self.table.setHorizontalHeaderLabels(["Index", "Click X", "Click Y"])
        table_layout.addWidget(self.table)

        # Button to remove the last click in the current group
        self.remove_last_click_button = QtWidgets.QPushButton("Remove Last Click")
        self.remove_last_click_button.clicked.connect(self.remove_last_click)
        table_layout.addWidget(self.remove_last_click_button)

        # Button to clear all clicks in the current group
        self.remove_all_clicks_button = QtWidgets.QPushButton("Clear All Clicks")
        self.remove_all_clicks_button.clicked.connect(self.remove_all_clicks)
        table_layout.addWidget(self.remove_all_clicks_button)

        side_panel.addWidget(self.table_group)

        # ============================================================
        # Group : CSV Save Path
        # ============================================================
        csv_save_group = QtWidgets.QGroupBox("Save CSV")
        csv_save_layout = QtWidgets.QVBoxLayout()
        csv_save_group.setLayout(csv_save_layout)
        csv_save_group.setStyleSheet("font-weight: bold;")

        # Add LineEdit for CSV file path and Save button
        self.csv_path_label = QtWidgets.QLabel("CSV File Path:")
        csv_save_layout.addWidget(self.csv_path_label)

        self.csv_path_edit = QtWidgets.QLineEdit(str(output_csv_path))
        self.csv_path_edit.setPlaceholderText("Enter path or filename...")
        csv_save_layout.addWidget(self.csv_path_edit)

        self.save_button = QtWidgets.QPushButton("Save CSV")
        self.save_button.clicked.connect(self.save_csv)
        csv_save_layout.addWidget(self.save_button)

        side_panel.addWidget(csv_save_group)



        side_panel.addStretch()  # Allow flexibility to expand vertically as needed


    def update(self):
        """
        Update the UI: the image, the table of clicks, and the drawing of clicks.
        This method is called after each relevant action (click, group change, etc.).
        """
        if not self.initialization_done:
            return
        self.update_group_selector()
        self.update_display()
        self.update_table()

    
    def set_image(self, image: Optional[numpy.ndarray]):
        """
        Set the image to be displayed in the application.
        
        Parameters
        ----------
        image : Optional[numpy.ndarray]
            The image to be displayed, loaded in BGR format using OpenCV.
        """
        if image is None:
            # Default to a blank image if no image is provided
            image = numpy.zeros((512, 512, 3), dtype=numpy.uint8)  # Create a blank black image
        
        image = numpy.array(image)
        if image.ndim == 2:  # If the image is grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Convert to BGR
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("Image must be in BGR format with 3 channels.")
        
        self.image = image


    def load_image(self):
        """
        Open a file dialog to load an image and update the display.
        """
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("Images (*.png *.jpg *.bmp *.tiff)")  # Set file filter for image types
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        file_dialog.setOption(QtWidgets.QFileDialog.ReadOnly)

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            image = cv2.imread(file_path)
            if image is None:
                QtWidgets.QMessageBox.warning(self, "Error", "Failed to load image.")
                return
            self.set_image(image)
        
        self.click_manager = ClickManager()  # Reset click manager for new image
        self.update()  # Update the display after loading a new image

    
    def load_clicks(self):
        """
        Open a file dialog to load clicks from a CSV file.
        """
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("CSV Files (*.csv)")
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        file_dialog.setOption(QtWidgets.QFileDialog.ReadOnly)

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            self.click_manager = ClickManager.load_from_csv(file_path)
        
        self.update()


    def update_display(self):
        """
        Convert the OpenCV image to a Qt image and display it scaled.
        Additionally, display the clicks for the current group.
        """
        colormap = self.get_selected_colormap()
        if colormap is not None:
            # Convert the image to grayscale and apply the colormap
            image_bw = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            image = cv2.applyColorMap(image_bw, colormap)
        else:
            image = self.image
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB for Qt

        # Set the image to the label
        h, w, ch = image.shape
        bytes_per_line = ch * w
        q_image = QtGui.QImage(image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(q_image)

        self.draw_clicks_on_image(pixmap)

        self.original_pixmap = pixmap
        self.resize_image()


    def resize_image(self):
        """
        Resize image to fit within the scroll area while maintaining the aspect ratio.
        Allow the image to shrink and expand based on window size, and allow shrinking when window is resized.
        """
        if hasattr(self, "original_pixmap"):
            # Get the size of the QLabel inside the scroll area
            label_size = self.scroll_area.size()

            # Resize the pixmap while maintaining the aspect ratio
            scaled_pixmap = self.original_pixmap.scaled(
                label_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

            self.image_label.setPixmap(scaled_pixmap)


    def resizeEvent(self, event):
        """
        Triggered when the window is resized. Rescale the image accordingly.
        """
        self.resize_image()


    def on_mouse_click(self, event):
        """
        Handle mouse click events on the image.

        Parameters
        ----------
        event : QMouseEvent
            The mouse event that occurred.
        """
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return

        scaled_size = pixmap.size()
        label_size = self.image_label.size()
        offset_x = (label_size.width() - scaled_size.width()) // 2
        offset_y = (label_size.height() - scaled_size.height()) // 2

        x = event.pos().x() - offset_x
        y = event.pos().y() - offset_y

        if 0 <= x < scaled_size.width() and 0 <= y < scaled_size.height():
            orig_h, orig_w, _ = self.image.shape
            scale_x = orig_w / scaled_size.width()
            scale_y = orig_h / scaled_size.height()
            img_x = x * scale_x
            img_y = y * scale_y

            # Left click: Add coordinates to the current group
            if event.button() == QtCore.Qt.LeftButton:
                self.click_manager.add_click(img_x, img_y)

            # Right click: Add a placeholder (None, None)
            elif event.button() == QtCore.Qt.RightButton:
                self.click_manager.add_click(None, None)

        self.update()


    def draw_clicks_on_image(self, pixmap: QtGui.QPixmap):
        """
        Draw the clicks on the current image with the selected color and size,
        only if the display clicks checkbox is checked.
        """
        if not self.display_click_checkbox.isChecked():
            return  # Don't draw if checkbox is not checked

        painter = QtGui.QPainter(pixmap)
        color = self.get_selected_color()
        pen = QtGui.QPen(color)
        painter.setPen(pen)

        fill_color = color if self.fill_click_checkbox.isChecked() else QtCore.Qt.transparent
        painter.setBrush(QtGui.QBrush(fill_color))

        # Get the size of the circle
        circle_size = self.get_selected_circle_size()

        for idx, (x, y) in enumerate(self.click_manager.groups[self.click_manager.current_group]):
            if x is not None and y is not None:
                # Drawing can only be done with integer coordinates
                x = int(x)
                y = int(y)
                # Draw a circle for each click
                painter.drawEllipse(x - circle_size // 2, y - circle_size // 2, circle_size, circle_size)

        painter.end()


    def get_selected_circle_size(self):
        """
        Get the selected circle size for drawing clicks.

        Returns
        -------
        int
            The size of the circle to draw.
        """
        size_map = {
            "Extra Small (XS)": 2,
            "Tiny": 5,
            "Small": 10,
            "Medium": 15,
            "Large": 20,
            "Extra Large (XL)": 25,
            "Huge": 30,
        }
        return size_map.get(self.circle_size_selector.currentText(), 10)  # Default to "Small"


    def get_selected_color(self):
        """
        Get the color selected in the color combo box.

        Returns
        -------
        QtGui.QColor
            The selected color.
        """
        color_map = {
            "Red": QtGui.QColor(255, 0, 0),
            "Green": QtGui.QColor(0, 255, 0),
            "Blue": QtGui.QColor(0, 0, 255),
            "Yellow": QtGui.QColor(255, 255, 0),
            "White": QtGui.QColor(255, 255, 255),
            "Black": QtGui.QColor(0, 0, 0),
            "Cyan": QtGui.QColor(0, 255, 255),
            "Magenta": QtGui.QColor(255, 0, 255),
            "Gray": QtGui.QColor(128, 128, 128),
        }
        return color_map.get(self.color_selector.currentText(), QtGui.QColor(255, 0, 0))
    

    def get_selected_colormap(self):
        """
        Get the selected colormap for displaying the image.

        Returns
        -------
        str
            The selected colormap.
        """
        colormap_map = {
            "Default": None,
            "Gray": cv2.COLORMAP_BONE,
            "Hot": cv2.COLORMAP_HOT,
            "Jet": cv2.COLORMAP_JET,
            "Rainbow": cv2.COLORMAP_RAINBOW,
            "Cool": cv2.COLORMAP_COOL,
            "Spring": cv2.COLORMAP_SPRING,
        }
        return colormap_map.get(self.colormap_selector.currentText(), None)


    def on_group_changed(self, text):
        """
        Called when the user selects a different group.
        """
        self.click_manager.set_group(text)
        self.update()


    def add_group(self):
        """
        Show dialog to add a new group.
        """
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Group", "Group name:")
        if ok and name and name not in self.click_manager.groups:
            self.click_manager.set_group(name)
        self.update()  # Update the display after adding a new group

    
    def update_group_selector(self):
        """
        Update the group selector with the current groups.
        """
        # Disable the signals
        self.group_selector.blockSignals(True)
        self.group_selector.clear()
        for group in self.click_manager.groups:
            self.group_selector.addItem(group)
        self.group_selector.setCurrentText(self.click_manager.current_group)
        self.group_selector.blockSignals(False)



    def rename_group(self):
        """
        Show dialog to rename the current group.
        """
        old_name = self.group_selector.currentText()
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename Group", "New name:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.click_manager.rename_group(old_name, new_name)
        self.update()


    def remove_last_click(self):
        """
        Remove the last click from the current group.
        """
        current_group = self.click_manager.extract_group()
        self.click_manager.remove_click(len(current_group) - 1)
        self.update()


    def remove_all_clicks(self):
        """
        Remove all clicks from the current group.
        """
        self.click_manager.clear_group()
        self.update()


    def update_table(self):
        """
        Update the table displaying the clicks in the current group.
        """
        current_group = self.click_manager.extract_group()
        self.table.setRowCount(len(current_group))

        for row, (x, y) in enumerate(current_group):
            if self.integer_coords_checkbox.isChecked():
                # Use integer coordinates
                x = int(x) if x is not None else None
                y = int(y) if y is not None else None
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row + 1)))  # Index
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(x)))  # Click X
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(y)))  # Click Y

    
    def save_csv(self):
        """
        Save the coordinates of the clicks to the specified CSV file.
        """
        # Get the path from the QLineEdit
        file_path = self.csv_path_edit.text()

        if not file_path:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a valid file path.")
            return

        try:
            self.click_manager.save_to_csv(file_path, as_integer=self.integer_coords_checkbox.isChecked())
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save CSV file: {str(e)}")


    def closeEvent(self, event):
        """
        Save click data when the window is closed.
        """
        event.accept()

