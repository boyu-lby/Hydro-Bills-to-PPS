import sys
from PyQt5.QtCore import Qt, pyqtSignal, QObject

from Excel_helper import insert_tuples_in_excel, read_column_values, clear_all, read_cell_content_from_first_two_col
import Global_variables
from Web_page_interact import pps_multiple_invoices_input


class Model(QObject):
    todoInvoicesChanged = pyqtSignal()
    left_section_data_ready = pyqtSignal(tuple)
    notificationPromted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.todo_invoices = dict()

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

        todo_invoices = []
        for invoice in self.todo_invoices.items():
            if invoice[1][1] is None or invoice[1][1] in ("", False):
                continue
            todo_invoices.append([invoice[0], invoice[1][0]])
        if len(todo_invoices) == 0:
            self.notificationPromted.emit("No Selected Invoices")
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