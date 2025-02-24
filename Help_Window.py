from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QScrollArea

class HelpDialog(QDialog):
    def __init__(self, help_path, parent=None):
        super().__init__(parent)
        self.help_path = help_path
        self.init_ui()
        self.load_help_content()

    def init_ui(self):
        self.setWindowTitle("Help Documentation")
        self.setFixedSize(600, 400)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Scroll Area for Help Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.content = QLabel()
        self.content.setWordWrap(True)
        self.content.setStyleSheet("""
            QLabel {
                font: 11pt 'Arial';
                color: #2C3E50;
                padding: 10px;
            }
        """)
        scroll.setWidget(self.content)

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #5DADE2;
                color: white;
                padding: 10px;
                font: bold 12pt 'Arial';
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3498DB;
            }
        """)

        layout.addWidget(scroll)
        layout.addWidget(close_btn)
        self.setLayout(layout)

    def load_help_content(self):
        try:
            with open(self.help_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.content.setText(content)
        except FileNotFoundError:
            self.content.setText("Help file not found at:\n" + self.help_path)
        except Exception as e:
            self.content.setText(f"Error loading help content: {str(e)}")