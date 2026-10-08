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

from dataclasses import dataclass, fields, replace as dataclass_replace
from typing import Iterable

from PyQt5 import QtGui, QtWidgets


# ==========================================================================
# Theme definition
# ==========================================================================

@dataclass(frozen=True)
class Theme:
    r"""Complete description of a visual theme.

    All colors are CSS-like strings accepted by :class:`QColor`
    (``"#RRGGBB"``, ``"#AARRGGBB"`` or color names).

    Parameters
    ----------
    name : str
        Human-readable theme name.
    dark : bool
        Whether the theme is dark. Used for a few contrast decisions.

    window : str
        Background of windows and main surfaces.
    surface : str
        Background of raised elements (toolbar, group boxes, menus).
    base : str
        Background of input and content widgets (text edits, tables,
        combo boxes, plots).
    alternate_base : str
        Alternate row color of tables and lists.
    border : str
        Default border color.
    border_strong : str
        Border color of hovered or focused elements.

    text : str
        Main text color.
    text_muted : str
        Secondary text color (labels, disabled text, placeholders).

    accent : str
        Main accent color (selection, checked buttons, focus).
    accent_hover : str
        Accent color under the mouse.
    accent_text : str
        Text color displayed on top of ``accent``.
    danger : str
        Color used for destructive or error states.
    warning : str
        Color used to flag a non-default state that needs attention
        (for instance a custom interpolation curve).
    warning_hover : str
        Warning color under the mouse.
    warning_text : str
        Text color displayed on top of ``warning``.

    plot_background : str
        Background of custom-painted plots.
    plot_grid : str
        Major grid line color of plots.
    plot_minor_grid : str
        Minor grid line color of plots.
    plot_axis : str
        Axis and tick color of plots.
    plot_text : str
        Tick label and axis title color of plots.
    plot_line : str
        Data line, curve, node and histogram bar color.
    plot_overlay : str
        Background of overlays drawn inside plots (for instance the
        mouse-coordinate box of :class:`QtLinearInterpolator`).

    font_family : str
        Application font family. An empty string keeps the system font.
    font_size : int
        Application font size in points.
    plot_font_size : int
        Font size used inside plots, in points.
    radius : int
        Corner radius of buttons, inputs and frames, in pixels.
    padding : int
        Base inner padding of buttons and inputs, in pixels.
    splitter_width : int
        Width of splitter handles, in pixels.

    Notes
    -----
    The class is immutable. Use :meth:`replace` to derive a new theme.
    """

    name: str
    dark: bool

    window: str
    surface: str
    base: str
    alternate_base: str
    border: str
    border_strong: str

    text: str
    text_muted: str

    accent: str
    accent_hover: str
    accent_text: str
    danger: str
    warning: str
    warning_hover: str
    warning_text: str

    plot_background: str
    plot_grid: str
    plot_minor_grid: str
    plot_axis: str
    plot_text: str
    plot_line: str
    plot_overlay: str

    font_family: str = ""
    font_size: int = 10
    plot_font_size: int = 8
    radius: int = 6
    padding: int = 5
    splitter_width: int = 6

    def replace(self, **changes) -> "Theme":
        r"""Return a copy of the theme with some fields replaced.

        Parameters
        ----------
        **changes
            Field names and their new values.

        Returns
        -------
        Theme
            New theme instance.

        Raises
        ------
        TypeError
            If a key is not a field of :class:`Theme`.

        Examples
        --------
        >>> compact = DARK_THEME.replace(font_size=9, padding=3)
        """
        return dataclass_replace(self, **changes)

    def to_dict(self) -> dict:
        r"""Return the theme as a plain dictionary.

        Returns
        -------
        dict
            Mapping ``field name -> value``. Useful to save a theme to
            JSON; :meth:`from_dict` performs the inverse operation.
        """
        return {
            field.name: getattr(self, field.name)
            for field in fields(self)
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        r"""Create a theme from a dictionary.

        Parameters
        ----------
        data : dict
            Mapping ``field name -> value``, as produced by
            :meth:`to_dict`. Unknown keys are ignored.

        Returns
        -------
        Theme
            New theme instance.

        Raises
        ------
        TypeError
            If a required field is missing.
        """
        names = {field.name for field in fields(cls)}

        return cls(**{
            key: value
            for key, value in data.items()
            if key in names
        })


# ==========================================================================
# Built-in themes
# ==========================================================================

DARK_THEME = Theme(
    name="Dark",
    dark=True,

    window="#16181d",
    surface="#1d2027",
    base="#22262e",
    alternate_base="#262a33",
    border="#2f343e",
    border_strong="#454c59",

    text="#e6e8ec",
    text_muted="#8f98a8",

    accent="#5b9cff",
    accent_hover="#7cb0ff",
    accent_text="#0d1117",
    danger="#ff6b6b",
    warning="#f0a030",
    warning_hover="#f5b555",
    warning_text="#0d1117",

    plot_background="#1b1e25",
    plot_grid="#2c313b",
    plot_minor_grid="#23272f",
    plot_axis="#7d8696",
    plot_text="#b4bcc9",
    plot_line="#5b9cff",
    plot_overlay="#dc22262e",
)
"""Theme: modern dark theme (default)."""


LIGHT_THEME = Theme(
    name="Light",
    dark=False,

    window="#f4f5f7",
    surface="#ffffff",
    base="#ffffff",
    alternate_base="#f7f8fa",
    border="#d9dde4",
    border_strong="#b3bac6",

    text="#1d2129",
    text_muted="#6b7280",

    accent="#2f6fe4",
    accent_hover="#4a84ec",
    accent_text="#ffffff",
    danger="#d64545",
    warning="#e8890c",
    warning_hover="#f59f2a",
    warning_text="#1d2129",

    plot_background="#ffffff",
    plot_grid="#e3e6eb",
    plot_minor_grid="#f0f2f5",
    plot_axis="#5f6672",
    plot_text="#4b5260",
    plot_line="#2f6fe4",
    plot_overlay="#dcffffff",
)
"""Theme: modern light theme."""


THEMES: dict[str, Theme] = {
    DARK_THEME.name.lower(): DARK_THEME,
    LIGHT_THEME.name.lower(): LIGHT_THEME,
}
"""dict[str, Theme]: Built-in themes indexed by lower-case name."""


def get_theme(name: str) -> Theme:
    r"""Return a built-in theme by name.

    Parameters
    ----------
    name : str
        Theme name, case-insensitive (``"dark"`` or ``"light"``).

    Returns
    -------
    Theme
        The requested theme.

    Raises
    ------
    KeyError
        If no built-in theme has this name.
    """
    key = str(name).lower()

    if key not in THEMES:
        raise KeyError(
            f"Unknown theme '{name}'. "
            f"Available themes: {', '.join(sorted(THEMES))}."
        )

    return THEMES[key]


# ==========================================================================
# Palette
# ==========================================================================

def build_palette(theme: Theme) -> QtGui.QPalette:
    r"""Build a :class:`QPalette` from a theme.

    The palette matters even with a stylesheet: widgets that paint
    themselves (and the default colors of the custom plots) read it.

    Parameters
    ----------
    theme : Theme
        Source theme.

    Returns
    -------
    QPalette
        Palette for the active and inactive groups, with muted colors for
        the disabled group.
    """
    palette = QtGui.QPalette()

    role = QtGui.QPalette
    color = QtGui.QColor

    entries = {
        role.Window: theme.window,
        role.WindowText: theme.text,
        role.Base: theme.base,
        role.AlternateBase: theme.alternate_base,
        role.ToolTipBase: theme.surface,
        role.ToolTipText: theme.text,
        role.PlaceholderText: theme.text_muted,
        role.Text: theme.text,
        role.Button: theme.surface,
        role.ButtonText: theme.text,
        role.BrightText: theme.danger,
        role.Highlight: theme.accent,
        role.HighlightedText: theme.accent_text,
        role.Link: theme.accent,
        role.LinkVisited: theme.accent_hover,
        role.Light: theme.border_strong,
        role.Midlight: theme.border_strong,
        role.Mid: theme.border,
        role.Dark: theme.window,
        role.Shadow: "#000000",
    }

    for palette_role, value in entries.items():
        palette.setColor(palette_role, color(value))

    for palette_role in (
        role.WindowText,
        role.Text,
        role.ButtonText,
    ):
        palette.setColor(
            role.Disabled,
            palette_role,
            color(theme.text_muted),
        )

    palette.setColor(
        role.Disabled,
        role.Highlight,
        color(theme.border_strong),
    )

    return palette


# ==========================================================================
# Stylesheet
# ==========================================================================

def build_stylesheet(theme: Theme) -> str:
    r"""Generate the Qt stylesheet of a theme.

    Parameters
    ----------
    theme : Theme
        Source theme.

    Returns
    -------
    str
        Qt stylesheet (QSS) covering the standard widgets used by the
        application: windows, toolbars, buttons, inputs, combo boxes,
        check boxes, group boxes, tables, scroll bars, splitters, menus,
        tabs, sliders, status bars and tooltips.

    Notes
    -----
    The stylesheet is a plain string: it can be edited, saved to a
    ``.qss`` file or extended before being applied with
    :func:`apply_theme`.
    """
    t = theme
    r = t.radius
    p = t.padding

    return f"""
/* ================================================================== */
/* Theme: {t.name}                                                     */
/* ================================================================== */

QWidget {{
    color: {t.text};
    selection-background-color: {t.accent};
    selection-color: {t.accent_text};
}}

QMainWindow, QDialog {{
    background-color: {t.window};
}}

QMainWindow::separator {{
    background: {t.border};
    width: 1px;
    height: 1px;
}}

/* ---------------------------- Tooltips ---------------------------- */

QToolTip {{
    color: {t.text};
    background-color: {t.surface};
    border: 1px solid {t.border_strong};
    border-radius: {r}px;
    padding: {p}px;
}}

/* ---------------------------- Toolbars ---------------------------- */

QToolBar {{
    background-color: {t.surface};
    border: none;
    border-bottom: 1px solid {t.border};
    padding: 4px;
    spacing: 4px;
}}

QToolBar::separator {{
    background-color: {t.border};
    width: 1px;
    margin: 4px 6px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: {r}px;
    padding: {p}px {p + 4}px;
}}

QToolButton:hover {{
    background-color: {t.base};
    border-color: {t.border};
}}

QToolButton:pressed {{
    background-color: {t.border};
}}

QToolButton:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
    color: {t.accent_text};
}}

QToolButton:checked:hover {{
    background-color: {t.accent_hover};
    border-color: {t.accent_hover};
}}

QToolButton::menu-indicator {{
    subcontrol-position: right center;
    right: 4px;
}}

QToolButton[popupMode="2"] {{
    padding-right: {p + 14}px;
}}

/* ---------------------------- Buttons ----------------------------- */

QPushButton {{
    background-color: {t.base};
    border: 1px solid {t.border};
    border-radius: {r}px;
    padding: {p}px {p + 7}px;
    min-height: 18px;
}}

QPushButton:hover {{
    border-color: {t.border_strong};
    background-color: {t.alternate_base};
}}

QPushButton:pressed {{
    background-color: {t.border};
}}

QPushButton:checked, QPushButton:default {{
    background-color: {t.accent};
    border-color: {t.accent};
    color: {t.accent_text};
}}

QPushButton:disabled, QToolButton:disabled {{
    color: {t.text_muted};
    border-color: {t.border};
    background-color: {t.surface};
}}

/* ----------------------------- Inputs ----------------------------- */

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {t.base};
    border: 1px solid {t.border};
    border-radius: {r}px;
    padding: {max(p - 2, 2)}px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.accent};
}}

/* --------------------------- Combo boxes -------------------------- */

QComboBox {{
    background-color: {t.base};
    border: 1px solid {t.border};
    border-radius: {r}px;
    padding: {max(p - 2, 2)}px {p + 2}px;
    min-height: 18px;
}}

QComboBox:hover {{
    border-color: {t.border_strong};
}}

QComboBox:focus {{
    border-color: {t.accent};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {t.surface};
    border: 1px solid {t.border_strong};
    border-radius: {r}px;
    padding: 4px;
    outline: none;
}}

/* --------------------------- Check boxes -------------------------- */

QCheckBox, QRadioButton {{
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border_strong};
    background-color: {t.base};
}}

QCheckBox::indicator {{
    border-radius: 4px;
}}

QRadioButton::indicator {{
    border-radius: 8px;
}}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t.accent};
}}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {t.accent};
    border-color: {t.accent};
}}

/* --------------------------- Group boxes -------------------------- */

QGroupBox {{
    background-color: {t.surface};
    border: 1px solid {t.border};
    border-radius: {r + 2}px;
    margin-top: 14px;
    padding: {p + 6}px {p + 2}px {p + 2}px {p + 2}px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {t.text_muted};
}}

QGroupBox QWidget {{
    font-weight: normal;
}}

/* ------------------------- Tables & lists ------------------------- */

QTableView, QTableWidget, QListView, QTreeView {{
    background-color: {t.base};
    alternate-background-color: {t.alternate_base};
    border: 1px solid {t.border};
    border-radius: {r}px;
    gridline-color: {t.border};
}}

QHeaderView::section {{
    background-color: {t.surface};
    color: {t.text_muted};
    border: none;
    border-bottom: 1px solid {t.border};
    border-right: 1px solid {t.border};
    padding: 4px 6px;
    font-weight: 600;
}}

QTableCornerButton::section {{
    background-color: {t.surface};
    border: none;
}}

/* --------------------------- Scroll bars -------------------------- */

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: {t.border_strong};
    border-radius: 3px;
    min-height: 24px;
    min-width: 24px;
}}

QScrollBar::handle:hover {{
    background-color: {t.text_muted};
}}

QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
    border: none;
    width: 0px;
    height: 0px;
}}

/* ---------------------------- Splitters --------------------------- */

QSplitter::handle {{
    background-color: {t.window};
}}

QSplitter::handle:horizontal {{
    width: {t.splitter_width}px;
    border-left: 1px solid {t.border};
}}

QSplitter::handle:vertical {{
    height: {t.splitter_width}px;
    border-top: 1px solid {t.border};
}}

QSplitter::handle:hover {{
    background-color: {t.accent};
}}

/* ------------------------------ Menus ----------------------------- */

QMenuBar {{
    background-color: {t.surface};
    border-bottom: 1px solid {t.border};
}}

QMenuBar::item:selected {{
    background-color: {t.base};
    border-radius: {r}px;
}}

QMenu {{
    background-color: {t.surface};
    border: 1px solid {t.border_strong};
    border-radius: {r}px;
    padding: 6px;
}}

QMenu::item {{
    padding: 5px 18px;
    border-radius: {r}px;
}}

QMenu::item:selected {{
    background-color: {t.accent};
    color: {t.accent_text};
}}

QMenu::separator {{
    height: 1px;
    background: {t.border};
    margin: 4px 8px;
}}

/* ------------------------------ Tabs ------------------------------ */

QTabWidget::pane {{
    border: 1px solid {t.border};
    border-radius: {r}px;
    background-color: {t.surface};
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {t.text_muted};
    padding: 6px 12px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:hover {{
    color: {t.text};
}}

QTabBar::tab:selected {{
    color: {t.text};
    border-bottom: 2px solid {t.accent};
}}

/* ----------------------------- Sliders ---------------------------- */

QSlider::groove:horizontal {{
    height: 4px;
    background-color: {t.border};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background-color: {t.accent};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background-color: {t.text};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

/* --------------------------- Status bar --------------------------- */

QStatusBar {{
    background-color: {t.surface};
    border-top: 1px solid {t.border};
    color: {t.text_muted};
}}

QStatusBar::item {{
    border: none;
}}

QStatusBar QLabel {{
    color: {t.text_muted};
    padding: 0 6px;
}}

/* -------------------------- Image viewer -------------------------- */

QGraphicsView {{
    background-color: {t.window};
    border: none;
}}
"""


# ==========================================================================
# Application
# ==========================================================================

def apply_theme(
    app: QtWidgets.QApplication,
    theme: Theme = LIGHT_THEME,
    extra_stylesheet: str = "",
    use_fusion: bool = True,
) -> None:
    r"""Apply a theme to a whole application.

    Parameters
    ----------
    app : QApplication
        Application to style.
    theme : Theme, default=LIGHT_THEME
        Theme to apply.
    extra_stylesheet : str, default=""
        Additional QSS appended after the generated stylesheet. Rules
        defined here take precedence over the theme rules.
    use_fusion : bool, default=True
        Whether to switch to the ``Fusion`` style, which gives a
        consistent look on every platform and fully honors palettes.

    Notes
    -----
    Call this function before creating the widgets when possible.
    Custom-painted plots (:class:`QtHistogram`, :class:`QtProfilePlot`,
    :class:`QtLinearInterpolator`) store their colors when they are
    created and are not affected by stylesheets: restyle them with
    :func:`style_plot_widget` (or :meth:`QtImageToolWindow.apply_theme`).

    Examples
    --------
    Apply the dark theme to a whole application::

        from PyQt5 import QtWidgets
        from theme import DARK_THEME, apply_theme

        app = QtWidgets.QApplication([])
        apply_theme(app, DARK_THEME)

    Derive a custom theme from an existing one::

        my_theme = DARK_THEME.replace(
            name="Dark green",
            accent="#3ecf8e",
            accent_hover="#5ee0a5",
        )

    Append custom rules to the generated stylesheet::

        apply_theme(
            app,
            LIGHT_THEME,
            extra_stylesheet="QPushButton { font-weight: 600; }",
        )
    """
    if use_fusion:
        app.setStyle("Fusion")

    app.setPalette(build_palette(theme))

    font = QtGui.QFont(app.font())

    if theme.font_family:
        font.setFamily(theme.font_family)

    font.setPointSize(theme.font_size)
    app.setFont(font)

    app.setStyleSheet(
        build_stylesheet(theme) + "\n" + extra_stylesheet
    )

    # Keep a reference so widgets can query the active theme.
    app.setProperty("theme_name", theme.name)


# ==========================================================================
# Custom-painted plots
# ==========================================================================

# Private attribute -> Theme field. Only attributes that exist on a given
# widget are modified, so the same table serves every plot class.
_PLOT_COLOR_ATTRIBUTES = {
    "_background_color": "plot_background",
    "_border_color": "border_strong",
    "_grid_color": "plot_grid",
    "_minor_grid_color": "plot_minor_grid",
    "_axis_color": "plot_axis",
    "_text_color": "plot_text",
    "_line_color": "plot_line",
    "_curve_color": "plot_line",
    "_node_color": "plot_line",
    "_bar_color": "plot_line",
    "_bar_border_color": "plot_line",
    "_coordinate_background_color": "plot_overlay",
}


def style_plot_widget(
    widget: QtWidgets.QWidget,
    theme: Theme = LIGHT_THEME,
) -> None:
    r"""Apply a theme to a custom-painted plot widget.

    Supported widgets are :class:`QtHistogram`, :class:`QtProfilePlot`
    and :class:`QtLinearInterpolator`. Their colors are stored in private
    attributes read by ``paintEvent``; QSS does not reach them.

    Parameters
    ----------
    widget : QWidget
        Plot widget to restyle. Attributes the widget does not define
        are skipped, so any widget can be passed safely.
    theme : Theme, default=LIGHT_THEME
        Theme to apply.

    Notes
    -----
    Histogram bars are drawn with a semi-transparent version of
    ``plot_line`` so that dense histograms stay readable.

    The plot font size is set to ``theme.plot_font_size``.
    """
    for attribute, field_name in _PLOT_COLOR_ATTRIBUTES.items():
        if not hasattr(widget, attribute):
            continue

        color = QtGui.QColor(getattr(theme, field_name))

        if attribute == "_bar_color":
            color.setAlpha(170)

        setattr(widget, attribute, color)

    if hasattr(widget, "_font"):
        font = QtGui.QFont(widget._font)
        font.setPointSize(theme.plot_font_size)

        if theme.font_family:
            font.setFamily(theme.font_family)

        widget._font = font

    widget.update()


def style_plot_widgets(
    widgets: Iterable[QtWidgets.QWidget],
    theme: Theme = LIGHT_THEME,
) -> None:
    r"""Apply a theme to several custom-painted plot widgets.

    Parameters
    ----------
    widgets : iterable of QWidget
        Plot widgets to restyle.
    theme : Theme, default=LIGHT_THEME
        Theme to apply.

    See Also
    --------
    style_plot_widget
    """
    for widget in widgets:
        style_plot_widget(widget, theme)