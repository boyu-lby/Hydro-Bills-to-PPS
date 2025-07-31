import time
import Global_variables
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api._generated import Error as PlaywrightError

from Excel_helper import read_column_values, populate_invoice_numbers, delete_cell_content_if_matches, \
    insert_tuples_in_excel, read_cell_content_from_first_two_col
from OCR_helper import convert_month_abbr, get_today_date
from VendorInvoicesExtraction.Get_invoice_extraction import get_invoice_extraction_function
from CustomizedExceptions import RequestApprovalError, InvoiceScanError, AmountError, PendingPaymentError, AccountNumberError, ExtractedDataUnmatchError, UnsaveableError
from scan_helper import find_file_with_substring, self_check, copy_as_pdf_in_original_and_destination, convert_to_float, \
    calculate_fiscal_year, months_to_next_fiscal_period, months_since_invoice, parse_invoice_date

TARGET_URL = "https://pps.mto.ad.gov.on.ca/Home.aspx"

def login(page: Page):
    ONTARIO_EMAIL = Global_variables.ontario_email
    ONTARIO_PASSWORD = Global_variables.ontario_password

    # Navigate to Microsoft login page
    page.goto("https://login.microsoftonline.com/")

    # Enter email/username
    page.fill("#i0116", ONTARIO_EMAIL)
    page.click("#idSIButton9")

    # Wait for and fill password if needed
    try:
        page.wait_for_selector("#passwd", timeout=10000)
        page.fill("#passwd", ONTARIO_PASSWORD)
        page.click("#idSIButton9")
    except PlaywrightTimeoutError:
        print("Password field did not appear; continuing...")

    # Handle "Stay signed in?" screen
    try:
        page.wait_for_selector("#idSIButton9", timeout=10000)
        page.click("#idSIButton9")
    except PlaywrightTimeoutError:
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
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Set False to see the browser window
            slow_mo=100  # Slow down operations by 100ms for better visibility
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}  # Set a large viewport
        )
        page = context.new_page()
        # Set the page to scrollable
        page.add_init_script("""
            document.documentElement.style.overflow = 'auto';
            document.body.style.overflow = 'auto';
            document.body.style.minHeight = '100vh';
        """)
        # Login Microsoft account
        login(page)

        succeed_invoices = []

        agreementNumberMap = {
            "Alectra": "2025-M-0002",
            "Burlington Hydro": "2025-M-0014",
            "Elexicon": "2025-M-0003",
            "Fortis": "2025-M-0022",
            "Grimsby": "2025-M-0012",
            "NPE": "2025-M-0004",
            "Oakville": "2025-M-0008",
            "Toronto Hydro": "2025-M-0006",
            "Welland": "2025-M-0011",
        }

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
                indicator = pps_single_invoice_input(results, agreementNumberMap[invoice[1]], page)

                # Rename the PDF, save into "Temp Hydro Invoices"
                copy_as_pdf_in_original_and_destination(pdf_file_path,
                                                        Global_variables.renamed_invoices_dir_path,
                                                        results["suggested_file_name"])

                info = (results["account_number"], results["suggested_file_name"][-7:], results["invoice_subtotal"], results["amount_due"])

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
        context.close()
        browser.close()

