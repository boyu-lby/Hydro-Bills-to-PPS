import fitz
import re
from scan_helper import get_month_year, convert_to_float, format_date_str, switch_date_and_month


def parse_oakville_bill(pdf_path):
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

    # 1) Account Number
    # Example snippet: "Account Number:\n100220-00"
    match = re.search(r'Account\s*Number:\s*(\d{5,8}-\d{0,4})', text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "Account: 100220-00\nFeb 18, 2025"
    match = re.search(r'Account:\s' + extracted_data["account_number"] + '\n([A-Za-z]{3}\s*\d{1,2},\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1)

    # 3) Amount Due
    # Example snippet: "TOTAL AMOUNT DUE\n$361.56"
    match = re.search(r'TOTAL\sAMOUNT\sDUE\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = convert_to_float(match.group(1))
    # Example snippet: "ACCOUNT BALANCE\n$361.56"
    match = re.search(r'ACCOUNT\sBALANCE\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?',
                      text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = convert_to_float(match.group(1))

    # 4) Your Total Electricity Charges
    # Example snippet: "Total Electricity Charges\n$120.70"
    match = re.search(r'Total\s*Electricity\s*Charges\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text,
                      re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = convert_to_float(match.group(1))

    # 5) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 6) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate\n$11.53 CR"
    match = re.search(r'Ontario\s*Electricity\s*Rebate\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})\sCR', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1).replace(", ", "")) * -1

    # 7) Balance Forward
    # Example snippet: "BALANCE FORWARD - Past Due, Please Pay\n$271.17 CR"
    match = re.search(r'BALANCE\sFORWARD\s-\sPast\sDue,\sPlease\sPay\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?', text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["balance_forward"] += amount_val
    # Example snippet: "BALANCE FORWARD \n$271.17 CR"
    match = re.search(r'BALANCE\sFORWARD\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})(\s*CR)?',
                      text, re.IGNORECASE)
    if match:
        amount_val = check_for_cr(match.group(1), match.group(2))
        extracted_data["balance_forward"] += amount_val

    # 8) Period
    match = re.search(r'(\d{2}/\d{2}/\d{4})\n(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(2)[3:6] + match.group(2)[:3] + match.group(2)[6:]
        extracted_data["period_end_date"] = match.group(1)[3:6] + match.group(1)[:3] + match.group(1)[6:]

    # 9) Late payment charge
    # Example snippet: "Total Other Charges\n$0.46"
    match = re.search(r'Total\sOther\sCharges\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))

    # 10) Invoice subtotal = amount_due - h.s.t.
    # Example snippet : "H.S.T. # 869177972\n$11.44"
    match = re.search(r'H\.S\.T\.\s#\s869177972\n\$(\d{1,3}(?:,\d{3})*\.\d{1,2})',
                      text, re.IGNORECASE)
    if match:
        hst = convert_to_float(match.group(1).replace(", ", ""))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

        # 11) Suggested File Name
        if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
            extracted_data["suggested_file_name"] = None
        else:
            extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(
                format_date_str(switch_date_and_month(
                    extracted_data["period_start_date"])))

    return extracted_data