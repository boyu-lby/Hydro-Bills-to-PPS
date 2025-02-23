import pdfplumber
import re

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float


def parse_toronto_hydro_bill(pdf_path):
    """
    Parse the hydro bill PDF and extract key fields:
    - Account Number
    - Statement Date
    - Amount Due
    - Your Total Electricity Charges
    - H.S.T.
    - Invoice Subtotal
    - Late Payment Charge
    - Ontario Electricity Rebate
    - Balance Forward
    - Period Start Date
    - Period End Date
    """
    # Initialize a dictionary to store extracted data
    extracted_data = {
        "account_number": None,
        "period_start_date": None,
        "period_end_date": None,
        "statement_date": None,
        "invoice_subtotal": None,
        "hst": 0,
        "total_electricity_charges": None,
        "Late Payment Charge": 0,
        "ontario_electricity_rebate": 0,
        "balance_forward": 0,
        "amount_due": None,
        "suggested_file_name" : None
    }

    with pdfplumber.open(pdf_path) as pdf:
        # If your data is always on page 1, just reference pdf.pages[0].
        page = pdf.pages[0]
        # ---------------------------------------------------------------------
        # 1) ACCOUNT NUMBER BY CROPPING
        #    Suppose we know that “Account Number” text and the actual number
        #    are in a region from x=50 to x=300, y=100 to y=150.
        #    (Coordinates will differ in your PDF.)
        # ---------------------------------------------------------------------
        account_bbox = (50, 100, 300, 150)
        cropped_account = page.crop(account_bbox)

        # Extract the text in that region
        account_text = cropped_account.extract_text() or ""

        # Now parse the text. Possibly the text is something like:
        #   "Account Number\n5697020993"
        # or "5697020993\nAccount Number"
        # so we can search for a sequence of digits near the phrase “Account Number”.
        match = re.search(r'(\d{8,})', account_text)  # capture a big chunk of digits
        if match:
            extracted_data["account_number"] = match.group(1)

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    # 2) Statement Date
    # Example snippet: "Statement Date Dec 11 2024"
    match = re.search(r'Statement\s*Date\s*([A-Za-z]{3}\s*\d{1,2}\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper()

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'Amount\s*Due\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = match.group(1)

    # 4) Your Total Electricity Charges
    # Example snippet: "Your Total Electricity Charges 82.72"
    electricity_sum = 0
    for match in re.finditer(r'Your\s*Total\s*Electricity\s*Charges\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE):
        amount_str = match.group(1)
        # Remove commas and convert to float
        amount_val = float(amount_str.replace(',', ''))
        electricity_sum += float(amount_val)
    if electricity_sum != 0:
        extracted_data["total_electricity_charges"] = electricity_sum

    # 5) H.S.T.
    # Example snippet: "H.S.T. 10.75" or "H.S.T. (H.S.T. Registration 895...) 10.75"
    # We'll capture the number. You might refine this if the text includes extra info on the same line.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 6) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate 10.84 CR"
    # The actual amount might come before "CR", so we can capture the numeric portion.
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1
    if extracted_data["ontario_electricity_rebate"] == 0:
        match = re.search(r'Total\s*Ontario\s*support:\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if match:
            extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1

    # 7) Balance Forward
    # Example snippet: "Balance Forward 85.97"
    match = re.search(r'Balance\s*Forward\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
    if match:
        # The numeric part (e.g. '19,299.99')
        amount_str = match.group(1)
        # Remove commas and convert to float
        amount_val = float(amount_str.replace(',', ''))

        # Check if ' CR' was captured
        if match.group(2) is not None:
            # If ' CR' is present, multiply by -1
            amount_val *= -1

        extracted_data["balance_forward"] = amount_val

    # 8) Period
    # Example snippet: "NOV 07 2024 TO DEC 05 2024"
    pattern = r'([A-Za-z]{3}\s*\d{1,2}\s*\d{4})\s*TO\s*([A-Za-z]{3}\s*\d{1,2}\s*\d{4})'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(1)
        extracted_data["period_end_date"] = match.group(2)

    # 9) Late payment charge
    # Example snippet: "Late Payment Charge 85.97"
    match = re.search(r'Late\s*Payment\s*Charge\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = match.group(1)

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'H\.S\.T\.\s*\(?[^\)]*\)?\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(extracted_data["period_start_date"])

    extracted_data["period_start_date"] = convert_date(extracted_data["period_start_date"])
    extracted_data["period_end_date"] = convert_date(extracted_data["period_end_date"])
    extracted_data["statement_date"] = convert_date(extracted_data["statement_date"])

    # Return or print the extracted data
    return extracted_data