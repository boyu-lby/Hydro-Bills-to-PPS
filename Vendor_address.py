from selenium.common import TimeoutException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import Global_variables

TARGET_URL = "https://pps.mto.ad.gov.on.ca/Home.aspx"

def login(driver):
    ONTARIO_EMAIL = "Boyu.Li@ontario.ca"
    ONTARIO_PASSWORD = "Vbybyvbyby200!"

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

def vendorAddressChangeMulti(account_numbers: list[str], address: str, comments: str):
    # Login in
    driver = webdriver.Chrome()
    login(driver)

    succeed_accounts = []
    failed_accounts = []

    for account in account_numbers:
        if account == "":
            failed_accounts.append(account)
            continue

        result_indicator = vendorAddressChangeSingle(driver, str(account), address, comments)
        if result_indicator in [-1, 0]:
            failed_accounts.append(account)
        elif result_indicator == 1:
            succeed_accounts.append(account)

    # Print result
    print(f"Succeed accounts: {succeed_accounts}.\nFailed accounts: {failed_accounts}.")

def vendorAddressChangeSingle(driver, account_number: str, address: str, comments: str):
    """

    :param comments:
    :param address:
    :param driver:
    :param account_number:
    :return: -1 failed, 0 pending, 1 succeed
    """
    driver.get(TARGET_URL)

    # Wait for the link to be present in the DOM
    wait = WebDriverWait(driver, 10)  # up to 10 seconds

    driver.find_element(By.ID, "contentPlaceHolder_tabControl1_tabA4").click()
    view_update_link = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        '//a[@class="homeLink" and contains(@href, "AwardTypeId=8")][text()="View/Update"]'
    )))

    # Store the current window handle
    original_window = driver.current_window_handle

    # Click the link
    view_update_link.click()

    # Input account number
    account_number_input_bar = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_utilityAccount"))
    )
    account_number_input_bar.clear()
    account_number_input_bar.send_keys(account_number.replace("-", "").replace(" ", ""))

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
        return -1

    # Check if any change in vendor tab is pending
    vendor_button_text = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "tabControl_Vendors_HyperLink"))
    ).text.strip()
    if vendor_button_text == "Vendors (Change Pending)":
        return 0

    # Click on vendor tab
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "tabControl_Vendors_HyperLink"))
    ).click()

    # Click on the telescope icon
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_vendorManagementControl_pendingVendor_pbSelectVendor"))
    ).click()

    # Switch to the new window
    for window_handle in driver.
        if window_handle != original_window:
            driver.switch_to.window(window_handle)
            break

    # Input address
    account_number_input_bar = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_address"))
    )
    account_number_input_bar.clear()
    account_number_input_bar.send_keys(address)

    # Input vendor number
    account_number_input_bar = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_vendorNumber"))
    )
    account_number_input_bar.clear()
    account_number_input_bar.send_keys('8847')

    # Click on the search button
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_pbSearch"))
    ).click()

    # search for the Maintenance one
    table = wait.until(
        EC.presence_of_element_located((By.ID, "contentPlaceHolder_searchResult"))
    )
    # Get all rows inside the table
    rows = table.find_elements(By.TAG_NAME, "tr")
    isMNTNCFound =False
    for row in rows:
        # Find all cells in the row
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) <= 6:
            continue
        site_code = cells[2].text.strip()
        if site_code == "MNTNC - 500 COM":
            first_cell = row.find_elements(By.TAG_NAME, "td")[0]
            clickable_link = first_cell.find_element(By.TAG_NAME, "a")
            clickable_link.click()
            isMNTNCFound = True
            continue
    if not isMNTNCFound:
        return -1

    # Switch to the original window
    driver.switch_to.window(original_window)

    # Input comments
    account_number_input_bar = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "contentPlaceHolder_vendorManagementControl_changeReason"))
    )
    account_number_input_bar.clear()
    account_number_input_bar.send_keys(comments)

    # Submit the request
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "contentPlaceHolder_operationsControl_btnVendorChange"))).click()
    return 1