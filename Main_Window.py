import sys
import os
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QDrag, QPalette, QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea,
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QLineEdit, QCheckBox
)
import Global_variables
from Configuration_Window import ConfigurationDialog
from Excel_helper import open_excel_app, open_succeed_invoices, open_funding_requested_invoices, open_failed_invoices
from Help_Window import HelpDialog


# -----------------------------
# Draggable Label (Right Side)
# -----------------------------
class DraggableLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            DraggableLabel {
                background-color: #D5F5E3;
                color: #0B5345;
                border: 2px solid #1ABC9C;
                border-radius: 8px;
                padding: 6px;
                font: 12pt 'Arial';
            }
            DraggableLabel:hover {
                background-color: #A2D9CE;
                cursor: grab;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text())
            drag.setMimeData(mime_data)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.exec_(Qt.CopyAction | Qt.MoveAction)
        else:
            super().mousePressEvent(event)

# ---------------------------------------------------
# A custom widget to represent the "bar" for each Text
# ---------------------------------------------------
class TextBar(QWidget):
    dropTextChanged = pyqtSignal(tuple)
    textBarDeleted = pyqtSignal(str)
    checkboxStateChanged = pyqtSignal(tuple)

    def __init__(self, text_content, parent=None):
        super().__init__(parent)
        self.text_content = str(text_content)
        self.original_style = """
                    QLabel {
                        background-color: #F8F9F9;
                        border: 1px solid #E5E7E9;
                        border-radius: 4px;
                        padding: 6px;
                        font: 10pt 'Arial';
                        qproperty-alignment: AlignVCenter;
                    }
                """
        self.setFixedHeight(60)
        self.drop_text = None
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.setStyleSheet("""
            TextBar {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
            }
        """)

        # Add checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
                    QCheckBox {
                        spacing: 8px;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                    }
                """)
        self.checkbox.stateChanged.connect(self.handle_checkbox_change)
        layout.addWidget(self.checkbox)

        # Text content display
        self.label_text = QLabel(self.text_content, self)
        self.label_text.setStyleSheet("""
            QLabel {
                background-color: #F8F9F9;
                border: 1px solid #E5E7E9;
                border-radius: 4px;
                padding: 6px;
                font: 10pt 'Arial';
                qproperty-alignment: AlignVCenter;
            }
        """)
        self.label_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.label_text)

        # Drop area
        self.drop_label = DropLabel("Drop here", self)
        self.drop_label.setMinimumWidth(150)
        layout.addWidget(self.drop_label)

        # Delete button
        self.delete_btn = QPushButton("×", self)
        self.delete_btn.setFixedSize(30, 30)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1948A;
                color: white;
                border-radius: 15px;
                font: bold 14pt 'Arial';
            }
            QPushButton:hover {
                background-color: #E74C3C;
                cursor: pointer;
            }
        """)
        self.delete_btn.clicked.connect(self.handle_delete_event)
        layout.addWidget(self.delete_btn)

        # Set initial opacity
        self.setWindowOpacity(1.0)

        # Enable transparency effects
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Connect the drop label's signal to a handler
        self.drop_label.dropped.connect(self.handle_drop_event)

    def set_highlight(self, highlight: bool):
        """Toggle highlight state"""
        if highlight:
            self.label_text.setStyleSheet("""
                QLabel {
                    background-color: #FFF3B0;
                    border: 2px solid #F1C40F;
                    border-radius: 4px;
                    padding: 6px;
                    font: 10pt 'Arial';
                    qproperty-alignment: AlignVCenter;
                }
            """)
        else:
            self.label_text.setStyleSheet(self.original_style)

    def handle_delete_event(self):
        self.textBarDeleted.emit(self.text_content)
        self.start_fade_out()

    def handle_drop_event(self, dropped_text):
        self.drop_text = dropped_text
        self.dropTextChanged.emit((self.text_content, self.drop_text))

    def start_fade_out(self):
        """Animates the deletion of the TextBar"""
        # Create fade animation
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)

        # Connect animation finish to actual deletion
        self.animation.finished.connect(self.deleteLater)

        # Start animation
        self.animation.start()

        # Disable interactions during animation
        self.setEnabled(False)

    def handle_checkbox_change(self, state):
        self.checkboxStateChanged.emit((self.text_content, state))

    # -------------------------------------------
