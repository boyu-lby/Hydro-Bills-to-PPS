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
        self.setFixedSize(400, 450)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Email Section
        email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        # Password Section
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)

        # Invoice pdf dir path Section
        path_label = QLabel("Invoice PDF dir path:")
        self.path_input = QLineEdit()
        layout.addWidget(path_label)
        layout.addWidget(self.path_input)

        # Time Interval Check Section
        time_interval_layout = QHBoxLayout()
        time_interval_label = QLabel("Time Interval Check:")
        self.time_interval_checkbox = QCheckBox()
        self.time_interval_checkbox.stateChanged.connect(self.toggle_time_interval)
        time_interval_layout.addWidget(time_interval_label)
        time_interval_layout.addWidget(self.time_interval_checkbox)
        layout.addLayout(time_interval_layout)

        self.time_interval_input = QLineEdit()
        self.time_interval_input.setValidator(QIntValidator(1, 999999))  # Only allow positive integers
        self.time_interval_input.setEnabled(False)  # Initially disabled
        layout.addWidget(self.time_interval_input)

        # Maximum Payment Amount Threshold Section
        max_payment_layout = QHBoxLayout()
        max_payment_label = QLabel("Maximum Payment Amount:")
        self.max_payment_checkbox = QCheckBox()
        self.max_payment_checkbox.stateChanged.connect(self.toggle_max_payment)
        max_payment_layout.addWidget(max_payment_label)
        max_payment_layout.addWidget(self.max_payment_checkbox)
        layout.addLayout(max_payment_layout)

        self.max_payment_input = QLineEdit()
        self.max_payment_input.setValidator(QIntValidator(1, 999999))  # Only allow positive integers
        self.max_payment_input.setEnabled(False)  # Initially disabled
        layout.addWidget(self.max_payment_input)

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
        layout.addWidget(save_btn)

        self.setLayout(layout)

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
                if len(lines) > 3:
                    time_interval_data = lines[3].strip().split(',')
                    if len(time_interval_data) == 2:
                        self.time_interval_checkbox.setChecked(time_interval_data[0] == 'True')
                        self.time_interval_input.setText(time_interval_data[1])
                        self.toggle_time_interval(self.time_interval_checkbox.checkState())
                        Global_variables.is_period_validation_needed = self.time_interval_checkbox.isChecked()
                        Global_variables.period_need_validate = int(self.time_interval_input.text())
                if len(lines) > 4:
                    max_payment_data = lines[4].strip().split(',')
                    if len(max_payment_data) == 2:
                        self.max_payment_checkbox.setChecked(max_payment_data[0] == 'True')
                        self.max_payment_input.setText(max_payment_data[1])
                        self.toggle_max_payment(self.max_payment_checkbox.checkState())
                        Global_variables.is_max_payment_validation_needed = self.max_payment_checkbox.isChecked()
                        Global_variables.max_payment_need_validate = int(self.max_payment_input.text())

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
                # Save time interval check state and value
                time_interval_value = self.time_interval_input.text() if self.time_interval_checkbox.isChecked() else ""
                f.write(f"{self.time_interval_checkbox.isChecked()},{time_interval_value}\n")
                # Save maximum payment amount state and value
                max_payment_value = self.max_payment_input.text() if self.max_payment_checkbox.isChecked() else ""
                f.write(f"{self.max_payment_checkbox.isChecked()},{max_payment_value}\n")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {str(e)}")

    def toggle_time_interval(self, state):
        self.time_interval_input.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.time_interval_input.clear()

    def toggle_max_payment(self, state):
        self.max_payment_input.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            self.max_payment_input.clear()