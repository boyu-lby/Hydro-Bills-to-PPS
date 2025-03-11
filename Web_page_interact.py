import time
import Global_variables
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from Excel_helper import read_column_values, populate_invoice_numbers, delete_cell_content_if_matches, \
    insert_tuples_in_excel, read_cell_content_from_first_two_col
from OCR_helper import convert_month_abbr, get_today_date
from VendorInvoicesExtraction.Get_invoice_extraction import get_invoice_extraction_function
from VendorInvoicesExtraction.NPE import parse_NPE_bill
from VendorInvoicesExtraction.NTP import parse_NTP_bill
from VendorInvoicesExtraction.alectra_scan import parse_alectra_bill
from VendorInvoicesExtraction.burlington_hydro_scan import parse_burlington_hydro_bill
from CustomizedExceptions import RequestApprovalError, InvoiceScanError, AmountError, PendingPaymentError, AccountNumberError, ExtractedDataUnmatchError, UnsaveableError
from VendorInvoicesExtraction.elexicon import parse_elexicon_bill
from VendorInvoicesExtraction.fortis_scan import parse_fortis_bill
from VendorInvoicesExtraction.grimsby import parse_grimsby_bill
from VendorInvoicesExtraction.hydro_one import parse_hydro_one_bill
from VendorInvoicesExtraction.toronto_hydro_scan import parse_toronto_hydro_bill
from VendorInvoicesExtraction.welland_scan import parse_welland_bill
from scan_helper import find_file_with_substring, self_check, copy_as_pdf_in_original_and_destination, convert_to_float, \
    calculate_fiscal_year, months_to_next_fiscal_period, months_since_invoice, parse_invoice_date

TARGET_URL = "https://pps.mto.ad.gov.on.ca/Home.aspx"

def login(driver):
    ONTARIO_EMAIL = Global_variables.ontario_email
    ONTARIO_PASSWORD = Global_variables.ontario_password

    # 2. Navigate to Microsoft login page.
    #    Often, just going to your target URL will redirect you to the MS login page,
    #    but you can also go directly to https://login.microsoftonline.com/ if needed.
    driver.get("https://login.microsoftonline.com/")

    # 3. Enter email/username.
    #    Common IDs or names:
    #    - "i0116" (older)
    #    - "loginfmt" (common)
    #    - Or use driver.find_element(By.NAME, "loginfmt")
    email_input = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.NAME, "loginfmt"))
    )
    email_input.clear()
    email_input.send_keys(ONTARIO_EMAIL)

    # 4. Click the "Next" button.
    #    The "Next" button often has ID "idSIButton9"
    next_button = driver.find_element(By.ID, "idSIButton9")
    next_button.click()

    # 5. (Try to) wait for the password field and enter the password.
    # If the browser remembers the password, this step might be skipped, causing a timeout.
    try:
        password_input = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.NAME, "passwd"))
        )
        password_input.clear()
        password_input.send_keys(ONTARIO_PASSWORD)

        sign_in_button = driver.find_element(By.ID, "idSIButton9")
        sign_in_button.click()
    except TimeoutException:
        # If we get here, the password field didn't appear within 5 seconds,
        # likely because the browser skipped or auto‐filled the password step.
        print("Password field did not appear; continuing...")

    # 7. (Optional) Handle "Stay signed in?" screen.
    #    Sometimes you see a prompt with the same button ID "idSIButton9" for "Yes."
    #    Or you might see "idBtn_Back" for "No." Adjust as needed.
    try:
        stay_signed_in_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "idSIButton9"))
        )
        stay_signed_in_button.click()
    except:
        print("No 'Stay signed in?' prompt appeared, continuing...")

def get_invoice_dir_path():
    try:
        with open(Global_variables.configuration_file_path, 'r') as f:
            lines = f.readlines()
            return lines[2].strip() if len(lines) > 1 else ""
    except FileNotFoundError:
        print(f"Warning","Configuration file not found. A new one will be created on save.")
    except Exception as e:
        print(f"Error", f"Failed to load config: {str(e)}")


