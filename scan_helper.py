import datetime
import os
import shutil
from logging import exception


def convert_to_float(amount_str) -> float:
    """
    Converts a string with commas (e.g., '3,238.41') into a float (e.g., 3238.41).
    Returns None if the conversion fails.
    """
    if isinstance(amount_str, float):
        return amount_str
    elif isinstance(amount_str, int):
        return amount_str
    try:
        # Remove any commas from the string
        clean_str = amount_str.replace(",", "").replace('$', '')
        # Convert to float
        return float(clean_str)
    except ValueError:
        # If there's any error in conversion, return None
        return None

def find_file_with_substring(directory_path, substring):
    """
    Returns the first file name in 'directory_path' that contains 'substring'.
    If no file names match, returns None.
    """
    try:
        # Get a list of all items in the directory
        entries = os.listdir(directory_path)

        # Iterate through each entry
        for entry in entries:
            # Check if the substring is in the file name
            if substring.replace(" ", "") in entry.replace(" ", ""):
                return directory_path +  "\\" + entry  # Return the first match

        # If no match is found
        return None

    except FileNotFoundError:
        print(f"Directory not found: {directory_path}")
        return None
    except PermissionError:
        print(f"Permission denied to access: {directory_path}")
        return None


def copy_as_pdf_in_original_and_destination(
        source_path, destination_path, new_file_name
):
    """
    1. Keeps the original file where it is (unchanged).
    2. Makes a copy in the same (original) folder, but renamed to .pdf.
    3. Also copies that .pdf to the destination folder.

    NOTE: This only renames/copies the file with a .pdf extension; it does not
    perform any actual format conversion to PDF.
    """
    try:
        # Ensure the destination folder exists
        os.makedirs(destination_path, exist_ok=True)

        # Extract original folder from the source path
        original_folder = os.path.dirname(source_path)

        # Make sure we don't accidentally duplicate .pdf
        base_name, _ = os.path.splitext(new_file_name)
        pdf_file_name = base_name + ".pdf"

        # Path for the PDF in the original folder
        pdf_in_original_folder = os.path.join(original_folder, pdf_file_name)

        # 1) Copy from source to a new PDF name in the same (original) folder
        shutil.copy2(source_path, pdf_in_original_folder)
        print(f"Created PDF copy in original folder: {pdf_in_original_folder}")

        # 2) Move that new PDF file into the destination folder
        destination_pdf_path = os.path.join(destination_path, pdf_file_name)

        shutil.move(pdf_in_original_folder, destination_pdf_path)
        print(f"Copied PDF to destination folder: {destination_pdf_path}")

        return destination_pdf_path

    except FileNotFoundError:
        print(f"Source file not found: {source_path}")
        return None
    except PermissionError:
        print(f"Permission error. Cannot access {source_path} or {destination_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def convert_date_from_full(date_str: str) -> str:
    """
    Converts a date string in the format 'MONTH DD, YYYY' (e.g., 'FEBRUARY 03, 2025')
    to 'dd/mm/yyyy' format.

    Parameters:
        date_str (str): Date string in the format 'MONTH DD, YYYY'.

    Returns:
        str: The date in 'dd/mm/yyyy' format.
    """
    # Convert to title case to ensure the month name is correctly formatted (e.g., 'February')
    dt = datetime.datetime.strptime(date_str.title(), "%B %d, %Y")
    return dt.strftime("%d/%m/%Y")


def get_month_year(date_str):
    """
    Takes a date string in 'MMM DD YYYY' format (e.g., 'OCT 31 2024').
    If DD <= 15, return 'MMMYYYY' of the same month/year.
    If DD >= 16, return 'MMMYYYY' of the *next* month/year (rolling over if DEC).
    """
    # Dictionary to map 3-letter month abbreviation to month number
    month_to_num = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }
    # Reverse lookup: map month number to 3-letter abbreviation
    num_to_month = {v: k for k, v in month_to_num.items()}

    # Split the input string into parts
    date_str.replace(',', '')
    month_str, day_str, year_str = date_str.split()
    day = int(day_str)
    year = int(year_str)

    # Convert the month abbreviation to a number (1-12)
    month_num = month_to_num[month_str.upper()]  # Ensure uppercase for safety

    # Decision based on the day
    if day <= 15:
        # Stay in the same month/year
        final_month_num = month_num
        final_year = year
    else:
        # Move to the next month
        final_month_num = month_num + 1
        final_year = year

        # If it was December, roll over to January and increment the year
        if final_month_num == 13:
            final_month_num = 1
            final_year = year + 1

    # Convert back to 3-letter abbreviation
    final_month_str = num_to_month[final_month_num]

    # Return in the format "MMMYYYY", e.g., "OCT2024"
    return f"{final_month_str}{final_year}"

def format_date_str(date_str):
    """
    Converts a date string from "MM/DD/YYYY" format to a string formatted as
    "MON DAY YEAR", where the month is a three-letter uppercase abbreviation.

    Parameters:
        date_str (str): A date string in the format "MM/DD/YYYY", e.g., "10/31/2024".

    Returns:
        str: The formatted date string, e.g., "OCT 31 2024".
    """
    # Parse the date string into a datetime object.
    date_obj = datetime.datetime.strptime(date_str, "%m/%d/%Y")

    # Get the three-letter month abbreviation in uppercase.
    month = date_obj.strftime("%b").upper()
    # Get the day as an integer (this removes any leading zeros).
    day = date_obj.day
    # Get the full year.
    year = date_obj.year

    # Format and return the string.
    return f"{month} {day} {year}"

def self_check(results):
    """
    Check if the sum of various amount match the total, and every mandatory data is extracted
    :param results: the data scanned from invoice
    :return: None
    """
    if results["invoice_subtotal"] != round(float(results["Late Payment Charge"]) + float(results["ontario_electricity_rebate"]) + \
        float(results["balance_forward"]) + float(results["total_electricity_charges"]), 2):
        return False
    for data in results:
        if data is None:
            return False
    return True

def calculate_fiscal_year(date):
    if date[3:5] in ["04", "05", "06", "07", "08", "09", "10", "11", "12"]:
        return date[-4:] + "-" + str(int(date[-4:])+1)[-2:]
    elif date[3:5] in ["01", "02", "03"]:
        return str(int(date[-4:]) - 1)[-4:] + "-" + date[-2:]
    else:
        print("invalid input date")
        return None


def months_to_next_fiscal_period(date_str: str) -> int:
    """
    Given a date string in the format 'MM/DD/YYYY', returns the number of months
    between that date and the next fiscal period. The fiscal periods start in March and September.

    Parameters:
        date_str (str): Date in the format 'MM/DD/YYYY', e.g., '10/31/2024'

    Returns:
        int: The number of whole months until the next fiscal period.
    """
    # Parse the input string into a datetime object.
    dt = datetime.datetime.strptime(date_str, "%d/%m/%Y")
    month = dt.month

    # Determine the next fiscal period and compute the month difference.
    if month < 3:
        # For January or February, next fiscal period is March of the same year.
        return 3 - month
    elif month < 9:
        # For March through August, next fiscal period is September of the same year.
        return 9 - month
    else:
        # For September through December, next fiscal period is March of the next year.
        return 15 - month

def switch_date_and_month(mm_dd):
    if len(mm_dd) > 5:
        return mm_dd[3:5] + mm_dd[2] + mm_dd[:2] + mm_dd[5:]
    return mm_dd[3:5] + mm_dd[2] + mm_dd[:2]