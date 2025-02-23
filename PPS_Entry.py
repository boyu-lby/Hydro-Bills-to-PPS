
import time

import pytesseract

from Excel_helper import read_column_values, populate_invoice_numbers, insert_tuples_in_excel, \
    delete_cell_content_if_matches
from OCR_helper import click_by_coordinate, click_on_text, input_text, press_enter, clear_input_bar, \
    scroll_up, get_today_date, convert_date, convert_month_abbr, check_page_loading, \
    click_button_by_text, find_button, click_on_color_bottom_first
from CustomizedExceptions import PendingPaymentError, OCRFindingError, AmountError, InvoiceScanError
from scan_helper import find_file_with_substring, copy_as_pdf_in_original_and_destination, self_check
from VendorInvoicesExtraction.toronto_hydro_scan import parse_toronto_hydro_bill

line_height = (100, 20)
short_wait_time = 0.2
long_wait_time = 3

def click_view_update():
    click_on_text('View/Update')

def click_search_utility_account():
    click_by_coordinate(325, 539)

def click_approved_contract():
    position = find_button("Approved")
    if position is None:
        print(f"Approved contract is not found!")
        return

    x, y, w, h = position

    # Calculate a center point for the bounding box
    center_x = x + w // 2
    center_y = y + h // 2

    # Button is 90 pixels left by "Approved"
    center_x -= 110

    # click the button
    click_by_coordinate(center_x, center_y)

def press_invoices():
    click_by_coordinate(555, 357)

def multi_invoices_process(times=-1):
    """
    This function takes the invoice number in 'Invoice To Do.xlsx' and invoice pdf in 'Invoice PDF' as input,
    automatically input into PPS, generated a named pdf into 'Temp Hydro Invoices', and recorded in 'Succeed Invoices'.
    If an account has no enough fund to pay or already has a payment on pending, it will be recorded in 'Saved Invoices'.
    If an unexpected error happened during the inputting process, it will be recorded in 'Failed Invoices'
    """
    # God bless, this line brings the fortune
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\LiBo3\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

    # Read invoices
    invoices_todo_lst = read_column_values(r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Invoices To Do.xlsx",
                                           "Sheet1", "Invoice Number")

    # Failed invoices will be stored in this list, and re-attempt later
    retry_invoices = []

    # No hope, number in this list will be stored into 'Failed Invoice'
    failed_invoices = []

    # Only for those invoices which is saved as draft but did not request for approval
    saved_invoices = []

    succeed_invoices = []
    number_of_iteration = 0

    # Iterate all invoices
    for invoice in invoices_todo_lst:
        if invoice is None:
            continue

        if number_of_iteration == times:
            break

        print(f"Start inputting '{invoice}'")
        info = None
        try:
            # Scan the invoice PDF and extract the data
            try:
                pdf_file_path = find_file_with_substring(r"C:\Users\LiBo3\Downloads", str(invoice))
                results = parse_toronto_hydro_bill(pdf_file_path)
                for key, value in results.items():
                    print(f"{key}: {value}")
            except:
                raise InvoiceScanError

            if not self_check(results):
                raise AmountError

            # Input data into PPS
            single_invoice_process(results)

            # Rename the PDF, save into "Temp Hydro Invoices"
            copy_as_pdf_in_original_and_destination(pdf_file_path,
                                                    r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Temp Hydro Invoices",
                                                    results["suggested_file_name"])

            info = (results["account_number"], results["suggested_file_name"][-7:], results["invoice_subtotal"])

        except OCRFindingError as e:
            populate_invoice_numbers(
                r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Failed Invoices.xlsx",
                "Sheet1", "Invoice Number", [invoice])

            print(f"OCRFindingError: {invoice}, can not find '{e.text}'")
            continue

        except PendingPaymentError as e:
            populate_invoice_numbers(
                r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Saved Invoices.xlsx",
                "Sheet1", "Invoice Number", [invoice])
            print(f"PendingPaymentError: {invoice}")
            continue

        except AmountError as e:
            populate_invoice_numbers(
                r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Failed Invoices.xlsx",
                "Sheet1", "Invoice Number", [invoice])

            print(f"'{e.account_number}' has an Unmatch amount")
            continue

        except InvoiceScanError as e:
            populate_invoice_numbers(
                r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Failed Invoices.xlsx",
                "Sheet1", "Invoice Number", [invoice])

            print(f"'{e.account_number}' failed on invoice scanning")
            continue

        else:
            if info is not None:
                print(f"{info[0]} is successfully inputted")
                insert_tuples_in_excel(r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Succeed Invoices.xlsx",
                                       "Sheet1", [info])
        finally:
            delete_cell_content_if_matches(r"C:\Users\LiBo3\OneDrive - Government of Ontario\Desktop\HBAES\Invoices To Do.xlsx",
                                           "Sheet1", "Invoice Number", invoice)
            number_of_iteration += 1