def pps_single_invoice_input(results, agreementNumber:str, page: Page = None) -> int:
    """
    :param results: Invoice data
    :param agreementNumber: agreement number for the summary billing
    :param page: Playwright page object
    :return: 1 indicates requested funding, 2 indicates requested payment approval
    """

    # Launch browser if not provided
    quit_after = False
    if page is None:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # Set to False to see the browser window
                slow_mo=100  # Slow down operations by 100ms for better visibility
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}  # Set a large viewport
            )
            page = context.new_page()
            quit_after = True
            login(page)

    try:
        # Navigate to target URL and wait for network to be idle
        page.goto(TARGET_URL, wait_until="networkidle")

        # Click on the tab and view/update link
        page.click("#contentPlaceHolder_tabControl1_tabA4")
        page.wait_for_load_state("networkidle")
        
        # Wait for and click the view/update link
        page.wait_for_selector('//a[@class="homeLink" and contains(@href, "AwardTypeId=8")][text()="View/Update"]')
        page.click('//a[@class="homeLink" and contains(@href, "AwardTypeId=8")][text()="View/Update"]')
        page.wait_for_load_state("networkidle")

        # Input account number and wait for the input to be ready
        page.wait_for_selector("#contentPlaceHolder_awardNumber")
        page.fill("#contentPlaceHolder_awardNumber", agreementNumber)

        # Press search and wait for results
        page.click("#contentPlaceHolder_pbSearch")
        page.wait_for_load_state("networkidle")

        # Process search results
        page.wait_for_selector("#contentPlaceHolder_searchResult")
        table = page.query_selector("#contentPlaceHolder_searchResult")
        if not table:
            raise UnsaveableError(results['account_number'], "Search results table not found")

        # Get all rows inside the table
        rows = table.query_selector_all("tr")
        approved_rows = []
        
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 2:
                status_text = cells[1].inner_text().strip()
                if status_text == "Approved":
                    approved_rows.append(row)

        if len(approved_rows) == 1:
            # Wait for the link to be clickable
            link = approved_rows[0].query_selector("td a")
            if not link:
                raise UnsaveableError(results['account_number'], "Approved row link not found")
            link.click()
            page.wait_for_load_state("networkidle")
            print("Clicked on the only row with 'Approved'.")
        else:
            raise UnsaveableError(results['account_number'], 'Expected to find only one approved account, but found zero or more than one approved account')

        # Check comments
        page.wait_for_selector("#contentPlaceHolder_agreementControl_ctl00_description")
        comments = page.locator("#contentPlaceHolder_agreementControl_ctl00_description").input_value()
        comments = comments.replace(' ', '').replace('-', '').replace("'", '')
        if 'DONOTPAY' in comments or 'DONTPAY' in comments:
            raise UnsaveableError(results['account_number'], "Found 'Do not pay' in comments")

        # Press 'invoice' to see all invoices
        page.click("#tabControl_InvoicesTab_HyperLink")
        page.wait_for_load_state("networkidle")

        # Check if any payment is pending and if the suggested invoice number exists
        page.wait_for_selector("#contentPlaceHolder_invoiceControl_invoices")
        table = page.query_selector("#contentPlaceHolder_invoiceControl_invoices")
        if not table:
            raise UnsaveableError(results['account_number'], "Invoice table not found")

        rows = table.query_selector_all("tr")
        index = 0
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) <= 9:
                continue

            invoice_number_text = cells[0].inner_text().strip()
            invoice_name = results["account_number"].replace("-", "").replace(' ', '') + convert_month_abbr(
                results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:]
            status_text = cells[5].inner_text().strip()
            if invoice_number_text.replace("-", "").replace(' ', '') == invoice_name and status_text != 'Cancelled':
                raise UnsaveableError(results['account_number'], f"{invoice_name} is already exists in PPS")
            index += 1

        # Check if enough funding in account
        indicator = 2
        requested = check_and_request_funding(page, results)
        if requested:
            indicator = 1

        # Press 'invoice' to see all invoices
        page.click("#tabControl_InvoicesTab_HyperLink")

        # Press 'new invoice' to creat a new invoice
        page.click("#contentPlaceHolder_invoiceControl_btnNewInvoice")

        # Input account number
        temp_input_text = results["account_number"].replace("-", "").replace(' ', '') + convert_month_abbr(results["suggested_file_name"][-7:-4]) + results["suggested_file_name"][-2:]
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_txtInvoiceNumber", temp_input_text)

        # Input period-to
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_workPeriodFrom", results["period_start_date"] + "\n")
        # Input period-from
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_workPeriodTo", results["period_end_date"] + "\n")
        # Input statement period
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_invoiceDate", results["statement_date"] + "\n")
        # Input current date
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_dateReceived", get_today_date() + "\n")
        # Input invoice subtotal
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_summaryInvoiceTotal", str(results["invoice_subtotal"]))
        # Input H.S.T.
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_summaryHSTTotal", str(results["hst"]))
        # Input comment.
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_ctl00_commentsBox", results["suggested_file_name"][-7:-4] + " " + results["suggested_file_name"][-4:])
        # Press 'Line Items' to specify amount detail
        page.click("#contentPlaceHolder_btnNext")

        # Press 'Add New Line'
        page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine")
        # Select amount type
        dropdown_menu = page.query_selector("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription")
        dropdown_menu.select_option("Electricity")
        # Input amount
        page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(results["total_electricity_charges"]).replace(",", ""))
        # Press 'Update'
        page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
        # Check if amount inputted succeed
        elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
        times = 0
        while elements and times < 10:
            time.sleep(0.5)
            print('wait')
            page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(results["total_electricity_charges"]).replace(",", ""))
            page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
            elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
            times += 1

        # Input Late Payment Charges Info
        if results["Late Payment Charge"] is not None and results["Late Payment Charge"] != 0:
            # Press 'Add New Line'
            page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine")
            # Select amount type
            select_dropdown = page.query_selector("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription")
            select_dropdown.select_option("Late Payment Charges")
            # Input amount
            page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(results["Late Payment Charge"]).replace(",", ""))
            # Press 'Update'
            page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
            # Check if amount inputted succeed
            elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
            times = 0
            while elements and times < 10:
                time.sleep(0.5)
                print('wait')
                page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(results["Late Payment Charge"]).replace(",", ""))
                page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
                elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
                times += 1

        # Input Electricity (Tax Exempt) Info
        ETE = round(results["balance_forward"] + results["ontario_electricity_rebate"], 2)
        if ETE is not None and ETE != 0:
            # Press 'Add New Line'
            page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_newLine")
            # Select amount type
            select_dropdown = page.query_selector("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_accountDescription")
            select_dropdown.select_option("Electricity (Tax Exempt)")
            # Input amount
            page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(ETE))
            # Press 'Update'
            page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
            # Check if amount inputted succeed
            elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
            times = 0
            while elements and times < 10:
                time.sleep(0.5)
                print('wait')
                page.fill("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_amount", str(ETE))
                # Press 'Update'
                page.click("#contentPlaceHolder_ContentPlaceHolder1_invoiceLines_btnSave")
                elements = page.query_selector_all("//li[normalize-space()='Line Amount is mandatory.']")
                times += 1

        # Check if the line items match
        message_text = page.query_selector("#PPSHeader_messageText")
        if message_text.inner_text().strip() != "The line items total matches the invoice total.":
            raise ExtractedDataUnmatchError(results["account_number"])

        # Press 'Confirmation'
        page.click("#contentPlaceHolder_btnNext")

        # Press 'Save As Pending Payment'
        page.click("#contentPlaceHolder_ContentPlaceHolder1_btnSaveAsPendingPayment")

        
        # Check if the button 'Request Approval' still exists
        error_b_element = None
        try:
            error_b_element = page.query_selector("#contentPlaceHolder_TabContainer1_TabPanel4_btnRequestApproval")

        except PlaywrightTimeoutError:
            raise UnsaveableError(results['account_number'], 'Web scraping element not found, check account status')

        finally:
            # If error message appears and we did not request for funding
            if error_b_element and indicator == 2:
                raise RequestApprovalError(results["account_number"], )
            return indicator

    except PlaywrightError as e:
        print(f"Playwright error occurred: {str(e)}")
        raise UnsaveableError(results['account_number'], f"Browser automation error: {str(e)}")
    finally:
        if quit_after:
            page.close()
            context.close()
            browser.close()


