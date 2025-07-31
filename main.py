import pyautogui

import time

import sys

from PyQt5.QtWidgets import QApplication
import traceback
import ctypes

from Controller import Controller
from Excel_helper import read_column_values
from Invoice_PDF_process import invoice_pdf_scan_and_rename
from Main_Window import MainWindow
from Model import Model

from pynput.mouse import Controller as MouseController, Button

from VendorInvoicesExtraction.elexicon import parse_elexicon_bill
from VendorInvoicesExtraction.oakville import parse_oakville_bill
from VendorInvoicesExtraction.toronto_hydro_scan import parse_toronto_hydro_bill
from scan_helper import find_file_with_substring, copy_as_pdf_in_original_and_destination, self_check, \
    months_since_invoice

from playwright.sync_api import sync_playwright
import os


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
    results = parse_toronto_hydro_bill(pdf_file_path)
    for key, value in results.items():
        print(f"{key}: {value}")
    print(self_check(results))


def show_native_error_popup(title, message):
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # 0x10 = MB_ICONERROR

def run_app():
    app = QApplication(sys.argv)

    # Create Model, View, Controller
    model = Model()
    view = MainWindow()
    controller = Controller(model, view)

    view.show()
    sys.exit(app.exec_())

def test():
    with sync_playwright() as p:
        browser_path = p.chromium.executable_path
        print("Chromium path:", browser_path)

if __name__ == "__main__":
    run_app()