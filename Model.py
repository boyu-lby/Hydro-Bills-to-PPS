from PyQt5.QtCore import Qt, pyqtSignal, QObject

from Excel_helper import insert_tuples_in_excel, read_column_values, clear_all, read_cell_content_from_first_two_col
import Global_variables
from Invoice_PDF_process import invoice_pdf_scan_and_rename
from Web_page_interact import pps_multiple_invoices_input


class Model(QObject):
    todoInvoicesChanged = pyqtSignal()
    left_section_data_ready = pyqtSignal(tuple)
    mainWindowNotificationPromted = pyqtSignal(str)
    renameWindowNotificationPromted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.todo_invoices = dict()
        try:
            with open(Global_variables.configuration_file_path, 'r') as f:
                lines = f.readlines()
                ONTARIO_EMAIL = lines[0].strip() if len(lines) > 0 else ""
                ONTARIO_PASSWORD = lines[1].strip() if len(lines) > 1 else ""
        except FileNotFoundError:
            print(f"Warning","Configuration file not found. A new one will be created on save.")
        except Exception as e:
            print(f"Error", f"Failed to load config: {str(e)}")

    def add_todo_invoice(self, account: str):
        print(f"added {account}")
        self.todo_invoices.update({account: [None, False]})

    def delete_todo_invoice(self, account: str):
        print(f"deleted {account}")
        self.todo_invoices.pop(account)

    def update_todo_invoice(self, account: str, vendor=None):
        print(f"updated {account} with vendor {vendor}")
        self.todo_invoices.update({account: [vendor, self.todo_invoices.get(account)[1]]})

    def update_invoice_checkbox_state(self, account: str, checkbox_state: bool):
        print(f"set {account}'s checkbox to {checkbox_state}")
        self.todo_invoices.update({account: [self.todo_invoices.get(account)[0], checkbox_state]})

    def save_todo_invoices_in_excel(self):
        clear_all(Global_variables.todo_invoices_excel_path,
                               'Sheet1')
        for invoice in self.todo_invoices.items():
            insert_tuples_in_excel(Global_variables.todo_invoices_excel_path,
                                   'Sheet1',
                                   [(invoice[0], invoice[1][0])])

    def process_all_todo_invoices(self):
        print(self.todo_invoices)

        # Save configuration
        self.save_config()
        todo_invoices = []
        for invoice in self.todo_invoices.items():
            if invoice[1][1] is None or invoice[1][1] in ("", False):
                continue
            todo_invoices.append([invoice[0], invoice[1][0]])
        if len(todo_invoices) == 0:
            self.mainWindowNotificationPromted.emit("No Selected Invoices")
            return
        pps_multiple_invoices_input(todo_invoices)
        self.read_todo_invoices_from_excel()
        self.send_left_section_data()

    def read_todo_invoices_from_excel(self):
        # Read invoices
        todo_invoices = read_cell_content_from_first_two_col(
            Global_variables.todo_invoices_excel_path,
            "Sheet1")
        self.todo_invoices = {}
        for todo_invoice in todo_invoices:
            self.todo_invoices.update({todo_invoice[0]:[("" if todo_invoice[1] is None else todo_invoice[1]), False]})
        self.todoInvoicesChanged.emit()

    def rename_files(self, file_paths: list[str], vendor: str):
        success = []
        fail = []
        not_found = []
        message = ""

        for path in file_paths:
            try:
                isSuccess, name = invoice_pdf_scan_and_rename(path, vendor)
                if isSuccess:
                    success.append(name)
                else:
                    fail.append(name)
            except FileNotFoundError as e:
                not_found.append(path)

        if success:
            message += "Successfully renamed files: "
            for name in success:
                message += f"{name}, "
            message = message[:-2] + "\n\n"
        if fail:
            message += "Files rename failed: "
            for name in fail:
                message += f"{name}, "
            message = message[:-2] + "\n\n"
        if not_found:
            message += "Paths not found: "
            for name in not_found:
                message += f"{name}, "
            message = message[:-2] + "\n"

        self.mainWindowNotificationPromted.emit(message)

    def save_config(self):
        try:
            with open(Global_variables.configuration_file_path, 'r') as f:
                lines = f.readlines()
                if len(lines) > 0:
                    Global_variables.ontario_email = (lines[0].strip() if len(lines) > 0 else "")
                if len(lines) > 1:
                    Global_variables.ontario_password = (lines[1].strip() if len(lines) > 1 else "")
                if len(lines) > 2:
                    Global_variables.todo_invoices_dir_path = (lines[2].strip() if len(lines) > 1 else "")
                if len(lines) > 3:
                    time_interval_data = lines[3].strip().split(',')
                    if len(time_interval_data) == 2:
                        Global_variables.is_period_validation_needed = time_interval_data[0]
                        Global_variables.period_need_validate = int(time_interval_data[1])
                if len(lines) > 4:
                    max_payment_data = lines[4].strip().split(',')
                    if len(max_payment_data) == 2:
                        Global_variables.is_max_payment_validation_needed = max_payment_data[0]
                        Global_variables.max_payment_need_validate = int(max_payment_data[1])
                if len(lines) > 5:
                    abnormal_amount_data = lines[5].strip().split(',')
                    if len(abnormal_amount_data) == 2:
                        Global_variables.is_abnormal_amount_validation_needed = abnormal_amount_data[0]
                        Global_variables.average_multiple_threshold = int(abnormal_amount_data[1])
        except FileNotFoundError:
            print(f"Warning", "Configuration file not found. A new one will be created on save.")
        except Exception as e:
            print(f"Error", f"Failed to load config: {str(e)}")

    def get_todo_invoices(self):
        return self.todo_invoices.items()

    def send_left_section_data(self):
        self.left_section_data_ready.emit((self.get_succeed_invoices(), self.get_funding_requested_invoices(), self.get_failed_invoices()))

    def get_failed_invoices(self) -> int:
        return len(read_column_values(Global_variables.failed_invoices_excel_path,
        "Sheet1", "Invoice Number"))

    def get_succeed_invoices(self) -> int:
        return len(read_column_values(Global_variables.succeed_invoices_excel_path,
        "Sheet1", "Invoice Number"))

    def get_funding_requested_invoices(self) -> int:
        return len(read_column_values(Global_variables.funding_requested_excel_path,
        "Sheet1", "Invoice Number"))