def pps_multiple_invoices_input(invoices_todo_lst):
    """
    This function takes the invoice number in 'Invoice To Do.xlsx' and invoice pdf in 'Invoice PDF' as input,
    automatically input into PPS, generated a named pdf into 'Temp Hydro Invoices', and recorded in 'Succeed Invoices'.
    If an account has no enough fund to pay or already has a payment on pending, it will be recorded in 'Saved Invoices'.
    If an unexpected error happened during the inputting process, it will be recorded in 'Failed Invoices'
    """
    # Read email and password from config


    # Login in
    driver = webdriver.Chrome()
    login(driver)

    succeed_invoices = []

    # Iterate all invoices
    for invoice in invoices_todo_lst:
        # invoice[0] is account number, invoice[1] is vendor
        print('-----------------------------')
        if invoice is None or invoice[0] is None:
            continue

        # Skip empty vendor invoice
        if invoice[1] is None or invoice[1].replace(" ", "") == "":
            continue

        print(f"Start inputting '{invoice[0]}'")
        info = None
        try:
            # Scan the invoice PDF and extract the data
            pdf_file_path = find_file_with_substring(get_invoice_dir_path(), str(invoice[0]))
            # Use right invoice scanning method
            scanning_method = get_invoice_extraction_function(invoice[1])
            results = scanning_method(pdf_file_path)
            if results is None:
                print(f"Invalid Vendor Name: {invoice[1]}")
                raise UnsaveableError(invoice[0], 'Invalid vendor name')

            for key, value in results.items():
                print(f"{key}: {value}")

            # Check invoice[0] (account number) match the account number in PDF
            if invoice[0].replace('-', '') not in results['account_number'].replace('-', '') and results['account_number'].replace('-', '') not in invoice[0].replace('-', ''):
                raise UnsaveableError(invoice[0], f"The data in file named '{invoice[0]}' contains the data of '{results['account_number']}'")

            # Check data is reasonable or not
            if not self_check(results):
                raise AmountError(invoice[0])

            # Input data into PPS
            indicator = pps_single_invoice_input(results, driver)

            # Rename the PDF, save into "Temp Hydro Invoices"
            copy_as_pdf_in_original_and_destination(pdf_file_path,
                                                    Global_variables.renamed_invoices_dir_path,
                                                    results["suggested_file_name"])

            info = (results["account_number"], results["suggested_file_name"][-7:], results["invoice_subtotal"])

        except UnsaveableError as e:
            insert_tuples_in_excel(Global_variables.failed_invoices_excel_path,
                "Sheet1", [(invoice[0], e.message)])
            continue

        except RequestApprovalError as e:
            populate_invoice_numbers(Global_variables.saved_invoices_excel_path,
                "Sheet1", "Invoice Number", [invoice[0]])
            print(f"RequestApprovalError: {invoice[0]}")
            continue

        except PermissionError as e:
            insert_tuples_in_excel(Global_variables.failed_invoices_excel_path,
                "Sheet1", [(invoice[0], "Permission denied")])
            continue

        except AttributeError as e:
            insert_tuples_in_excel(Global_variables.failed_invoices_excel_path,
                                   "Sheet1", [(invoice[0], "Invoice file not found in folder")])
            continue

        except Exception as e:
            insert_tuples_in_excel(Global_variables.failed_invoices_excel_path,
            "Sheet1", [(invoice[0], "Please report this problem to the developer, " + type(e).__name__)])
            print(f"{type(e).__name__}: {invoice[0]}")
            print(str(e))
            continue

        else:
            if info is not None:
                if indicator == 2:
                    print(f"{info[0]} is successfully inputted")
                    insert_tuples_in_excel(Global_variables.succeed_invoices_excel_path,
                        "Sheet1", [info])
                elif indicator == 1:
                    print(f"{info[0]} is successfully requested for funding, and payment is saved as draft")
                    insert_tuples_in_excel(Global_variables.funding_requested_excel_path,
                        "Sheet1", [info])
        finally:
            delete_cell_content_if_matches(Global_variables.todo_invoices_excel_path,
                "Sheet1", "Invoice Number", invoice[0])
    driver.quit()

