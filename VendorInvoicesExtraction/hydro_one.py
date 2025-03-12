import pdfplumber
import re
import fitz

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month, \
    convert_date_from_full, get_prev_month_dates


def parse_hydro_one_bill(pdf_path):
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

    print(text)

    def check_for_cr(amount, cr=None):
        # The numeric part (e.g. '19,299.99')
        amount_str = amount
        # Remove commas and convert to float
        amount_val = convert_to_float(amount_str.replace(',', ''))

        # Check if ' CR' was captured
        if cr is not None:
            # If ' CR' is present, multiply by -1
            amount_val *= -1
        return amount_val

    # I defined the blue invoice as format A, the red one as format B

    # 1) Account Number
    match = re.search(r"Your account number[ is]?:\s*((?:\d\s*)*)", text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper().replace(' ', '').replace('\n', '')

    # 2) Statement Date
    match = re.search(r'This statement is issued on:\s*([A-Za-z]{3,10}\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
    if match:
        isFormatA = True
        extracted_data["statement_date"] = convert_date_from_full(match.group(1).upper())
    else:
        isFormatA = False
        match = re.search(r'Billing date:\s*([A-Za-z]{3,10}\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
        if match:
            extracted_data["statement_date"] = match.group(1).replace(',', '')

    # 3) Amount Due
    if isFormatA:
        match = re.search(r'What do I owe\?\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if match:
            extracted_data["amount_due"] = convert_to_float(match.group(1).replace(",", ""))
    else:
        match = re.search(r'Total amount you owe\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
        if match:
            amount_val = check_for_cr(match.group(1), match.group(2))
            extracted_data["amount_due"] = amount_val

    # 4) Ontario Electricity Rebate
    match = re.search(r'ONTARIO\s*ELECTRICITY\s*REBATE\s*\.*\s*(-?\$\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1

    # 9) Late Payment Charge
    match = re.search(r"Your Adjustments\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))

    # 5) Total Electricity Charges
    subtotal_text = 0
    if isFormatA:
        subtotal_raw_text = re.search(r'Total of your electricity charges\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if subtotal_raw_text:
            subtotal_text = convert_to_float(subtotal_raw_text.group(1))
        hst_raw_text = re.search(r'HST \(87086-5821-RT0001\)\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if hst_raw_text:
            subtotal_text -= convert_to_float(hst_raw_text.group(1))
        rebate_raw_text = re.search(r'Ontario Electricity Rebate\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if rebate_raw_text:
            subtotal_text -= convert_to_float(rebate_raw_text.group(1))
        extracted_data["total_electricity_charges"] = round(subtotal_text, 2)
    else:
        subtotal_raw_text = re.search(r'Total of your electricity charges\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if subtotal_raw_text:
            subtotal_text = convert_to_float(subtotal_raw_text.group(1))
        hst_raw_text = re.search(r'HST \(87086-5821-RT0001\)\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
        if hst_raw_text:
            subtotal_text -= check_for_cr(hst_raw_text.group(1), hst_raw_text.group(2))
        rebate_raw_text = re.search(r'Ontario Electricity Rebate\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
        if rebate_raw_text:
            subtotal_text -= check_for_cr(rebate_raw_text.group(1), rebate_raw_text.group(2))
        extracted_data["total_electricity_charges"] = round(subtotal_text, 2)

    # 6) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 7) Balance Forward
    # Example snippet: "Balance forward $0.00"
    if isFormatA:
        match = re.search(r'Balance carried forward from previous statement\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
        if match:
            extracted_data["balance_forward"] = convert_to_float(match.group(1))
    else:
        match = re.search(r'Balance forward\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
        if match:
            amount_val = check_for_cr(match.group(1), match.group(2))
            extracted_data["balance_forward"] += amount_val
        match = re.search(r'Total adjustments\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
        if match:
            amount_val = check_for_cr(match.group(1), match.group(2))
            extracted_data["balance_forward"] += amount_val

    # 8) Period
    match = re.search(r"For the period of:\s*([A-Za-z]{3,10}\s*\d{1,2},\s*\d{4}) - ([A-Za-z]{3,10}\s*\d{1,2},\s*\d{4})", text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = convert_date_from_full(match.group(1).upper())
        extracted_data["period_end_date"] = convert_date_from_full(match.group(2).upper())
    else:
        extracted_data["period_start_date"], extracted_data["period_end_date"] = get_prev_month_dates(extracted_data['statement_date'])

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'HST \(87086-5821-RT0001\)\s*\.*\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match and extracted_data["amount_due"]:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(format_date_str(switch_date_and_month(extracted_data["period_start_date"])))

    # Reformat the dates
    extracted_data['period_start_date'] = extracted_data['period_start_date']
    extracted_data['period_end_date'] = extracted_data['period_end_date']
    extracted_data['statement_date'] = extracted_data['statement_date']

    # Return or print the extracted data
    return extracted_data