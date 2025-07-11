import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import numpy
import cv2
import os
from typing import Optional


from .click_manager import ClickManager
from .image_viewer import ImageViewer

class ClickImageApp(QtWidgets.QMainWindow):
    r"""
    A PyQt application to collect mouse clicks on an image,
    grouping them by user-defined categories.

    Parameters
    ----------
    image : Optional[numpy.ndarray]
        The input image to be displayed, loaded in GRAY or BGR format using OpenCV.
    output : Optional[str]
        The path where the output csv file will be saved.
    """
    def __init__(self, image: Optional[numpy.ndarray] = None, output: Optional[str] = None):
        super().__init__()

        # Start logging
        self.log_text_edit = QtWidgets.QTextEdit()
        self.log_text_edit.setReadOnly(True)  # Make it read-only

        # Detect changes
        self._image_has_changed = True
        self._colormap_has_changed = True

        # Initialize the click manager and image viewer
        self.set_image(image)
        if output is None:
            output = "pyclickimage_clicks_defaults.csv"

        self.click_manager = ClickManager()
        self.viewer = ImageViewer()
        self.viewer.left_click_signal.connect(self._process_left_click)
        self.viewer.right_click_signal.connect(self._process_right_click)

        self.setWindowTitle("Click Image UI")

        self.initialization_done = False
        self._init_ui(output)
        self.initialization_done = True
        self._append_to_log("Application initialized successfully.")

        self.update()


    def _init_ui(self, output: str):
        r"""
        Initialize the UI layout, widgets, and connect signals.
        """
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(layout)

        # Left side: Image viewer
        layout.addWidget(self.viewer)
    
        # Right side: Organize widgets in logical groups
        side_panel = QtWidgets.QVBoxLayout()

        # Side panel widget with a fixed width
        side_panel_widget = QtWidgets.QWidget()
        side_panel_widget.setLayout(side_panel)
        side_panel_widget.setMinimumWidth(350)  # Fixed width for the side panel
        side_panel_widget.setMaximumWidth(700)  # Maximum width for the side panel
        layout.addWidget(side_panel_widget)

        # Tool bar for quick actions
        toolbar = QtWidgets.QToolBar("Toolbar")
        toolbar.setMovable(False)  # Make the toolbar non-movable
        self.addToolBar(toolbar)

        def add_action(text, shortcut, callback, checkable=False):
            action = QtWidgets.QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.setCheckable(checkable)
            action.triggered.connect(callback)
            toolbar.addAction(action)
            return action

        add_action("Zoom In", "Ctrl++", lambda: self.viewer.manual_zoom(True))
        add_action("Zoom Out", "Ctrl+-", lambda: self.viewer.manual_zoom(False))
        add_action("Toggle Drag", None, self.viewer.toggle_drag_mode, checkable=True).setChecked(True)
        add_action("Reset View", "Ctrl+0", self.viewer.reset_view)

        # ============================================================
        # Group : Load Image
        # ============================================================
        load_image_group = QtWidgets.QGroupBox("Load Image")
        load_image_layout = QtWidgets.QVBoxLayout()
        load_image_group.setLayout(load_image_layout)
        load_image_group.setStyleSheet("font-weight: bold;")

        # Load Image button
        load_image_button = QtWidgets.QPushButton("Load Image")
        load_image_button.clicked.connect(self.on_load_image)
        load_image_layout.addWidget(load_image_button)

        # Load Clicks button
        load_clicks_button = QtWidgets.QPushButton("Load Clicks")
        load_clicks_button.clicked.connect(self.on_load_clicks)
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
        self.add_group_button.clicked.connect(self.on_add_group)
        click_settings_layout.addWidget(self.add_group_button)

        # Rename Group button
        self.rename_group_button = QtWidgets.QPushButton("Rename Group")
        self.rename_group_button.clicked.connect(self.on_rename_group)
        click_settings_layout.addWidget(self.rename_group_button)

        # Delete Group button
        self.delete_group_button = QtWidgets.QPushButton("Delete Group")
        self.delete_group_button.clicked.connect(self.on_delete_group)
        click_settings_layout.addWidget(self.delete_group_button)

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
        self.colormap_selector.currentIndexChanged.connect(self.on_colormap_changed)
        display_options_layout.addWidget(QtWidgets.QLabel("Colormap:"))
        display_options_layout.addWidget(self.colormap_selector)

        # Color selector
        self.color_selector = QtWidgets.QComboBox()
        self.color_selector.addItem("Gray")
        self.color_selector.addItem("Red")
        self.color_selector.addItem("Green")
        self.color_selector.addItem("Blue")
        self.color_selector.addItem("Yellow")
        self.color_selector.addItem("White")
        self.color_selector.addItem("Black")
        self.color_selector.addItem("Cyan")
        self.color_selector.addItem("Magenta")
        self.color_selector.currentIndexChanged.connect(self.on_color_changed)
        self.color_selector.setCurrentIndex(1)  # Default to "Red"
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
        self.circle_size_selector.currentIndexChanged.connect(self.on_size_changed)
        self.circle_size_selector.setCurrentIndex(2)  # Default to "Small"
        display_options_layout.addWidget(QtWidgets.QLabel("Circle Size:"))
        display_options_layout.addWidget(self.circle_size_selector)

        # Dropdown to choose the width of the circles
        self.circle_width_selector = QtWidgets.QComboBox()
        self.circle_width_selector.addItem("Thin")
        self.circle_width_selector.addItem("Medium")
        self.circle_width_selector.addItem("Large")
        self.circle_width_selector.currentIndexChanged.connect(self.on_width_changed)
        self.circle_width_selector.setCurrentIndex(1)  # Default to "Medium"
        display_options_layout.addWidget(QtWidgets.QLabel("Circle Width:"))
        display_options_layout.addWidget(self.circle_width_selector)

        # Checkbox to control whether clicks should be drawn
        self.display_click_checkbox = QtWidgets.QCheckBox("Display Clicks")
        self.display_click_checkbox.setChecked(True)  # By default, display clicks
        self.display_click_checkbox.stateChanged.connect(self.on_display_clicks_changed)
        display_options_layout.addWidget(self.display_click_checkbox)

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
        self.remove_last_click_button.clicked.connect(self.on_remove_last_click)
        table_layout.addWidget(self.remove_last_click_button)

        # Button to clear all clicks in the current group
        self.remove_all_clicks_button = QtWidgets.QPushButton("Clear All Clicks")
        self.remove_all_clicks_button.clicked.connect(self.on_remove_all_clicks)
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

        self.csv_path_edit = QtWidgets.QLineEdit(str(output))
        self.csv_path_edit.setPlaceholderText("Enter path or filename...")
        csv_save_layout.addWidget(self.csv_path_edit)

        self.save_button = QtWidgets.QPushButton("Save CSV")
        self.save_button.clicked.connect(self.save_csv)
        csv_save_layout.addWidget(self.save_button)

        side_panel.addWidget(csv_save_group)

        # =============================================================
        # Group Log
        # =============================================================
        log_group = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout()
        log_group.setLayout(log_layout)
        log_group.setStyleSheet("font-weight: bold;")

        # Add a TextEdit for logging
        log_layout.addWidget(self.log_text_edit)

        # Add the log group to the side panel
        side_panel.addWidget(log_group)


        side_panel.addStretch()  # Allow flexibility to expand vertically as needed


    # ============================================================
    # Loging
    # ============================================================
    def _append_to_log(self, message):
        r"""
        Append message to the QTextEdit widget.
        """
        self.log_text_edit.append(message)

    # ============================================================
    # UI Update Methods
    # ============================================================
    def update(self):
        r"""
        Update the UI: the image, the table of clicks, and the drawing of clicks.
        This method is called after each relevant action (click, group change, etc.).
        """
        if not self.initialization_done:
            return
        self.update_group_selector()
        self.update_display()
        self.update_table()

    
    def set_image(self, image: Optional[numpy.ndarray]):
        r"""
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
        self._image_has_changed = True


    def update_display(self):
        """
        Convert the OpenCV image to a Qt image and display it scaled.
        Additionally, display the clicks for the current group.
        """
        if self._image_has_changed or self._colormap_has_changed:
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

            # set the pixmap to the viewer
            self.viewer.set_image(pixmap)
            self._image_has_changed = False
            self._colormap_has_changed = False

        self.draw_clicks_on_image()


    def draw_clicks_on_image(self):
        """
        Draw the clicks on the image in the viewer.
        """
        if not self.display_click_checkbox.isChecked():
            self.viewer.remove_all_circles()

        else:
            self.viewer.remove_all_circles()
            self.viewer.circles_color = self.get_selected_color()
            self.viewer.circles_radius = self.get_selected_circle_size()
            self.viewer.circles_width = self.get_selected_width()
            current_group = self.click_manager.extract_group()
            for index, (x, y) in enumerate(current_group):
                if x is not None and y is not None:
                    self.viewer.add_circle(center=(x, y))

    def update_table(self):
        """
        Update the table displaying the clicks in the current group.
        """
        current_group = self.click_manager.extract_group()
        self.table.setRowCount(len(current_group))

        for row, (x, y) in enumerate(current_group):
            x = x if x is not None else ''
            y = y if y is not None else ''
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row)))  # Index
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(x)))  # Click X
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(y)))  # Click Y


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


    # ============================================================
    # Save CSV and quit
    # ===========================================================
    def save_csv(self):
        """
        Save the coordinates of the clicks to the specified CSV file.
        """
        # Get the path from the QLineEdit
        file_path = self.csv_path_edit.text()

        if not file_path:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a valid file path.")
            return
        
        # Ensure the path can be a correct CSV file
        try:
            self.click_manager.save_to_csv(file_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save CSV file: {str(e)}")


    def closeEvent(self, event):
        """
        Save click data when the window is closed.
        """
        event.accept()



    # ============================================================
    # Dictionary Methods
    # ===========================================================
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
    

    def get_selected_width(self):
        """
        Get the selected width for drawing circles.

        Returns
        -------
        int
            The width of the circle to draw.
        """
        width_map = {
            "Thin": 1,
            "Medium": 2,
            "Large": 4,
        }
        return width_map.get(self.circle_width_selector.currentText(), 2)
    

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


    # ============================================================
    # Event Handlers
    # ============================================================
    def on_load_image(self):
        """
        Open a file dialog to load an image and update the display.
        """
        self._append_to_log("Opening file dialog to load image...")
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("Images (*.png *.PNG *.jpg *.JPG *.jpeg *.JPEG *.bmp *.BMP *.tiff *.TIFF *.tif *.TIF)")
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        file_dialog.setOption(QtWidgets.QFileDialog.ReadOnly)

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            self._append_to_log(f"Loading image from: {file_path}")

            image = cv2.imread(file_path)
            if image is None:
                QtWidgets.QMessageBox.warning(self, "Error", "Failed to load image.")
                return
            
            self.set_image(image)
            self._append_to_log("Image loaded successfully.")

        self.click_manager = ClickManager()  # Reset click manager for new image
        self.update()  # Update the display after loading a new image

    
    def on_load_clicks(self):
        """
        Open a file dialog to load clicks from a CSV file.
        """
        self._append_to_log("Opening file dialog to load clicks...")
        file_dialog = QtWidgets.QFileDialog(self)
        file_dialog.setNameFilter("CSV Files (*.csv *.CSV)")
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        file_dialog.setOption(QtWidgets.QFileDialog.ReadOnly)

        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            self._append_to_log(f"Loading clicks from: {file_path}")

            if not os.path.exists(file_path):
                QtWidgets.QMessageBox.warning(self, "Error", "File does not exist.")
                return
            
            self.click_manager = ClickManager.load_from_csv(file_path)
            self._append_to_log("Clicks loaded successfully.")
        
        self.update()


    def on_colormap_changed(self, index):
        """
        Called when the user selects a different colormap.
        """
        self._append_to_log(f"Colormap changed to: {self.colormap_selector.currentText()}")
        self._colormap_has_changed = True
        self.update()

    
    def on_color_changed(self, index):
        """
        Called when the user selects a different color for the clicks.
        """
        self._append_to_log(f"Click color changed to: {self.color_selector.currentText()}")
        self.update()


    def on_size_changed(self, index):
        """
        Called when the user selects a different size for the circles.
        """
        self._append_to_log(f"Circle size changed to: {self.circle_size_selector.currentText()}")
        self.update()


    def on_width_changed(self, index):
        """
        Called when the user selects a different width for the circles.
        """
        self._append_to_log(f"Circle width changed to: {self.circle_width_selector.currentText()}")
        self.update()

    
    def on_display_clicks_changed(self, state):
        """
        Called when the user checks or unchecks the display clicks checkbox.
        """
        if state == QtCore.Qt.Checked:
            self._append_to_log("Displaying clicks on the image.")
        else:
            self._append_to_log("Hiding clicks on the image.")
        self.update()


    def on_group_changed(self, text):
        """
        Called when the user selects a different group.
        """
        self._append_to_log(f"Group changed to: {text}")
        self.click_manager.set_group(text)
        self.update()


    def on_add_group(self):
        """
        Show dialog to add a new group.
        """
        self._append_to_log("Adding a new group...")
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Group", "Group name:")
        if ok and name and name not in self.click_manager.groups:
            self.click_manager.set_group(name)
            self._append_to_log(f"Group '{name}' added successfully.")
        elif not ok:
            self._append_to_log("Group addition cancelled.")
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "Group name already exists or is invalid.")
            self._append_to_log("Failed to add group: name already exists or is invalid.")
        self.update()  # Update the display after adding a new group


    def on_rename_group(self):
        """
        Show dialog to rename the current group.
        """
        old_name = self.group_selector.currentText()
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Rename Group", "New name:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.click_manager.rename_group(old_name, new_name)
            self._append_to_log(f"Group '{old_name}' renamed to '{new_name}'.")
        self.update()

    
    def on_delete_group(self):
        """
        Show dialog to delete the current group.
        """
        self._append_to_log("Deleting the current group...")
        self.click_manager.remove_group()
        self.update()


    def on_remove_last_click(self):
        """
        Remove the last click from the current group.
        """
        current_group = self.click_manager.extract_group()
        if current_group is None or len(current_group) == 0:
            QtWidgets.QMessageBox.warning(self, "Warning", "No clicks to remove.")
            return
        self.click_manager.remove_click(len(current_group) - 1)
        self._append_to_log("Removing the last click from the current group.")
        self.update()


    def on_remove_all_clicks(self):
        """
        Remove all clicks from the current group.
        """
        self._append_to_log("Removing all clicks from the current group.")
        self.click_manager.clear_group()
        self.update()


        
    def _process_left_click(self, x: int, y: int):
        r"""
        Process a left click event on the image viewer.

        Add the click to the current group and update the display.
        """
        if not self.initialization_done:
            return

        if self.click_manager.current_group is None:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a group before clicking.")
            return
        
        # Add the click to the current group
        self.click_manager.add_click(x, y)
        self.update()  # Update the display after adding a click


    def _process_right_click(self, x: int, y: int):
        r"""
        Process a right click event on the image viewer.
        """
        pass

   
