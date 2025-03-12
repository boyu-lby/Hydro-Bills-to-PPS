from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, 
    QMessageBox, QWidget, QHBoxLayout, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

class PDFListItemWidget(QWidget):
    delete_clicked = pyqtSignal(str)  # Signal to emit when delete button is clicked

    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.init_ui()

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
    pdf_paths_updated = pyqtSignal(list)  # Signal to emit when PDF paths are updated

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
        rename_btn.clicked.connect(self.clear_files)  # Keeping the same function for now
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
                
        # Emit updated paths
        self.pdf_paths_updated.emit(self.pdf_paths)

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
        
        # Emit signal with updated paths
        self.pdf_paths_updated.emit(self.pdf_paths)
        event.acceptProposedAction()

    def clear_files(self):
        self.pdf_paths.clear()
        self.file_list.clear()
        self.pdf_paths_updated.emit(self.pdf_paths) 