# DropLabel: A label that accepts drops (text)
# -------------------------------------------
class DropLabel(QLabel):
    dropped = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            DropLabel {
                background-color: #F0F3F4;
                border: 2px dashed #B2BABB;
                border-radius: 6px;
                padding: 6px;
                font: 10pt 'Arial';
                qproperty-alignment: AlignVCenter;
            }
            DropLabel:hover {
                background-color: #E5E8E8;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            dropped_text = event.mimeData().text()
            self.setText(dropped_text)
            event.acceptProposedAction()

            # Emit the signal with the dropped text
            self.dropped.emit(dropped_text)


class SplitButton(QWidget):
    clicked = pyqtSignal()  # Single click signal for the whole button

    def __init__(self, left_text, right_text, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui(left_text, right_text)

    def init_ui(self, left_text, right_text):
        # Base styling
        self.setStyleSheet("""
            SplitButton {
                background-color: #5DADE2;
                border-radius: 8px;
                border: 2px solid #2E86C1;
            }
            SplitButton:hover {
                background-color: #3498DB;
            }
            SplitButton:pressed {
                background-color: #2E86C1;
            }
        """)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left Part (70%)
        left_label = QLabel(left_text)
        left_label.setAlignment(Qt.AlignCenter)
        left_label.setStyleSheet("""
            QLabel {
                color: white;
                font: bold 12pt 'Arial';
                border-right: 2px solid #2E86C1;
                padding: 6px;
            }
        """)
        layout.addWidget(left_label, stretch=7)

        # Right Part (30%)
        self.right_label = QLabel(right_text)
        self.right_label.setAlignment(Qt.AlignCenter)
        self.right_label.setStyleSheet("""
            QLabel {
                color: white;
                font: bold 10pt 'Arial';
                padding: 6px;
            }
        """)
        layout.addWidget(self.right_label, stretch=3)

    def mousePressEvent(self, event):
        self.clicked.emit()
        # Add pressed visual feedback
        self.setStyleSheet("""
            SplitButton {
                background-color: #2E86C1;
                border-radius: 8px;
                border: 2px solid #2E86C1;
            }
        """)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Restore normal styling
        self.setStyleSheet("""
            SplitButton {
                background-color: #5DADE2;
                border-radius: 8px;
                border: 2px solid #2E86C1;
            }
            SplitButton:hover {
                background-color: #3498DB;
            }
        """)
        super().mouseReleaseEvent(event)

    def set_text_to_right_label(self, text):
        self.right_label.setText(text)

# ---------------------------------
# Middle Widget (PDF Drop Zone)
# ---------------------------------
class MiddleWidget(QWidget):
    todoInvoiceUpdateRequest = pyqtSignal(str)
    dropTextChanged = pyqtSignal(str, str)
    textBarDeleted = pyqtSignal(str)
    checkboxStateChanged = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.textBars = []
        self.init_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.notification_expanded = False

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -------------------------
        # 1) Top Control Bar
        # -------------------------
        top_bar = QWidget()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: #F4F6F6; border-bottom: 2px solid #D0D3D4;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_layout.setSpacing(10)

        # Add global checkbox
        self.global_checkbox = QCheckBox()
        self.global_checkbox.setStyleSheet("""
                    QCheckBox {
                        spacing: 8px;
                        margin-left: 5px;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                    }
                """)
        self.global_checkbox.stateChanged.connect(self.toggle_all_checkboxes)
        top_layout.addWidget(self.global_checkbox)

        # Search Bar (Replaces Notification Label)
        self.search_label = QLineEdit()
        self.search_label.setPlaceholderText("Search...")
        self.search_label.setStyleSheet("""
                   QLineEdit {
                       background-color: #F8F9F9;
                       border: 1px solid #E5E7E9;
                       border-radius: 4px;
                       padding: 6px;
                       font: 10pt 'Arial';
                       color: #2C3E50;
                   }
                   QLineEdit:hover {
                       border: 1px solid #1ABC9C;
                   }
                   QLineEdit:focus {
                       border: 2px solid #1ABC9C;
                   }
               """)
        self.search_label.returnPressed.connect(self.perform_search)
        top_layout.addWidget(self.search_label, stretch=7)

        # Right Side Container (Global controls)
        right_controls = QWidget()
        right_controls.setStyleSheet("background: transparent;")
        right_layout = QHBoxLayout(right_controls)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Global Drop Area (Styled like TextBar's DropLabel)
        self.global_drop = DropLabel("Apply to All")
        self.global_drop.setFixedSize(150, 35)  # Match TextBar drop area size
        self.global_drop.setStyleSheet("""
                    DropLabel {
                        background-color: #F0F3F4;
                        border: 2px dashed #B2BABB;
                        color: #2C3E50;
                        font: 10pt 'Arial';
                        border-radius: 6px;
                    }
                    DropLabel:hover {
                        background-color: #E5E8E8;
                    }
                """)
        right_layout.addWidget(self.global_drop)

        # Global Delete Button
        self.global_delete_btn = QPushButton("×")
        self.global_delete_btn.setFixedSize(30, 30)
        self.global_delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F1948A;
                        color: white;
                        border-radius: 15px;
                        font: bold 14pt 'Arial';
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                    QPushButton:pressed {
                        background-color: #CB4335;
                    }
                """)
        self.global_delete_btn.setToolTip("Delete all items")
        right_layout.addWidget(self.global_delete_btn)

        top_layout.addWidget(right_controls, stretch=2)

        main_layout.addWidget(top_bar)

        # -------------------------
        # 2) Notification Section
        # -------------------------
        self.notification_container = QWidget()
        self.notification_container.setStyleSheet("""
                    QWidget {
                        background-color: #FCF3CF;
                        border-bottom: 1px solid #F4D03F;
                    }
                """)
        self.notification_container.setMaximumHeight(0)
        self.notification_container.setMinimumHeight(0)

        notification_layout = QVBoxLayout(self.notification_container)
        notification_layout.setContentsMargins(10, 5, 10, 5)

        self.notification_label = QLabel()
        self.notification_label.setStyleSheet("""
                    QLabel {
                        color: #7E5109;
                        font: 10pt 'Arial';
                        padding: 5px;
                    }
                """)
        self.notification_label.setWordWrap(True)

        scroll = QScrollArea()
        scroll.setWidget(self.notification_label)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        notification_layout.addWidget(scroll)

        main_layout.addWidget(self.notification_container)

        # --------------------------------
        # 3) Scroll Area for TextBars
        # --------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#scrollContent {
                background-color: transparent;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Fixed bottom input bar
        input_bar = QWidget()
        input_bar.setFixedHeight(60)
        input_bar.setStyleSheet("background-color: #FFFFFF; border-top: 2px solid #E5E7E9;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(20, 10, 20, 10)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text and press Enter to create TextBar")
        self.text_input.setStyleSheet("""
            QLineEdit {
                font: 12pt 'Arial';
                padding: 8px;
                border: 2px solid #D5F5E3;
                border-radius: 6px;
            }
        """)
        self.text_input.returnPressed.connect(self.add_text_bar)

        input_layout.addWidget(self.text_input)
        main_layout.addWidget(input_bar)

        # -------------------------
        # 3) Connect Global Drop
        # -------------------------
        self.global_drop.dropped.connect(self.apply_to_all_bars)
        self.global_delete_btn.clicked.connect(self.clear_text_bars)

    def perform_search(self):
        """Handle search functionality with highlighting and scrolling"""
        search_text = self.search_label.text().strip().lower()
        first_match = None

        # Clear previous highlights
        for i in range(self.scroll_layout.count() - 1):
            item = self.scroll_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), TextBar):
                text_bar = item.widget()
                text_bar.set_highlight(False)  # Clear previous highlight

                # Check match
                if search_text and search_text in text_bar.text_content.lower():
                    text_bar.set_highlight(True)
                    if not first_match:
                        first_match = text_bar

        # Scroll to first match if exists
        if first_match:
            self.scroll_area.ensureWidgetVisible(first_match)
        elif search_text:
            self.expand_notification(f"No results found for '{search_text}'")

    def expand_notification(self, message: str, duration_ms: int = 300):
        """Expand notification section with animation"""
        self.notification_label.setText(message)

        self.anim = QPropertyAnimation(self.notification_container, b"maximumHeight")
        self.anim.setDuration(duration_ms)
        self.anim.setStartValue(self.notification_container.height())
        self.anim.setEndValue(100)  # Adjust height as needed
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.start()

        self.notification_expanded = True

    def collapse_notification(self, duration_ms: int = 200):
        """Collapse notification section with animation"""
        self.anim = QPropertyAnimation(self.notification_container, b"maximumHeight")
        self.anim.setDuration(duration_ms)
        self.anim.setStartValue(self.notification_container.height())
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.InQuad)
        self.anim.start()

        self.notification_expanded = False

    def apply_to_all_bars(self, text):
        """Apply dropped text to all TextBars"""
        for i in range(self.scroll_layout.count() - 1):  # Exclude stretch
            text_bar = self.scroll_layout.itemAt(i).widget()
            if isinstance(text_bar, TextBar):
                text_bar.drop_label.setText(text)
                self.dropTextChanged.emit(text_bar.text_content, text)

    def add_text_bar(self):
        # to prevent adding duplicated invoice number
        self.collapse_notification(duration_ms=0)
        account = self.text_input.text().strip().replace(" ", "")
        for textBar in self.textBars:
            if account == textBar.text_content:
                self.expand_notification("Input account number already existed")
                return

        if account:
            text_bar = TextBar(account)
            self.textBars.append(text_bar)
            text_bar.dropTextChanged.connect(self.handle_drop_event)
            text_bar.textBarDeleted.connect(self.handle_text_bar_delete_event)
            text_bar.checkboxStateChanged.connect(self.handle_checkbox_state_change_event)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, text_bar)
            self.text_input.clear()
            self.todoInvoiceUpdateRequest.emit(account)

    def add_text_bar_from_model(self, account, vendor, checkbox_state):
        text_bar = TextBar(account)
        text_bar.drop_label.setText(vendor)
        text_bar.drop_text = vendor
        text_bar.checkbox.setChecked(checkbox_state)
        self.textBars.append(text_bar)
        text_bar.dropTextChanged.connect(self.handle_drop_event)
        text_bar.textBarDeleted.connect(self.handle_text_bar_delete_event)
        text_bar.checkboxStateChanged.connect(self.handle_checkbox_state_change_event)
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, text_bar)

    def toggle_all_checkboxes(self, state):
        """Toggle all TextBar checkboxes based on global checkbox"""
        for i in range(self.scroll_layout.count() - 1):
            item = self.scroll_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), TextBar):
                item.widget().checkbox.setChecked(state == Qt.Checked)

    def clear_text_bars(self):
        """Remove all TextBar widgets with fade effect"""
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), TextBar):
                # Start fade out animation
                item.widget().handle_delete_event()

    def clear_text_bars_in_view(self):
        """Remove all TextBar widgets with fade effect in View only, will not affect Model"""
        self.textBars = []
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item.widget() and isinstance(item.widget(), TextBar):
                # Start fade out animation
                item.widget().start_fade_out()

    def handle_drop_event(self, pair):
        self.dropTextChanged.emit(pair[0], pair[1])

    def handle_text_bar_delete_event(self, account):
        self.textBarDeleted.emit(account)
        for i in range(len(self.textBars)):
            if self.textBars[i].text_content == account:
                self.textBars.pop(i)
                break

    def handle_checkbox_state_change_event(self, pair):
        self.checkboxStateChanged.emit(pair[0], pair[1])

# ---------------------------------
# Main Window
# ---------------------------------
class MainWindow(QMainWindow):
    todoInvoicesSaveRequest = pyqtSignal()
    todoInvoicesProcessRequest = pyqtSignal()
    left_section_update_required = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fancy Drag and Drop PDF + Text GUI")
        self.setGeometry(100, 100, 1400, 900)

        # Main window styling
        self.setStyleSheet("""
                    QMainWindow {
                        background-color: #EBF5FB;
                    }
                    QScrollArea {
                        border: none;
                    }
                """)

        # Central widget and main vertical layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_vertical_layout = QVBoxLayout(central_widget)
        main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        main_vertical_layout.setSpacing(0)

        # Top sections container (original three panels)
        top_sections = QWidget()
        main_horizontal_layout = QHBoxLayout(top_sections)
        main_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        main_horizontal_layout.setSpacing(0)

        # ----------------------
        # 1) Left Section (3/13)
        # ----------------------
        left_frame = QFrame()
        left_frame.setStyleSheet("""
                    QFrame {
                        background-color: #2E4053;
                        border-right: 2px solid #1A252F;
                    }
                """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(15, 15, 15, 15)

        # Add Configuration and Help buttons
        config_help_container = QWidget()
        config_help_container.setStyleSheet("background: transparent;")
        config_help_layout = QHBoxLayout(config_help_container)
        config_help_layout.setContentsMargins(0, 0, 0, 0)
        config_help_layout.setSpacing(10)

        # Configuration Button
        self.config_btn = QPushButton("Configuration")
        self.config_btn.setFixedHeight(50)
        self.config_btn.setStyleSheet("""
            QPushButton {
                background-color: #7D3C98;
                color: white;
                font: bold 12pt 'Arial';
                border: 2px solid #6C3483;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #6C3483;
            }
        """)
        config_help_layout.addWidget(self.config_btn, stretch=1)
        self.config_path = Global_variables.configuration_file_path
        self.config_btn.clicked.connect(self.show_config_dialog)

        # Help Button
        self.help_btn = QPushButton("Help")
        self.help_btn.setFixedHeight(50)
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #28B463;
                color: white;
                font: bold 12pt 'Arial';
                border: 2px solid #239B56;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #239B56;
            }
        """)
        # Help file path
        self.help_path = Global_variables.help_file_path
        # Connect help button
        self.help_btn.clicked.connect(self.show_help_dialog)
        config_help_layout.addWidget(self.help_btn, stretch=1)

        left_layout.addWidget(config_help_container)

        # Add Refresh Button at the top
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                font: bold 12pt 'Arial';
                border: 2px solid #2E86C1;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #3498DB;
            }
        """)
        self.refresh_btn.setFixedHeight(80)
        left_layout.addWidget(self.refresh_btn)
        self.refresh_btn.clicked.connect(self.left_section_update_required.emit)

        # Split buttons
        self.succeed_invoices_button = SplitButton("Succeed Invoices", "0")
        self.funding_request_invoices_button = SplitButton("Funding Requested", "0")
        self.failed_invoices_button = SplitButton("Failed Invoices", "0")
        self.succeed_invoices_button.setStyleSheet("SplitButton { background-color: #5DADE2; border-color: #2E86C1; }")
        self.funding_request_invoices_button.setStyleSheet("SplitButton { background-color: #48C9B0; border-color: #17A589; }")
        self.failed_invoices_button.setStyleSheet("SplitButton { background-color: #F4D03F; border-color: #D4AC0D; }")

        self.succeed_invoices_button.clicked.connect(open_succeed_invoices)
        self.funding_request_invoices_button.clicked.connect(open_funding_requested_invoices)
        self.failed_invoices_button.clicked.connect(open_failed_invoices)

        left_layout.addWidget(self.succeed_invoices_button)
        left_layout.addWidget(self.funding_request_invoices_button)
        left_layout.addWidget(self.failed_invoices_button)
        left_layout.addStretch()

        # ----------------------
        # 2) Middle Section (7/13)
        # ----------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.middle_widget = MiddleWidget()
        scroll_area.setWidget(self.middle_widget)

        # ----------------------
        # 3) Right Section (3/13)
        # ----------------------
        right_frame = QFrame()
        right_frame.setStyleSheet("""
                    QFrame {
                        background-color: #2E4053;
                        border-left: 2px solid #A569BD;
                    }
                """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(20, 20, 20, 20)

        # Draggable labels
        texts = ["", "Alectra", "Burlington Hydro", "Fortis", "Grimsby", "Toronto Hydro", "Welland"]
        for t in texts:
            lbl = DraggableLabel(t)
            right_layout.addWidget(lbl)
        right_layout.addStretch()

        # Add sections to main horizontal layout
        main_horizontal_layout.addWidget(left_frame, 3)
        main_horizontal_layout.addWidget(scroll_area, 7)
        main_horizontal_layout.addWidget(right_frame, 3)

        # ----------------------
        # 4) Bottom Section
        # ----------------------
        bottom_section = QWidget()
        bottom_section.setFixedHeight(80)
        bottom_section.setStyleSheet("""
                    QWidget {
                        background-color: #2C3E50;
                        border-top: 2px solid #1A252F;
                    }
                """)

        # Bottom buttons
        bottom_layout = QHBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        bottom_layout.setSpacing(20)

        process_button = QPushButton("Save and Process All Selected")
        btn_bottom2 = QPushButton("💾 Save Todo Invoices")

        for btn in [process_button, btn_bottom2]:
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setStyleSheet("""
                        QPushButton {
                            color: white;
                            font: bold 14pt 'Arial';
                            padding: 12px;
                            border-radius: 8px;
                        }
                    """)

        process_button.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB;
                        border: 2px solid #2980B9;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                """)

        btn_bottom2.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        border: 2px solid #219A52;
                    }
                    QPushButton:hover { background-color: #219A52; }
                """)
        process_button.clicked.connect(self._on_process_clicked)
        btn_bottom2.clicked.connect(self._on_save_clicked)

        bottom_layout.addWidget(process_button)
        bottom_layout.addWidget(btn_bottom2)

        # Combine all sections
        main_vertical_layout.addWidget(top_sections, 1)  # Expandable
        main_vertical_layout.addWidget(bottom_section, 0)  # Fixed height

        # Finalize layout
        central_widget.setLayout(main_vertical_layout)

    def show_config_dialog(self):
        dialog = ConfigurationDialog(self.config_path, self)
        dialog.exec_()

    def show_help_dialog(self):
        dialog = HelpDialog(self.help_path, self)
        dialog.exec_()

    def _on_save_clicked(self):
        self.todoInvoicesSaveRequest.emit()
        self.middle_widget.expand_notification("Successfully saved")

    def _on_process_clicked(self):
        self.todoInvoicesSaveRequest.emit()
        self.todoInvoicesProcessRequest.emit()

    def update_left_section(self, numbers):
        self.succeed_invoices_button.set_text_to_right_label(str(numbers[0]))
        self.funding_request_invoices_button.set_text_to_right_label(str(numbers[1]))
        self.failed_invoices_button.set_text_to_right_label(str(numbers[2]))
