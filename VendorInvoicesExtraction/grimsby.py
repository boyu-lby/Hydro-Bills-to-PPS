import pdfplumber
import re

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float


def parse_grimsby_bill(pdf_path):
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

    # 1) Account Number
    # Example snippet: "Account #: Amount Due:
    #                   1008968    $ 104.20"
    match = re.search(r"Amount\s*Due:\s*\n?(\d{7})", text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "Statement Date: Due Date:
    #                   Jan. 08, 2025   Feb. 03, 2025"
    # It usually to appears at first
    match = re.search(r'([A-Za-z]{3}\.\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1).upper().replace(",", "").replace(".", "")

    # 3) Amount Due
    # Example snippet: "Amount Due: $168.60"
    match = re.search(r'Amount\s*Due:\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = float(match.group(1).replace(",", ""))

    # 4) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate -13.67"
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*\$?(-?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = float(match.group(1).replace(",", ""))

    # 5) Total Electricity Charges
    # Example snippet:
    # Electricity
    # Off Peak (305.5900 kWh @ $0.0760/kWh) 23.22
    # Mid Peak (38.6900 kWh @ $0.1220/kWh) 4.72
    # On Peak (59.3700 kWh @ $0.1580/kWh) 9.38
    # Delivery Charges 64.24
    # Regulatory Charges 2.75
    # HST 87249 8225 RT0001 13.56
    # Ontario Electricity Rebate -13.67
    # Subtotal: $104.20
    subtotal_text = re.search(r'Subtotal:?\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE).group(1)
    hst_text = re.search(r'HST\s*864874839RT0001\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE).group(1)
    if subtotal_text:
        extracted_data["total_electricity_charges"] = round((float(subtotal_text.replace(',', '')) -
                                                             float(hst_text) - extracted_data[
                                                                 "ontario_electricity_rebate"]), 2)

    # 6) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 7) Balance Forward
    # Example snippet: "Balance forward $0.00"
    match = re.search(r'Balance\s*Forward\s*From\s*Previous\s*Amount\s*Owing\s*(-?\$\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["balance_forward"] = float(match.group(1).replace(",", "").replace("$", ""))
    match = re.search(r'Balance\s*forward\s*(-?\$\d{1,3}(?:,\d{3})*\.\d{1,2})', text,
                      re.IGNORECASE)
    if match:
        extracted_data["balance_forward"] = float(match.group(1).replace(",", "").replace("$", ""))

    # 8) Period
    # Example snippet: "From: Dec 1, 2024 00:00
    # To: Jan 1, 2025 00:00"
    match1 = re.search(r"From:\s*([A-Za-z]{3}\.?\s*\d{1,2},\s*\d{4})", text, re.IGNORECASE)
    match2 = re.search(r"To:\s*([A-Za-z]{3}\.?\s*\d{1,2},\s*\d{4})", text, re.IGNORECASE)
    if match1:
        extracted_data["period_start_date"] = match1.group(1).upper().replace(",", "")
    if match2:
        extracted_data["period_end_date"] = match2.group(1).upper().replace(",", "")

    # 9) Late Payment Charge
    # Example snippet: "Late Payment Charge 2.84"
    match = re.search(r"Late\s*Payment\s*Charge\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))
    # Example snippet: "Interest Charge 2.84"
    match = re.search(r"Interest\s*Charge\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] += convert_to_float(match.group(1))

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'HST\s*864874839RT0001\s*(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match and extracted_data["amount_due"]:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(
            extracted_data["period_start_date"])

    # Reformat the dates
    extracted_data["period_start_date"] = convert_date(extracted_data["period_start_date"])
    extracted_data["period_end_date"] = convert_date(extracted_data["period_end_date"])
    extracted_data["statement_date"] = convert_date(extracted_data["statement_date"])

    # Return or print the extracted data
    return extracted_data