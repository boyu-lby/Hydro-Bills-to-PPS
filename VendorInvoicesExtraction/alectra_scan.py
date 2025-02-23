import pdfplumber
import re
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month, convert_date_from_full


def parse_alectra_bill(pdf_path):
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
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    # 1) Account Number
    # Example snippet: "Account Number: 4062320000"
    match = re.search(r'Account\s*Number:*\s*(\d{9,13})', text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "Statement Date January 29, 2025"
    match = re.search(r'Statement\s*Date\s*([A-Za-z]{3,10}\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper()

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'Amount\s*Due\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = convert_to_float(match.group(1))

    # 4) Your Total Electricity Charges
    # Example snippet: "Your Total Electricity Charges 82.72"
    match = re.search(r'Your\s*Total\s*Electricity\s*Charges\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = convert_to_float(match.group(1))

    # 5) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 6) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate $16.01"
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1

    # 7) Balance Forward
    # Example snippet 1: "Balance Forward $85.97"
    # Example snippet 2: "Balance Forward - IF LATE PAY IMMEDIATELY $688.99"
    match = re.search(r'Balance\s*Forward\s*[a-zA-Z-\s]{0,30}\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
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
    # Example snippet: "12/23/2024 01/23/2025"
    match = re.search(r'(\d{2}/\d{2}/\d{4})\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(1)
        extracted_data["period_end_date"] = match.group(2)

    # 9) Late payment charge
    # Example snippet: "Penalty Adjustment $0.64"
    match = re.search(r'Penalty\s*Adjustment\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = float(match.group(1))

    # 10) Invoice subtotal = amount_due - h.s.t.
    # Example snippet : "H.S.T. (H.S.T. Registration 728604299) $15.88"
    match = re.search(r'H\.S\.T\.\s*\(H\.S\.T\.\s*Registration\s*728604299\)\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(format_date_str(
            extracted_data["period_start_date"]))

    # 12) standardize date format to 'dd/mm/yyyy':
    extracted_data["period_start_date"] = switch_date_and_month(extracted_data["period_start_date"])
    extracted_data["period_end_date"] = switch_date_and_month(extracted_data["period_end_date"])
    extracted_data["statement_date"] = convert_date_from_full(extracted_data["statement_date"])

    return extracted_data