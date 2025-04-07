import re
import fitz

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month, \
    convert_date_from_full, get_prev_month_dates


def parse_milton_bill(pdf_path):
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
        "hst": None,
        "total_electricity_charges": None,
        "Late Payment Charge": 0,
        "ontario_electricity_rebate": 0,
        "balance_forward": 0,
        "amount_due": None,
        "suggested_file_name" : None
    }

    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()

    print(text)

    # 1) Account Number
    match = re.search(r'Account\s*Number:\s*(\d{5,10}-\d{2})', text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1)

    # 2) Statement Date
    match = re.search(r'This statement was issued on:\s*([A-Za-z]{3} \d{2}, \d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = convert_date(match.group(1).replace(',', ''))

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'Amount\s*Due\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = match.group(1)


    # 4) Your Total Electricity Charges
    match = re.search(r'Electric Charges\n\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = convert_to_float(match.group(1))
    match = re.search(r'Delivery\n\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] += convert_to_float(match.group(1))
    match = re.search(r'Regulatory Charges\n\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] += convert_to_float(match.group(1))


    # 5) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 6) Ontario Electricity Rebate
    # Example snippet: "ONTARIO ELECTRICITY REBATE\n-$15.81"
    match = re.search(r'Ontario Electricity Rebate\s*\(\$(\d{1,3}(?:,\d{3})*\.\d{1,2})\)', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1).replace(", ", "")) * -1

    # 7) Balance Forward
    # Example snippet: "BALANCE FORWARD (Due Now)\n$117.68"
    match = re.search(r'BALANCE\s*FORWARD\s*\(Due Now\)\n(-)?\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        # The numeric part (e.g. '19,299.99')
        amount_str = match.group(2)
        # Remove commas and convert to float
        amount_val = convert_to_float(amount_str)

        # Check if '-' was captured
        if match.group(1) is not None:
            # If '-' is present, multiply by -1
            amount_val *= -1

        extracted_data["balance_forward"] = amount_val

    # 8) Period
    # Example snippet: "For the period of: Dec 24, 2024 - Jan 28, 2025"
    match = re.search(r'For the period of:\s*([A-Za-z]{3} \d{2}, \d{4}) - ([A-Za-z]{3} \d{2}, \d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = convert_date(match.group(1).replace(',', ''))
        extracted_data["period_end_date"] = convert_date(match.group(2).replace(',', ''))

    # 9) Late payment charge
    # Example snippet: "OVERDUE INTEREST\n$0.46"
    match = re.search(r'OVERDUE\s*INTEREST\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))

    # 10) Invoice subtotal = amount_due - h.s.t.
    # Example snippet : "H.S.T. #895730216RT $15.69"
    match = re.search(r'H\.S\.T\. #895730216RT\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})',
                      text, re.IGNORECASE)
    if match:
        hst = convert_to_float(match.group(1).replace(", ", ""))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(format_date_str(switch_date_and_month(extracted_data["period_start_date"])))


    return extracted_data