def pps_single_invoice_input(results, driver=None) -> int:
    """
    :param results:
    :param driver:
    :return: 1 indicates requested funding, 2 indicates requested payment approval
    """
    # Check if amount is greater that the maximum amount threshold
    if convert_to_float(results["amount_due"]) > Global_variables.maximum_payment_amount:
        raise UnsaveableError(results['account_number'], "Exceeds maximum amount threshold")

    # 1. Launch browser (make sure you have installed ChromeDriver or another WebDriver)
    quit_after = False
    if driver is None:
        driver = webdriver.Chrome()
        quit_after = True
        login(driver)

    try:
        # 8. Now that you're logged in, navigate to your actual target URL
        driver.get(TARGET_URL)

        # 9. At this point, you should be in your authenticated session.

        # Wait for the link to be present in the DOM
        wait = WebDriverWait(driver, 10)  # up to 10 seconds

        driver.find_element(By.ID, "contentPlaceHolder_tabControl1_tabA4").click()
        view_update_link = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//a[@class="homeLink" and contains(@href, "AwardTypeId=8")][text()="View/Update"]'
        )))
        # Click the link
        view_update_link.click()

        # Input account number
        account_number_input_bar = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_utilityAccount"))
        )
        account_number_input_bar.clear()
        account_number_input_bar.send_keys(results["account_number"].replace("-", "").replace(" ", ""))

        # Press 'search' for account number
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_pbSearch"))
        ).click()

        # Wait for results table and process rows
        table = wait.until(
            EC.presence_of_element_located((By.ID, "contentPlaceHolder_searchResult"))
        )

        # Get all rows inside the table
        rows = table.find_elements(By.TAG_NAME, "tr")

        approved_rows = []
        for row in rows:
            # Find all cells in the row
            cells = row.find_elements(By.TAG_NAME, "td")

            # We need at least 2 cells: first cell is clickable text, second cell is 'Approved' or 'Completed'
            if len(cells) >= 2:
                status_text = cells[1].text.strip()
                if status_text == "Approved":
                    approved_rows.append(row)

            # Check if exactly one row has 'Approved'
        if len(approved_rows) == 1:
            # Find the first cell of that row and click the clickable link inside it
            row = approved_rows[0]
            # Typically the first cell might contain a link, e.g. <td><a>Clickable Text</a></td>
            first_cell = row.find_elements(By.TAG_NAME, "td")[0]
            clickable_link = first_cell.find_element(By.TAG_NAME, "a")
            clickable_link.click()
            print("Clicked on the only row with 'Approved'.")
        else:
            raise UnsaveableError(results['account_number'], 'Expected to find only one approved account, but found zero or more than one approved account')

        # Check if 'Do not pay' is written in comments
        comments = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_agreementControl_ctl00_description"))
        ).get_attribute("value")
        comments = comments.replace(' ', '').replace('-', '').replace("'", '')
        if 'DONOTPAY' in comments or 'DONTPAY' in comments:
            raise UnsaveableError(results['account_number'], "Found 'Do not pay' in comments")

        # Press 'invoice' to see all invoices
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "tabControl_InvoicesTab_HyperLink"))
        ).click()

        # Check if any payment is pending and if the suggested invoice number exists
        table = wait.until(
            EC.presence_of_element_located((By.ID, "contentPlaceHolder_invoiceControl_invoices"))
        )
        # Get all rows inside the table
        rows = table.find_elements(By.TAG_NAME, "tr")
        asserted_invoice_rows = []
        index = 0
        is_period_checked = False
        for row in rows:
            # Find all cells in the row
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) <= 9:
                continue
            # Check if last element contains text 'Pending Payment'
            # cell contains: invoice number, vendor name, address, city, postal code, amount, currency, date received, cost center, status
            status_text = cells[9].text.strip()
            if status_text == "Pending Payment" and index < 40:
                raise PendingPaymentError(results["account_number"])
            # Check first two asserted invoices, check if they haven't been paid for a long time
            elif status_text == "Asserted":
                asserted_invoice_rows.append(cells)
                if Global_variables.is_period_validation_needed and not is_period_checked and months_since_invoice(cells[0].text.strip()) >= 5:
                    raise UnsaveableError(results["account_number"], "This account haven't been paid for a long time")
                is_period_checked = True

            invoice_number_text = cells[0].text.strip()
            if invoice_number_text.replace("-", "").replace(' ', '') == results["account_number"].replace("-", "").replace(' ', '') + convert_month_abbr(results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:]\
                    and status_text != 'Cancelled':
                raise UnsaveableError(results['account_number'], f"{results['suggested_file_name']} is already exists")
            index += 1

        validate_invoice_amount(results, asserted_invoice_rows)

        # Check if enough funding in account
        indicator = 2
        requested = check_and_request_funding(driver, results)
        if requested:
            indicator = 1

        # Press 'invoice' to see all invoices
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "tabControl_InvoicesTab_HyperLink"))
        ).click()

        # Press 'new invoice' to creat a new invoice
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_invoiceControl_btnNewInvoice"))
        ).click()

        # Input account number
        temp_input_text = results["account_number"].replace("-", "").replace(' ', '') + convert_month_abbr(results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:]
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_txtInvoiceNumber"))
        ).send_keys(temp_input_text)

        # Input period-to
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_workPeriodFrom"))
        ).send_keys(results["period_start_date"]+Keys.ENTER)
        # Input period-from
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_workPeriodTo"))
        ).send_keys(results["period_end_date"]+Keys.ENTER)
        # Input statement period
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_invoiceDate"))
        ).send_keys(results["statement_date"]+Keys.ENTER)
        # Input current date
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_dateReceived"))
        ).send_keys(get_today_date()+Keys.ENTER)
        # Input invoice subtotal
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_summaryInvoiceTotal"))
        ).send_keys(str(results["invoice_subtotal"]))
        # Input H.S.T.
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_summaryHSTTotal"))
        ).send_keys(str(results["hst"]))
        # Input comment.
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_ctl00_commentsBox"))
        ).send_keys(results["suggested_file_name"][-7:-4] + " " + results["suggested_file_name"][-4:])
        # Press 'Line Items' to specify amount detail
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_btnNext"))
        ).click()

        # Press 'Add New Line'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine"))
        ).click()
        # Select amount type
        dropdown_menu = wait.until(
            EC.presence_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription"))
        )
        select_dropdown = Select(dropdown_menu)
        select_dropdown.select_by_visible_text("Electricity")
        # Input amount
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
        ).send_keys(str(results["total_electricity_charges"]).replace(",", ""))
        # Press 'Update'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
        ).click()
        # Check if amount inputted succeed
        elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
        times = 0
        while elements and times < 10:
            time.sleep(0.5)
            print('wait')
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
            ).send_keys(str(results["total_electricity_charges"]).replace(",", ""))
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
            ).click()
            elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
            times += 1

        # Input Late Payment Charges Info
        if results["Late Payment Charge"] is not None and results["Late Payment Charge"] != 0:
            # Press 'Add New Line'
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine"))
            ).click()
            # Select amount type
            dropdown_menu = wait.until(
                EC.presence_of_element_located(
                    (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription"))
            )
            select_dropdown = Select(dropdown_menu)
            select_dropdown.select_by_visible_text("Late Payment Charges")
            # Input amount
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
            ).send_keys(str(results["Late Payment Charge"]).replace(",", ""))
            # Press 'Update'
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
            ).click()
            # Check if amount inputted succeed
            elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
            times = 0
            while elements and times < 10:
                time.sleep(0.5)
                print('wait')
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
                ).send_keys(str(results["Late Payment Charge"]).replace(",", ""))
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
                ).click()
                elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
                times += 1

        # Input Electricity (Tax Exempt) Info
        ETE = round(results["balance_forward"] + results["ontario_electricity_rebate"], 2)
        if ETE is not None and ETE != 0:
            # Press 'Add New Line'
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine"))
            ).click()
            # Select amount type
            dropdown_menu = wait.until(
                EC.presence_of_element_located(
                    (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription"))
            )
            select_dropdown = Select(dropdown_menu)
            select_dropdown.select_by_visible_text("Electricity (Tax Exempt)")
            # Input amount
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
            ).send_keys(ETE)
            # Press 'Update'
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
            ).click()
            # Check if amount inputted succeed
            elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
            times = 0
            while elements and times < 10:
                time.sleep(0.5)
                print('wait')
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount"))
                ).send_keys(ETE)
                # Press 'Update'
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.ID, "contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave"))
                ).click()
                elements = driver.find_elements(By.XPATH, "//li[normalize-space()='Line Amount is mandatory.']")
                times += 1

        # Check if the line items match
        message_text = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "PPSHeader_messageText"))
        )
        if message_text.text.strip() != "The line items total matches the invoice total.":
            raise ExtractedDataUnmatchError(results["account_number"])

        # Press 'Confirmation'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_btnNext"))
        ).click()

        # Press 'Save As Pending Payment'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_btnSaveAsPendingPayment"))
        ).click()

        # Press 'New Payment Certificate'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_TabContainer1_TabPanel4_btnNewPaymentCertificate"))
        ).click()

        # Input comment again
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_paymentCertificateHeader_comments"))
        ).send_keys(results["suggested_file_name"][-7:-4] + " " + results["suggested_file_name"][-4:])

        # Press 'Confirmation'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_btnNext"))
        ).click()

        # Check if 'Confirmation' is clicked successfully
        element = WebDriverWait(driver, 0.5).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_btnNext"))
        )
        times = 0
        while element and times < 20:
            try:
                element.click()
                element = WebDriverWait(driver, 0.5).until(
                    EC.visibility_of_element_located((By.ID, "contentPlaceHolder_btnNext"))
                )
            except:
                pass
            finally:
                time.sleep(0.5)
                times += 1

        # Press 'Save As Draft'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_ContentPlaceHolder1_SavePC"))
        ).click()

        # Press 'Request Approval'
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_TabContainer1_TabPanel4_btnRequestApproval"))
        ).click()

        # Check if the button 'Request Approval' still exists
        error_b_element = None
        try:
            error_b_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contentPlaceHolder_TabContainer1_TabPanel4_btnRequestApproval"))
            )

        except TimeoutException:
            raise UnsaveableError(results['account_number'], 'Web scraping element not found, check account status')

        finally:
            # If error message appears and we did not request for funding
            if error_b_element and indicator == 2:
                raise RequestApprovalError(results["account_number"], )
            return indicator

    finally:
        # 10. Close the browser when done
        if quit_after:
            driver.quit()


