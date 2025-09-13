"""
BootForge StepperHeader Widget
Beautiful horizontal stepper component showing wizard progress through 6-step deployment workflow
"""

import logging
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QTimer, pyqtSlot
# pyqtProperty import - LSP server may show false positive, but works at runtime
from PyQt6.QtCore import pyqtProperty  # type: ignore
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPixmap, QPalette, QIcon

from src.gui.stepper_wizard import WizardStep, WizardController
from src.gui.modern_theme import BootForgeTheme
from src.gui.icon_manager import IconManager


class StepState(Enum):
    """Visual states for stepper steps"""
    LOCKED = auto()      # Step not yet accessible (gray, disabled)
    ACTIVE = auto()      # Current step being worked on (blue, highlighted) 
    COMPLETE = auto()    # Successfully completed step (green, checkmark)
    ERROR = auto()       # Step has validation error (red, warning icon)


class StepIndicator(QWidget):
    """Individual step indicator widget with number/icon and connecting line"""
    
    clicked = pyqtSignal(int)  # Emits step index when clicked
    
    def __init__(self, step_index: int, step_name: str, is_last: bool = False):
        super().__init__()
        self.step_index = step_index
        self.step_name = step_name
        self.is_last = is_last
        self.state = StepState.LOCKED
        self._clickable = False
        
        # Initialize icon manager
        self.icon_manager = IconManager()
        
        # Styling constants - increased sizes for better visibility
        self.CIRCLE_SIZE = 48
        self.LINE_WIDTH = 4
        self.LINE_LENGTH = 100
        
        # Step icons mapping
        self.step_icons = {
            0: "device",    # Detect Hardware
            1: "image",     # Select OS Image
            2: "settings",  # Configure USB
            3: "warning",   # Safety Review
            4: "verify",    # Build & Verify
            5: "success"    # Summary
        }
        
        # Colors using modern theme
        self.colors = {
            StepState.LOCKED: {
                'circle': BootForgeTheme.COLORS['text_disabled'],
                'text': BootForgeTheme.COLORS['text_disabled'],
                'line': BootForgeTheme.COLORS['border']
            },
            StepState.ACTIVE: {
                'circle': BootForgeTheme.COLORS['primary'],
                'text': BootForgeTheme.COLORS['text_primary'],
                'line': BootForgeTheme.COLORS['primary']
            },
            StepState.COMPLETE: {
                'circle': BootForgeTheme.COLORS['success'],
                'text': BootForgeTheme.COLORS['text_primary'], 
                'line': BootForgeTheme.COLORS['success']
            },
            StepState.ERROR: {
                'circle': BootForgeTheme.COLORS['error'],
                'text': BootForgeTheme.COLORS['text_primary'],
                'line': BootForgeTheme.COLORS['error']
            }
        }
        
        self.setFixedSize(self.LINE_LENGTH + self.CIRCLE_SIZE if not is_last else self.CIRCLE_SIZE, 100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Enhanced shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        # Animation properties for smooth transitions
        self._scale_factor = 1.0
        self._opacity = 1.0
        
        # Scale animation for hover effects
        self._scale_animation = QPropertyAnimation(self, b"scaleFactor")
        self._scale_animation.setDuration(200)
        self._scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity animation for state transitions
        self._opacity_animation = QPropertyAnimation(self, b"opacityValue")
        self._opacity_animation.setDuration(300)
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Timer for pulse animation on active state
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse_active_step)
        self._pulse_direction = 1
        
        self.logger = logging.getLogger(f"{__name__}.StepIndicator")
    
    def set_state(self, state: StepState, clickable: bool = False):
        """Update step visual state and clickability with smooth animations"""
        state_changed = (self.state != state)
        clickable_changed = (self._clickable != clickable)
        
        if state_changed or clickable_changed:
            if state_changed:
                old_state = self.state
                self.state = state
                self.logger.debug(f"Step {self.step_index} state changed from {old_state.name} to {state.name}")
                
                # Animate state transition
                self._animate_state_change(old_state, state)
            
            if clickable_changed:
                self._clickable = clickable
                # Update cursor based on clickability
                if clickable and self.state in [StepState.COMPLETE, StepState.ACTIVE]:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                self.logger.debug(f"Step {self.step_index} clickability changed to {clickable}")
            
            self.update()  # Trigger repaint when any property changes
    
    def is_clickable(self) -> bool:
        """Check if step is clickable"""
        return self._clickable
    
    def mousePressEvent(self, a0):
        """Handle mouse clicks"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton and self.is_clickable():
            self.clicked.emit(self.step_index)
            self.logger.debug(f"Step {self.step_index} clicked")
        super().mousePressEvent(a0)
    
    def paintEvent(self, a0):
        """Custom paint method for step visualization with modern styling"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get colors for current state
        color_scheme = self.colors[self.state]
        circle_color = QColor(color_scheme['circle'])
        text_color = QColor(color_scheme['text'])
        line_color = QColor(color_scheme['line'])
        
        # Draw enhanced connecting line (if not last step)
        if not self.is_last:
            line_y = self.height() // 2 - 10  # Adjusted for new circle position
            line_start_x = self.CIRCLE_SIZE + 8
            line_end_x = self.width() - 8
            
            # Draw background line
            bg_pen = QPen(QColor(BootForgeTheme.COLORS['border']), self.LINE_WIDTH - 1)
            painter.setPen(bg_pen)
            painter.drawLine(line_start_x, line_y, line_end_x, line_y)
            
            # Draw progress line for completed/active steps
            if self.state in [StepState.COMPLETE, StepState.ACTIVE]:
                progress_pen = QPen(line_color, self.LINE_WIDTH)
                progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(progress_pen)
                
                # Calculate progress length
                progress_length = line_end_x - line_start_x
                if self.state == StepState.COMPLETE:
                    progress_end = line_end_x
                else:  # ACTIVE
                    progress_end = line_start_x + (progress_length * 0.5)  # 50% for active
                
                painter.drawLine(line_start_x, line_y, int(progress_end), line_y)
        
        # Apply scale factor for animations
        scaled_size = int(self.CIRCLE_SIZE * self._scale_factor)
        size_diff = scaled_size - self.CIRCLE_SIZE
        
        # Draw step circle with enhanced styling and animation support
        circle_x = -size_diff // 2
        circle_y = (self.height() - scaled_size) // 2 - 10
        circle_rect = QRect(circle_x, circle_y, scaled_size, scaled_size)
        
        # Apply opacity for animations
        painter.setOpacity(self._opacity)
        
        # Enhanced hover effect for clickable steps
        if self.is_clickable() and self.underMouse():
            # Draw glow effect
            glow_rect = QRect(circle_x - 4, circle_y - 4, self.CIRCLE_SIZE + 8, self.CIRCLE_SIZE + 8)
            glow_color = QColor(circle_color)
            glow_color.setAlpha(60)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(glow_rect)
        
        # Main circle with gradient effect
        painter.setBrush(QBrush(circle_color))
        border_color = QColor(circle_color)
        border_color = border_color.darker(120)
        painter.setPen(QPen(border_color, 2))
        painter.drawEllipse(circle_rect)
        
        # Draw step content (icon or number)
        if self.state == StepState.COMPLETE:
            # Use success icon
            icon = self.icon_manager.get_icon("success", 24, text_color.name())
            icon_rect = QRect(circle_x + 12, circle_y + 12, 24, 24)
            icon.paint(painter, icon_rect)
        elif self.state == StepState.ERROR:
            # Use error icon
            icon = self.icon_manager.get_icon("error", 24, text_color.name())
            icon_rect = QRect(circle_x + 12, circle_y + 12, 24, 24)
            icon.paint(painter, icon_rect)
        elif self.state == StepState.ACTIVE and self.step_index in self.step_icons:
            # Use step-specific icon for active state
            icon_name = self.step_icons[self.step_index]
            icon = self.icon_manager.get_icon(icon_name, 24, text_color.name())
            icon_rect = QRect(circle_x + 12, circle_y + 12, 24, 24)
            icon.paint(painter, icon_rect)
        else:
            # Draw step number for locked state
            font = QFont(BootForgeTheme.FONTS['default_family'], 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(text_color))
            painter.drawText(circle_rect, Qt.AlignmentFlag.AlignCenter, str(self.step_index + 1))
        
        # Draw step name below circle with improved styling
        name_rect = QRect(circle_x - 30, circle_y + self.CIRCLE_SIZE + 8, self.CIRCLE_SIZE + 60, 25)
        font = QFont(BootForgeTheme.FONTS['default_family'], 10)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        
        # Adjust text color based on state using theme colors
        if self.state == StepState.LOCKED:
            painter.setPen(QPen(QColor(BootForgeTheme.COLORS['text_disabled'])))
        elif self.state == StepState.ACTIVE:
            painter.setPen(QPen(QColor(BootForgeTheme.COLORS['text_primary'])))
        else:
            painter.setPen(QPen(QColor(BootForgeTheme.COLORS['text_secondary'])))
        
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, self.step_name)
    
    def _animate_state_change(self, old_state: StepState, new_state: StepState):
        """Animate the transition between states"""
        # Stop any existing animations
        self._opacity_animation.stop()
        self._pulse_timer.stop()
        
        if new_state == StepState.COMPLETE:
            # Completion animation - scale up briefly then back to normal
            self._scale_animation.setStartValue(1.0)
            self._scale_animation.setEndValue(1.2)
            self._scale_animation.finished.connect(self._completion_animation_finished)
            self._scale_animation.start()
        
        elif new_state == StepState.ACTIVE:
            # Start subtle pulse animation for active state
            self._pulse_timer.start(2000)  # Pulse every 2 seconds
        
        elif new_state == StepState.ERROR:
            # Error shake animation
            self._shake_animation()
    
    def _completion_animation_finished(self):
        """Called when completion scale animation finishes"""
        # Scale back to normal
        self._scale_animation.finished.disconnect()
        self._scale_animation.setStartValue(1.2)
        self._scale_animation.setEndValue(1.0)
        self._scale_animation.start()
    
    def _pulse_active_step(self):
        """Create a subtle pulse effect for active steps"""
        if self.state == StepState.ACTIVE:
            if self._pulse_direction > 0:
                self._opacity_animation.setStartValue(1.0)
                self._opacity_animation.setEndValue(0.7)
                self._pulse_direction = -1
            else:
                self._opacity_animation.setStartValue(0.7)
                self._opacity_animation.setEndValue(1.0)
                self._pulse_direction = 1
            
            self._opacity_animation.start()
    
    def _shake_animation(self):
        """Create a shake animation for error states"""
        original_pos = self.pos()
        
        # Simple shake by moving slightly left and right
        shake_timer = QTimer()
        shake_count = 0
        max_shakes = 6
        
        def shake_step():
            nonlocal shake_count
            if shake_count < max_shakes:
                offset = 3 if shake_count % 2 == 0 else -3
                self.move(original_pos.x() + offset, original_pos.y())
                shake_count += 1
            else:
                self.move(original_pos)
                shake_timer.stop()
        
        shake_timer.timeout.connect(shake_step)
        shake_timer.start(50)  # 50ms intervals
    
    def enterEvent(self, event):
        """Handle mouse enter with animation"""
        if self.is_clickable():
            self._scale_animation.stop()
            self._scale_animation.setStartValue(1.0)
            self._scale_animation.setEndValue(1.1)
            self._scale_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, a0):
        """Handle mouse leave with animation"""
        if self.is_clickable():
            self._scale_animation.stop()
            self._scale_animation.setStartValue(1.1)
            self._scale_animation.setEndValue(1.0)
            self._scale_animation.start()
        super().leaveEvent(a0)
    
    # PyQt Properties for animations
    def getScaleFactor(self):
        return self._scale_factor
    
    def setScaleFactor(self, value):
        self._scale_factor = value
        self.update()
    
    def getOpacityValue(self):
        return self._opacity
    
    def setOpacityValue(self, value):
        self._opacity = value
        self.update()
    
    scaleFactor = pyqtProperty(float, getScaleFactor, setScaleFactor)
    opacityValue = pyqtProperty(float, getOpacityValue, setOpacityValue)