def single_invoice_process(results):
    # Navigate to home page
    check_page_loading()
    scroll_up(600)
    time.sleep(1)
    try:
        click_button_by_text("Home", order=-1)
    except OCRFindingError:
        print("Home Button Not Found")

    # On the menu of Maintenance, click on the View/Update
    check_page_loading()
    click_by_coordinate(644, 364)

    # Enter account number
    check_page_loading()
    click_by_coordinate(325, 539)
    clear_input_bar()
    input_text(str(results["account_number"]).replace("-", ""))
    press_enter()

    # Click approved contract
    check_page_loading()
    click_approved_contract()

    # Click on 'Invoices'
    check_page_loading()
    press_invoices()

    # Check if pending payment exists
    if find_button("Pending Payment"):
        raise PendingPaymentError(results["account_number"])

    # Click on 'New Invoice'
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    time.sleep(0.5)
    click_on_color_bottom_first("#006699")

    # Contract General Info Entry
    # Input invoice number
    check_page_loading()
    time.sleep(1)
    click_by_coordinate(486, 370)
    input_text(results["account_number"] + convert_month_abbr(results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:])
    # Input work start period
    time.sleep(short_wait_time)
    click_by_coordinate(496, 410)
    input_text(convert_date(results["period_start_date"]))
    press_enter()
    # Input work end period
    time.sleep(short_wait_time)
    click_by_coordinate(496, 460)
    input_text(convert_date(results["period_end_date"]))
    press_enter()
    # Input statement date
    time.sleep(short_wait_time)
    click_by_coordinate(867, 300)
    input_text(convert_date(results["statement_date"]))
    press_enter()
    # Input date received
    time.sleep(short_wait_time)
    click_by_coordinate(888, 336)
    input_text(get_today_date())
    press_enter()
    # Input invoice subtotal
    time.sleep(short_wait_time)
    click_by_coordinate(911, 495)
    input_text(str(results["invoice_subtotal"]))
    # Input invoice h.s.t.
    time.sleep(short_wait_time)
    click_by_coordinate(910, 532)
    input_text(str(results["hst"]))
    # Input comment
    time.sleep(short_wait_time)
    click_by_coordinate(700, 645)
    input_text(results["suggested_file_name"][-7:-4] + " " + results["suggested_file_name"][-4:])
    # Click next
    time.sleep(short_wait_time)
    scroll_up(-300)
    check_page_loading()
    click_by_coordinate(1500, 850)

    line_number = 0
    temp_height = 0 # Height will increase based on the number of line added
    # Input Electricity Info
    # Add new line
    check_page_loading()
    time.sleep(1)
    click_button_by_text("Add New Line")
    # Select line type
    check_page_loading()
    click_by_coordinate(1400, 475)
    # Select electricity
    time.sleep(short_wait_time)
    click_on_text("Electricity")
    check_page_loading()
    # Input electricity subtotal

    time.sleep(short_wait_time)
    time.sleep(1)
    click_by_coordinate(764, 534)
    clear_input_bar()
    input_text(str(results["total_electricity_charges"]).replace(",", ""))
    press_enter()
    # Update Line
    time.sleep(short_wait_time)
    click_button_by_text("Update")
    temp_height += line_height[0]

    # Input Late Payment Charges Info
    if results["Late Payment Charge"] is not None and results["Late Payment Charge"] != 0:
        # Add new line
        check_page_loading()
        time.sleep(1)
        click_button_by_text("Add New Line")
        # Select line type
        check_page_loading()
        click_by_coordinate(1400, 475 + temp_height)

        # Select late payment charges
        time.sleep(short_wait_time)
        click_on_text("Late")
        check_page_loading()
        # Input Late Payment Charges
        time.sleep(short_wait_time)
        time.sleep(1)
        click_by_coordinate(764, 534 + temp_height)
        clear_input_bar()
        input_text(str(results["Late Payment Charge"]).replace(",", ""))
        press_enter()
        # Update Line
        time.sleep(short_wait_time)
        click_button_by_text("Update")
        temp_height += line_height[1]

    # Input Electricity (Tax Exempt) Info
    ETE = round(results["balance_forward"] + results["ontario_electricity_rebate"], 2)
    if ETE is not None and ETE != 0:
        # Add new line
        check_page_loading()
        time.sleep(1)
        click_button_by_text("Add New Line")
        # Select line type
        check_page_loading()
        click_by_coordinate(1400, 475 + temp_height)

        # Select Electricity (Tax Exempt)
        time.sleep(short_wait_time)
        click_button_by_text("Electricity Tax Exempt")

        # Input Electricity (Tax Exempt)
        time.sleep(short_wait_time)
        time.sleep(1)
        click_by_coordinate(764, 534 + temp_height)
        clear_input_bar()
        input_text(str(ETE).replace(",", ""))
        press_enter()
        # Update Line
        time.sleep(short_wait_time)
        click_button_by_text("Update")
        temp_height += line_height[1]

    # Click on 'Confirmation' to navigate to the next page
    check_page_loading()
    click_button_by_text("Confirmation", -1)
    # On the page, sometimes 'Processing' won't show up, but still processing, so we use time.sleep(5)
    time.sleep(5)

    # Click on 'Save As Pending Payment'
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    click_by_coordinate(925, 807)

    # Click on 'New Payment Certificate'
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    click_by_coordinate(1023, 828)

    # Write comments
    check_page_loading()
    click_by_coordinate(657, 545)
    input_text(results["suggested_file_name"][-7:-4] + " " + results["suggested_file_name"][-4:])

    # Click on 'Holdback'
    check_page_loading()
    click_button_by_text('Holdback', -1)
    time.sleep(4)

    # Click on 'Confirmation' to navigate to the next page
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    click_button_by_text("Confirmation", 2)
    # On the page, sometimes 'Processing' won't show up, but still processing, so we use time.sleep(5)
    time.sleep(5)

    # Click on 'Save As Draft"
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    click_button_by_text("Save As Draft")

    # Click on 'Request Approval"
    check_page_loading()
    scroll_up(-600)
    check_page_loading()
    click_button_by_text("Request Approval")

    # Check if fund is enough
    check_page_loading()
    if find_button("Error requesting payment certificate"):
        raise PendingPaymentError(results["account_number"])

    # Back to home menu
    check_page_loading()
    click_button_by_text("Home", -1)
