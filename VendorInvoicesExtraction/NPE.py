import pdfplumber
import re
import fitz

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month


def parse_NPE_bill(pdf_path):
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

    # 1) Account Number
    # Example snippet: "MESSAGES:
    match = re.search(r"MESSAGES:\s*\n?(\d{3,9}-?\d{0,2})", text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "REGULAR
    # INTERVAL >50KW
    # 02/21/2025"
    match = re.search(r'REGULAR\n[^\n]*\n(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper().replace(",", "").replace(".", "")

    # 3) Amount Due
    # Example snippet: "Total Amount Due: $168.60"
    match = re.search(r'TOTAL\s*AMOUNT\s*DUE\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = convert_to_float(match.group(1).replace(",", ""))

    # 4) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate -13.67"
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*\$?(-?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1).replace(",", ""))

    # 9) Late Payment Charge
    # Example snippet: "Late Payment Charge 2.84"
    match = re.search(r"Late\s*Payment\s*Charge\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))
    # Example snippet: "Interest Charge 2.84"
    match = re.search(r"Interest\s*Charge\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] += convert_to_float(match.group(1))

    # 5) Total Electricity Charges
    subtotal_text = re.search(r'Electric\s*Charges\s*Sub-total:?\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if subtotal_text:
        subtotal_text = subtotal_text.group(1)
    hst_text = re.search(r'HST\s*\(#R871969127\)\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if subtotal_text and hst_text:
        extracted_data["total_electricity_charges"] = round((convert_to_float(subtotal_text.replace(',', '')) -
                                                             convert_to_float(hst_text.group(1)) - extracted_data["Late Payment Charge"]), 2)

    # 6) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 7) Balance Forward
    # Example snippet: "Balance forward $0.00"
    match = re.search(r'BALANCE\s*FORWARD\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["balance_forward"] = convert_to_float(match.group(1).replace(",", "").replace("$", ""))

    # 8) Period
    # Example snippet: "ELE: 0000064543 02/01/2025
    # 01/01/2025"
    match = re.search(r"ELE:\s*\d{8,12}\s*(\d{2}/\d{2}/\d{4})\n(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(2).upper().replace(",", "")
        extracted_data["period_end_date"] = match.group(1).upper().replace(",", "")

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'HST\s*\(#R871969127\)\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match and extracted_data["amount_due"]:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(
            format_date_str(extracted_data["period_start_date"]))

    # Reformat the dates
    extracted_data['period_start_date'] = switch_date_and_month(extracted_data['period_start_date'])
    extracted_data['period_end_date'] = switch_date_and_month(extracted_data['period_end_date'])
    extracted_data['statement_date'] = switch_date_and_month(extracted_data['statement_date'])

    # Return or print the extracted data
    return extracted_data