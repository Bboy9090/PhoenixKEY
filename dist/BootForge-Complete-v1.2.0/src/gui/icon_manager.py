"""
BootForge Icon Manager
Professional icon management system for consistent UI theming
"""

import os
from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPolygon
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtSvg import QSvgRenderer


class IconManager:
    """Manages application icons with theming support"""
    
    def __init__(self):
        self.assets_dir = Path(__file__).parent.parent.parent / "assets" / "icons"
        self._icon_cache: Dict[str, QIcon] = {}
        
        # Define icon mappings
        self.icon_map = {
            # App icons
            "app": "app_icon_premium.png",
            
            # Toolbar icons
            "refresh": self._create_refresh_icon,
            "play": self._create_play_icon,
            "stop": self._create_stop_icon,
            "settings": self._create_settings_icon,
            
            # Step icons
            "device": self._create_device_icon,
            "image": self._create_image_icon,
            "deploy": self._create_deploy_icon,
            "verify": self._create_verify_icon,
            
            # Status icons
            "success": self._create_success_icon,
            "warning": self._create_warning_icon,
            "error": self._create_error_icon,
            "info": self._create_info_icon,
            
            # Navigation icons
            "chevron_right": self._create_chevron_right_icon,
            "chevron_left": self._create_chevron_left_icon,
        }
    
    def get_icon(self, name: str, size: int = 24, color: str = "#ffffff") -> QIcon:
        """Get icon by name with optional size and color customization"""
        cache_key = f"{name}_{size}_{color}"
        
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        icon = QIcon()
        
        if name in self.icon_map:
            icon_source = self.icon_map[name]
            
            if isinstance(icon_source, str):
                # Load from file
                icon_path = self.assets_dir / icon_source
                if icon_path.exists():
                    icon = QIcon(str(icon_path))
                else:
                    icon = self._create_fallback_icon(name, size, color)
            else:
                # Generate programmatically
                icon = icon_source(size, color)
        else:
            icon = self._create_fallback_icon(name, size, color)
        
        self._icon_cache[cache_key] = icon
        return icon
    
    def _create_fallback_icon(self, name: str, size: int, color: str) -> QIcon:
        """Create a simple fallback icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        
        # Simple shape based on name
        if "play" in name:
            triangle = QPolygon([
                QPoint(int(size * 0.3), int(size * 0.2)),
                QPoint(int(size * 0.8), int(size * 0.5)),
                QPoint(int(size * 0.3), int(size * 0.8))
            ])
            painter.drawPolygon(triangle)
        elif "stop" in name:
            painter.fillRect(int(size * 0.25), int(size * 0.25), int(size * 0.5), int(size * 0.5), QColor(color))
        else:
            painter.drawEllipse(int(size * 0.25), int(size * 0.25), int(size * 0.5), int(size * 0.5))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_refresh_icon(self, size: int, color: str) -> QIcon:
        """Create refresh/reload icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Circular arrow
        center = size // 2
        radius = int(size * 0.35)
        painter.drawArc(center - radius, center - radius, 2 * radius, 2 * radius, 16 * 30, 16 * 300)
        
        # Arrow head
        arrow_size = int(size * 0.15)
        painter.drawLine(center + radius - arrow_size, center - radius + arrow_size, 
                        center + radius, center - radius)
        painter.drawLine(center + radius, center - radius, 
                        center + radius - arrow_size, center - radius - arrow_size)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_play_icon(self, size: int, color: str) -> QIcon:
        """Create play icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        
        # Triangle
        triangle = QPolygon([
            QPoint(int(size * 0.3), int(size * 0.2)),
            QPoint(int(size * 0.8), int(size * 0.5)),
            QPoint(int(size * 0.3), int(size * 0.8))
        ])
        painter.drawPolygon(triangle)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_stop_icon(self, size: int, color: str) -> QIcon:
        """Create stop icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        
        # Square
        square_size = int(size * 0.5)
        painter.fillRect((size - square_size) // 2, (size - square_size) // 2, 
                        square_size, square_size, QColor(color))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_settings_icon(self, size: int, color: str) -> QIcon:
        """Create settings/gear icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))
        
        # Simple gear representation
        center = size // 2
        outer_radius = int(size * 0.4)
        inner_radius = int(size * 0.25)
        
        # Outer circle with notches
        painter.drawEllipse(center - outer_radius, center - outer_radius, 
                           2 * outer_radius, 2 * outer_radius)
        
        # Inner circle
        painter.drawEllipse(center - inner_radius, center - inner_radius, 
                           2 * inner_radius, 2 * inner_radius)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_device_icon(self, size: int, color: str) -> QIcon:
        """Create USB device icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))
        
        # USB connector shape
        rect_width = int(size * 0.4)
        rect_height = int(size * 0.6)
        x = (size - rect_width) // 2
        y = (size - rect_height) // 2
        
        painter.fillRect(x, y, rect_width, rect_height, QColor(color))
        
        # USB symbol
        painter.setPen(QColor("#2b2b2b"))
        painter.drawLine(int(x + rect_width * 0.3), int(y + rect_height * 0.3), 
                        int(x + rect_width * 0.7), int(y + rect_height * 0.3))
        painter.drawLine(int(x + rect_width * 0.3), int(y + rect_height * 0.7), 
                        int(x + rect_width * 0.7), int(y + rect_height * 0.7))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_image_icon(self, size: int, color: str) -> QIcon:
        """Create OS image icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))
        
        # Disc shape
        center = size // 2
        outer_radius = int(size * 0.4)
        inner_radius = int(size * 0.15)
        
        painter.drawEllipse(center - outer_radius, center - outer_radius, 
                           2 * outer_radius, 2 * outer_radius)
        
        # Inner hole
        painter.setBrush(Qt.GlobalColor.transparent)
        painter.drawEllipse(center - inner_radius, center - inner_radius, 
                           2 * inner_radius, 2 * inner_radius)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_deploy_icon(self, size: int, color: str) -> QIcon:
        """Create deployment/rocket icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        
        # Rocket shape
        rocket_points = QPolygon([
            QPoint(int(size * 0.5), int(size * 0.1)),  # Top
            QPoint(int(size * 0.65), int(size * 0.7)),  # Right side
            QPoint(int(size * 0.5), int(size * 0.6)),   # Bottom center
            QPoint(int(size * 0.35), int(size * 0.7)),  # Left side
        ])
        painter.drawPolygon(rocket_points)
        
        # Flame
        flame_points = QPolygon([
            QPoint(int(size * 0.45), int(size * 0.7)),
            QPoint(int(size * 0.5), int(size * 0.9)),
            QPoint(int(size * 0.55), int(size * 0.7)),
        ])
        painter.setBrush(QColor("#ff6b35"))
        painter.drawPolygon(flame_points)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_verify_icon(self, size: int, color: str) -> QIcon:
        """Create verification/checkmark icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(3)
        painter.setPen(pen)
        
        # Checkmark
        painter.drawLine(int(size * 0.2), int(size * 0.5), int(size * 0.4), int(size * 0.7))
        painter.drawLine(int(size * 0.4), int(size * 0.7), int(size * 0.8), int(size * 0.3))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_success_icon(self, size: int, color: str = "#10b981") -> QIcon:
        """Create success checkmark icon"""
        return self._create_verify_icon(size, color)
    
    def _create_warning_icon(self, size: int, color: str = "#f59e0b") -> QIcon:
        """Create warning triangle icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        
        # Triangle
        triangle = QPolygon([
            QPoint(int(size * 0.5), int(size * 0.1)),
            QPoint(int(size * 0.1), int(size * 0.9)),
            QPoint(int(size * 0.9), int(size * 0.9))
        ])
        painter.drawPolygon(triangle)
        
        # Exclamation mark
        painter.setBrush(QColor("#2b2b2b"))
        painter.fillRect(int(size * 0.46), int(size * 0.3), int(size * 0.08), int(size * 0.35), QColor("#2b2b2b"))
        painter.fillRect(int(size * 0.46), int(size * 0.75), int(size * 0.08), int(size * 0.08), QColor("#2b2b2b"))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_error_icon(self, size: int, color: str = "#ef4444") -> QIcon:
        """Create error X icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(3)
        painter.setPen(pen)
        
        # X
        painter.drawLine(int(size * 0.2), int(size * 0.2), int(size * 0.8), int(size * 0.8))
        painter.drawLine(int(size * 0.8), int(size * 0.2), int(size * 0.2), int(size * 0.8))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_info_icon(self, size: int, color: str = "#3b82f6") -> QIcon:
        """Create info icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        
        # Circle
        center = size // 2
        radius = int(size * 0.4)
        painter.drawEllipse(center - radius, center - radius, 2 * radius, 2 * radius)
        
        # i
        painter.setBrush(QColor("#ffffff"))
        painter.fillRect(int(size * 0.46), int(size * 0.25), int(size * 0.08), int(size * 0.08), QColor("#ffffff"))
        painter.fillRect(int(size * 0.46), int(size * 0.4), int(size * 0.08), int(size * 0.35), QColor("#ffffff"))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_chevron_right_icon(self, size: int, color: str) -> QIcon:
        """Create right chevron icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Chevron
        painter.drawLine(int(size * 0.3), int(size * 0.2), int(size * 0.7), int(size * 0.5))
        painter.drawLine(int(size * 0.7), int(size * 0.5), int(size * 0.3), int(size * 0.8))
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_chevron_left_icon(self, size: int, color: str) -> QIcon:
        """Create left chevron icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Chevron
        painter.drawLine(int(size * 0.7), int(size * 0.2), int(size * 0.3), int(size * 0.5))
        painter.drawLine(int(size * 0.3), int(size * 0.5), int(size * 0.7), int(size * 0.8))
        
        painter.end()
        return QIcon(pixmap)


# Global icon manager instance
icon_manager = IconManager()