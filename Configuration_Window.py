from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QCheckBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
import Global_variables


class ConfigurationDialog(QDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("Configuration")
        self.setMinimumSize(400, 500)  # Set minimum size instead of fixed size

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Email Section
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setMinimumHeight(30)  # Set minimum height for input fields
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        # Password Section
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)

        # Invoice pdf dir path Section
        path_label = QLabel("Invoice PDF dir path:")
        self.path_input = QLineEdit()
        self.path_input.setMinimumHeight(30)
        layout.addWidget(path_label)
        layout.addWidget(self.path_input)

        # Add stretch to push the save button to the bottom
        layout.addStretch()

        # Save Button
        save_btn = QPushButton("Save & Close")
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px;
                font: bold 12pt 'Arial';
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #219A52;
            }
        """)
        save_btn.setMinimumHeight(40)  # Set minimum height for the save button
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def on_checkbox_state_changed(self, checkbox, input_field):
        input_field.setEnabled(checkbox.isChecked())
        if not checkbox.isChecked():
            input_field.clear()
        input_field.setStyleSheet("QLineEdit { background-color: %s }" % ("#FFFFFF" if checkbox.isChecked() else "#F0F0F0"))

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                lines = f.readlines()
                if len(lines) > 0:
                    self.email_input.setText(lines[0].strip() if len(lines) > 0 else "")
                if len(lines) > 1:
                    self.password_input.setText(lines[1].strip() if len(lines) > 1 else "")
                if len(lines) > 2:
                    self.path_input.setText(lines[2].strip() if len(lines) > 1 else "")

        except FileNotFoundError:
            QMessageBox.warning(self, "Warning",
                                "Configuration file not found. A new one will be created on save.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config: {str(e)}")

    def save_config(self):
        try:
            with open(self.config_path, 'w') as f:
                f.write(f"{self.email_input.text()}\n")
                f.write(f"{self.password_input.text()}\n")
                f.write(f"{self.path_input.text()}\n")
                
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {str(e)}")