def get_remaining_funding(driver, results) -> float:
    """Get the remaining function for the fiscal year which the bill belongs to"""
    remaining = convert_to_float(WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_awardTitle_remaining"))
    ).text.strip())

    # Get current fiscal year
    current_fiscal_year = calculate_fiscal_year(results['statement_date'])
    if current_fiscal_year is None:
        raise UnsaveableError(results['invoice_number'], 'failed to calculate fiscal year')

    # Click 'Financial Information'
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "tabControl_Financials_HyperLink"))
    ).click()

    # Click 'New Adjustment'
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_operationsControl_btnNew"))
    ).click()

    # Wait for the link to be present in the DOM
    wait = WebDriverWait(driver, 10)  # up to 10 seconds

    # Iterate through all fiscal year, calculate the remaining amount for this fiscal year
    table = wait.until(
        EC.presence_of_element_located((By.ID, "contentPlaceHolder_financialControl_distribution_gridFiscal"))
    )

    # Get all rows inside the table
    rows = table.find_elements(By.TAG_NAME, "tr")
    is_future_fiscal_year = False
    for row in rows:
        # Find all cells in the row
        cells = row.find_elements(By.TAG_NAME, "td")

        if len(cells) < 3:
            continue

        if is_future_fiscal_year:
            remaining -= convert_to_float(cells[1].text.strip())
        # Check if the fiscal year is current fiscal year'
        fiscal_year = cells[0].text.strip()
        if fiscal_year == current_fiscal_year:
            is_future_fiscal_year = True

    return round(remaining, 2)