def get_remaining_funding(page: Page, results) -> float:
    """Get the remaining function for the fiscal year which the bill belongs to"""
    remaining = convert_to_float(retrying_find_element(page, "#contentPlaceHolder_awardTitle_remaining").inner_text().strip())

    # Click 'Financial Information'
    page.click("#tabControl_Financials_HyperLink")

    # Click 'New Adjustment'
    page.click("#contentPlaceHolder_operationsControl_btnNew")

    # Wait for the link to be present in the DOM
    wait = page.wait_for_selector("#contentPlaceHolder_financialControl_distribution_gridFiscal", timeout=10000)

    # Iterate through all fiscal year, calculate the remaining amount for this fiscal year
    # Get current fiscal year
    current_fiscal_year = 0
    for attempt in range(2):
        try:
            table = page.query_selector("#contentPlaceHolder_financialControl_distribution_gridFiscal")
            rows = table.query_selector_all("tr")
            break  # success, exit loop
        except PlaywrightTimeoutError:
            if attempt < 2 - 1:
                time.sleep(1)  # optional: wait a bit before retrying
            else:
                raise  # re-raise if last attempt
    for row in rows[1:]:
        # Find all cells in the row
        cells = row.query_selector_all("td")
        input_elements = cells[2].query_selector_all("input")
        if input_elements:
            current_fiscal_year = cells[0].inner_text().strip()
            break
    if current_fiscal_year == 0:
        raise UnsaveableError(results['account_number'], 'Unable to find current fiscal year. Please contact the developer for this problem')

    # Get all rows inside the table
    is_future_fiscal_year = False
    for row in rows:
        # Find all cells in the row
        cells = row.query_selector_all("td")

        if len(cells) < 3:
            continue

        if is_future_fiscal_year:
            remaining -= convert_to_float(cells[1].inner_text().strip())
        # Check if the fiscal year is current fiscal year'
        fiscal_year = cells[0].inner_text().strip()
        if fiscal_year == current_fiscal_year:
            is_future_fiscal_year = True

    return round(remaining, 2)

