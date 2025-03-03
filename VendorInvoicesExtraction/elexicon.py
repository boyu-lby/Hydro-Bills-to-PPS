import fitz
import re

from OCR_helper import convert_date
from scan_helper import get_month_year, convert_to_float, switch_date_and_month, format_date_str
from datetime import datetime, timedelta


def parse_elexicon_bill(pdf_path):
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
    # Example snippet: "visit ontario.ca/yourelectricitybill.
    # 00051774-03
    match = re.search(r"visit\s*ontario.ca/yourelectricitybill\.\s*(\d{3,10}-?\d{0,3})", text, re.IGNORECASE)
    if match:
        extracted_data["account_number"] = match.group(1).upper()

    # 2) Statement Date
    # Example snippet: "Jan 07 - Feb 07, 2025
    # Feb 25, 2025"
    # If this invoice is unmetered, then there is no read period, only statement is available
    is_unmetered = re.search(r'(Unmetered)', text, re.IGNORECASE)
    if is_unmetered:
        match = re.search(r'([A-Za-z]{3}\s*\d{2},\s*\d{4})', text, re.IGNORECASE)
        if match:
            extracted_data["statement_date"] = match.group(1).replace(",", "")
    else:
        match = re.search(r'[A-Za-z]{3}\s*\d{2}\s*-\s*[A-Za-z]{3}\s*\d{2},\s*\d{4}\s*([A-Za-z]{3}\s*\d{2},\s*\d{4})', text, re.IGNORECASE)
        if match:
            extracted_data["statement_date"] = match.group(1).replace(",", "")

    # 3) Amount Due
    # Example snippet: "Total Account Balance:
    # $180.32
    match = re.search(r'TOTAL\s*Account\s*Balance\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = convert_to_float(match.group(1).replace(",", ""))

    # 4) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate -$7.67"
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = convert_to_float(match.group(1).replace(",", "").replace('$', ''))

    # 9) Late Payment Charge
    # Example snippet: "Interest Charge on Overdue Amount $1.17"
    match = re.search(r"Interest\s*Charge\s*on\s*Overdue\s*Amount\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})", text, re.IGNORECASE)
    if match:
        extracted_data["Late Payment Charge"] = convert_to_float(match.group(1))

    # 5) Total Electricity Charges
    subtotal_text = re.search(r'CURRENT\s*CHARGES\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text,
                              re.IGNORECASE)
    if subtotal_text:
        subtotal_text = subtotal_text.group(1)
    hst_text = re.search(r'H\.S\.T\.\s*\(Registration\s*#\s*88628-2920-RT0001\)\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if subtotal_text and hst_text:
        extracted_data["total_electricity_charges"] = round((convert_to_float(subtotal_text.replace(',', '')) -
                                                             convert_to_float(hst_text.group(1)) - extracted_data[
                                                                 "Late Payment Charge"] - extracted_data["ontario_electricity_rebate"]), 2)

    # 6) H.S.T.
    extracted_data["hst"] = round(extracted_data["total_electricity_charges"] * 0.13, 2)

    # 7) Balance Forward
    # Example snippet: "Balance forward $0.00"
    match = re.search(r'BALANCE\s*FORWARD\s*(-?\$?\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["balance_forward"] = convert_to_float(match.group(1).replace(",", "").replace("$", ""))

    # 8) Period
    if is_unmetered:
        print(extracted_data["statement_date"])
        periods = get_previous_month_range(extracted_data["statement_date"])
        extracted_data["period_start_date"] = periods[0]
        extracted_data["period_end_date"] = periods[1]
    else:
        match = re.search(r"([A-Za-z]{3}\s*\d{2}\s*-\s*[A-Za-z]{3}\s*\d{2},\s*\d{4})", text, re.IGNORECASE)
        if match:
            periods = parse_date_range(match.group(1))
            extracted_data["period_start_date"] = periods[0]
            extracted_data["period_end_date"] = periods[1]

    # 10) Invoice subtotal = amount_due - h.s.t.
    match = re.search(r'H\.S\.T\.\s*\(Registration\s*#\s*88628-2920-RT0001\)\s*\$?(\d{1,3}(?:,\d{3})*\.\d{1,2})', text, re.IGNORECASE)
    if match and extracted_data["amount_due"]:
        hst = convert_to_float(match.group(1))
        extracted_data["invoice_subtotal"] = round(convert_to_float(extracted_data["amount_due"]) - hst, 2)

    # 11) Suggested File Name
    if extracted_data['account_number'] is None or extracted_data['period_start_date'] is None:
        extracted_data["suggested_file_name"] = None
    else:
        extracted_data["suggested_file_name"] = extracted_data['account_number'] + " " + get_month_year(format_date_str(switch_date_and_month(extracted_data["period_start_date"])))

    # Reformat the dates
    extracted_data['statement_date'] = convert_date(extracted_data['statement_date'])

    # Return or print the extracted data
    return extracted_data

def parse_date_range(date_range_str: str):
    """
    Parse a date range string of the form 'MMM DD - MMM DD, YYYY'
    and return two date strings in DD/MM/YYYY format.
    Example:
        Input:  "Dec 07 - Jan 07, 2025"
        Output: ("07/12/2024", "07/01/2025")
    """
    # Map month abbreviations to month numbers
    month_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    # Split the input into left and right parts around the dash
    # e.g. "Dec 07 - Jan 07, 2025" -> left="Dec 07 ", right=" Jan 07, 2025"
    left, right = date_range_str.split('-')
    left = left.strip()  # "Dec 07"
    right = right.strip()  # "Jan 07, 2025"

    # Parse the right part ("Jan 07, 2025")
    #   right_month_str = "Jan"
    #   right_day_str   = "07,"
    #   right_year_str  = "2025"
    right_parts = right.replace(',', '').split()  # ["Jan", "07", "2025"]
    right_month_str, right_day_str, right_year_str = right_parts
    right_month = month_map[right_month_str]
    right_day = int(right_day_str)
    right_year = int(right_year_str)

    # Parse the left part ("Dec 07")
    left_parts = left.split()  # ["Dec", "07"]
    left_month_str, left_day_str = left_parts
    left_month = month_map[left_month_str]
    left_day = int(left_day_str)

    # Determine the year for the left date
    # If left month is greater (later in calendar) than right month,
    # assume the left date is from the previous year.
    if left_month > right_month:
        left_year = right_year - 1
    else:
        left_year = right_year

    # Format both dates in DD/MM/YYYY
    left_date_str = f"{left_day:02d}/{left_month:02d}/{left_year}"
    right_date_str = f"{right_day:02d}/{right_month:02d}/{right_year}"

    return left_date_str, right_date_str


def get_previous_month_range(date_str: str):
    """
    Given a date string in the format 'MMM DD, YYYY',
    return a tuple of strings (start_date_str, end_date_str)
    where:
      - start_date_str is the first day of the previous month (DD/MM/YYYY)
      - end_date_str is the last day of the previous month (DD/MM/YYYY)

    Example:
        Input:  "Feb 09 2024"
        Output: ("01/01/2024", "31/01/2024")
    """
    # Parse the input date string (e.g. "Feb 09, 2024") into a date object
    date_obj = datetime.strptime(date_str, "%b %d %Y").date()

    # Find the first day of the current month
    # For example, if date_obj is 2024-02-09, then current_month_first is 2024-02-01
    current_month_first = date_obj.replace(day=1)

    # Subtract 1 day from the first day of the current month to get the last day of the previous month
    # Using the above example, last_day_prev_month becomes 2024-01-31
    last_day_prev_month = current_month_first - timedelta(days=1)

    # Replace the 'day' component with 1 to get the first day of the previous month
    # So we get first_day_prev_month = 2024-01-01
    first_day_prev_month = last_day_prev_month.replace(day=1)

    # Format both dates in DD/MM/YYYY
    start_date_str = first_day_prev_month.strftime("%d/%m/%Y")
    end_date_str = last_day_prev_month.strftime("%d/%m/%Y")

    return start_date_str, end_date_str