def check_and_request_funding(driver, results) -> bool:
    # Click if funding is in pending
    financial_information_button_text = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "tabControl_Financials_HyperLink"))
    ).text.strip()
    is_funding_in_pending = False
    if financial_information_button_text == 'Financial (Approval Pending)':
        is_funding_in_pending = True

    # Get remaining funding
    remaining_funding = get_remaining_funding(driver, results)

    # Check if funding request is needed
    if convert_to_float(results['amount_due']) <= remaining_funding:
        return False

    if is_funding_in_pending:
        raise UnsaveableError(results['account_number'], 'Funding request is in pending')

    # Calculate the approximate amount needed
    approximate_amount_needed = round((((convert_to_float(results['amount_due']) - convert_to_float(results['balance_forward']))
                                 * min(max(months_to_next_fiscal_period(results['period_start_date']), 1), 6)) - remaining_funding +
                                 convert_to_float(results['balance_forward']))+1.0, 0)
    print(f"amount_due: {results['amount_due']}")
    print(f"balance_forward: {str(results['balance_forward'])}")
    print(f"approximate_amount_needed: {str(approximate_amount_needed)}")

    # Get current fiscal year
    current_fiscal_year = calculate_fiscal_year(results['statement_date'])
    if current_fiscal_year is None:
        raise UnsaveableError(results['invoice_number'], 'failed to calculate fiscal year')

    # Wait for the link to be present in the DOM
    wait = WebDriverWait(driver, 10)  # up to 10 seconds

    # Locate the current fiscal year
    table = wait.until(
        EC.presence_of_element_located((By.ID, "contentPlaceHolder_financialControl_distribution_gridFiscal"))
    )

    # Get all rows inside the table
    rows = table.find_elements(By.TAG_NAME, "tr")

    is_future_fiscal_year = False
    for row in rows:
        # Find all cells in the row
        cells = row.find_elements(By.TAG_NAME, "td")

        if len(cells) < 3:
            continue

        # Check if the fiscal year is current fiscal year'
        fiscal_year = cells[0].text.strip()
        if fiscal_year == current_fiscal_year:
            input_bar = cells[2].find_element(By.TAG_NAME, "input")
            input_bar.send_keys(str(approximate_amount_needed))

    # Input total amount adjustment
    amount_input_bar = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_financialControl_amount"))
    )
    amount_input_bar.clear()
    amount_input_bar.send_keys(str(approximate_amount_needed))

    # Input description
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_financialControl_comments"))
    ).send_keys('ADJ')

    # Click 'Request Approval
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_operationsControl_btnRequestApproval"))
    ).click()

    return True

