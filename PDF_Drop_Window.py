from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget,
    QMessageBox, QWidget, QHBoxLayout, QListWidgetItem, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class PDFListItemWidget(QWidget):
    delete_clicked = pyqtSignal(str)  # Signal to emit when delete button is clicked

    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.init_ui()
        self.notification_expanded = False

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 8, 5, 8)  # Increased vertical margins
        layout.setSpacing(10)

        # File path label
        self.path_label = QLabel(self.pdf_path)
        self.path_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font: 11pt 'Arial';
            }
        """)
        layout.addWidget(self.path_label)

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(28, 28)  # Slightly larger button
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1948A;
                color: white;
                border-radius: 14px;
                font: bold 16pt 'Arial';
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E74C3C;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.pdf_path))
        layout.addWidget(delete_btn)

        self.setLayout(layout)

class PDFDropDialog(QDialog):
    rename_button_clicked = pyqtSignal(list, str) # Signal to emit when rename button is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_paths = []  # List to store PDF file paths
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PDF Files")
        self.setFixedSize(600, 400)
        self.setAcceptDrops(True)  # Enable drop events

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Notification section
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

        layout.addWidget(self.notification_container)

        # Vendor Dropdown Menu
        self.vendor_menu = QComboBox()
        self.vendor_menu.addItems(['Select Vendor', 'Alectra', 'Burlington', 'Elexicon', 'Fortis', 'Grimsby', 'Hydro One', 'NPE', 'NTP', 'Toronto Hydro', 'Welland'])
        self.vendor_menu.currentTextChanged.connect(self.vendor_menu_changed)
        layout.addWidget(self.vendor_menu)

        # Drop area label
        self.drop_label = QLabel("Drop PDF files here")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: #F0F3F4;
                border: 2px dashed #B2BABB;
                border-radius: 6px;
                padding: 20px;
                font: 14pt 'Arial';
                color: #2C3E50;
            }
        """)
        layout.addWidget(self.drop_label)

        # List widget to show dropped files
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E5E7E9;
                border-radius: 4px;
                padding: 5px;
                font: 11pt 'Arial';
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #F2F3F4;
                min-height: 40px;  /* Minimum height for items */
            }
            QListWidget::item:selected {
                background-color: #EBF5FB;
                color: #2C3E50;
            }
        """)
        layout.addWidget(self.file_list)

        # Rename button (formerly Clear button)
        rename_btn = QPushButton("Rename Files")
        rename_btn.clicked.connect(self.rename_dropped_files)  # Keeping the same function for now
        rename_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px;
                font: bold 12pt 'Arial';
                border-radius: 5px;
                border: 2px solid #219A52;
            }
            QPushButton:hover {
                background-color: #219A52;
            }
        """)
        layout.addWidget(rename_btn)

        self.setLayout(layout)

    def vendor_menu_changed(self, text):
        self.collapse_notification()

    def add_pdf_to_list(self, file_path):
        # Create list item and custom widget
        item = QListWidgetItem()
        widget = PDFListItemWidget(file_path)
        widget.delete_clicked.connect(self.remove_pdf)
        
        # Set item size
        item.setSizeHint(widget.sizeHint())
        
        # Add to list widget
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, widget)

    def remove_pdf(self, file_path):
        self.collapse_notification()
        # Remove from paths list
        if file_path in self.pdf_paths:
            self.pdf_paths.remove(file_path)
            
        # Remove from list widget
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            if widget.pdf_path == file_path:
                self.file_list.takeItem(i)
                break

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # Check if all files are PDFs
            urls = event.mimeData().urls()
            if all(url.toLocalFile().lower().endswith('.pdf') for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                if file_path not in self.pdf_paths:
                    self.pdf_paths.append(file_path)
                    self.add_pdf_to_list(file_path)

    def rename_dropped_files(self):
        self.collapse_notification()
        if self.vendor_menu.currentText() == 'Select Vendor':
            self.expand_notification("Please select a vendor")
            return
        if not self.pdf_paths:
            return
        self.rename_button_clicked.emit(self.pdf_paths, self.vendor_menu.currentText())
        self.accept()

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