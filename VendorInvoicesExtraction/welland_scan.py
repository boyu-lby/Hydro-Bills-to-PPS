import fitz
import pdfplumber
import re
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month


def parse_welland_bill(pdf_path):
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
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()

    # 1) Account Number
    # Example snippet: "Account Number\n00019232-00"
    match = re.search(r'Account\s*Number\n(\d{5,10}-\d{2})', text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "Amount Due\n2025-01-17"
    match = re.search(r'Amount\s*Due\n(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper()
    year = extracted_data["statement_date"][:4]
    month = extracted_data["statement_date"][5:7]
    date = extracted_data["statement_date"][-2:]
    extracted_data["statement_date"] = month + "/" + date + "/" + year

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'Amount\s*Due\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = match.group(1)

    # 4) Your Total Electricity Charges
    # Example snippet: "TOTAL ELECTRICITY CHARGES\n$120.70"
    match = re.search(r'TOTAL\s*ELECTRICITY\s*CHARGES\n\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text,
                      re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = convert_to_float(match.group(1))

    # 5) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 6) Ontario Electricity Rebate
    # Example snippet: "ONTARIO ELECTRICITY REBATE\n-$15.81"
    match = re.search(r'ONTARIO\s*ELECTRICITY\s*REBATE\n-\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
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
    # Example snippet: "Billing Period: 2024-12-01 to 2025-01-01"
    match = re.search(r'Billing\s*Period:\s*(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(1)
        extracted_data["period_end_date"] = match.group(2)
    year = extracted_data["period_start_date"][:4]
    month = extracted_data["period_start_date"][5:7]
    date = extracted_data["period_start_date"][-2:]
    extracted_data["period_start_date"] = month + "/" + date + "/" + year
    year = extracted_data["period_end_date"][:4]
    month = extracted_data["period_end_date"][5:7]
    date = extracted_data["period_end_date"][-2:]
    extracted_data["period_end_date"] = month + "/" + date + "/" + year

    # 9) Late payment charge
    # Example snippet: "OVERDUE INTEREST\n$0.46"
    match = re.search(r'OVERDUE\s*INTEREST\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))

    # 10) Invoice subtotal = amount_due - h.s.t.
    # Example snippet : "TAXES *HST (863759692RT0001)\n$15.69"
    match = re.search(r'TAXES\s*\*HST\s*\(863759692RT0001\)\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})',
                      text, re.IGNORECASE)
    if match:
        hst = convert_to_float(match.group(1).replace(", ", ""))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(
            format_date_str(
                extracted_data["period_start_date"]))

    # Reformat Dates
    extracted_data["period_start_date"] = switch_date_and_month(extracted_data["period_start_date"])
    extracted_data["period_end_date"] = switch_date_and_month(extracted_data["period_end_date"])
    extracted_data["statement_date"] = switch_date_and_month(extracted_data["statement_date"])


    return extracted_data