def validate_invoice_amount(result, asserted_invoice_rows):
    """
    Validates the current invoice amount against historical data.
    Checks for balance forward and significant amount deviations.
    
    Args:
        result (dict): Current invoice data containing 'suggested_file_name' and 'amount_due'
        asserted_invoice_rows (list): List of previous invoice records
        
    Raises:
        UnsavableError: If the invoice amount is significantly higher than historical average
    """
    if not asserted_invoice_rows:
        return  # No historical data to compare against
        
    # Get current invoice date
    current_year, current_month = parse_invoice_date(result['suggested_file_name'])
    
    # Find the latest invoice date from historical data
    latest_date = None
    latest_invoice = None
    for row in asserted_invoice_rows:
        try:
            year, month = parse_invoice_date(row[0].text.strip())
            if latest_date is None or (year > latest_date[0] or 
                (year == latest_date[0] and month > latest_date[1])):
                latest_date = (year, month)
                latest_invoice = row
        except ValueError:
            continue  # Skip invalid invoice numbers
            
    if not latest_invoice:
        return  # No valid historical invoices found
        
    # Check for balance forward
    current_invoice_weight = 1
    months_diff = (current_year - latest_date[0]) * 12 + (current_month - latest_date[1])
    if months_diff > 1:
        current_invoice_weight = months_diff
        print(f"Warning: {months_diff} months gap detected between invoices. "
              f"Current: {current_month}/{current_year}, "
              f"Latest: {latest_date[1]}/{latest_date[0]}")
    
    # Calculate weighted average of last 6 months
    valid_invoices = []
    for row in asserted_invoice_rows:
        try:
            year, month = parse_invoice_date(row[0].text.strip())
            amount = convert_to_float(row[5].text.strip())
            if amount is not None:
                valid_invoices.append({
                    'year': year,
                    'month': month,
                    'amount': amount
                })
        except (ValueError, TypeError):
            continue
    
    if not valid_invoices:
        return  # No valid historical amounts to compare against
    
    # Sort invoices by date
    valid_invoices.sort(key=lambda x: (x['year'], x['month']))
    
    # Take last 6 invoices
    if len(valid_invoices) > 6:
        valid_invoices = valid_invoices[-6:]
    
    # Calculate weights based on gaps between invoices
    weighted_amounts = []
    for i in range(len(valid_invoices)):
        current = valid_invoices[i]
        if i == 0:
            weight = 1
        else:
            # For other invoices, check gap with the previous invoice
            prev_invoice = valid_invoices[i - 1]
            months_from_prev = (current['year'] - prev_invoice['year']) * 12 + (current['month'] - prev_invoice['month'])
            weight = max(1, months_from_prev)  # Weight is at least 1
            
        weighted_amounts.append((current['amount'], weight))
    
    # Calculate weighted average
    total_weight = sum(weight for _, weight in weighted_amounts)
    weighted_sum = sum(amount * weight for amount, weight in weighted_amounts)
    avg_amount = weighted_sum / total_weight if total_weight > 0 else 0
    
    current_amount = convert_to_float(result['amount_due'])
    
    if current_amount is None:
        return  # Current amount is invalid
        
    # Check if current amount is significantly higher than average
    if (current_amount / current_invoice_weight) > avg_amount * Global_variables.average_multiple_threshold:
        raise UnsaveableError(result['account_number'],
            f"Current invoice amount (${current_amount:.2f}) is more than "
            f"{Global_variables.average_multiple_threshold}x the weighted average "
            f"historical amount (${avg_amount:.2f})"
        )

