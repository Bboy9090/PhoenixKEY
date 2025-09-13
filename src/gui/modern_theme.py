"""
BootForge Modern Theme System
Professional styling and color palette for the application
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtWidgets import QApplication


class BootForgeTheme:
    """Professional theme configuration for BootForge"""
    
    # Color Palette
    COLORS = {
        # Primary colors
        "primary": "#0078d4",           # Electric blue
        "primary_hover": "#106ebe",     # Darker blue on hover
        "primary_pressed": "#005a9e",   # Even darker on press
        
        # Background colors
        "bg_primary": "#1e1e1e",        # Main background
        "bg_secondary": "#2d2d30",      # Secondary panels
        "bg_tertiary": "#3e3e42",       # Cards and elevated elements
        "bg_input": "#3c3c3c",          # Input fields
        
        # Surface colors
        "surface": "#252526",           # Menu bars, toolbars
        "surface_hover": "#3e3e40",     # Hover state
        "surface_pressed": "#4a4a4c",   # Pressed state
        
        # Border colors
        "border": "#464647",            # Default borders
        "border_light": "#6a6a6b",      # Lighter borders
        "border_focus": "#0078d4",      # Focused elements
        
        # Text colors
        "text_primary": "#ffffff",      # Primary text
        "text_secondary": "#cccccc",    # Secondary text
        "text_muted": "#9d9d9d",        # Muted text
        "text_disabled": "#6d6d6d",     # Disabled text
        
        # Status colors
        "success": "#10b981",           # Success green
        "warning": "#f59e0b",           # Warning orange
        "error": "#ef4444",             # Error red
        "info": "#3b82f6",              # Info blue
        
        # Accent colors
        "accent_1": "#8b5cf6",          # Purple accent
        "accent_2": "#06b6d4",          # Cyan accent
        "accent_3": "#f97316",          # Orange accent
    }
    
    # Typography
    FONTS = {
        "default_family": "Segoe UI, system-ui, sans-serif",
        "monospace_family": "Consolas, 'Courier New', monospace",
        "sizes": {
            "xs": 10,
            "sm": 12,
            "base": 14,
            "lg": 16,
            "xl": 18,
            "2xl": 24,
            "3xl": 30,
        }
    }
    
    # Spacing
    SPACING = {
        "xs": 4,
        "sm": 8,
        "base": 16,
        "lg": 24,
        "xl": 32,
        "2xl": 48,
        "3xl": 64,
    }
    
    # Border radius
    RADIUS = {
        "sm": 4,
        "base": 6,
        "lg": 8,
        "xl": 12,
        "full": 9999,
    }
    
    # Shadows
    SHADOWS = {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "base": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        "lg": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "xl": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    }
    
    @classmethod
    def get_stylesheet(cls) -> str:
        """Get the complete application stylesheet"""
        return f"""
        /* === MAIN APPLICATION === */
        QMainWindow {{
            background-color: {cls.COLORS['bg_primary']};
            color: {cls.COLORS['text_primary']};
            font-family: {cls.FONTS['default_family']};
            font-size: {cls.FONTS['sizes']['base']}px;
        }}
        
        /* === MENU BAR === */
        QMenuBar {{
            background-color: {cls.COLORS['surface']};
            color: {cls.COLORS['text_primary']};
            border-bottom: 1px solid {cls.COLORS['border']};
            padding: 4px 0px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 8px 12px;
            border-radius: {cls.RADIUS['sm']}px;
            margin: 2px 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {cls.COLORS['surface_hover']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {cls.COLORS['surface_pressed']};
        }}
        
        QMenu {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            border-radius: {cls.RADIUS['sm']}px;
            margin: 1px;
        }}
        
        QMenu::item:selected {{
            background-color: {cls.COLORS['primary']};
        }}
        
        /* === TOOLBAR === */
        QToolBar {{
            background-color: {cls.COLORS['surface']};
            border: none;
            spacing: {cls.SPACING['sm']}px;
            padding: {cls.SPACING['sm']}px;
        }}
        
        QToolBar::separator {{
            background-color: {cls.COLORS['border']};
            width: 1px;
            margin: 4px 8px;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: {cls.RADIUS['base']}px;
            padding: 8px 12px;
            color: {cls.COLORS['text_primary']};
            font-weight: 500;
        }}
        
        QToolButton:hover {{
            background-color: {cls.COLORS['surface_hover']};
        }}
        
        QToolButton:pressed {{
            background-color: {cls.COLORS['surface_pressed']};
        }}
        
        /* === STATUS BAR === */
        QStatusBar {{
            background-color: {cls.COLORS['surface']};
            border-top: 1px solid {cls.COLORS['border']};
            color: {cls.COLORS['text_secondary']};
            padding: 4px 8px;
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        
        /* === TABS === */
        QTabWidget::pane {{
            border: 1px solid {cls.COLORS['border']};
            background-color: {cls.COLORS['bg_secondary']};
            border-radius: {cls.RADIUS['base']}px;
            margin-top: 2px;
        }}
        
        QTabBar::tab {{
            background-color: {cls.COLORS['bg_tertiary']};
            color: {cls.COLORS['text_secondary']};
            padding: 12px 20px;
            margin-right: 2px;
            border-top-left-radius: {cls.RADIUS['base']}px;
            border-top-right-radius: {cls.RADIUS['base']}px;
            font-weight: 500;
        }}
        
        QTabBar::tab:selected {{
            background-color: {cls.COLORS['primary']};
            color: {cls.COLORS['text_primary']};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {cls.COLORS['surface_hover']};
            color: {cls.COLORS['text_primary']};
        }}
        
        /* === BUTTONS === */
        QPushButton {{
            background-color: {cls.COLORS['bg_tertiary']};
            border: 1px solid {cls.COLORS['border']};
            padding: 10px 20px;
            border-radius: {cls.RADIUS['base']}px;
            color: {cls.COLORS['text_primary']};
            font-weight: 500;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {cls.COLORS['surface_hover']};
            border-color: {cls.COLORS['border_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {cls.COLORS['surface_pressed']};
        }}
        
        QPushButton:disabled {{
            background-color: {cls.COLORS['bg_input']};
            color: {cls.COLORS['text_disabled']};
            border-color: {cls.COLORS['border']};
        }}
        
        /* Primary button style */
        QPushButton[class="primary"] {{
            background-color: {cls.COLORS['primary']};
            border-color: {cls.COLORS['primary']};
            color: {cls.COLORS['text_primary']};
        }}
        
        QPushButton[class="primary"]:hover {{
            background-color: {cls.COLORS['primary_hover']};
            border-color: {cls.COLORS['primary_hover']};
        }}
        
        QPushButton[class="primary"]:pressed {{
            background-color: {cls.COLORS['primary_pressed']};
            border-color: {cls.COLORS['primary_pressed']};
        }}
        
        /* === GROUP BOXES === */
        QGroupBox {{
            font-weight: 600;
            border: 2px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['lg']}px;
            margin-top: 16px;
            color: {cls.COLORS['text_primary']};
            background-color: {cls.COLORS['bg_secondary']};
            padding-top: 12px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            background-color: {cls.COLORS['bg_secondary']};
            color: {cls.COLORS['primary']};
        }}
        
        /* === PROGRESS BARS === */
        QProgressBar {{
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            text-align: center;
            color: {cls.COLORS['text_primary']};
            background-color: {cls.COLORS['bg_input']};
            font-weight: 500;
            min-height: 20px;
        }}
        
        QProgressBar::chunk {{
            background-color: {cls.COLORS['primary']};
            border-radius: {cls.RADIUS['sm']}px;
            margin: 1px;
        }}
        
        /* === LABELS === */
        QLabel {{
            color: {cls.COLORS['text_primary']};
            background-color: transparent;
        }}
        
        QLabel[class="secondary"] {{
            color: {cls.COLORS['text_secondary']};
        }}
        
        QLabel[class="muted"] {{
            color: {cls.COLORS['text_muted']};
        }}
        
        QLabel[class="heading"] {{
            font-size: {cls.FONTS['sizes']['xl']}px;
            font-weight: 600;
            color: {cls.COLORS['text_primary']};
        }}
        
        QLabel[class="subheading"] {{
            font-size: {cls.FONTS['sizes']['lg']}px;
            font-weight: 500;
            color: {cls.COLORS['text_secondary']};
        }}
        
        /* === INPUT FIELDS === */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {cls.COLORS['bg_input']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            padding: 8px 12px;
            color: {cls.COLORS['text_primary']};
            selection-background-color: {cls.COLORS['primary']};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {cls.COLORS['border_focus']};
        }}
        
        /* === COMBO BOXES === */
        QComboBox {{
            background-color: {cls.COLORS['bg_input']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            padding: 8px 12px;
            color: {cls.COLORS['text_primary']};
            min-width: 100px;
        }}
        
        QComboBox:hover {{
            border-color: {cls.COLORS['border_light']};
        }}
        
        QComboBox:focus {{
            border-color: {cls.COLORS['border_focus']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {cls.COLORS['text_secondary']};
            width: 0px;
            height: 0px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            selection-background-color: {cls.COLORS['primary']};
        }}
        
        /* === LIST WIDGETS === */
        QListWidget {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            alternate-background-color: {cls.COLORS['bg_tertiary']};
        }}
        
        QListWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {cls.COLORS['border']};
        }}
        
        QListWidget::item:selected {{
            background-color: {cls.COLORS['primary']};
        }}
        
        QListWidget::item:hover {{
            background-color: {cls.COLORS['surface_hover']};
        }}
        
        /* === TREE WIDGETS === */
        QTreeWidget {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            alternate-background-color: {cls.COLORS['bg_tertiary']};
        }}
        
        QTreeWidget::item {{
            padding: 4px 8px;
            border-bottom: 1px solid {cls.COLORS['border']};
        }}
        
        QTreeWidget::item:selected {{
            background-color: {cls.COLORS['primary']};
        }}
        
        QTreeWidget::item:hover {{
            background-color: {cls.COLORS['surface_hover']};
        }}
        
        /* === SCROLL BARS === */
        QScrollBar:vertical {{
            background-color: {cls.COLORS['bg_input']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {cls.COLORS['border_light']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {cls.COLORS['text_muted']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {cls.COLORS['bg_input']};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {cls.COLORS['border_light']};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {cls.COLORS['text_muted']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* === SPLITTERS === */
        QSplitter::handle {{
            background-color: {cls.COLORS['border']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {cls.COLORS['primary']};
        }}
        
        /* === FRAMES === */
        QFrame {{
            background-color: transparent;
            border: none;
        }}
        
        QFrame[class="card"] {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['lg']}px;
            padding: {cls.SPACING['base']}px;
        }}
        
        QFrame[class="elevated"] {{
            background-color: {cls.COLORS['bg_tertiary']};
            border: 1px solid {cls.COLORS['border_light']};
            border-radius: {cls.RADIUS['lg']}px;
        }}
        
        /* === CHECKBOXES === */
        QCheckBox {{
            color: {cls.COLORS['text_primary']};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {cls.COLORS['border']};
            border-radius: 3px;
            background-color: {cls.COLORS['bg_input']};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {cls.COLORS['border_light']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {cls.COLORS['primary']};
            border-color: {cls.COLORS['primary']};
        }}
        
        /* === TABLE WIDGETS === */
        QTableWidget {{
            background-color: {cls.COLORS['bg_secondary']};
            border: 1px solid {cls.COLORS['border']};
            border-radius: {cls.RADIUS['base']}px;
            gridline-color: {cls.COLORS['border']};
        }}
        
        QTableWidget::item {{
            padding: 8px 12px;
            border-bottom: 1px solid {cls.COLORS['border']};
        }}
        
        QTableWidget::item:selected {{
            background-color: {cls.COLORS['primary']};
        }}
        
        QHeaderView::section {{
            background-color: {cls.COLORS['bg_tertiary']};
            border: 1px solid {cls.COLORS['border']};
            padding: 8px 12px;
            font-weight: 600;
        }}
        """
    
    @classmethod
    def apply_theme(cls, app: QApplication):
        """Apply the theme to the application"""
        # Set global font
        font = QFont(cls.FONTS['default_family'])
        font.setPointSize(cls.FONTS['sizes']['base'])
        app.setFont(font)
        
        # Apply stylesheet
        app.setStyleSheet(cls.get_stylesheet())
        
        # Set dark palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(cls.COLORS['bg_primary']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(cls.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Base, QColor(cls.COLORS['bg_secondary']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(cls.COLORS['bg_tertiary']))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(cls.COLORS['bg_tertiary']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(cls.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Text, QColor(cls.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Button, QColor(cls.COLORS['bg_tertiary']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(cls.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(cls.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.Link, QColor(cls.COLORS['primary']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(cls.COLORS['primary']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(cls.COLORS['text_primary']))
        
        app.setPalette(palette)