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
from PyQt5 import QtWidgets, QtGui, QtCore

from .annotation_session import AnnotationSession
from .qt_image_tool_window import QtImageToolWindow, read_image
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

    Notes
    -----
    The image is displayed by an embedded :class:`QtImageToolWindow`,
    whose toolbar (display mode, colormap, *Interpolation*) handles the
    display contrast.
    """

    # ================================
    # Init
    # ================================

    def __init__(
        self,
        images: str | Path | list[str | Path] | None = None,
        session: str | Path | None = None,
    ) -> None:
        r"""
        Create the Click Image application.

        Parameters
        ----------
        images : str, pathlib.Path, list or None, optional
            Images to preload at startup.

        session : str, pathlib.Path or None, optional
            Annotation session file to load at startup.
            The file format is detected automatically from its extension.

            Supported formats:

            - CSV
            - JSON

        Raises
        ------
        ValueError
            If images and a session file are provided together.

        Notes
        -----
        Images and sessions are mutually exclusive.

        A session file already contains:

        - image paths,
        - annotation groups,
        - click coordinates,
        - current selections,
        - session options.

        Therefore, providing additional images is not allowed.
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

        self._is_empty_image = True

        # --------------------------
        # Display states
        # --------------------------

        # Contrast and colormap are managed by QtImageToolWindow.

        self.show_clicks = True
        self.show_other_clicks = False

        self.marker_color = QtGui.QColor(255, 0, 0)
        self.other_marker_color = QtGui.QColor(0, 0, 255)

        self.marker_size = 8
        self.other_marker_size = 8

        # -------------------------
        # Core components
        # -------------------------

        # Global annotation state
        self.session = AnnotationSession()
        self.precision_mode = "float"

        # Image viewer: QtImageToolWindow embedded as a widget.
        # Images are managed by this application, so "Open" is removed.
        self.image_tool = QtImageToolWindow(
            remove_open=True,
            half_shift=True,
        )

        # Direct access to the underlying QtImageViewer (markers,
        # crosshair, half-shift).
        self.viewer = self.image_tool.viewer

        self.image_tool.auto_marker = False

        self.image_tool.left_click.connect(self._process_left_click)

        self.image_tool.right_click.connect(self._process_right_click)

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

        self.layout.addWidget(self.image_tool, 1)

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

            self.session = AnnotationSession.from_file(session)

        elif images is not None:

            if isinstance(images, (str, Path)):
                images = [images]

            for image in images:

                image = Path(image)

                self.session.add_image(image)

                img = read_image(image)

                if img is not None:
                    self.image_cache[image] = img

            if self.session.images:
                self.session.select_current_image_index(0)

        # -------------------------
        # Initialization finished
        # -------------------------

        self.initialization_done = True

        self._append_log("Application ready.")

        self.synchronize_images()
        self.synchronize_groups()
        self.synchronize_params()
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
        # SESSION
        # ============================================================

        session_group = QtWidgets.QGroupBox("Session")
        session_layout = QtWidgets.QHBoxLayout(session_group)

        self.load_session_btn = QtWidgets.QPushButton("Load Session")
        self.load_session_btn.clicked.connect(self.on_load_session)

        self.save_session_btn = QtWidgets.QPushButton("Save Session")
        self.save_session_btn.clicked.connect(self.on_save_session)

        session_layout.addWidget(self.load_session_btn)
        session_layout.addWidget(self.save_session_btn)

        self.side.addWidget(session_group)

        # ============================================================
        # IMAGES
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
        self.add_image_btn.setFixedHeight(32)
        self.add_image_btn.clicked.connect(self.on_add_images)

        self.remove_image_btn = QtWidgets.QPushButton("🗑")
        self.remove_image_btn.setToolTip("Remove current image")
        self.remove_image_btn.setFixedHeight(32)
        self.remove_image_btn.clicked.connect(self.on_remove_image)

        row.addWidget(self.add_image_btn)
        row.addWidget(self.remove_image_btn)

        self.sort_image_alpha_btn = QtWidgets.QPushButton("⇅a")
        self.sort_image_alpha_btn.setToolTip("Sort images alphabetically")
        self.sort_image_alpha_btn.setFixedHeight(32)
        # Minimum width so that the whole icon text is visible.
        self.sort_image_alpha_btn.setMinimumWidth(44)
        self.sort_image_alpha_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.sort_image_alpha_btn.clicked.connect(self.on_sort_images_alpha)

        self.sort_image_natural_btn = QtWidgets.QPushButton("⇅0")
        self.sort_image_natural_btn.setToolTip(
            "Sort images naturally (numeric ordering)"
        )
        self.sort_image_natural_btn.setFixedHeight(32)
        # Minimum width so that the whole icon text is visible.
        self.sort_image_natural_btn.setMinimumWidth(44)
        self.sort_image_natural_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.sort_image_natural_btn.clicked.connect(self.on_sort_images_natural)

        row.addWidget(self.sort_image_alpha_btn)
        row.addWidget(self.sort_image_natural_btn)

        image_layout.addLayout(row)

        self.fullpath_checkbox = QtWidgets.QCheckBox("Full path")

        self.fullpath_checkbox.setChecked(True)

        self.fullpath_checkbox.stateChanged.connect(self.synchronize_images)

        image_layout.addWidget(self.fullpath_checkbox)

        self.side.addWidget(image_group)

        # ============================================================
        # GROUP MANAGEMENT
        # ============================================================

        group_box = QtWidgets.QGroupBox("Groups")
        group_layout = QtWidgets.QVBoxLayout(group_box)

        row = QtWidgets.QHBoxLayout()

        row.addWidget(QtWidgets.QLabel("Current group"))

        self.group_selector = QtWidgets.QComboBox()

        self.group_selector.currentIndexChanged.connect(self.on_change_current_group)

        row.addWidget(self.group_selector)

        group_layout.addLayout(row)

        # Group buttons

        row = QtWidgets.QHBoxLayout()

        self.add_group_btn = QtWidgets.QPushButton("+")
        self.add_group_btn.setToolTip("Add group")
        self.add_group_btn.setFixedHeight(32)
        self.add_group_btn.clicked.connect(self.on_add_group)

        self.rename_group_btn = QtWidgets.QPushButton("✎")
        self.rename_group_btn.setToolTip("Rename group")
        self.rename_group_btn.setFixedHeight(32)
        self.rename_group_btn.clicked.connect(self.on_rename_group)

        self.delete_group_btn = QtWidgets.QPushButton("🗑")
        self.delete_group_btn.setToolTip("Delete group")
        self.delete_group_btn.setFixedHeight(32)
        self.delete_group_btn.clicked.connect(self.on_delete_group)

        self.sort_group_alpha_btn = QtWidgets.QPushButton("⇅a")
        self.sort_group_alpha_btn.setToolTip("Sort groups alphabetically")
        self.sort_group_alpha_btn.setFixedHeight(32)
        # Minimum width so that the whole icon text is visible.
        self.sort_group_alpha_btn.setMinimumWidth(44)
        self.sort_group_alpha_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.sort_group_alpha_btn.clicked.connect(self.on_sort_groups_alpha)

        self.sort_group_natural_btn = QtWidgets.QPushButton("⇅0")
        self.sort_group_natural_btn.setToolTip(
            "Sort groups naturally (numeric ordering)"
        )
        self.sort_group_natural_btn.setFixedHeight(32)
        # Minimum width so that the whole icon text is visible.
        self.sort_group_natural_btn.setMinimumWidth(44)
        self.sort_group_natural_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed,
        )
        self.sort_group_natural_btn.clicked.connect(self.on_sort_groups_natural)

        row.addWidget(self.add_group_btn)
        row.addWidget(self.rename_group_btn)
        row.addWidget(self.delete_group_btn)
        row.addWidget(self.sort_group_alpha_btn)
        row.addWidget(self.sort_group_natural_btn)

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

        self.display_other_clicks_checkbox = QtWidgets.QCheckBox("Display all groups")
        self.display_other_clicks_checkbox.setChecked(False)
        self.display_other_clicks_checkbox.stateChanged.connect(
            self.on_display_other_clicks_changed
        )
        display_layout.addWidget(self.display_other_clicks_checkbox)

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
            shortcuts,
            callback,
        ):
            action = QtWidgets.QAction(name, self)

            if isinstance(shortcuts, (str, QtGui.QKeySequence)):
                shortcuts = [shortcuts]

            action.setShortcuts(shortcuts)
            action.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)
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
            ["Ctrl+Left", "P"],
            self.previous_image,
        )

        add_action(
            "Next image",
            ["Ctrl+Right", "N"],
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

        # Image display controls (reset view, colormap, contrast) are
        # provided by the toolbar of QtImageToolWindow.

        # ============================================================
        # CLICKS
        # ============================================================

        toolbar.addSeparator()

        clicks_btn = QtWidgets.QToolButton()
        clicks_btn.setText("⚙ Clicks")
        clicks_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        clicks_menu = QtWidgets.QMenu(self)

        clicks_panel = QtWidgets.QWidget()
        clicks_layout = QtWidgets.QVBoxLayout(clicks_panel)

        # --------------
        # CURRENT GROUP CLICKS
        # --------------

        current_group = QtWidgets.QGroupBox("Current group clicks")
        current_layout = QtWidgets.QFormLayout(current_group)

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

        current_layout.addRow(
            "Marker",
            marker_widget,
        )

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

        current_layout.addRow(
            "Size",
            self.size_selector,
        )

        clicks_layout.addWidget(current_group)

        # --------------
        # OTHER GROUP CLICKS
        # --------------

        other_group = QtWidgets.QGroupBox("Other group clicks")
        other_layout = QtWidgets.QFormLayout(other_group)

        # Other marker color

        other_marker_widget = QtWidgets.QWidget()
        other_marker_layout = QtWidgets.QHBoxLayout(other_marker_widget)
        other_marker_layout.setContentsMargins(0, 0, 0, 0)

        self.other_color_btn = QtWidgets.QPushButton("Color")
        self.other_color_btn.clicked.connect(self.choose_other_color)

        self.other_color_preview = QtWidgets.QLabel("   ")
        self.other_color_preview.setStyleSheet(
            "background-color: rgb(0,0,255); border: 1px solid black;"
        )

        other_marker_layout.addWidget(self.other_color_btn)
        other_marker_layout.addWidget(self.other_color_preview)

        other_layout.addRow(
            "Marker",
            other_marker_widget,
        )

        # Other marker size

        self.other_size_selector = QtWidgets.QComboBox()

        self.other_size_selector.addItems(
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

        self.other_size_selector.setCurrentText("8")

        self.other_size_selector.currentTextChanged.connect(
            self.on_other_marker_size_changed
        )

        other_layout.addRow(
            "Size",
            self.other_size_selector,
        )

        clicks_layout.addWidget(other_group)

        # --------------
        # MENU
        # --------------

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

        self.image_selector.clear()

        fullpath = self.fullpath_checkbox.isChecked()

        for entry in self.session.images:

            image = entry.path

            text = str(image) if fullpath else image.name

            self.image_selector.addItem(
                text,
                str(image),
            )

        # Restore current selection
        if self.session.current_image_index >= 0:

            self.image_selector.setCurrentIndex(self.session.current_image_index)

        elif self.session.current_image_index < 0 and self.image_selector.count() > 0:

            self.image_selector.setCurrentIndex(0)
            self.session.select_current_image_index(0)
            self._image_has_changed = True

        # Empty combobox -> no current image
        else:

            self.session.select_current_image_index(-1)
            self._image_has_changed = True

        self.image_selector.blockSignals(False)

    def synchronize_groups(self):
        r"""
        Synchronize group selector with current session groups.
        """

        self.group_selector.blockSignals(True)

        self.group_selector.clear()

        for group in self.session.groups:

            self.group_selector.addItem(
                group,
                group,
            )

        # Restore current selection
        if self.session.current_group_index >= 0:

            self.group_selector.setCurrentIndex(self.session.current_group_index)

        # No current group -> select first group
        elif self.session.current_group_index < 0 and self.group_selector.count() > 0:

            self.group_selector.setCurrentIndex(0)

            self.session.select_current_group(self.group_selector.itemData(0))

        # Empty combobox -> no current group
        else:

            self.session.select_current_group(None)

        self.group_selector.blockSignals(False)

    def synchronize_params(self):
        r"""
        Synchronize checkbox with current session.
        """

        self.int_precision_checkbox.blockSignals(True)
        self.int_precision_checkbox.setChecked(self.session.precision_mode == "int")
        self.int_precision_checkbox.blockSignals(False)

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
            image = read_image(image_path)

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

        self.session.select_current_image_path(current_image)

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

        if self.session.current_image_path is None:
            return None

        image_path = self.session.current_image_path

        if image_path in self.image_cache:
            return self.image_cache[image_path]

        image = read_image(image_path)

        if image is None:
            return None

        self.image_cache[image_path] = image

        return image

    def on_remove_image(self):
        r"""
        Remove the current image from the annotation session.
        """

        if self.session.current_image_path is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No image",
                "There is no current image to remove.",
            )
            return

        image_path = self.session.current_image_path

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
            self.session.current_image_path = None
            return

        image_path = self.image_selector.itemData(index)

        if image_path is None:
            self.session.current_image_path = None
            return

        image_path = Path(image_path)

        try:
            self.session.select_current_image_path(image_path)

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

    def on_sort_images_alpha(self):
        r"""
        Sort images alphabetically.
        """

        self.session.sort_images_alpha(fullpath=self.fullpath_checkbox.isChecked())

        self.synchronize_images()

    def on_sort_images_natural(self):
        r"""
        Sort images using natural numeric ordering.
        """

        self.session.sort_images_natural(fullpath=self.fullpath_checkbox.isChecked())

        self.synchronize_images()

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
            self.session.select_current_group(group_name)

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

            self.session.select_current_group(
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
            self.session.select_current_group(group_name)

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

    def on_sort_groups_alpha(self):
        r"""
        Sort groups alphabetically.
        """

        self.session.sort_groups_alpha()

        self.synchronize_groups()

    def on_sort_groups_natural(self):
        r"""
        Sort groups using natural numeric ordering.
        """

        self.session.sort_groups_natural()

        self.synchronize_groups()

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

        if self.session.current_image_path is None:

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
            f"on '{self.session.current_image_path.name}': "
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
            f"on '{self.session.current_image_path.name}'."
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
            entry.click_manager.n_clicks > 0 for entry in self.session.images
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

                if half_shift:
                    self.session.apply_half_shift(mode="on")
                else:
                    self.session.apply_half_shift(mode="off")

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
            f"on '{self.session.current_image_path.name}'."
        )

    def on_remove_all_clicks(self) -> None:
        r"""
        Remove all clicks from the current image and group.
        """

        if self.session.current_image_path is None:
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

        image_name = self.session.current_image_path.name
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
        Load an annotation session from CSV or JSON.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Annotation Session",
            "",
            "Session files (*.json *.csv)",
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
            self.session = AnnotationSession.from_file(
                file_path,
            )

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
        Save the current annotation session.

        Supported formats:

        - JSON: complete project backup.
        - CSV: annotation export.
        """

        if len(self.session.images) == 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Empty session",
                "There is no image to save.",
            )
            return

        file_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Annotation Session",
            "",
            ("JSON Session (*.json);;" "CSV Export (*.csv)"),
        )

        if not file_path:
            return

        path = Path(file_path)

        # Determine extension if the user omitted it
        if path.suffix.lower() not in (".json", ".csv"):

            if "JSON" in selected_filter:
                path = path.with_suffix(".json")

            else:
                path = path.with_suffix(".csv")

        try:

            if path.suffix.lower() == ".json":
                self.session.to_json(path)

            elif path.suffix.lower() == ".csv":
                self.session.to_csv(path)

            else:
                raise ValueError(f"Unsupported session format: {path.suffix}")

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

        Notes
        -----
        The image is sent to :class:`QtImageToolWindow` only when it
        changed. Normalization, contrast and colormap are handled by the
        tool window. Markers are redrawn on every call.
        """

        if self._image_has_changed:

            image = self.get_current_image()

            if image is None:
                self.image_tool.clear_image()

            else:
                try:
                    self.image_tool.set_image(image)

                except (TypeError, ValueError) as e:
                    self.image_tool.clear_image()
                    self._append_log(f"Cannot display image: {e}")

            self._image_has_changed = False

        # ----------------------
        # Draw annotations
        # ----------------------
        self.viewer.clear_markers()

        pts = self.session.current_clicks

        if self.show_clicks:

            for x, y in pts:

                if x is None or y is None:
                    continue

                self.viewer.draw_cross(
                    x,
                    y,
                    self.marker_color,
                    self.marker_size,
                )

        if self.show_clicks and self.show_other_clicks:

            for group in self.session.groups:
                if group != self.session.current_group:
                    pts = self.session.get_clicks(group)

                    for x, y in pts:

                        if x is None or y is None:
                            continue

                        self.viewer.draw_cross(
                            x,
                            y,
                            self.other_marker_color,
                            self.other_marker_size,
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

    def on_display_clicks_changed(self, state: int) -> None:
        r"""
        Toggle annotation marker visibility.
        """

        self.show_clicks = state == QtCore.Qt.Checked

        self._append_log(f"Display clicks: {self.show_clicks}")

        self.update()

    def on_display_other_clicks_changed(self, state: int) -> None:
        r"""
        Toggle annotation marker visibility.
        """

        self.show_other_clicks = state == QtCore.Qt.Checked

        self._append_log(f"Display all clicks: {self.show_other_clicks}")

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

    def choose_other_color(self) -> None:
        r"""
        Change annotation marker color.
        """

        color = QtWidgets.QColorDialog.getColor(
            self.other_marker_color,
            self,
        )

        if not color.isValid():
            return

        self.other_marker_color = color

        self.other_color_preview.setStyleSheet(
            f"background-color: {color.name()};" "border: 1px solid black;"
        )

        self._append_log(f"Marker color for not-current group changed: {color.name()}")

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

    def on_other_marker_size_changed(self, value: str) -> None:
        r"""
        Update annotation marker size.
        """

        try:
            self.other_marker_size = float(value)

        except ValueError:
            self.other_marker_size = 8.0

        self._append_log(
            f"Marker size for not-current group changed: {self.other_marker_size:.1f}"
        )

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

            self.on_change_current_group(index)

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
        r"""
        Open the help dialog.

        The help is organized in tabs, one per topic. Each tab is a
        read-only :class:`QTextBrowser`, so links are clickable.
        """

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("pyclickimage Help")
        dialog.resize(760, 580)

        layout = QtWidgets.QVBoxLayout(dialog)

        tabs = QtWidgets.QTabWidget()

        def add_tab(title: str, html: str) -> None:
            r"""
            Add a help tab.

            Parameters
            ----------
            title : str
                Tab title.
            html : str
                Tab content (Qt rich text).
            """
            browser = QtWidgets.QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.setHtml(html)
            tabs.addTab(browser, title)

        def table(
            rows: list[tuple[str, str]],
            header: tuple[str, str] | None = None,
        ) -> str:
            r"""
            Build a two-column HTML table with visible cell borders.

            Parameters
            ----------
            rows : list of tuple of str
                ``(left, right)`` cells. The left cell is displayed in
                bold.
            header : tuple of str, optional
                Column titles.

            Returns
            -------
            str
                Qt rich-text table.
            """
            html = (
                '<table width="100%" border="1" cellspacing="0" '
                'cellpadding="6" style="border-collapse: collapse; '
                'border-color: #b3bac6;">'
            )

            if header is not None:
                html += (
                    f'<tr><th width="35%" align="left">{header[0]}</th>'
                    f'<th align="left">{header[1]}</th></tr>'
                )

            for left, right in rows:
                html += (
                    f'<tr><td width="35%"><b>{left}</b></td>'
                    f"<td>{right}</td></tr>"
                )

            return html + "</table>"

        # ==========================================================
        # Getting started
        # ==========================================================

        add_tab(
            "Getting started",
            """
            <h2>Getting started</h2>

            <p>
            pyclickimage collects precise point coordinates on images.
            Points are organized in <b>groups</b> and stored per image.
            </p>

            <h3>Typical workflow</h3>

            <ol>
                <li>Add one or more images (<b>+</b> in the
                <b>Images</b> panel, or <b>Ctrl + O</b>).</li>
                <li>Create a group (<b>+</b> in the <b>Groups</b> panel,
                or <b>Ctrl + G</b>).</li>
                <li>Left-click on the image to add points to the current
                group. Right-click adds an empty placeholder.</li>
                <li>Navigate between images (<b>N</b> / <b>P</b>) and
                groups (<b>Ctrl + Up / Down</b>).</li>
                <li>Save the session (<b>Ctrl + S</b>).</li>
            </ol>

            <p>
            Clicks can only be added when both a current image and a
            current group are selected.
            </p>
            """,
        )

        # ==========================================================
        # Images and groups
        # ==========================================================

        add_tab(
            "Images and groups",
            """
            <h2>Images</h2>

            <p>
            The <b>Images</b> panel manages the images of the session.
            </p>
            """
            + table(
                [
                    ("+", "Add one or several images."),
                    ("🗑", "Remove the current image and all its clicks."),
                    ("⇅a", "Sort the images alphabetically."),
                    (
                        "⇅0",
                        "Sort the images naturally (numeric ordering: "
                        "img2 before img10).",
                    ),
                    (
                        "Full path",
                        "Show full paths or file names only in the "
                        "selector.",
                    ),
                ]
            )
            + """
            <p>
            Supported formats: PNG, JPEG, BMP, TIFF. Grayscale, color,
            8-bit, 16-bit and floating-point images are supported. Image
            paths containing commas (<b>,</b>) are not supported because
            sessions can be exported to CSV.
            </p>

            <h2>Groups</h2>

            <p>
            Groups organize the annotations: each click belongs to the
            current group. A group exists on every image of the session.
            </p>
            """
            + table(
                [
                    ("+", "Create a group."),
                    ("✎", "Rename the current group."),
                    (
                        "🗑",
                        "Delete the current group and its clicks on "
                        "<b>every</b> image.",
                    ),
                    ("⇅a", "Sort the groups alphabetically."),
                    ("⇅0", "Sort the groups naturally."),
                ]
            ),
        )

        # ==========================================================
        # Clicks
        # ==========================================================

        add_tab(
            "Clicks",
            """
            <h2>Clicks</h2>

            <h3>Adding clicks</h3>
            """
            + table(
                [
                    ("Left click", "Add a point to the current group."),
                    (
                        "Right click",
                        "Add an empty placeholder (missing point), to keep "
                        "point indices aligned between images.",
                    ),
                ]
            )
            + """
            <p>
            A press and release with almost no movement is a click;
            moving the mouse while a button is pressed adds no point.
            </p>

            <h3>Clicks panel</h3>
            """
            + table(
                [
                    (
                        "Undo (Ctrl + Z)",
                        "Remove the last click of the current group on the "
                        "current image.",
                    ),
                    (
                        "Clear (Ctrl + Shift + Z)",
                        "Remove all clicks of the current group on the "
                        "current image.",
                    ),
                    (
                        "Integer precision",
                        "Display rounded coordinates. Stored coordinates "
                        "are not modified.",
                    ),
                    (
                        "Half-shift coordinates",
                        "Coordinate convention, see the "
                        "<b>Coordinates</b> tab.",
                    ),
                ]
            )
            + """
            <p>
            The table lists the clicks of the current group on the
            current image. Empty placeholders have empty X and Y.
            </p>

            <h3>Markers</h3>
            """
            + table(
                [
                    ("Display clicks (Space)", "Show or hide the markers."),
                    (
                        "Display all groups",
                        "Also show the clicks of the other groups.",
                    ),
                    (
                        "⚙ Clicks",
                        "Color and size of the markers, for the current "
                        "group and for the other groups.",
                    ),
                    ("⚙ Crosshair", "Color of the cursor crosshair."),
                ]
            ),
        )

        # ==========================================================
        # Coordinates
        # ==========================================================

        add_tab(
            "Coordinates",
            """
            <h2>Coordinates</h2>

            <p>
            Coordinates are always stored as floating-point values
            (sub-pixel precision) and follow the NumPy image
            convention <code>image[y, x]</code>:
            </p>

            <ul>
                <li><b>x</b>: horizontal coordinate (column), increasing
                to the right.</li>
                <li><b>y</b>: vertical coordinate (row), increasing
                downward.</li>
            </ul>

            <h3>Pixel reference (half-shift)</h3>
            """
            + table(
                [
                    (
                        "Half-shift enabled (default)",
                        "The <b>center</b> of the first pixel is "
                        "<code>(0, 0)</code>.<br>"
                        "Pixel <code>n</code> covers "
                        "<code>[n - 0.5, n + 0.5]</code>.",
                    ),
                    (
                        "Half-shift disabled",
                        "The <b>top-left corner</b> of the first pixel is "
                        "<code>(0, 0)</code>.<br>"
                        "Pixel <code>n</code> covers "
                        "<code>[n, n + 1]</code>.",
                    ),
                ],
                header=("Convention", "Meaning"),
            )
            + """
            <p>
            When the option is changed and clicks already exist, the
            application asks whether the existing clicks should be shifted
            by 0.5 pixel to keep pointing at the same image locations.
            </p>

            <h3>Displayed precision</h3>

            <p>
            <b>Integer precision</b> only changes how coordinates are
            displayed in the table; stored values keep their full
            precision.
            </p>
            """,
        )

        # ==========================================================
        # Display
        # ==========================================================

        add_tab(
            "Display",
            """
            <h2>Image display</h2>

            <p>
            The toolbar above the image controls how the image is
            displayed. None of these settings modify the image data or
            the click coordinates.
            </p>

            <h3>Navigation</h3>
            """
            + table(
                [
                    ("Mouse wheel", "Zoom in / out around the cursor."),
                    ("Mouse left drag", "Move the image."),
                    ("Reset view", "Fit the image in the view."),
                ]
            )
            + """
            <h3>Display mode</h3>
            """
            + table(
                [
                    (
                        "Original",
                        "The image as it is. Grayscale images are shown in "
                        "gray, color images keep their colors. The colormap "
                        "is <b>never</b> applied in this mode, so the "
                        "colormap selector is disabled.",
                    ),
                    (
                        "Processed",
                        "The image intensities go through the "
                        "<b>interpolation</b> curve (display contrast), then "
                        "through the selected <b>colormap</b>. Color images "
                        "are converted to luminance first.",
                    ),
                ]
            )
            + """
            <h3>Colormap and interpolation</h3>
            """
            + table(
                [
                    (
                        "Colormap",
                        "Color scale of the <b>Processed</b> mode. "
                        "<b>B/W</b> is a neutral linear grayscale from black "
                        "to white; <b>Bone</b> is a gray scale with a blue "
                        "tint.",
                    ),
                    (
                        "Interpolation",
                        "Opens the curve editor that maps intensities to "
                        "display levels. See the <b>Interpolation</b> tab.",
                    ),
                ]
            )
            + """
            <h3>Analysis tools</h3>
            """
            + table(
                [
                    (
                        "Profiles",
                        "Horizontal profile (below the image) and vertical "
                        "profile (right of the image) through the cursor "
                        "position. Drag the separators to resize them.",
                    ),
                    (
                        "Histogram",
                        "Histogram of the whole image. <i>Cumulative</i> and "
                        "<i>Percentage</i> modes are available below the "
                        "plot.",
                    ),
                    (
                        "Right button drag",
                        "Histogram of the selected region of the image.",
                    ),
                ]
            )
            + """
            <p>
            The status bar below the image shows the image size, type and
            intensity range, and the pixel value under the cursor (and its
            interpolated value in <b>Processed</b> mode).
            </p>
            """,
        )

        # ==========================================================
        # Interpolation
        # ==========================================================

        add_tab(
            "Interpolation",
            """
            <h2>Interpolation (display contrast)</h2>

            <p>
            The interpolation is a piecewise-linear curve that maps the
            image intensities (horizontal axis) to display levels
            between <b>0</b> (black, or the first color of the colormap)
            and <b>1</b> (white, or the last color). It replaces the
            usual brightness / contrast / min / max settings and is only
            used in <b>Processed</b> mode.
            </p>

            <p>
            Open it with the <b>Interpolation</b> button of the image
            toolbar, then select <b>Processed</b> to see its effect.
            Every change is applied to the image immediately.
            </p>

            <h3>Editing the curve</h3>
            """
            + table(
                [
                    ("Double-click", "Add a node."),
                    ("Left button drag", "Move a node."),
                    ("Right click on a node", "Remove the node."),
                ]
            )
            + """
            <ul>
                <li>The first and last nodes are always present and stay
                at the minimum and maximum intensity of the image; only
                their level can be changed.</li>
                <li>Nodes cannot cross each other: the curve always
                increases along the horizontal axis.</li>
                <li>By default, the horizontal axis shows the full range
                of the image type (for example 0 - 255 for 8-bit images,
                0 - 65535 for 16-bit images), while the curve spans the
                actual intensities of the image. Check <b>Crop X axis to
                the image intensities</b> to zoom the axis on the curve,
                which is useful when the image uses a small part of its
                range. The option is kept when the image changes.</li>
                <li>The mouse coordinates are shown in the top-right
                corner of the plot.</li>
            </ul>

            <h3>Examples</h3>
            """
            + table(
                [
                    (
                        "Stretch a dark image",
                        "Add a node at the intensity that should become "
                        "white and drag it to level 1. Brighter pixels are "
                        "displayed in white.",
                    ),
                    (
                        "Threshold",
                        "Add two close nodes at the threshold intensity, "
                        "the first at level 0 and the second at level 1.",
                    ),
                    (
                        "Invert",
                        "Set the first node to level 1 and the last node "
                        "to level 0.",
                    ),
                    (
                        "Highlight a range",
                        "Use a steep segment over the intensities of "
                        "interest and flat segments elsewhere.",
                    ),
                ]
            )
            + """
            <h3>Buttons</h3>
            """
            + table(
                [
                    (
                        "Reset nodes",
                        "Remove all intermediate nodes (straight line from "
                        "the minimum to the maximum intensity).",
                    ),
                    ("Save nodes…", "Save the curve to a JSON file."),
                    (
                        "Load nodes…",
                        "Load a curve from a JSON file. Intensities keep "
                        "their absolute values: nodes outside the "
                        "intensity range of the current image are dropped, "
                        "and the status bar says when the curve was "
                        "adjusted.",
                    ),
                ]
            )
            + """
            <h3>Changing image</h3>

            <ul>
                <li>If the new image has the same total intensity range
                (same image type, for example two 16-bit images), the
                nodes are kept and the end nodes follow the new minimum
                and maximum intensities.</li>
                <li>If the total range changes (for example 8-bit to
                16-bit), the curve is reset and its nodes are
                removed.</li>
            </ul>
            """,
        )

        # ==========================================================
        # Session
        # ==========================================================

        add_tab(
            "Session",
            """
            <h2>Annotation sessions</h2>

            <p>
            A session contains the loaded images, the groups, the clicks
            and the session options.
            </p>

            <h3>Saving</h3>

            <p>
            <b>Save Session</b> (<b>Ctrl + S</b>) offers two formats:
            </p>
            """
            + table(
                [
                    (
                        "JSON",
                        "Complete session backup (recommended to resume "
                        "work later).",
                    ),
                    (
                        "CSV",
                        "Annotation export, one row per click with the "
                        "image, group, index and X / Y coordinates. Empty "
                        "placeholders have empty coordinates.",
                    ),
                ]
            )
            + """
            <h3>Loading</h3>

            <p>
            <b>Load Session</b> (<b>Ctrl + Shift + O</b>) reads a JSON
            or CSV session and <b>replaces</b> the current session.
            The image files must still be available at their saved
            paths.
            </p>

            <p>
            The application asks for confirmation before quitting with
            unsaved changes.
            </p>
            """,
        )

        # ==========================================================
        # Shortcuts
        # ==========================================================

        add_tab(
            "Shortcuts",
            "<h2>Keyboard shortcuts</h2>"
            + "<h3>Session</h3>"
            + table(
                [
                    ("Ctrl + O", "Add images"),
                    ("Ctrl + Shift + O", "Load a session"),
                    ("Ctrl + S", "Save the session"),
                    ("Ctrl + Q", "Quit"),
                ],
                header=("Shortcut", "Action"),
            )
            + "<h3>Images</h3>"
            + table(
                [
                    ("Ctrl + Right  or  N", "Next image"),
                    ("Ctrl + Left  or  P", "Previous image"),
                ],
                header=("Shortcut", "Action"),
            )
            + "<h3>Groups</h3>"
            + table(
                [
                    ("Ctrl + G", "Add a group"),
                    ("F2", "Rename the current group"),
                    ("Ctrl + Delete", "Delete the current group"),
                    ("Ctrl + Up", "Previous group"),
                    ("Ctrl + Down", "Next group"),
                ],
                header=("Shortcut", "Action"),
            )
            + "<h3>Clicks</h3>"
            + table(
                [
                    ("Ctrl + Z", "Undo the last click"),
                    (
                        "Ctrl + Shift + Z",
                        "Clear the clicks of the current group on the "
                        "current image",
                    ),
                ],
                header=("Shortcut", "Action"),
            )
            + "<h3>Display</h3>"
            + table(
                [
                    ("Space", "Show / hide the markers"),
                    ("Mouse wheel", "Zoom"),
                    ("Middle button drag", "Move the image"),
                ],
                header=("Shortcut", "Action"),
            )
            + "<h3>Help</h3>"
            + table(
                [("F1", "Open this help")],
                header=("Shortcut", "Action"),
            ),
        )

        # ==========================================================
        # About
        # ==========================================================

        add_tab(
            "About",
            f"""
            <h2>pyclickimage</h2>

            <p>
            Version <b>{__version__}</b>
            </p>

            <p>
            Releases and updates:
            <a href="https://github.com/Artezaru/pyclickimage/releases">
            https://github.com/Artezaru/pyclickimage/releases
            </a>
            </p>

            <p>
            Copyright (C) 2025-2026 Artezaru.<br>
            Distributed under the GNU General Public License v3 or later.
            </p>

            <h3>Contact</h3>

            <p>
            For bug reports, feature requests or any issue with the
            application, contact the developer:
            <a href="mailto:artezaru.github@proton.me">
            artezaru.github@proton.me
            </a>
            </p>
            """,
        )

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