def tester_function(results, driver=None):

    # 1. Launch browser (make sure you have installed ChromeDriver or another WebDriver)
    quit_after = False
    if driver is None:
        driver = webdriver.Chrome()
        quit_after = True
        login(driver)

    try:
        # 8. Now that you're logged in, navigate to your actual target URL
        driver.get(TARGET_URL)

        # 9. At this point, you should be in your authenticated session.

        # Wait for the link to be present in the DOM
        wait = WebDriverWait(driver, 10)  # up to 10 seconds

        driver.find_element(By.ID, "contentPlaceHolder_tabControl1_tabA4").click()
        view_update_link = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            '//a[@class="homeLink" and contains(@href, "AwardTypeId=8")][text()="View/Update"]'
        )))
        # Click the link
        view_update_link.click()

        # Input account number
        account_number_input_bar = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_utilityAccount"))
        )
        account_number_input_bar.clear()
        account_number_input_bar.send_keys(results["account_number"].replace("-", "").replace(" ", ""))

        # Press 'search' for account number
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "contentPlaceHolder_pbSearch"))
        ).click()

        # Wait for results table and process rows
        table = wait.until(
            EC.presence_of_element_located((By.ID, "contentPlaceHolder_searchResult"))
        )

        # Get all rows inside the table
        rows = table.find_elements(By.TAG_NAME, "tr")

        approved_rows = []
        for row in rows:
            # Find all cells in the row
            cells = row.find_elements(By.TAG_NAME, "td")

            # We need at least 2 cells: first cell is clickable text, second cell is 'Approved' or 'Completed'
            if len(cells) >= 2:
                status_text = cells[1].text.strip()
                if status_text == "Approved":
                    approved_rows.append(row)

            # Check if exactly one row has 'Approved'
        if len(approved_rows) == 1:
            # Find the first cell of that row and click the clickable link inside it
            row = approved_rows[0]
            # Typically the first cell might contain a link, e.g. <td><a>Clickable Text</a></td>
            first_cell = row.find_elements(By.TAG_NAME, "td")[0]
            clickable_link = first_cell.find_element(By.TAG_NAME, "a")
            clickable_link.click()
            print("Clicked on the only row with 'Approved'.")
        else:
            raise AccountNumberError(results["account_number"])

        check_and_request_funding(driver, results)
        
         # Press 'invoice' to see all invoices
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "tabControl_InvoicesTab_HyperLink"))
        ).click()

        # Check if any payment is pending and if the suggested invoice number exists
        table = wait.until(
            EC.presence_of_element_located((By.ID, "contentPlaceHolder_invoiceControl_invoices"))
        )
        # Get all rows inside the table
        rows = table.find_elements(By.TAG_NAME, "tr")
        asserted_invoice_rows = []
        index = 0
        is_period_checked = False
        for row in rows:
            # Find all cells in the row
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) <= 9:
                continue
            # Check if last element contains text 'Pending Payment'
            # cell contains: invoice number, vendor name, address, city, postal code, amount, currency, date received, cost center, status
            status_text = cells[9].text.strip()
            if status_text == "Pending Payment" and index < 40:
                raise PendingPaymentError(results["account_number"])
            # Check first two asserted invoices, check if they haven't been paid for a long time
            elif status_text == "Asserted":
                asserted_invoice_rows.append(cells)
                if Global_variables.is_period_validation_needed and not is_period_checked and months_since_invoice(cells[0].text.strip()) >= 5:
                    raise UnsaveableError(results["account_number"], "This account haven't been paid for a long time")
                is_period_checked = True

            invoice_number_text = cells[0].text.strip()
            if invoice_number_text.replace("-", "").replace(' ', '') == results["account_number"].replace("-", "").replace(' ', '') + convert_month_abbr(results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:]\
                    and status_text != 'Cancelled':
                raise UnsaveableError(results['account_number'], f"{results['suggested_file_name']} is already exists")
            index += 1

        validate_invoice_amount(results, asserted_invoice_rows)
    finally:
        if quit_after:
            driver.quit()