def check_and_request_funding(page: Page, results) -> bool:
    # Check if funding is in pending
    financial_information_button_text = retrying_find_element(page, "#tabControl_Financials_HyperLink").inner_text().strip()
    is_funding_in_pending = False
    if financial_information_button_text == 'Financial (Approval Pending)':
        is_funding_in_pending = True

    if is_funding_in_pending:
        raise UnsaveableError(results['account_number'], 'Funding request is in pending')

    # Get remaining funding
    remaining_funding = get_remaining_funding(page, results)

    # Check if funding request is needed
    if convert_to_float(results['amount_due']) <= remaining_funding:
        return False

    # Calculate the approximate amount needed
    n_months = min(max(months_to_next_fiscal_period(results['period_start_date']) if Global_variables.is_auto_months_calculation_enabled else Global_variables.auto_months_threshold, 1), 6)
    print(f"n_months = {n_months}")
    approximate_amount_needed = round((((convert_to_float(results['amount_due']) - convert_to_float(results['balance_forward'])) * n_months)
                                   - remaining_funding + convert_to_float(results['balance_forward']))+1.0, 0)
    print(f"amount_due: {results['amount_due']}")
    print(f"balance_forward: {str(results['balance_forward'])}")
    print(f"approximate_amount_needed: {str(approximate_amount_needed)}")

    # Wait for the link to be present in the DOM
    wait = page.wait_for_selector("#contentPlaceHolder_financialControl_distribution_gridFiscal", timeout=10000)

    table = wait.query_selector("#contentPlaceHolder_financialControl_distribution_gridFiscal")

    # Get current fiscal year
    current_fiscal_year = 0
    rows = table.query_selector_all("tr")
    for row in rows[1:]:
        # Find all cells in the row
        cells = row.query_selector_all("td")
        input_elements = cells[2].query_selector_all("input")
        if input_elements:
            current_fiscal_year = cells[0].inner_text().strip()
            break
    if current_fiscal_year == 0:
        raise UnsaveableError(results['account_number'], 'Unable to find current fiscal year. Please contact the developer for this problem')

    is_future_fiscal_year = False
    for row in rows:
        # Find all cells in the row
        cells = row.query_selector_all("td")

        if len(cells) < 3:
            continue

        # Check if the fiscal year is current fiscal year'
        fiscal_year = cells[0].inner_text().strip()
        if fiscal_year == current_fiscal_year:
            input_bar = cells[2].query_selector("input")
            input_bar.fill(str(approximate_amount_needed))

    # Input total amount adjustment
    amount_input_bar = retrying_find_element(page, "#contentPlaceHolder_financialControl_amount")
    amount_input_bar.fill(str(approximate_amount_needed))

    # Input description
    retrying_find_element(page, "#contentPlaceHolder_financialControl_comments", "ADJ")

    # Click 'Request Approval
    page.click("#contentPlaceHolder_operationsControl_btnRequestApproval")

    return True


def retrying_find_element(page: Page, selector: str, timeout: int = 10000, max_attempts: int = 3):
    """Playwright version of retrying element finder"""
    attempts = 0
    while attempts < max_attempts:
        try:
            element = page.wait_for_selector(selector, timeout=timeout)
            return element
        except PlaywrightTimeoutError:
            attempts += 1
            if attempts < max_attempts:
                time.sleep(1)
                print(f"Attempt {attempts} failed to find element {selector}, retrying...")
        except PlaywrightError as e:
            print(f"Unexpected error while finding element {selector}: {str(e)}")
            raise

    raise PlaywrightTimeoutError(f"Failed to find element {selector} after {max_attempts} attempts")

