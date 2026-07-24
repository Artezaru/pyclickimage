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
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import cv2
from PyQt5 import QtWidgets, QtGui, QtCore

from .annotation_session import AnnotationSession
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

    # ================================
    # Init
    # ================================

    def __init__(
        self,
        images=None,
        session=None,
    ):
        r"""
        Create the Click Image application.

        Parameters
        ----------
        images : None, str, pathlib.Path or list of str/pathlib.Path, optional
            Images to preload at startup.

        session : None, str or pathlib.Path, optional
            CSV annotation session to preload.

        Notes
        -----
        ``images`` and ``session`` are mutually exclusive.
        A session CSV already contains the image list and annotations.
        """

        super().__init__()

        if images is not None and session is not None:
            raise ValueError(
                "Cannot initialize application with both images and session."
            )

        self.setWindowTitle(f"Click Image Application - pyclickimage v{__version__}")

        # -------------------------
        # State flags
        # -------------------------
        self.initialization_done = False

        self._is_saved = True

        self._image_has_changed = True
        self._colormap_has_changed = True

        self._is_empty_image = True

        # --------------------------
        # Display states
        # --------------------------

        self.alpha = 1.0
        self.beta_pc = 0

        self.display_min_pc = 0
        self.display_max_pc = 100

        self.show_clicks = True

        self.marker_color = QtGui.QColor(255, 0, 0)

        self.marker_size = 8

        # -------------------------
        # Core components
        # -------------------------

        # Global annotation state
        self.session = AnnotationSession()
        self.precision_mode = "float"

        # Image viewer
        self.viewer = ImageViewer(half_shift=True)

        self.viewer.auto_marker = False

        self.viewer.left_click_signal.connect(self._process_left_click)

        self.viewer.right_click_signal.connect(self._process_right_click)

        # -------------------------
        # Image cache
        # -------------------------

        self.image_cache: Dict[Path, np.ndarray] = {}

        # -------------------------
        # Logging
        # -------------------------

        self.log_text_edit = QtWidgets.QTextEdit()
        self.log_text_edit.setReadOnly(True)

        # -------------------------
        # Main widget
        # -------------------------

        self.central = QtWidgets.QWidget()

        self.setCentralWidget(self.central)

        self.layout = QtWidgets.QHBoxLayout()

        self.central.setLayout(self.layout)

        # Quit shortcut

        quit_action = QtWidgets.QAction("Quit", self)

        quit_action.setShortcut("Ctrl+Q")

        quit_action.triggered.connect(self.close)

        self.addAction(quit_action)

        # Viewer

        self.layout.addWidget(self.viewer)

        # Side panel

        self.side = QtWidgets.QVBoxLayout()

        self.side_widget = QtWidgets.QWidget()

        self.side_widget.setFixedWidth(340)

        self.side_widget.setLayout(self.side)

        # -------------------------
        # Build interface
        # -------------------------

        self._init_left_panel()

        self._init_toolbar()

        self._init_shortcuts()

        # -------------------------
        # Load initial data
        # -------------------------

        if session is not None:

            self.session = AnnotationSession.from_csv(str(session))

            self.image_cache = {}

        elif images is not None:

            if isinstance(images, (str, Path)):
                images = [images]

            for image in images:

                image = Path(image)

                self.session.add_image(image)

                img = cv2.imread(str(image))

                if img is not None:
                    self.image_cache[image] = img

            if len(self.session.images) > 0:
                self.session.change_current_image(self.session.images[0])

        # -------------------------
        # Initialization finished
        # -------------------------

        self.initialization_done = True

        self._append_log("Application ready.")

        self.synchronize_images()
        self.synchronize_groups()
        self.update()

    def _init_left_panel(self):
        r"""
        Build the left interface for multi-image annotation session.
        """

        # ============================================================
        # Scroll Area
        # ============================================================

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(360)
        scroll.setWidget(self.side_widget)

        self.layout.addWidget(scroll)

        # ============================================================
        # SESSION / IMAGES
        # ============================================================

        image_group = QtWidgets.QGroupBox("Images")
        image_layout = QtWidgets.QVBoxLayout(image_group)

        # Current image selector

        row = QtWidgets.QHBoxLayout()

        row.addWidget(QtWidgets.QLabel("Current image"))

        self.image_selector = QtWidgets.QComboBox()
        self.image_selector.currentIndexChanged.connect(self.on_change_current_image)
        row.addWidget(self.image_selector)

        image_layout.addLayout(row)

        # Image buttons

        row = QtWidgets.QHBoxLayout()

        self.add_image_btn = QtWidgets.QPushButton("+")
        self.add_image_btn.setToolTip("Add image")
        self.add_image_btn.clicked.connect(self.on_add_images)

        self.remove_image_btn = QtWidgets.QPushButton("🗑")
        self.remove_image_btn.setToolTip("Remove current image")
        self.remove_image_btn.clicked.connect(self.on_remove_image)

        row.addWidget(self.add_image_btn)
        row.addWidget(self.remove_image_btn)

        image_layout.addLayout(row)

        self.fullpath_checkbox = QtWidgets.QCheckBox("Full path")

        self.fullpath_checkbox.setChecked(True)

        self.fullpath_checkbox.stateChanged.connect(self.synchronize_images)

        image_layout.addWidget(self.fullpath_checkbox)

        self.side.addWidget(image_group)

        # ============================================================
        # SESSION CSV
        # ============================================================

        session_group = QtWidgets.QGroupBox("Session")
        session_layout = QtWidgets.QHBoxLayout(session_group)

        self.load_session_btn = QtWidgets.QPushButton("Load Session CSV")
        self.load_session_btn.clicked.connect(self.on_load_session)

        self.save_session_btn = QtWidgets.QPushButton("Save Session CSV")
        self.save_session_btn.clicked.connect(self.on_save_session)

        session_layout.addWidget(self.load_session_btn)
        session_layout.addWidget(self.save_session_btn)

        self.side.addWidget(session_group)

        # ============================================================
        # GROUP MANAGEMENT
        # ============================================================

        group_box = QtWidgets.QGroupBox("Groups")
        group_layout = QtWidgets.QVBoxLayout(group_box)

        row = QtWidgets.QHBoxLayout()

        row.addWidget(QtWidgets.QLabel("Current group"))

        self.group_selector = QtWidgets.QComboBox()

        self.group_selector.currentTextChanged.connect(self.on_change_current_group)

        row.addWidget(self.group_selector)

        group_layout.addLayout(row)

        # Group buttons

        row = QtWidgets.QHBoxLayout()

        self.add_group_btn = QtWidgets.QPushButton("+")
        self.add_group_btn.setToolTip("Add group")
        self.add_group_btn.clicked.connect(self.on_add_group)

        self.rename_group_btn = QtWidgets.QPushButton("✎")
        self.rename_group_btn.setToolTip("Rename group")
        self.rename_group_btn.clicked.connect(self.on_rename_group)

        self.delete_group_btn = QtWidgets.QPushButton("🗑")
        self.delete_group_btn.setToolTip("Delete group")
        self.delete_group_btn.clicked.connect(self.on_delete_group)

        row.addWidget(self.add_group_btn)
        row.addWidget(self.rename_group_btn)
        row.addWidget(self.delete_group_btn)

        group_layout.addLayout(row)

        self.side.addWidget(group_box)

        # ============================================================
        # CLICK MANAGEMENT
        # ============================================================

        click_box = QtWidgets.QGroupBox("Clicks")
        click_layout = QtWidgets.QVBoxLayout(click_box)

        # Buttons

        row = QtWidgets.QHBoxLayout()

        self.undo_btn = QtWidgets.QPushButton("Undo")
        self.undo_btn.clicked.connect(self.on_remove_last_click)

        self.clear_btn = QtWidgets.QPushButton("Clear")
        self.clear_btn.clicked.connect(self.on_remove_all_clicks)

        row.addWidget(self.undo_btn)
        row.addWidget(self.clear_btn)

        click_layout.addLayout(row)

        # Options

        self.int_precision_checkbox = QtWidgets.QCheckBox("Integer precision")
        self.int_precision_checkbox.setChecked(False)
        self.int_precision_checkbox.stateChanged.connect(self.on_precision_changed)

        click_layout.addWidget(self.int_precision_checkbox)

        self.half_shift_checkbox = QtWidgets.QCheckBox("Half-shift coordinates")
        self.half_shift_checkbox.setChecked(True)
        self.half_shift_checkbox.stateChanged.connect(self.on_half_shift_changed)

        click_layout.addWidget(self.half_shift_checkbox)

        self.side.addWidget(click_box)

        # ============================================================
        # TABLE
        # ============================================================

        self.table = QtWidgets.QTableWidget(0, 3)

        self.table.setHorizontalHeaderLabels(["Index", "X", "Y"])

        self.table.setMinimumHeight(180)

        self.side.addWidget(self.table)

        # ============================================================
        # DISPLAY OPTIONS
        # ============================================================

        display_box = QtWidgets.QGroupBox("Display")
        display_layout = QtWidgets.QVBoxLayout(display_box)

        # Display clicks

        self.display_clicks_checkbox = QtWidgets.QCheckBox("Display clicks")
        self.display_clicks_checkbox.setChecked(True)
        self.display_clicks_checkbox.stateChanged.connect(
            self.on_display_clicks_changed
        )
        display_layout.addWidget(self.display_clicks_checkbox)

        self.side.addWidget(display_box)

        # ============================================================
        # LOG
        # ============================================================

        self.log_text_edit = QtWidgets.QTextEdit()

        self.log_text_edit.setReadOnly(True)

        self.side.addWidget(self.log_text_edit)

    def _init_shortcuts(self):
        r"""
        Initialize global keyboard shortcuts.
        """

        def add_action(
            name,
            shortcut,
            callback,
        ):
            action = QtWidgets.QAction(name, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)
            return action

        # ==========================================================
        # Application
        # ==========================================================

        add_action(
            "Open image",
            "Ctrl+O",
            self.on_add_images,
        )

        add_action(
            "Open session",
            "Ctrl+Shift+O",
            self.on_load_session,
        )

        add_action(
            "Save session",
            "Ctrl+S",
            self.on_save_session,
        )

        add_action(
            "Help",
            "F1",
            self.show_help,
        )

        # ==========================================================
        # Groups
        # ==========================================================

        add_action(
            "Add group",
            "Ctrl+G",
            self.on_add_group,
        )

        add_action(
            "Rename group",
            "F2",
            self.on_rename_group,
        )

        add_action(
            "Delete group",
            "Ctrl+Delete",
            self.on_delete_group,
        )

        add_action(
            "Previous group",
            "Ctrl+Up",
            self.previous_group,
        )

        add_action(
            "Next group",
            "Ctrl+Down",
            self.next_group,
        )

        # ==========================================================
        # Images
        # ==========================================================

        add_action(
            "Previous image",
            "Ctrl+Tab",
            self.previous_image,
        )

        add_action(
            "Next image",
            "Ctrl+Shift+Tab",
            self.next_image,
        )

        # ==========================================================
        # Clicks
        # ==========================================================

        add_action(
            "Undo click",
            "Ctrl+Z",
            self.on_remove_last_click,
        )

        add_action(
            "Clear clicks",
            "Ctrl+Shift+Z",
            self.on_remove_all_clicks,
        )

        # ==========================================================
        # Display
        # ==========================================================

        add_action(
            "Toggle clicks display",
            "Space",
            self.toggle_display_clicks,
        )

    def _init_toolbar(self):
        r"""Build toolbar"""
        # ============================================================
        # Toolbar
        # ============================================================

        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)

        # ===========================================================
        # Help
        # ===========================================================

        help_action = QtWidgets.QAction("Help", self)
        help_action.setToolTip("Open help")

        help_action.triggered.connect(self.show_help)

        toolbar.addAction(help_action)

        toolbar.addSeparator()

        # ============================================================
        # RESET
        # ============================================================

        toolbar.addAction("Reset View", self.viewer.reset_view)

        toolbar.addSeparator()

        # ============================================================
        # IMAGE
        # ============================================================

        image_btn = QtWidgets.QToolButton()
        image_btn.setText("⚙ Image")
        image_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        image_menu = QtWidgets.QMenu(self)

        image_panel = QtWidgets.QWidget()
        image_layout = QtWidgets.QFormLayout(image_panel)

        # -------------------------
        # Colormap
        # -------------------------

        self.colormap_selector = QtWidgets.QComboBox()
        self.colormap_selector.addItems(
            [
                "Default",
                "Gray",
                "Hot",
                "Jet",
                "Rainbow",
                "Cool",
                "Spring",
            ]
        )

        self.colormap_selector.currentIndexChanged.connect(self.on_colormap_changed)

        image_layout.addRow("Colormap", self.colormap_selector)

        # -------------------------
        # Alpha
        # -------------------------

        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(1, 500)
        self.alpha_slider.setValue(100)

        self.alpha_value_label = QtWidgets.QLabel("1.00")

        self.alpha_slider.valueChanged.connect(self.on_contrast_changed)

        alpha_widget = QtWidgets.QWidget()
        alpha_layout = QtWidgets.QHBoxLayout(alpha_widget)
        alpha_layout.setContentsMargins(0, 0, 0, 0)

        alpha_layout.addWidget(self.alpha_slider)
        alpha_layout.addWidget(self.alpha_value_label)

        image_layout.addRow("Alpha", alpha_widget)

        # -------------------------
        # Beta
        # -------------------------

        self.beta_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.beta_slider.setRange(-100, 100)
        self.beta_slider.setValue(0)

        self.beta_value_label = QtWidgets.QLabel("0%")

        self.beta_slider.valueChanged.connect(self.on_contrast_changed)

        beta_widget = QtWidgets.QWidget()
        beta_layout = QtWidgets.QHBoxLayout(beta_widget)
        beta_layout.setContentsMargins(0, 0, 0, 0)

        beta_layout.addWidget(self.beta_slider)
        beta_layout.addWidget(self.beta_value_label)

        image_layout.addRow("Beta", beta_widget)

        # -------------------------
        # Min
        # -------------------------

        self.min_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.min_slider.setRange(0, 100)
        self.min_slider.setValue(0)

        self.min_value_label = QtWidgets.QLabel("0%")

        self.min_slider.valueChanged.connect(self.on_contrast_changed)

        min_widget = QtWidgets.QWidget()
        min_layout = QtWidgets.QHBoxLayout(min_widget)
        min_layout.setContentsMargins(0, 0, 0, 0)

        min_layout.addWidget(self.min_slider)
        min_layout.addWidget(self.min_value_label)

        image_layout.addRow("Min", min_widget)

        # -------------------------
        # Max
        # -------------------------

        self.max_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.max_slider.setRange(0, 100)
        self.max_slider.setValue(100)

        self.max_value_label = QtWidgets.QLabel("100%")

        self.max_slider.valueChanged.connect(self.on_contrast_changed)

        max_widget = QtWidgets.QWidget()
        max_layout = QtWidgets.QHBoxLayout(max_widget)
        max_layout.setContentsMargins(0, 0, 0, 0)

        max_layout.addWidget(self.max_slider)
        max_layout.addWidget(self.max_value_label)

        image_layout.addRow("Max", max_widget)

        # -------------------------
        # Reset contrast
        # -------------------------

        self.reset_contrast_btn = QtWidgets.QPushButton("Reset")

        self.reset_contrast_btn.clicked.connect(self.on_reset_contrast)

        image_layout.addRow(self.reset_contrast_btn)

        image_action = QtWidgets.QWidgetAction(image_menu)
        image_action.setDefaultWidget(image_panel)

        image_menu.addAction(image_action)

        image_btn.setMenu(image_menu)

        toolbar.addWidget(image_btn)

        # ============================================================
        # CLICKS
        # ============================================================

        toolbar.addSeparator()

        clicks_btn = QtWidgets.QToolButton()
        clicks_btn.setText("⚙ Clicks")
        clicks_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        clicks_menu = QtWidgets.QMenu(self)

        clicks_panel = QtWidgets.QWidget()
        clicks_layout = QtWidgets.QFormLayout(clicks_panel)

        self.display_clicks_checkbox = QtWidgets.QCheckBox("Display clicks")

        self.display_clicks_checkbox.setChecked(True)

        self.display_clicks_checkbox.stateChanged.connect(
            self.on_display_clicks_changed
        )

        clicks_layout.addRow(self.display_clicks_checkbox)

        # Marker color

        marker_widget = QtWidgets.QWidget()
        marker_layout = QtWidgets.QHBoxLayout(marker_widget)
        marker_layout.setContentsMargins(0, 0, 0, 0)

        self.color_btn = QtWidgets.QPushButton("Color")
        self.color_btn.clicked.connect(self.choose_color)

        self.color_preview = QtWidgets.QLabel("   ")

        self.color_preview.setStyleSheet(
            "background-color: rgb(255,0,0); border: 1px solid black;"
        )

        marker_layout.addWidget(self.color_btn)
        marker_layout.addWidget(self.color_preview)

        clicks_layout.addRow("Marker", marker_widget)

        # Marker size

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

        clicks_layout.addRow(
            "Size",
            self.size_selector,
        )

        clicks_action = QtWidgets.QWidgetAction(clicks_menu)
        clicks_action.setDefaultWidget(clicks_panel)

        clicks_menu.addAction(clicks_action)

        clicks_btn.setMenu(clicks_menu)

        toolbar.addWidget(clicks_btn)

        # ============================================================
        # CROSSHAIR
        # ============================================================

        toolbar.addSeparator()

        crosshair_btn = QtWidgets.QToolButton()
        crosshair_btn.setText("⚙ Crosshair")
        crosshair_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        crosshair_menu = QtWidgets.QMenu(self)

        crosshair_panel = QtWidgets.QWidget()
        crosshair_layout = QtWidgets.QFormLayout(crosshair_panel)

        crosshair_widget = QtWidgets.QWidget()
        crosshair_widget_layout = QtWidgets.QHBoxLayout(crosshair_widget)

        crosshair_widget_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.crosshair_color_btn = QtWidgets.QPushButton("Color")

        self.crosshair_color_btn.clicked.connect(self.crosshair_choose_color)

        self.crosshair_color_preview = QtWidgets.QLabel("   ")

        self.crosshair_color_preview.setStyleSheet(
            "background-color: rgb(255,0,0); border: 1px solid black;"
        )

        crosshair_widget_layout.addWidget(self.crosshair_color_btn)

        crosshair_widget_layout.addWidget(self.crosshair_color_preview)

        crosshair_layout.addRow(
            "Color",
            crosshair_widget,
        )

        crosshair_action = QtWidgets.QWidgetAction(crosshair_menu)

        crosshair_action.setDefaultWidget(crosshair_panel)

        crosshair_menu.addAction(crosshair_action)

        crosshair_btn.setMenu(crosshair_menu)

        toolbar.addWidget(crosshair_btn)

        # ============================================================
        # LOGS
        # ============================================================
        toolbar.addSeparator()

        clear_log_btn = QtWidgets.QToolButton()
        clear_log_btn.setText("Clear logs")
        clear_log_btn.clicked.connect(self.clear_logs)

        toolbar.addWidget(clear_log_btn)

    # =======================
    # Synchro
    # =======================
    def synchronize_images(self):
        r"""
        Synchronize image selector with current session images.
        """

        self.image_selector.blockSignals(True)

        current_image = self.session.current_image

        self.image_selector.clear()

        fullpath = self.fullpath_checkbox.isChecked()

        for image in self.session.images:

            image = Path(image)

            text = str(image) if fullpath else image.name

            self.image_selector.addItem(
                text,
                str(image),
            )

        # Restore current selection
        if current_image is not None:

            current_image = str(current_image)

            for index in range(self.image_selector.count()):

                if self.image_selector.itemData(index) == current_image:
                    self.image_selector.setCurrentIndex(index)
                    break

        # If session has no current image, use combobox current index
        if self.session.current_image is None:

            index = self.image_selector.currentIndex()

            if index >= 0:

                image_path = self.image_selector.itemData(index)

                if image_path is not None:
                    self.session.change_current_image(image_path)
                    self._image_has_changed = True

        self.image_selector.blockSignals(False)

    def synchronize_groups(self):
        r"""
        Synchronize group selector with current session groups.
        """

        self.group_selector.blockSignals(True)

        current_group = self.session.current_group

        self.group_selector.clear()

        for group in self.session.groups:

            self.group_selector.addItem(
                group,
                group,
            )

        # Restore current group
        if current_group is not None:

            for index in range(self.group_selector.count()):

                if self.group_selector.itemData(index) == current_group:
                    self.group_selector.setCurrentIndex(index)
                    break

        # No current group -> select first available
        if self.session.current_group is None and self.group_selector.count() > 0:

            self.group_selector.setCurrentIndex(0)

            self.session.current_group = self.group_selector.currentData()

        # Empty combobox -> no current group
        elif self.group_selector.count() == 0:

            self.session.current_group = None

        self.group_selector.blockSignals(False)

    # ===============================
    # Images management
    # ===============================
    def on_add_images(self):
        r"""
        Add one or multiple images to the current annotation session.
        """

        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )

        if not file_paths:
            return

        added_images = []

        for file_path in file_paths:

            image_path = Path(file_path)

            # Check forbidden comma in path
            if "," in str(image_path):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid image path",
                    f"Image path cannot contain ',' :\n{image_path}",
                )
                continue

            # Load image to verify it is valid
            image = cv2.imread(str(image_path))

            if image is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid image",
                    f"Failed to load image:\n{image_path}",
                )
                continue

            try:
                self.session.add_image(image_path)

                # Cache image
                self.image_cache[image_path] = image

                added_images.append(image_path)

            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Cannot add image",
                    str(e),
                )

        if not added_images:
            return

        # Select last added image
        current_image = added_images[-1]

        self.session.change_current_image(current_image)

        self._append_log(f"{len(added_images)} image(s) added.")

        self._image_has_changed = True
        self._is_saved = False

        self.synchronize_images()
        self.update()

    def get_current_image(self) -> Optional[np.ndarray]:
        r"""
        Return the current image from cache.

        If the image is not cached, it is loaded from disk.

        Returns
        -------
        numpy.ndarray or None
            Current BGR image.
        """

        if self.session.current_image is None:
            return None

        image_path = self.session.current_image

        if image_path in self.image_cache:
            return self.image_cache[image_path]

        image = cv2.imread(str(image_path))

        if image is None:
            return None

        self.image_cache[image_path] = image

        return image

    def on_remove_image(self):
        r"""
        Remove the current image from the annotation session.
        """

        if self.session.current_image is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No image",
                "There is no current image to remove.",
            )
            return

        image_path = self.session.current_image

        reply = QtWidgets.QMessageBox.question(
            self,
            "Remove image",
            f"Remove image:\n{image_path.name}?\n\n"
            "All associated clicks will be lost.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.session.remove_image(image_path)

            # Remove from cache
            if image_path in self.image_cache:
                del self.image_cache[image_path]

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                str(e),
            )
            return

        self._image_has_changed = True
        self._is_saved = False

        self.synchronize_images()
        self.update()
        self._append_log(f"Image removed: {image_path.name}")

    def on_change_current_image(self, index: int) -> None:
        r"""
        Change the currently displayed image.
        """

        if index < 0:
            self.session.current_image = None
            return

        image_path = self.image_selector.itemData(index)

        if image_path is None:
            self.session.current_image = None
            return

        image_path = Path(image_path)

        try:
            self.session.change_current_image(image_path)

        except KeyError as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot change image",
                str(e),
            )
            return

        self._image_has_changed = True
        self._is_saved = False

        self.update()

        self._append_log(f"Current image changed: {image_path.name}")

    # =====================
    # Group management
    # =====================

    def on_add_group(self) -> None:
        r"""
        Create a new annotation group.
        """

        group_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Add group",
            "Group name:",
        )

        if not ok:
            return

        group_name = group_name.strip()

        if not group_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid group",
                "Group name cannot be empty.",
            )
            return

        try:
            self.session.add_group(group_name)
            self.session.change_current_group(group_name)

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot create group",
                str(e),
            )
            return

        self._is_saved = False

        self.synchronize_groups()
        self.update()

        self._append_log(f"Group created: {group_name}")

    def on_delete_group(self) -> None:
        r"""
        Delete the current annotation group.
        """

        group_name = self.session.current_group

        if group_name is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No group selected",
                "There is no current group to delete.",
            )
            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete group",
            f"Delete group '{group_name}'?\n" "All associated clicks will be removed.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.session.delete_group(group_name)

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Cannot delete group",
                str(e),
            )
            return

        self._is_saved = False

        self.synchronize_groups()
        self.update()

        self._append_log(f"Group deleted: {group_name}")

    def on_rename_group(self) -> None:
        r"""
        Rename the current annotation group.
        """

        old_name = self.session.current_group

        if old_name is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No group selected",
                "There is no current group to rename.",
            )
            return

        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename group",
            "New group name:",
            text=old_name,
        )

        if not ok:
            return

        new_name = new_name.strip()

        if not new_name:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid group",
                "Group name cannot be empty.",
            )
            return

        if new_name == old_name:
            return

        try:
            self.session.rename_group(
                old_name,
                new_name,
            )

            self.session.change_current_group(
                new_name,
            )

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot rename group",
                str(e),
            )
            return

        self._is_saved = False

        self.synchronize_groups()
        self.update()

        self._append_log(f"Group renamed: {old_name} -> {new_name}")

    def on_change_current_group(self, index: int) -> None:
        r"""
        Change the currently active annotation group.
        """

        if index < 0:
            self.session.current_group = None
            return

        group_name = self.group_selector.itemData(index)

        if group_name is None:
            self.session.current_group = None
            return

        try:
            self.session.change_current_group(group_name)

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Cannot change group",
                str(e),
            )
            return

        self._is_saved = False

        self.update()

        self._append_log(f"Current group changed: {group_name}")

    # ============================
    # Clicks Management
    # ============================
    def _check_annotation_ready(self) -> bool:
        r"""
        Check if an image and a group are selected.

        Returns
        -------
        bool
            True if annotations can be added.
        """

        if self.session.current_image is None:

            QtWidgets.QMessageBox.warning(
                self,
                "No image",
                "WARNING: No image selected.\n\n"
                "Please load an image before adding clicks.",
            )

            return False

        if self.session.current_group is None:

            QtWidgets.QMessageBox.warning(
                self,
                "No group",
                "WARNING: No annotation group selected.\n\n"
                "Please create or select a group before adding clicks.",
            )

            return False

        return True

    def _process_left_click(self, x: float, y: float):
        r"""
        Add click to current image/group.
        """

        if not self.initialization_done:
            return

        if not self._check_annotation_ready():
            return

        self.session.add_click(x, y)

        self._is_saved = False

        self._append_log(
            f"Click added to '{self.session.current_group}' "
            f"on '{self.session.current_image.name}': "
            f"({x:.3f}, {y:.3f})"
        )

        self.update()

    def _process_right_click(self, x: float, y: float):
        r"""
        Add empty click placeholder.
        """

        if not self.initialization_done:
            return

        if not self._check_annotation_ready():
            return

        self.session.add_click(None, None)

        self._is_saved = False

        self._append_log(
            f"Empty click added to '{self.session.current_group}' "
            f"on '{self.session.current_image.name}'."
        )

        self.update()

    def on_precision_changed(self, state):
        r"""
        Change displayed coordinate precision.
        """

        use_int = state == QtCore.Qt.Checked

        self.session.set_precision_mode("int" if use_int else "float")

        self._append_log(f"Precision mode: {'INT' if use_int else 'FLOAT'}")

        self.update()

    def on_half_shift_changed(self, state):
        r"""
        Toggle half-shift mode for the whole session.
        """

        half_shift = state == QtCore.Qt.Checked

        has_clicks = any(
            manager.n_clicks > 0 for manager in self.session.click_managers.values()
        )

        if has_clicks:

            msg = QtWidgets.QMessageBox(self)

            msg.setWindowTitle("Existing clicks detected")
            msg.setText(
                "Do you want to shift all previous clicked points "
                "by 0.5 to match the new coordinate system?"
            )
            msg.setInformativeText("No = keep clicks\nYes = shift clicks")
            msg.setStandardButtons(QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes)
            msg.setDefaultButton(QtWidgets.QMessageBox.Yes)

            if msg.exec_() == QtWidgets.QMessageBox.Yes:

                for manager in self.session.click_managers.values():

                    if half_shift:
                        manager.to_half_shift_on()
                    else:
                        manager.to_half_shift_off()

        self.viewer.half_shift = half_shift

        self._append_log(f"Half-Shift mode: {half_shift}")

        self._is_saved = False
        self.update()

    def on_remove_last_click(self) -> None:
        r"""
        Remove the last click.
        """

        if not self._check_annotation_ready():
            return

        try:
            self.session.remove_last_click()

        except Exception as e:

            QtWidgets.QMessageBox.warning(
                self,
                "Cannot remove click",
                str(e),
            )

            return

        self._is_saved = False

        self.update()

        self._append_log(
            f"Last click removed from '{self.session.current_group}' "
            f"on '{self.session.current_image.name}'."
        )

    def on_remove_all_clicks(self) -> None:
        r"""
        Remove all clicks from the current image and group.
        """

        if self.session.current_image is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No image selected",
                "WARNING: No image selected.\n\n"
                "Please load an image before removing clicks.",
            )
            return

        if self.session.current_group is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No group selected",
                "WARNING: No annotation group selected.\n\n"
                "Please create or select a group before removing clicks.",
            )
            return

        image_name = self.session.current_image.name
        group_name = self.session.current_group

        answer = QtWidgets.QMessageBox.question(
            self,
            "Clear clicks",
            f"Remove all clicks from group '{group_name}'\n"
            f"on image '{image_name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.session.remove_all_clicks()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Cannot remove clicks",
                str(e),
            )
            return

        self._is_saved = False

        self._append_log(
            f"All clicks removed from '{group_name}' " f"on '{image_name}'."
        )

        self.update()

    # ================================
    # Session Management
    # ================================
    def on_load_session(self) -> None:
        r"""
        Load an annotation session from CSV.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Annotation Session",
            "",
            "CSV files (*.csv)",
        )

        if not file_path:
            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Load session",
            "Current session will be replaced.\nContinue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.session = AnnotationSession.from_csv(file_path)

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Cannot load session",
                str(e),
            )
            return

        self._is_saved = True
        self._image_has_changed = True

        # Synchronize interface
        self.synchronize_images()
        self.synchronize_groups()

        self.update()

        self._append_log(f"Session loaded: {file_path}")

    def on_save_session(self) -> None:
        r"""
        Save the current annotation session to CSV.
        """

        if len(self.session.images) == 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Empty session",
                "There is no image to save.",
            )
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Annotation Session",
            "",
            "CSV files (*.csv)",
        )

        if not file_path:
            return

        path = Path(file_path)

        # Add .csv extension if missing
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        try:
            self.session.to_csv(str(path))

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Cannot save session",
                str(e),
            )
            return

        self._is_saved = True

        self._append_log(f"Session saved: {path}")

    # =============================
    # Updates
    # =============================
    def update(self):
        r"""
        Refresh complete interface.
        """
        if not self.initialization_done:
            return

        self.update_table()
        self.update_viewer()

    def update_viewer(self):
        r"""
        Render current image and annotations.
        """

        image = self.get_current_image()

        if image is None:
            image = np.zeros(
                (512, 512, 3),
                dtype=np.uint8,
            )

        img = image.astype(np.float32)

        if np.issubdtype(image.dtype, np.integer):
            imax = np.iinfo(image.dtype).max
        else:
            imax = 1.0

        dm = self.display_min_pc * imax / 100
        dM = self.display_max_pc * imax / 100
        b = self.beta_pc * imax / 100

        img = np.clip(img, dm, dM)

        img = (img - dm) / max(1, dM - dm) * imax

        img = img * self.alpha + b

        img = np.clip(
            np.round(img),
            0,
            imax,
        ).astype(image.dtype)

        if self._image_has_changed or self._colormap_has_changed:

            colormap = self.get_selected_colormap()

            if colormap is not None:
                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2GRAY,
                )

                img = cv2.applyColorMap(
                    gray,
                    colormap,
                )

            rgb = cv2.cvtColor(
                img,
                cv2.COLOR_BGR2RGB,
            )

            h, w, ch = rgb.shape

            qimg = QtGui.QImage(
                rgb.data,
                w,
                h,
                ch * w,
                QtGui.QImage.Format_RGB888,
            ).copy()

            self.viewer.set_image(QtGui.QPixmap.fromImage(qimg))

            self._image_has_changed = False
            self._colormap_has_changed = False

        # ----------------------
        # Draw annotations
        # ----------------------
        self.viewer.clear_markers()

        pts = self.session.current_clicks

        if self.show_clicks:

            for x, y in pts:

                if x is None or y is None:
                    continue

                self.viewer.add_marker(
                    (x, y),
                    self.marker_color,
                    self.marker_size,
                )

    def _format_value(self, v):
        r"""
        Format a coordinate for display in the table.
        """

        if v is None:
            return ""

        if self.int_precision_checkbox.isChecked():
            return str(int(round(v)))

        return f"{v:.3f}"

    def update_table(self):
        r"""
        Update table with current image/group clicks.
        """

        if self.session.current_group is None:
            self.table.setRowCount(0)
            return

        pts = self.session.current_clicks

        self.table.clearContents()
        self.table.setRowCount(len(pts))

        for i, (x, y) in enumerate(pts):

            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i)))

            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(self._format_value(x)))

            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(self._format_value(y)))

    # =========================
    # Display
    # =========================

    def on_colormap_changed(self, index: int) -> None:
        r"""
        Update image colormap.
        """

        self._colormap_has_changed = True

        self._append_log(f"Colormap changed: {self.colormap_selector.currentText()}")

        self.update()

    def get_selected_colormap(self) -> Optional[int]:
        r"""
        Return OpenCV colormap corresponding to current selection.

        Returns
        -------
        int or None
            OpenCV colormap identifier.
        """

        COLORMAPS = {
            "Default": None,
            "Gray": cv2.COLORMAP_BONE,
            "Hot": cv2.COLORMAP_HOT,
            "Jet": cv2.COLORMAP_JET,
            "Rainbow": cv2.COLORMAP_RAINBOW,
            "Cool": cv2.COLORMAP_COOL,
            "Spring": cv2.COLORMAP_SPRING,
        }

        return COLORMAPS.get(
            self.colormap_selector.currentText(),
            None,
        )

    def on_contrast_changed(self) -> None:
        r"""
        Update image contrast parameters.
        """

        self.alpha = self.alpha_slider.value() / 100.0
        self.beta_pc = self.beta_slider.value()

        self.display_min_pc = self.min_slider.value()
        self.display_max_pc = self.max_slider.value()

        self.alpha_value_label.setText(f"{self.alpha:.2f}")

        self.beta_value_label.setText(f"{self.beta_pc}%")

        self.min_value_label.setText(f"{self.display_min_pc}%")

        self.max_value_label.setText(f"{self.display_max_pc}%")

        self._image_has_changed = True

        self.update()

    def on_reset_contrast(self) -> None:
        r"""
        Reset all contrast parameters to default values.
        """

        self.alpha_slider.setValue(100)
        self.beta_slider.setValue(0)

        self.min_slider.setValue(0)
        self.max_slider.setValue(100)

        # Trigger update once
        self.on_contrast_changed()

    def on_display_clicks_changed(self, state: int) -> None:
        r"""
        Toggle annotation marker visibility.
        """

        self.show_clicks = state == QtCore.Qt.Checked

        self._append_log(f"Display clicks: {self.show_clicks}")

        self.update()

    def crosshair_choose_color(self) -> None:
        r"""
        Change viewer crosshair color.
        """

        color = QtWidgets.QColorDialog.getColor(
            self.viewer.get_crosshair_color(),
            self,
        )

        if not color.isValid():
            return

        self.viewer.set_crosshair_color(color)

        self.crosshair_color_preview.setStyleSheet(
            f"background-color: {color.name()};" "border: 1px solid black;"
        )

        self._append_log(f"Crosshair color changed: {color.name()}")

        self.update()

    def choose_color(self) -> None:
        r"""
        Change annotation marker color.
        """

        color = QtWidgets.QColorDialog.getColor(
            self.marker_color,
            self,
        )

        if not color.isValid():
            return

        self.marker_color = color

        self.color_preview.setStyleSheet(
            f"background-color: {color.name()};" "border: 1px solid black;"
        )

        self._append_log(f"Marker color changed: {color.name()}")

        self.update()

    def on_marker_size_changed(self, value: str) -> None:
        r"""
        Update annotation marker size.
        """

        try:
            self.marker_size = float(value)

        except ValueError:
            self.marker_size = 8.0

        self._append_log(f"Marker size changed: {self.marker_size:.1f}")

        self.update()

    # ========================
    # Shortcuts
    # ========================
    def toggle_display_clicks(self):
        r"""
        Toggle the display of annotation markers.

        This updates the associated checkbox state, which triggers
        the display callback.
        """

        checked = self.display_clicks_checkbox.isChecked()

        self.display_clicks_checkbox.setChecked(not checked)

    def select_group_index(self, index):
        r"""
        Select an annotation group by its combobox index.

        Parameters
        ----------
        index : int
            Index of the group to select.
        """

        if 0 <= index < self.group_selector.count():

            self.group_selector.blockSignals(True)

            self.group_selector.setCurrentIndex(index)

            self.on_change_current_group(self.group_selector.currentText())

            self.group_selector.blockSignals(False)

            self.update()

    def select_image_index(self, index):
        r"""
        Select an image by its combobox index.

        Parameters
        ----------
        index : int
            Index of the image to select.
        """

        if 0 <= index < self.image_selector.count():

            self.image_selector.blockSignals(True)

            self.image_selector.setCurrentIndex(index)

            self.on_change_current_image(index)

            self.image_selector.blockSignals(False)

            self.update()

    def previous_group(self):
        r"""
        Select the previous annotation group.
        """

        self.select_group_index(self.group_selector.currentIndex() - 1)

    def next_group(self):
        r"""
        Select the next annotation group.
        """

        self.select_group_index(self.group_selector.currentIndex() + 1)

    def previous_image(self):
        r"""
        Select the previous image in the session.
        """

        self.select_image_index(self.image_selector.currentIndex() - 1)

    def next_image(self):
        r"""
        Select the next image in the session.
        """

        self.select_image_index(self.image_selector.currentIndex() + 1)

    # ============================================================
    # Utils
    # ============================================================
    def _append_log(self, msg: str):
        r"""
        Append log message.
        """
        self.log_text_edit.append(msg)

    def clear_logs(self):
        r"""
        Clear log message.
        """
        self.log_text_edit.clear()

    def show_help(self):

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("pyclickimage Help")
        dialog.resize(600, 450)

        layout = QtWidgets.QVBoxLayout(dialog)

        tabs = QtWidgets.QTabWidget()

        # ==========================================================
        # Prerequisites
        # ==========================================================

        prereq = QtWidgets.QTextEdit()
        prereq.setReadOnly(True)

        prereq.setHtml("""
            <h2>Prerequisites</h2>

            <p>
            Before annotating images, the application requires:
            </p>

            <ul>
                <li>
                At least one image must be loaded.
                </li>
                <li>
                At least one annotation group must be created.
                </li>
            </ul>

            <p>
            Clicks can only be added when both a current image
            and a current group are selected.
            </p>
            """)

        tabs.addTab(prereq, "Prerequisites")

        # ==========================================================
        # Images
        # ==========================================================

        images = QtWidgets.QTextEdit()
        images.setReadOnly(True)

        images.setHtml("""
            <h2>Images</h2>

            <p>
            The <b>Images</b> panel manages the images included in
            the current annotation session.
            </p>

            <ul>
                <li>
                Click the <b>+</b> button to add an image.
                </li>
                <li>
                Click the <b>🗑</b> button to remove the currently selected image.
                </li>
                <li>
                Use the dropdown menu to switch between loaded images.
                </li>
            </ul>

            <p>
            Image paths containing commas (<b>,</b>) are not supported
            because annotations are saved using CSV files.
            </p>
            """)

        tabs.addTab(images, "Images")

        # ==========================================================
        # Groups
        # ==========================================================

        groups = QtWidgets.QTextEdit()
        groups.setReadOnly(True)

        groups.setHtml("""
            <h2>Groups</h2>

            <p>
            Groups are used to organize annotations.
            Each click belongs to the currently selected group.
            </p>

            <ul>
                <li>
                Click the <b>+</b> button to create a new group.
                </li>
                <li>
                Select a group using the dropdown menu.
                </li>
                <li>
                Use the rename button to change a group's name.
                </li>
                <li>
                Use the <b>🗑</b> button to delete the current group.
                </li>
            </ul>

            <p>
            Deleting a group removes all associated clicks
            from every image.
            </p>
            """)

        tabs.addTab(groups, "Groups")

        # ==========================================================
        # Mouse
        # ==========================================================

        mouse = QtWidgets.QTextEdit()
        mouse.setReadOnly(True)

        mouse.setHtml("""
            <h2>Mouse controls</h2>

            <p>
            Mouse interactions are performed directly on the displayed image.
            </p>

            <ul>
                <li>
                <b>Left click</b>:
                add an annotation point at the clicked position.
                </li>

                <li>
                <b>Right click</b>:
                add an empty point placeholder.
                </li>

                <li>
                <b>Mouse wheel</b>:
                zoom in or out on the image.
                </li>

                <li>
                <b>Middle mouse button drag</b>:
                move the image while keeping the button pressed.
                </li>
            </ul>

            <p>
            The clicked position is converted into image coordinates.
            See the <b>Coordinates</b> section for details about the
            coordinate system.
            </p>
            """)

        tabs.addTab(mouse, "Mouse")

        # ==========================================================
        # Coordinates
        # ==========================================================

        coordinates = QtWidgets.QTextEdit()
        coordinates.setReadOnly(True)

        coordinates.setHtml("""
            <h2>Coordinates</h2>

            <p>
            Annotation coordinates are always internally stored as
            floating-point values.
            </p>

            <p>
            Coordinates follow the NumPy image convention:
            </p>

            <pre>
            image[y, x]
            </pre>

            <p>
            where:
            </p>

            <ul>
                <li>
                <b>x</b> is the horizontal coordinate (column).
                </li>

                <li>
                <b>y</b> is the vertical coordinate (row).
                </li>
            </ul>

            <p>
            The displayed values depend on the selected
            <b>Integer precision</b> mode:
            </p>

            <ul>
                <li>
                <b>Float mode</b>:
                coordinates are displayed with decimal values.
                </li>

                <li>
                <b>Integer mode</b>:
                coordinates are rounded and displayed as integers.
                </li>
            </ul>

            <h3>Pixel reference</h3>

            <p>
            By default, the coordinate reference system considers the
            center of the first pixel as:
            </p>

            <pre>
            (0, 0)
            </pre>

            <p>
            If <b>Half-shift coordinates</b> is disabled, the coordinate
            system is shifted so that pixel boundaries are used instead.
            </p>

            <p>
            This option only changes the coordinate representation.
            Stored annotations remain consistent.
            </p>
            """)

        tabs.addTab(coordinates, "Coordinates")

        # ==========================================================
        # Session
        # ==========================================================

        session = QtWidgets.QTextEdit()
        session.setReadOnly(True)

        session.setHtml("""
            <h2>Annotation sessions</h2>

            <p>
            A session contains all loaded images, annotation groups,
            and associated clicks.
            </p>

            <h3>Saving a session</h3>

            <ul>
                <li>
                Use <b>Save Session CSV</b> to export the current session.
                </li>

                <li>
                The CSV file contains image paths, groups, coordinates,
                and click indices.
                </li>
            </ul>

            <h3>Loading a session</h3>

            <ul>
                <li>
                Use <b>Load Session CSV</b> to restore a previous session.
                </li>

                <li>
                Loading a session replaces the current annotation session.
                </li>
            </ul>

            <p>
            Make sure that image files are still available at their original
            paths before loading a saved session.
            </p>
            """)

        tabs.addTab(session, "Session")

        # ==========================================================
        # Shortcuts
        # ==========================================================

        shortcuts = QtWidgets.QTextEdit()
        shortcuts.setReadOnly(True)

        shortcuts.setHtml("""
            <h2>Keyboard shortcuts</h2>

            <h3>Session</h3>

            <ul>
                <li>
                <b>Ctrl + O</b> : Open image.
                </li>

                <li>
                <b>Ctrl + Shift + O</b> : Open annotation session.
                </li>

                <li>
                <b>Ctrl + S</b> : Save annotation session.
                </li>

                <li>
                <b>Ctrl + Q</b> : Quit application.
                </li>
            </ul>


            <h3>Groups</h3>

            <ul>
                <li>
                <b>Ctrl + G</b> : Add a new annotation group.
                </li>

                <li>
                <b>F2</b> : Rename current group.
                </li>

                <li>
                <b>Ctrl + Up / Down arrows</b> : Navigate between groups.
                </li>
            </ul>


            <h3>Images</h3>

            <ul>
                <li>
                <b>Tab</b> : Select next image.
                </li>

                <li>
                <b>Shift + Tab</b> : Select previous image.
                </li>
            </ul>


            <h3>Annotations</h3>

            <ul>
                <li>
                <b>Ctrl + Z</b> : Undo last click.
                </li>

                <li>
                <b>Ctrl + Shift + Z</b> : Remove all clicks
                from current image/group.
                </li>
            </ul>


            <h3>Display</h3>

            <ul>
                <li>
                <b>Space</b> : Toggle display of annotations.
                </li>

                <li>
                <b>Mouse wheel</b> : Zoom image.
                </li>

                <li>
                <b>Middle mouse drag</b> : Move image.
                </li>
            </ul>


            <h3>Help</h3>

            <ul>
                <li>
                <b>F1</b> : Open help window.
                </li>
            </ul>

            """)

        tabs.addTab(shortcuts, "Shortcuts")

        # ==========================================================
        # Contact
        # ==========================================================

        contact = QtWidgets.QTextEdit()
        contact.setReadOnly(True)

        contact.setHtml("""
            <h2>Contact</h2>

            <p>
            pyclickimage
            </p>

            <p>
            Copyright (C) 2025-2026 Artezaru
            </p>

            <p>
            Email:
            <a href="mailto:artezaru.github@proton.me">
            artezaru.github@proton.me
            </a>
            </p>

            <p>
            For bug reports, feature requests, or any issue with the
            application, please contact the developer using the email above.
            </p>
            """)

        tabs.addTab(contact, "Contact")

        layout.addWidget(tabs)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)

        layout.addWidget(close_btn)

        dialog.exec_()

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
