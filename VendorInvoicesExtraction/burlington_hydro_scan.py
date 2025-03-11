import pdfplumber
import re

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float


def parse_burlington_hydro_bill(pdf_path):
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

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

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

    # 1) Account Number
    # Example snippet: "Account Number: 106703-0001284"
    match = re.search(r"Account\s*Number:\s*(\d{6}-\d{7})", text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()


    # 2) Statement Date
    # Example snippet: "Statement Date Dec 11 2024"
    match = re.search(r'Statement\s*Date:\s*([A-Za-z]{3}\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper().replace(",", "")

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'TOTAL\s*AMOUNT\s*DUE\s*[A-Za-z]{3}\s*\d{1,2},\s*\d{4}\s*\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(\s*CR)?', text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["amount_due"] = amount_val

    # 5) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate 10.84 CR" OR "Monthly Deposit Interest 33.38CR"
    # The actual amount might come before "CR", so we can capture the numeric portion.
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1
    match = re.search(r'Monthly\s*Deposit\s*Interest\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        if extracted_data["ontario_electricity_rebate"]:
            extracted_data["ontario_electricity_rebate"] += convert_to_float(match.group(1)) * -1
        else:
            extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1)) * -1


    # 4) Total Electricity Charges
    # Example snippet: "Total Electricity Charges $82.72"
    match = re.search(r'Total\s*Electricity\s*Charges\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    hst_text = re.search(r'H\.S\.T\.\s*REG\.#\s*86829\s*1980\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = round((convert_to_float(match.group(1).replace(',', '')) -
                                                       convert_to_float(hst_text.group(1)) - extracted_data["ontario_electricity_rebate"]), 2)

    # 6) H.S.T.
    # Example snippet: "H.S.T. 10.75" or "H.S.T. (H.S.T. Registration 895...) 10.75"
    hst = 0
    match = re.search(r'H\.S\.T\.\s*REG\.#\s*86829\s*1980\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    total_electricity_charges = convert_to_float(re.search(r'Total\s*Electricity\s*Charges\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE).group(1).replace(",", ""))
    if match:
        hst = convert_to_float(match.group(1))
    extracted_data["hst"] = round((total_electricity_charges - hst - extracted_data["ontario_electricity_rebate"]) * 0.13, 2)

    # 7) Balance Forward
    # Example snippet: "Last Statement Amount $1,402.18"

    match = re.search(r'Last\s*Statement\s*Amount\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["balance_forward"] += amount_val

    match = re.search(r'Payments\s*since\s*last\s*statement,\s*Thank\s*you\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?',
                      text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["balance_forward"] += amount_val

    match = re.search(r'Customer\s*Transfer\s*Discount\s*\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?',
                      text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["balance_forward"] += amount_val


    extracted_data["balance_forward"] = round(extracted_data["balance_forward"], 2)

    # 8) Period
    # Example snippet: "NOV 07 2024 TO DEC 05 2024"
    pattern = r'([A-Za-z]{3}\s*\d{1,2},\s*\d{4})\s*TO\s*([A-Za-z]{3}\s*\d{1,2},\s*\d{4})'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(1).upper().replace(",", "")
        extracted_data["period_end_date"] = match.group(2).upper().replace(",", "")

    # 9) Late payment charge
    # Example snippet: "TOTAL LATE PENALTIES APPLIED $16.16"
    match = re.search(r'TOTAL\s*LATE\s*PENALTIES\s*APPLIED\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = match.group(1)

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'H\.S\.T\.\s*REG\.#\s*86829\s*1980\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match and extracted_data["amount_due"]:
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