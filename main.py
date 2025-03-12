import pyautogui

import time

import sys

from PyQt5.QtWidgets import QApplication

from Controller import Controller
from Invoice_PDF_process import invoice_pdf_scan_and_rename
from Main_Window import MainWindow
from Model import Model

from pynput.mouse import Controller as MouseController, Button

from VendorInvoicesExtraction.NTP import parse_NTP_bill
from VendorInvoicesExtraction.burlington_hydro_scan import parse_burlington_hydro_bill
from VendorInvoicesExtraction.hydro_one import parse_hydro_one_bill
from scan_helper import find_file_with_substring, copy_as_pdf_in_original_and_destination, self_check, \
    months_since_invoice
from VendorInvoicesExtraction.welland_scan import parse_welland_bill

def keep_active():
    print("Keeping Microsoft Teams active. Press Ctrl+C to stop.")
    while True:
        pyautogui.move(1, 0)  # Move mouse slightly
        time.sleep(2)  # Wait 2 seconds
        pyautogui.move(-1, 0)  # Move it back
        mouse = MouseController()
        mouse.click(Button.left, 2)
        time.sleep(30)  # Wait 5 minutes before repeating

def print_results(invoice):
    pdf_file_path = find_file_with_substring(r"C:\Users\LiBo3\Downloads", invoice)
    results = parse_hydro_one_bill(pdf_file_path)
    for key, value in results.items():
        print(f"{key}: {value}")
    print(self_check(results))


def run_app():
    app = QApplication(sys.argv)

    # Create Model, View, Controller
    model = Model()
    view = MainWindow()
    controller = Controller(model, view)

    view.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_app()
