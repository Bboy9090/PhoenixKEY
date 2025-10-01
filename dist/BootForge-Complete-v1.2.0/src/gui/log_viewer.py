"""
BootForge Log Viewer Widget
Real-time log viewing and filtering
"""

import logging
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QComboBox, QLineEdit, QPushButton, QCheckBox,
    QLabel, QSplitter, QGroupBox, QListWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor, QColor


class LogViewer(QWidget):
    """Log viewer widget with filtering and real-time updates"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Log data
        self.log_entries = []
        self.filtered_entries = []
        self.max_entries = 1000
        
        # Filter settings
        self.level_filter = "ALL"
        self.text_filter = ""
        self.auto_scroll = True
        
        self._setup_ui()
        self._setup_timer()
    
    def _setup_ui(self):
        """Setup log viewer UI"""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        # Level filter
        filter_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.currentTextChanged.connect(self._update_filters)
        filter_layout.addWidget(self.level_combo)
        
        # Text filter
        filter_layout.addWidget(QLabel("Filter:"))
        self.text_filter_edit = QLineEdit()
        self.text_filter_edit.setPlaceholderText("Filter by text...")
        self.text_filter_edit.textChanged.connect(self._update_filters)
        filter_layout.addWidget(self.text_filter_edit)
        
        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self._clear_logs)
        filter_layout.addWidget(clear_button)
        
        # Auto-scroll checkbox
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.toggled.connect(self._toggle_auto_scroll)
        filter_layout.addWidget(self.auto_scroll_check)
        
        layout.addWidget(filter_group)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 9))
        
        # Set dark theme for log display
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
            }
        """)
        
        layout.addWidget(self.log_display)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.entry_count_label = QLabel("Entries: 0")
        status_layout.addWidget(self.entry_count_label)
        status_layout.addStretch()
        
        layout.addLayout(status_layout)
    
    def _setup_timer(self):
        """Setup timer for periodic log updates"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms
    
    def _update_filters(self):
        """Update filter settings and refresh display"""
        self.level_filter = self.level_combo.currentText()
        self.text_filter = self.text_filter_edit.text().lower()
        self._apply_filters()
        self._update_display()
    
    def _apply_filters(self):
        """Apply current filters to log entries"""
        self.filtered_entries = []
        
        for entry in self.log_entries:
            # Level filter
            if self.level_filter != "ALL" and entry['level'] != self.level_filter:
                continue
            
            # Text filter
            if self.text_filter and self.text_filter not in entry['message'].lower():
                continue
            
            self.filtered_entries.append(entry)
    
    def _update_display(self):
        """Update log display"""
        if not self.filtered_entries:
            return
        
        # Get current scroll position
        scrollbar = self.log_display.verticalScrollBar()
        was_at_bottom = scrollbar.value() == scrollbar.maximum()
        
        # Clear and rebuild display
        self.log_display.clear()
        
        for entry in self.filtered_entries[-500:]:  # Show last 500 entries
            self._add_entry_to_display(entry)
        
        # Update entry count
        self.entry_count_label.setText(f"Entries: {len(self.filtered_entries)}")
        
        # Auto-scroll if enabled and was at bottom
        if self.auto_scroll and was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
    
    def _add_entry_to_display(self, entry: dict):
        """Add a single log entry to display"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Set color based on log level
        color = self._get_level_color(entry['level'])
        
        # Format entry
        timestamp = entry['timestamp']
        level = entry['level'].ljust(8)
        message = entry['message']
        
        # Insert formatted text
        cursor.insertHtml(
            f'<span style="color: #808080">{timestamp}</span> '
            f'<span style="color: {color}; font-weight: bold">[{level}]</span> '
            f'<span style="color: #d4d4d4">{message}</span><br>'
        )
    
    def _get_level_color(self, level: str) -> str:
        """Get color for log level"""
        colors = {
            'DEBUG': '#808080',
            'INFO': '#4fc3f7',
            'WARNING': '#ffb74d',
            'ERROR': '#f44336',
            'CRITICAL': '#e91e63'
        }
        return colors.get(level, '#d4d4d4')
    
    def _clear_logs(self):
        """Clear all log entries"""
        self.log_entries.clear()
        self.filtered_entries.clear()
        self.log_display.clear()
        self.entry_count_label.setText("Entries: 0")
    
    def _toggle_auto_scroll(self, enabled: bool):
        """Toggle auto-scroll"""
        self.auto_scroll = enabled
    
    @pyqtSlot(str, str, str)
    def add_log_entry(self, level: str, timestamp: str, message: str):
        """Add new log entry"""
        entry = {
            'level': level,
            'timestamp': timestamp,
            'message': message
        }
        
        self.log_entries.append(entry)
        
        # Limit number of entries
        if len(self.log_entries) > self.max_entries:
            self.log_entries = self.log_entries[-self.max_entries:]
        
        # Apply filters to new entry
        self._apply_filters()
    
    def export_logs(self, filename: str) -> bool:
        """Export logs to file"""
        try:
            with open(filename, 'w') as f:
                f.write("BootForge Log Export\\n")
                f.write("=" * 50 + "\\n\\n")
                
                for entry in self.log_entries:
                    f.write(f"{entry['timestamp']} [{entry['level']}] {entry['message']}\\n")
            
            self.logger.info(f"Logs exported to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return False
    
    def connect_to_logger(self, gui_handler):
        """Connect to GUI log handler"""
        if gui_handler:
            gui_handler.log_message.connect(self.add_log_entry)