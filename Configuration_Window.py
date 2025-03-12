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
        self.time_interval_checkbox.stateChanged.connect(lambda: self.on_checkbox_state_changed(self.time_interval_checkbox, self.time_interval_input))
        time_interval_layout.addWidget(time_interval_label)
        time_interval_layout.addWidget(self.time_interval_checkbox)
        layout.addLayout(time_interval_layout)

        self.time_interval_input = QLineEdit()
        self.time_interval_input.setValidator(QIntValidator(1, 999999))  # Only allow positive integers
        layout.addWidget(self.time_interval_input)

        # Maximum Payment Amount Threshold Section
        max_payment_layout = QHBoxLayout()
        max_payment_label = QLabel("Maximum Payment Amount:")
        self.max_payment_checkbox = QCheckBox()
        self.max_payment_checkbox.stateChanged.connect(lambda: self.on_checkbox_state_changed(self.max_payment_checkbox, self.max_payment_input))
        max_payment_layout.addWidget(max_payment_label)
        max_payment_layout.addWidget(self.max_payment_checkbox)
        layout.addLayout(max_payment_layout)

        self.max_payment_input = QLineEdit()
        self.max_payment_input.setValidator(QIntValidator(1, 999999))  # Only allow positive integers
        layout.addWidget(self.max_payment_input)

        # Abnormal Amount Detection Section
        abnormal_amount_layout = QHBoxLayout()
        abnormal_amount_label = QLabel("Abnormal Amount Detection:")
        self.abnormal_amount_checkbox = QCheckBox()
        self.abnormal_amount_checkbox.stateChanged.connect(lambda: self.on_checkbox_state_changed(self.abnormal_amount_checkbox, self.abnormal_amount_input))
        abnormal_amount_layout.addWidget(abnormal_amount_label)
        abnormal_amount_layout.addWidget(self.abnormal_amount_checkbox)
        layout.addLayout(abnormal_amount_layout)

        self.abnormal_amount_input = QLineEdit()
        self.abnormal_amount_input.setValidator(QIntValidator(1, 999999))  # Only allow positive integers
        layout.addWidget(self.abnormal_amount_input)

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
        
        # Initialize input fields state
        self.on_checkbox_state_changed(self.time_interval_checkbox, self.time_interval_input)
        self.on_checkbox_state_changed(self.max_payment_checkbox, self.max_payment_input)
        self.on_checkbox_state_changed(self.abnormal_amount_checkbox, self.abnormal_amount_input)

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
                if len(lines) > 3:
                    time_interval_data = lines[3].strip().split(',')
                    if len(time_interval_data) == 2:
                        self.time_interval_checkbox.setChecked(time_interval_data[0] == 'True')
                        self.time_interval_input.setText(time_interval_data[1])
                        Global_variables.is_period_validation_needed = self.time_interval_checkbox.isChecked()
                        Global_variables.period_need_validate = int(self.time_interval_input.text()) if time_interval_data[1] else 0
                if len(lines) > 4:
                    max_payment_data = lines[4].strip().split(',')
                    if len(max_payment_data) == 2:
                        self.max_payment_checkbox.setChecked(max_payment_data[0] == 'True')
                        self.max_payment_input.setText(max_payment_data[1])
                        Global_variables.is_max_payment_validation_needed = self.max_payment_checkbox.isChecked()
                        Global_variables.max_payment_need_validate = int(self.max_payment_input.text()) if max_payment_data[1] else 0
                if len(lines) > 5:
                    abnormal_amount_data = lines[5].strip().split(',')
                    if len(abnormal_amount_data) == 2:
                        self.abnormal_amount_checkbox.setChecked(abnormal_amount_data[0] == 'True')
                        self.abnormal_amount_input.setText(abnormal_amount_data[1])
                        Global_variables.is_abnormal_amount_validation_needed = self.abnormal_amount_checkbox.isChecked()
                        Global_variables.average_multiple_threshold = int(self.abnormal_amount_input.text()) if abnormal_amount_data[1] else 3

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
                time_interval_value = self.time_interval_input.text().strip()
                is_time_interval_valid = self.time_interval_checkbox.isChecked() and bool(time_interval_value)
                f.write(f"{is_time_interval_valid},{time_interval_value if is_time_interval_valid else ''}\n")
                
                # Save maximum payment amount state and value
                max_payment_value = self.max_payment_input.text().strip()
                is_max_payment_valid = self.max_payment_checkbox.isChecked() and bool(max_payment_value)
                f.write(f"{is_max_payment_valid},{max_payment_value if is_max_payment_valid else ''}\n")
                
                # Save abnormal amount detection state and value
                abnormal_amount_value = self.abnormal_amount_input.text().strip()
                is_abnormal_amount_valid = self.abnormal_amount_checkbox.isChecked() and bool(abnormal_amount_value)
                f.write(f"{is_abnormal_amount_valid},{abnormal_amount_value if is_abnormal_amount_valid else ''}\n")
                
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {str(e)}")