class StepperHeader(QWidget):
    """
    Beautiful horizontal stepper header showing progress through 6-step deployment workflow
    
    Features:
    - Visual progress indication with different states
    - Click-back navigation to completed steps
    - Professional styling with animations
    - Integration with WizardController signals
    """
    
    step_clicked = pyqtSignal(int)  # Emitted when user clicks a step
    
    def __init__(self, wizard_controller: Optional[WizardController] = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.wizard_controller = wizard_controller
        
        # Step definitions
        self.step_names = [
            "Detect Hardware",
            "Select OS Image", 
            "Configure USB",
            "Safety Review",
            "Build & Verify",
            "Summary"
        ]
        
        # State tracking
        self.current_step_index = 0
        self.step_states: List[StepState] = [StepState.LOCKED] * len(self.step_names)
        self.step_states[0] = StepState.ACTIVE  # Start with first step active
        
        # UI components
        self.step_indicators: List[StepIndicator] = []
        
        self._setup_ui()
        self._setup_connections()
        
        # Initialize visual state and progress label
        self._update_step_states()
        self._update_progress_label()
        
        self.logger.info("StepperHeader initialized with 6 steps")
    
    def _setup_ui(self):
        """Setup the stepper header UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Title section with enhanced styling
        title_layout = QHBoxLayout()
        
        title_label = QLabel("Deployment Workflow")
        title_font = QFont(BootForgeTheme.FONTS['default_family'], 
                          BootForgeTheme.FONTS['sizes']['xl'], 
                          QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {BootForgeTheme.COLORS['text_primary']};")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Enhanced progress indicator
        self.progress_label = QLabel("Step 1 of 6")
        progress_font = QFont(BootForgeTheme.FONTS['default_family'], 
                             BootForgeTheme.FONTS['sizes']['sm'], 
                             QFont.Weight.Medium)
        self.progress_label.setFont(progress_font)
        self.progress_label.setStyleSheet(f"""
            color: {BootForgeTheme.COLORS['text_secondary']};
            background-color: {BootForgeTheme.COLORS['bg_input']};
            padding: 4px 12px;
            border-radius: {BootForgeTheme.RADIUS['base']}px;
            border: 1px solid {BootForgeTheme.COLORS['border']};
        """)
        title_layout.addWidget(self.progress_label)
        
        layout.addLayout(title_layout)
        
        # Stepper indicators section with enhanced spacing
        stepper_layout = QHBoxLayout()
        stepper_layout.setContentsMargins(BootForgeTheme.SPACING['base'], 
                                        BootForgeTheme.SPACING['lg'], 
                                        BootForgeTheme.SPACING['base'], 0)
        stepper_layout.setSpacing(BootForgeTheme.SPACING['xs'])
        
        # Create step indicators
        for i, step_name in enumerate(self.step_names):
            is_last = (i == len(self.step_names) - 1)
            step_indicator = StepIndicator(i, step_name, is_last)
            step_indicator.clicked.connect(self._on_step_clicked)
            
            self.step_indicators.append(step_indicator)
            stepper_layout.addWidget(step_indicator)
            
            if not is_last:
                stepper_layout.addStretch()
        
        layout.addLayout(stepper_layout)
        
        # Apply styling
        self._apply_styling()
    
    def _apply_styling(self):
        """Apply modern theme styling to the stepper header"""
        self.setStyleSheet(f"""
            StepperHeader {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {BootForgeTheme.COLORS['bg_secondary']}, 
                    stop:1 {BootForgeTheme.COLORS['bg_tertiary']});
                border: 1px solid {BootForgeTheme.COLORS['border']};
                border-radius: {BootForgeTheme.RADIUS['lg']}px;
                margin: {BootForgeTheme.SPACING['sm']}px;
            }}
        """)
        
        # Set enhanced height for better visual hierarchy
        self.setFixedHeight(140)
    
    def _setup_connections(self):
        """Setup signal connections with WizardController"""
        if self.wizard_controller:
            # Listen for step changes
            self.wizard_controller.step_changed.connect(self._on_wizard_step_changed)
            
            # Listen for validation failures
            self.wizard_controller.validation_failed.connect(self._on_validation_failed)
            
            # Connect our step clicks to wizard controller
            self.step_clicked.connect(self._on_step_navigation_requested)
            
            self.logger.debug("Connected to WizardController signals")
    
    def set_current_step(self, step_index: int):
        """Set the current active step"""
        if 0 <= step_index < len(self.step_names):
            old_index = self.current_step_index
            self.current_step_index = step_index
            
            # Update step states
            self._update_step_states()
            self._update_progress_label()
            
            self.logger.info(f"Current step changed from {old_index} to {step_index}")
    
    def mark_step_complete(self, step_index: int):
        """Mark a step as completed"""
        if 0 <= step_index < len(self.step_names):
            self.step_states[step_index] = StepState.COMPLETE
            self.step_indicators[step_index].set_state(StepState.COMPLETE, clickable=True)
            self.logger.debug(f"Step {step_index} marked as complete")
    
    def mark_step_error(self, step_index: int):
        """Mark a step as having an error"""
        if 0 <= step_index < len(self.step_names):
            self.step_states[step_index] = StepState.ERROR
            self.step_indicators[step_index].set_state(StepState.ERROR, clickable=True)
            self.logger.warning(f"Step {step_index} marked as error")
    
    def _update_step_states(self):
        """Update visual states of all step indicators"""
        for i, indicator in enumerate(self.step_indicators):
            if i < self.current_step_index:
                # Previous steps should be complete
                if self.step_states[i] != StepState.ERROR:
                    self.step_states[i] = StepState.COMPLETE
                indicator.set_state(self.step_states[i], clickable=True)
            elif i == self.current_step_index:
                # Current step is active
                if self.step_states[i] != StepState.ERROR:
                    self.step_states[i] = StepState.ACTIVE
                indicator.set_state(self.step_states[i], clickable=True)
            else:
                # Future steps are locked
                self.step_states[i] = StepState.LOCKED
                indicator.set_state(StepState.LOCKED, clickable=False)
    
    def _update_progress_label(self):
        """Update the progress label text with enhanced formatting"""
        step_name = self.step_names[self.current_step_index]
        progress_percentage = int(((self.current_step_index + 1) / len(self.step_names)) * 100)
        self.progress_label.setText(f"Step {self.current_step_index + 1}/{len(self.step_names)} • {progress_percentage}% Complete")
    
    def _on_step_clicked(self, step_index: int):
        """Handle step indicator clicks with enhanced navigation guards"""
        # Validate step index bounds
        if not (0 <= step_index < len(self.step_names)):
            self.logger.warning(f"Step {step_index} click ignored - invalid index")
            return
        
        # Enhanced navigation guards
        step_state = self.step_states[step_index]
        is_completed_step = step_state == StepState.COMPLETE
        is_current_step = (step_index == self.current_step_index and step_state == StepState.ACTIVE)
        is_accessible = step_index <= self.current_step_index
        
        # Only allow navigation to:
        # 1. Completed steps (can go back to review)
        # 2. Current active step (refresh current step)
        # 3. Steps that aren't in error state (unless it's current step)
        can_navigate = (
            is_accessible and 
            (is_completed_step or is_current_step) and
            (step_state != StepState.ERROR or is_current_step)
        )
        
        if can_navigate:
            self.step_clicked.emit(step_index)
            self.logger.info(f"Step navigation requested to step {step_index} (state: {step_state.name})")
        else:
            self.logger.debug(f"Step {step_index} click ignored - not accessible (state: {step_state.name}, current: {self.current_step_index})")
    
    def _on_step_navigation_requested(self, step_index: int):
        """Handle step navigation requests"""
        if self.wizard_controller:
            try:
                current_index = self.current_step_index
                
                if step_index < current_index:
                    # Navigate backward using back() method
                    steps_to_go_back = current_index - step_index
                    for _ in range(steps_to_go_back):
                        if not self.wizard_controller.back():
                            self.logger.warning(f"Failed to navigate back to step {step_index}")
                            break
                    self.logger.info(f"Navigated back from step {current_index} to step {step_index}")
                elif step_index == current_index:
                    # Stay on current step - just refresh UI
                    self.logger.debug(f"Staying on current step {step_index}")
                else:
                    # Forward navigation not allowed for step clicking
                    self.logger.warning(f"Forward navigation to step {step_index} not allowed via step clicking")
                    
            except Exception as e:
                self.logger.error(f"Failed to navigate to step {step_index}: {e}")
        else:
            self.logger.warning(f"No wizard controller available for step {step_index}")
    
    def _on_wizard_step_changed(self, old_step, new_step):
        """Handle wizard step changes from controller"""
        if hasattr(new_step, 'value'):
            # Convert WizardStep enum to index
            step_index = list(WizardStep).index(new_step)
            self.set_current_step(step_index)
        else:
            self.logger.warning(f"Received unknown step type: {new_step}")
    
    def _on_validation_failed(self, step_name: str, error_message: str):
        """Handle validation failure signals"""
        # Find step index by name and mark as error
        for i, name in enumerate(self.step_names):
            if step_name.lower() in name.lower():
                self.mark_step_error(i)
                self.logger.error(f"Validation failed for {step_name}: {error_message}")
                break
    
    def get_current_step_index(self) -> int:
        """Get the current step index"""
        return self.current_step_index
    
    def get_step_states(self) -> List[StepState]:
        """Get current states of all steps"""
        return self.step_states.copy()
    
    def reset_to_beginning(self):
        """Reset stepper to the beginning"""
        self.current_step_index = 0
        self.step_states = [StepState.LOCKED] * len(self.step_names)
        self.step_states[0] = StepState.ACTIVE
        self._update_step_states()
        self._update_progress_label()
        self.logger.info("StepperHeader reset to beginning")


# Utility function for creating stepper header
def create_stepper_header(wizard_controller: Optional[WizardController] = None) -> StepperHeader:
    """
    Factory function to create a properly configured StepperHeader
    
    Args:
        wizard_controller: Optional WizardController for integration
        
    Returns:
        Configured StepperHeader widget
    """
    return StepperHeader(wizard_controller)