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

import sys
import os
from typing import Optional

import numpy as np
import cv2
from PyQt5 import QtWidgets, QtGui, QtCore

from .click_manager import ClickManager
from .image_viewer import ImageViewer
from .__version__ import __version__


class ClickImageApp(QtWidgets.QMainWindow):
    r"""
    PyQt application for collecting precise mouse clicks on images.

    Features
    --------
    - Subpixel precision (float coordinates)
    - Optional integer rounding mode
    - Multiple click groups
    - CSV export/import
    - Real-time overlay rendering
    """

    def __init__(
        self, image: Optional[np.ndarray] = None, output: Optional[str] = None
    ):
        super().__init__()

        self.setWindowTitle(f"Click Image Application - pyclickimage v{__version__}")

        # -------------------------
        # State flags
        # -------------------------
        self.initialization_done = False
        self._is_saved = False
        self._image_has_changed = True
        self._colormap_has_changed = True
        self._is_empty_image = True

        # -------------------------
        # Core components
        # -------------------------
        self.click_manager = ClickManager(precision_mode="float")
        self.viewer = ImageViewer()

        # -------------------------
        # Logging
        # -------------------------
        self.log_text_edit = QtWidgets.QTextEdit()
        self.log_text_edit.setReadOnly(True)

        # -------------------------
        # Output file
        # -------------------------
        self.output_path = output

        # -------------------------
        # Image
        # -------------------------
        self.set_image(image)

        # -------------------------
        # Markers
        # -------------------------
        self.marker_color = QtGui.QColor(255, 0, 0)
        self.marker_size = 8

        # -------------------------
        # UI
        # -------------------------
        self._init_ui()

        # -------------------------
        # Signals
        # -------------------------
        self.viewer.auto_marker = False  # Don't draw directly
        self.viewer.left_click_signal.connect(self._process_left_click)
        self.viewer.right_click_signal.connect(self._process_right_click)

        self.initialization_done = True
        self._append_log("Application ready.")
        if self.output_path is not None:
            self._append_log(f"Output CSV path setted to : {self.output_path}")

        self.update()

    # ============================================================
    # UI
    # ============================================================

    def _init_ui(self):
        r"""
        Build full interface layout.
        """

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QHBoxLayout()
        central.setLayout(layout)

        quit_action = QtWidgets.QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        self.addAction(quit_action)

        # -------------------------
        # Viewer
        # -------------------------
        layout.addWidget(self.viewer)

        # -------------------------
        # Side panel
        # -------------------------
        side = QtWidgets.QVBoxLayout()
        side_widget = QtWidgets.QWidget()
        side_widget.setFixedWidth(340)
        side_widget.setLayout(side)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(360)
        scroll.setWidget(side_widget)

        layout.addWidget(scroll)

        # ============================================================
        # Load Image
        # ============================================================
        self.load_btn = QtWidgets.QPushButton("Load Image (Ctrl+O)")
        self.load_btn.clicked.connect(self.on_load_image)
        self.load_btn.setShortcut("Ctrl+O")
        side.addWidget(self.load_btn)

        row = QtWidgets.QHBoxLayout()

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
        row.addWidget(QtWidgets.QLabel("Image Colormap:"))
        row.addWidget(self.colormap_selector)

        side.addLayout(row)

        self.loadc_btn = QtWidgets.QPushButton("Load Clicks")
        self.loadc_btn.clicked.connect(self.on_load_clicks)
        side.addWidget(self.loadc_btn)

        # ============================================================
        # Precision mode
        # ============================================================
        self.precision_checkbox = QtWidgets.QCheckBox("Integer precision mode (Ctrl+I)")
        self.precision_checkbox.setChecked(False)
        self.precision_checkbox.stateChanged.connect(self.on_precision_changed)
        self.precision_checkbox.setShortcut("Ctrl+I")
        side.addWidget(self.precision_checkbox)

        # ============================================================
        # Group selector
        # ============================================================
        row = QtWidgets.QHBoxLayout()

        row.addWidget(QtWidgets.QLabel("Group"))

        self.group_selector = QtWidgets.QComboBox()
        self.group_selector.addItem("default")
        self.group_selector.currentTextChanged.connect(self.on_group_changed)

        row.addWidget(self.group_selector)

        side.addLayout(row)

        # -------------------------
        # Group management buttons
        # -------------------------
        row = QtWidgets.QHBoxLayout()

        self.add_group_btn = QtWidgets.QPushButton("+")
        self.add_group_btn.setToolTip("Add group (Ctrl+G)")
        self.add_group_btn.clicked.connect(self.on_add_group)
        self.add_group_btn.setShortcut("Ctrl+G")

        self.rename_group_btn = QtWidgets.QPushButton("✎")
        self.rename_group_btn.setToolTip("Rename group (Ctrl+R)")
        self.rename_group_btn.clicked.connect(self.on_rename_group)
        self.rename_group_btn.setShortcut("Ctrl+R")

        self.delete_group_btn = QtWidgets.QPushButton("🗑")
        self.delete_group_btn.setToolTip("Delete group (Ctrl+D)")
        self.delete_group_btn.clicked.connect(self.on_delete_group)
        self.delete_group_btn.setShortcut("Ctrl+D")

        row.addWidget(self.add_group_btn)
        row.addWidget(self.rename_group_btn)
        row.addWidget(self.delete_group_btn)

        side.addLayout(row)

        # --------------------------
        # Click Management
        # --------------------------
        row = QtWidgets.QHBoxLayout()

        self.undo_btn = QtWidgets.QPushButton("Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.on_undo_last_click)
        self.undo_btn.setShortcut("Ctrl+Z")

        self.clear_btn = QtWidgets.QPushButton("Clear (Ctrl+Shift+Z)")
        self.clear_btn.clicked.connect(self.on_undo_all_click)
        self.clear_btn.setShortcut("Ctrl+Shift+Z")

        row.addWidget(self.undo_btn)
        row.addWidget(self.clear_btn)

        side.addLayout(row)

        # ============================================================
        # Table
        # ============================================================
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Index", "X", "Y"])
        self.table.setMinimumHeight(180)
        side.addWidget(self.table)

        # ============================================================
        # Save button
        # ============================================================
        row = QtWidgets.QHBoxLayout()

        self.save_btn = QtWidgets.QPushButton("Save CSV (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_csv)
        self.save_btn.setShortcut("Ctrl+S")
        row.addWidget(self.save_btn)

        self.save_as_btn = QtWidgets.QPushButton("Save As CSV (Ctrl+Shift+S)")
        self.save_as_btn.clicked.connect(self.save_as_csv)
        self.save_as_btn.setShortcut("Ctrl+Shift+S")
        row.addWidget(self.save_as_btn)

        side.addLayout(row)

        # ============================================================
        # Log
        # ============================================================
        side.addWidget(self.log_text_edit)

        # ============================================================
        # Toolbar
        # ============================================================
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction("Reset View", self.viewer.reset_view)

        toolbar.addSeparator()

        # ============================================================
        # Crosser color (button + preview)
        # ============================================================
        crosshair_color_widget = QtWidgets.QWidget()
        crosshair_color_layout = QtWidgets.QHBoxLayout()
        crosshair_color_layout.setContentsMargins(0, 0, 0, 0)

        self.crosshair_color_btn = QtWidgets.QPushButton("Color")
        self.crosshair_color_btn.clicked.connect(self.crosshair_choose_color)

        self.crosshair_color_preview = QtWidgets.QLabel("   ")
        self.crosshair_color_preview.setStyleSheet(
            "background-color: rgb(255,0,0); border: 1px solid black;"
        )

        crosshair_color_layout.addWidget(QtWidgets.QLabel("Crosshair"))
        crosshair_color_layout.addWidget(self.crosshair_color_btn)
        crosshair_color_layout.addWidget(self.crosshair_color_preview)

        crosshair_color_widget.setLayout(crosshair_color_layout)

        toolbar.addWidget(crosshair_color_widget)

        toolbar.addSeparator()

        # ============================================================
        # Marker color (button + preview)
        # ============================================================
        color_widget = QtWidgets.QWidget()
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)

        self.color_btn = QtWidgets.QPushButton("Color")
        self.color_btn.clicked.connect(self.choose_color)

        self.color_preview = QtWidgets.QLabel("   ")
        self.color_preview.setStyleSheet(
            "background-color: rgb(255,0,0); border: 1px solid black;"
        )

        color_layout.addWidget(QtWidgets.QLabel("Marker"))
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_preview)

        color_widget.setLayout(color_layout)

        toolbar.addWidget(color_widget)

        toolbar.addSeparator()

        # ============================================================
        # Marker size selector
        # ============================================================
        size_widget = QtWidgets.QWidget()
        size_layout = QtWidgets.QHBoxLayout()
        size_layout.setContentsMargins(0, 0, 0, 0)

        self.size_selector = QtWidgets.QComboBox()
        self.size_selector.addItems(
            [
                "0.2",
                "0.5",
                "1",
                "2",
                "4",
                "6",
                "8",
                "10",
                "12",
                "16",
                "20",
                "30",
                "50",
                "75",
                "100",
            ]
        )
        self.size_selector.setCurrentText("8")
        self.size_selector.currentTextChanged.connect(self.on_marker_size_changed)

        size_layout.addWidget(QtWidgets.QLabel("Size"))
        size_layout.addWidget(self.size_selector)

        size_widget.setLayout(size_layout)

        toolbar.addWidget(size_widget)

        toolbar.addSeparator()

    # ============================================================
    # Precision mode
    # ============================================================

    def on_precision_changed(self, state):
        r"""
        Toggle integer/float precision mode.
        """
        INT = state == QtCore.Qt.Checked
        self.click_manager.precision_mode = "int" if INT else "float"
        self._append_log(f"Precision mode: {'INT' if INT else 'FLOAT'}")
        self.update()

    # ============================================================
    # Image
    # ============================================================

    def set_image(self, image: Optional[np.ndarray]):
        r"""
        Set image to display.
        """

        if image is None:
            image = np.zeros((512, 512, 3), dtype=np.uint8)
            self._is_empty_image = True
        else:
            self._is_empty_image = False

        image = np.array(image)

        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        if image.shape[2] != 3:
            raise ValueError("Image must be BGR 3 channels")

        self.image = image
        self._image_has_changed = True

    def on_load_image(self):
        r"""
        Load an image from file dialog.

        If clicks already exist, ask user whether to clear them or keep them.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )

        if not file_path:
            return

        # -------------------------
        # Load image with OpenCV
        # -------------------------
        image = cv2.imread(file_path)

        if image is None:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to load image.")
            return

        # -------------------------
        # Check existing clicks
        # -------------------------
        has_clicks = any(len(v) > 0 for v in self.click_manager.groups.values())

        if has_clicks:
            msg = QtWidgets.QMessageBox(self)
            msg.setWindowTitle("Existing clicks detected")
            msg.setText("Do you want to keep existing clicks?")
            msg.setInformativeText(
                "Yes = keep clicks\nNo = delete all clicks\nCancel = abort"
            )

            msg.setStandardButtons(
                QtWidgets.QMessageBox.Yes
                | QtWidgets.QMessageBox.No
                | QtWidgets.QMessageBox.Cancel
            )

            choice = msg.exec_()

            if choice == QtWidgets.QMessageBox.Cancel:
                return

            if choice == QtWidgets.QMessageBox.No:
                self.click_manager = ClickManager()
                self._append_log("Clicks cleared due to image reload.")

        # -------------------------
        # Apply image
        # -------------------------
        self.set_image(image)

        self._image_has_changed = True
        self._is_saved = False

        self._append_log(f"Image loaded: {file_path}")

        self.update()

    # ============================================================
    # Update pipeline
    # ============================================================

    def update(self):
        r"""
        Refresh UI.
        """
        if not self.initialization_done:
            return

        self.update_groups()
        self.update_table()
        self.update_viewer()

    def _format_value(self, v):
        if v is None:
            return ""

        if self.click_manager.use_int_precision:
            return str(int(round(v)))

        return f"{v:.3f}"

    def update_viewer(self):
        r"""
        Render image + clicks.
        """
        if self._image_has_changed or self._colormap_has_changed:
            colormap = self.get_selected_colormap()
            img = self.image  # BGR (OpenCV standard)

            if colormap is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                img = cv2.applyColorMap(gray, colormap)

            # conversion unique pour Qt
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            h, w, ch = rgb.shape
            bytes_per_line = ch * w

            qimg = QtGui.QImage(
                rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
            )
            pix = QtGui.QPixmap.fromImage(qimg)

            self.viewer.set_image(pix)
            self._image_has_changed = False
            self._colormap_has_changed = False

        # redraw clicks
        self.viewer.clear_markers()

        pts = self.click_manager.extract_group()

        for x, y in pts:
            if x is None or y is None:
                continue
            self.viewer.add_marker((x, y), self.marker_color, self.marker_size)

    def update_table(self):
        r"""
        Update table with current group points.
        """
        pts = self.click_manager.extract_group()

        if self.click_manager.use_float_precision:
            self.table.setHorizontalHeaderLabels(["Index", "X (float)", "Y (float)"])
        else:
            self.table.setHorizontalHeaderLabels(["Index", "X (int)", "Y (int)"])

        self.table.setRowCount(len(pts))

        for i, (x, y) in enumerate(pts):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i)))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(self._format_value(x)))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(self._format_value(y)))

    def update_groups(self):
        r"""
        Sync group selector.
        """
        self.group_selector.blockSignals(True)
        self.group_selector.clear()

        for g in self.click_manager.groups:
            self.group_selector.addItem(g)

        self.group_selector.setCurrentText(self.click_manager.current_group)
        self.group_selector.blockSignals(False)

    # ============================================================
    # Click handling
    # ============================================================

    def _process_left_click(self, x: float, y: float):
        r"""
        Store click.
        """
        if not self.initialization_done:
            return

        self.click_manager.add_click(x, y)
        self._is_saved = False
        self.update()

    def _process_right_click(self, x: float, y: float):
        r"""
        Store placeholder click.
        """
        if not self.initialization_done:
            return

        self.click_manager.add_click(None, None)
        self._is_saved = False
        self.update()

    def on_undo_last_click(self):
        r"""
        Remove last click from current group.
        """

        group = self.click_manager.current_group
        pts = self.click_manager.extract_group()

        if not pts:
            QtWidgets.QMessageBox.information(self, "Undo", "No clicks to remove.")
            return

        # Remove last point
        self.click_manager.remove_click(len(pts) - 1)

        self._append_log(f"Removed last click from group '{group}'")

        self._is_saved = False
        self.update()

    def on_undo_all_click(self):
        r"""
        Remove all click from current group.
        """

        group = self.click_manager.current_group
        pts = self.click_manager.extract_group()

        if not pts:
            QtWidgets.QMessageBox.information(self, "Undo", "No clicks to remove.")
            return

        # Remove last point
        self.click_manager.clear_group()

        self._append_log(f"Removed all clicks from group '{group}'")

        self._is_saved = False
        self.update()

    # ============================================================
    # Design
    # ============================================================
    def crosshair_choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self.viewer.get_crosshair_color(), self)

        if color.isValid():
            self.viewer.set_crosshair_color(color)
            self.update()

            self.crosshair_color_preview.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid black;"
            )

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(self.marker_color, self)

        if color.isValid():
            self.marker_color = color
            self.update()

            self.color_preview.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid black;"
            )

    def on_marker_size_changed(self, value: str):
        r"""
        Update marker size.
        """

        try:
            self.marker_size = float(value)
        except ValueError:
            self.marker_size = 8

        self._append_log(f"Marker size set to {self.marker_size}")

        self.update()

    def on_colormap_changed(self, index):
        """
        Called when the user selects a different colormap.
        """
        self._append_log(f"Colormap changed to: {self.colormap_selector.currentText()}")
        self._colormap_has_changed = True
        self.update()

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
    # Groups
    # ============================================================

    def on_group_changed(self, name):
        r"""
        Switch active group.
        """
        self.click_manager.set_group(name)
        self.update()

    def on_add_group(self):
        r"""
        Create a new click group.
        """

        name, ok = QtWidgets.QInputDialog.getText(self, "New Group", "Group name:")

        if not ok or not name:
            return

        if name in self.click_manager.groups:
            QtWidgets.QMessageBox.warning(self, "Error", "Group already exists.")
            return

        self.click_manager.set_group(name)
        self._append_log(f"Group created: {name}")
        self._is_saved = False
        self.update()

    def on_rename_group(self):
        r"""
        Rename current group.
        """

        old_name = self.click_manager.current_group

        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Group", "New name:", text=old_name
        )

        if not ok or not new_name:
            return

        if new_name in self.click_manager.groups:
            QtWidgets.QMessageBox.warning(self, "Error", "Name already exists.")
            return

        self.click_manager.rename_group(old_name, new_name)

        self._append_log(f"Renamed group {old_name} → {new_name}")
        self._is_saved = False
        self.update()

    def on_delete_group(self):
        r"""
        Delete current group with safety checks.
        """

        current = self.click_manager.current_group

        if len(self.click_manager.groups) <= 1:
            QtWidgets.QMessageBox.warning(
                self, "Error", "You cannot delete the last remaining group."
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Group",
            f"Delete group '{current}' ?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        self.click_manager.remove_group(current)

        self._append_log(f"Deleted group: {current}")
        self._is_saved = False

        self.update()

    # ============================================================
    # Save
    # ============================================================
    def save_csv(self):
        r"""
        Save clicks to CSV.
        """
        try:
            # -------------------------------------------------
            # If no output path -> ask user
            # -------------------------------------------------
            if self.output_path is None:
                file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Save CSV", "", "CSV Files (*.csv)"
                )

                if not file_path:
                    self._append_log("Save cancelled.")
                    return

                self.output_path = file_path

                if self.output_path is not None:
                    self._append_log(f"Output CSV path setted to : {self.output_path}")

            # -------------------------------------------------
            # Save
            # -------------------------------------------------
            self.click_manager.save_to_csv(self.output_path)

            self._append_log(f"Saved to {self.output_path}")
            self._is_saved = True

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def save_as_csv(self):
        output_path = self.output_path
        self.output_path = None
        self.save_csv()
        if self.output_path is None:
            self.output_path = output_path

    def on_load_clicks(self):
        r"""
        Load clicks from CSV and replace current data.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Clicks", "", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        # -------------------------
        # Warning
        # -------------------------
        reply = QtWidgets.QMessageBox.question(
            self,
            "Load clicks",
            "This will replace current clicks. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply == QtWidgets.QMessageBox.No:
            return

        try:
            # -------------------------
            # Load ClickManager
            # -------------------------
            self.click_manager = ClickManager.load_from_csv(file_path)

            self._append_log(f"Clicks loaded from {file_path}")

            # -------------------------
            # Refresh UI
            # -------------------------
            self._is_saved = False
            self.update()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    # ============================================================
    # Utils
    # ============================================================

    def _append_log(self, msg: str):
        r"""
        Append log message.
        """
        self.log_text_edit.append(msg)

    # ============================================================
    # Close event
    # ============================================================

    def closeEvent(self, event):
        r"""
        Confirm exit if unsaved.
        """
        if not self._is_saved:
            res = QtWidgets.QMessageBox.question(
                self,
                "Exit",
                "Unsaved changes. Quit anyway?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if res == QtWidgets.QMessageBox.No:
                event.ignore()
                return

        event.accept()
